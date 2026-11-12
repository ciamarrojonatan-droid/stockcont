"""StockCont & DarkFactory — Word-Timed Voice Aligner & Trigger Extractor.

Extracts exact audio durations, detects spoken energy islands, aligns transcripts
word-by-word (supporting optional faster-whisper with deterministic RMS/syllabic
forced-alignment fallback), generates SRT captions, and emits timestamped
overlay/map/stamp trigger events tied to spoken keywords.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.video.ffmpeg_processor import decode_audio_pcm_mono, probe_audio_duration

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.voice_aligner")

DEFAULT_TRIGGER_KEYWORDS: Tuple[str, ...] = (
    "classified",
    "declassified",
    "1983",
    "radar",
    "bunker",
    "missile",
    "nuclear",
    "serpukhov",
    "norad",
    "map",
    "corridor",
    "protocol",
    "top secret",
)


def _atomic_write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text atomically via temporary file + replace() (ADR-02)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return path


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def _syllable_weight(token: str) -> float:
    cleaned = _normalize_token(token)
    if not cleaned:
        return 1.0
    vowels = re.findall(r"[aeiouy]+", cleaned)
    return float(max(1, len(vowels), min(5, round(len(cleaned) / 3.2))))


def _format_srt_ts(sec: float) -> str:
    clamped = max(0.0, float(sec))
    hrs = int(clamped // 3600)
    mins = int((clamped % 3600) // 60)
    secs = int(clamped % 60)
    ms = int(round((clamped - int(clamped)) * 1000.0))
    if ms >= 1000:
        secs += 1
        ms -= 1000
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


@dataclass
class WordTiming:
    """Single word timing interval on the narration timeline."""

    word: str
    start_sec: float
    end_sec: float
    confidence: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WordTriggerEvent:
    """Visual/audio cue anchored to a spoken keyword timestamp."""

    keyword: str
    matched_word: str
    timestamp_sec: float
    end_sec: float
    action_type: str  # "stamp" | "map_pin" | "lower_third" | "sfx"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VoiceAlignmentResult:
    """Complete alignment output including word intervals, SRT captions, and triggers."""

    audio_path: str
    duration_sec: float
    backend_used: str
    speech_islands: List[Tuple[float, float]] = field(default_factory=list)
    word_timings: List[WordTiming] = field(default_factory=list)
    word_triggers: List[WordTriggerEvent] = field(default_factory=list)
    srt_content: str = ""
    subtitles_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VoiceAligner:
    """Aligns spoken narration audio to transcript words and visual trigger events."""

    def detect_speech_islands(
        self,
        samples: np.ndarray,
        sample_rate: int,
        frame_ms: int = 20,
        hop_ms: int = 10,
        min_silence_sec: float = 0.18,
        min_island_sec: float = 0.08,
    ) -> List[Tuple[float, float]]:
        """Segment audio into contiguous speech activity intervals using RMS energy."""
        if len(samples) == 0 or sample_rate <= 0:
            return []

        duration = len(samples) / float(sample_rate)
        frame_len = max(32, int(sample_rate * frame_ms / 1000.0))
        hop_len = max(16, int(sample_rate * hop_ms / 1000.0))

        rms: List[float] = []
        times: List[float] = []
        for start in range(0, max(1, len(samples) - frame_len + 1), hop_len):
            seg = samples[start : start + frame_len]
            rms.append(float(np.sqrt(np.mean(seg * seg))))
            times.append(start / float(sample_rate))

        if not rms:
            return [(0.0, round(duration, 3))]

        rms_arr = np.asarray(rms, dtype=np.float32)
        peak = float(np.max(rms_arr))
        if peak <= 1e-5:
            return [(0.0, round(duration, 3))]

        noise_floor = float(np.percentile(rms_arr, 15))
        threshold = max(0.012, noise_floor * 2.2, peak * 0.08)

        active = rms_arr >= threshold
        raw_spans: List[Tuple[float, float]] = []
        in_span = False
        span_start = 0.0
        for idx, is_active in enumerate(active):
            t_cur = times[idx]
            if is_active and not in_span:
                in_span = True
                span_start = t_cur
            elif not is_active and in_span:
                in_span = False
                raw_spans.append((span_start, min(duration, t_cur + frame_ms / 1000.0)))
        if in_span:
            raw_spans.append((span_start, duration))

        if not raw_spans:
            return [(0.0, round(duration, 3))]

        merged: List[Tuple[float, float]] = [raw_spans[0]]
        for s_start, s_end in raw_spans[1:]:
            prev_start, prev_end = merged[-1]
            if s_start - prev_end <= min_silence_sec:
                merged[-1] = (prev_start, max(prev_end, s_end))
            else:
                merged.append((s_start, s_end))

        filtered = [
            (round(s, 3), round(e, 3))
            for s, e in merged
            if (e - s) >= min_island_sec
        ]
        return filtered or [(0.0, round(duration, 3))]

    @staticmethod
    def _try_whisper_word_alignment(audio_path: Path) -> Optional[List[WordTiming]]:
        """Use faster-whisper if installed in the environment; return None otherwise."""
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError:
            return None

        try:
            model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(str(audio_path), word_timestamps=True)
            words: List[WordTiming] = []
            for seg in segments:
                for w in getattr(seg, "words", None) or []:
                    token = str(getattr(w, "word", "")).strip()
                    if token:
                        words.append(
                            WordTiming(
                                word=token,
                                start_sec=round(float(w.start), 3),
                                end_sec=round(float(w.end), 3),
                                confidence=round(float(getattr(w, "probability", 0.9)), 3),
                            )
                        )
            return words or None
        except Exception as exc:
            logger.warning("faster-whisper alignment skipped (%s); using energy aligner.", exc)
            return None

    def _align_words_to_islands(
        self,
        tokens: List[str],
        islands: List[Tuple[float, float]],
    ) -> List[WordTiming]:
        """Distribute words proportionally by syllable weight across active speech islands."""
        if not tokens:
            return []

        if not islands:
            return [
                WordTiming(word=tok, start_sec=round(i * 0.4, 3), end_sec=round((i + 1) * 0.4, 3), confidence=0.6)
                for i, tok in enumerate(tokens)
            ]

        weights = [_syllable_weight(tok) for tok in tokens]
        total_weight = sum(weights) or 1.0
        island_durations = [max(0.05, end - start) for start, end in islands]
        total_speech_sec = sum(island_durations) or 1.0

        # Map each token's cumulative syllable span onto the concatenated speech timeline
        timings: List[WordTiming] = []
        cum_weight = 0.0
        for tok, w in zip(tokens, weights):
            speech_start = (cum_weight / total_weight) * total_speech_sec
            cum_weight += w
            speech_end = (cum_weight / total_weight) * total_speech_sec

            abs_start = self._map_speech_pos_to_audio_time(speech_start, islands, island_durations)
            abs_end = self._map_speech_pos_to_audio_time(speech_end, islands, island_durations)
            if abs_end <= abs_start:
                abs_end = round(abs_start + 0.08, 3)

            timings.append(
                WordTiming(
                    word=tok,
                    start_sec=round(abs_start, 3),
                    end_sec=round(abs_end, 3),
                    confidence=0.82,
                )
            )
        return timings

    @staticmethod
    def _map_speech_pos_to_audio_time(
        speech_pos_sec: float,
        islands: List[Tuple[float, float]],
        island_durations: List[float],
    ) -> float:
        remaining = max(0.0, speech_pos_sec)
        for (start, end), dur in zip(islands, island_durations):
            if remaining <= dur + 1e-6:
                return min(end, start + remaining)
            remaining -= dur
        return islands[-1][1]

    @staticmethod
    def build_srt_from_word_timings(
        word_timings: Sequence[WordTiming],
        max_words_per_cue: int = 7,
        pause_break_sec: float = 0.30,
    ) -> str:
        """Group word timings into readable SRT subtitle blocks broken on pauses/punctuation."""
        if not word_timings:
            return ""

        groups: List[List[WordTiming]] = []
        current: List[WordTiming] = []
        for wt in word_timings:
            if current:
                gap = wt.start_sec - current[-1].end_sec
                ends_sentence = current[-1].word.rstrip().endswith((".", "!", "?", ";"))
                if len(current) >= max_words_per_cue or gap >= pause_break_sec or ends_sentence:
                    groups.append(current)
                    current = []
            current.append(wt)
        if current:
            groups.append(current)

        blocks: List[str] = []
        for idx, grp in enumerate(groups, start=1):
            start_ts = _format_srt_ts(grp[0].start_sec)
            end_ts = _format_srt_ts(max(grp[-1].end_sec, grp[0].start_sec + 0.25))
            line = " ".join(item.word for item in grp)
            blocks.append(f"{idx}\n{start_ts} --> {end_ts}\n{line}\n")
        return "\n".join(blocks)

    @staticmethod
    def extract_word_triggers(
        word_timings: Sequence[WordTiming],
        trigger_keywords: Optional[Sequence[str]] = None,
    ) -> List[WordTriggerEvent]:
        """Match spoken tokens against trigger keywords and classify overlay action types."""
        keywords = list(trigger_keywords) if trigger_keywords is not None else list(DEFAULT_TRIGGER_KEYWORDS)
        norm_keywords = [(_normalize_token(k), k) for k in keywords if _normalize_token(k)]
        triggers: List[WordTriggerEvent] = []
        seen_pairs: set[Tuple[str, float]] = set()

        for wt in word_timings:
            tok_norm = _normalize_token(wt.word)
            if not tok_norm:
                continue
            for kw_norm, kw_raw in norm_keywords:
                if kw_norm == tok_norm or (len(kw_norm) >= 4 and kw_norm in tok_norm):
                    key = (kw_raw.lower(), wt.start_sec)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    action = "stamp"
                    if any(m in kw_norm for m in ("map", "corridor", "serpukhov", "norad")):
                        action = "map_pin"
                    elif any(m in kw_norm for m in ("198", "199", "197", "196", "protocol")):
                        action = "lower_third"
                    triggers.append(
                        WordTriggerEvent(
                            keyword=kw_raw,
                            matched_word=wt.word,
                            timestamp_sec=wt.start_sec,
                            end_sec=wt.end_sec,
                            action_type=action,
                        )
                    )
        return triggers

    def align_transcript(
        self,
        audio_path: Path | str,
        transcript: str,
        trigger_keywords: Optional[Sequence[str]] = None,
        use_whisper: bool = False,
        save_srt: bool = True,
        srt_output_path: Optional[Path | str] = None,
    ) -> VoiceAlignmentResult:
        """Probe audio duration, align words to spoken audio, write SRT, and emit trigger cues."""
        src = Path(audio_path).resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Narration audio file not found: {src}")

        clean_text = (transcript or "").strip()
        tokens = clean_text.split()
        duration_sec = probe_audio_duration(src, fallback_word_count=max(1, len(tokens)))

        samples, sr = decode_audio_pcm_mono(src, target_sr=16000)
        islands = self.detect_speech_islands(samples, sr)

        word_timings: Optional[List[WordTiming]] = None
        backend = "energy_syllabic_aligner"
        if use_whisper:
            whisper_words = self._try_whisper_word_alignment(src)
            if whisper_words:
                word_timings = whisper_words
                backend = "faster_whisper"

        if word_timings is None:
            word_timings = self._align_words_to_islands(tokens, islands)

        srt_content = self.build_srt_from_word_timings(word_timings)
        srt_path: Optional[Path] = None
        if save_srt and srt_content:
            srt_path = Path(srt_output_path).resolve() if srt_output_path else src.with_suffix(".srt")
            _atomic_write_text(srt_path, srt_content)

        triggers = self.extract_word_triggers(word_timings, trigger_keywords=trigger_keywords)

        return VoiceAlignmentResult(
            audio_path=src.as_posix(),
            duration_sec=duration_sec,
            backend_used=backend,
            speech_islands=islands,
            word_timings=word_timings,
            word_triggers=triggers,
            srt_content=srt_content,
            subtitles_path=srt_path.as_posix() if srt_path else None,
        )
