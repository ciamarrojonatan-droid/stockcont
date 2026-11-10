"""StockCont & DarkFactory — Autonomous Voice Engine (Deepgram Aura TTS).

Provides lightning-fast, studio-grade speech synthesis with zero-RPA friction,
commercial licensing compliance, and Ableton Live 'Complex Pro' tempo matching.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

logger = logging.getLogger("VoiceEngine")

# Default voice catalog with commercial licensing
DEEPGRAM_VOICE_CATALOG = {
    "aura-helios-en": {
        "gender": "male",
        "style": "authoritative_documentary",
        "description": "Deep British baritone, measured cadence, ideal for Nolan/Cold War thrillers.",
    },
    "aura-asteria-en": {
        "gender": "female",
        "style": "dramatic_clear",
        "description": "Crisp dramatic American voice, sharp articulation, high cinematic presence.",
    },
    "aura-arcas-en": {
        "gender": "male",
        "style": "calm_investigative",
        "description": "Calm, resonant baritone, ideal for deep dive investigations and espionage.",
    },
    "aura-zeus-en": {
        "gender": "male",
        "style": "commanding_epic",
        "description": "Commanding, thunderous tone for historical turning points and climaxes.",
    },
    "aura-orpheus-en": {
        "gender": "male",
        "style": "narrative_smooth",
        "description": "Smooth storytelling voice, engaging pacing for long-form video documentaries.",
    },
    "aura-athena-en": {
        "gender": "female",
        "style": "commanding_narrative",
        "description": "Authoritative female voice for strategic analysis and historical narratives.",
    },
    "aura-luna-en": {
        "gender": "female",
        "style": "mysterious_calm",
        "description": "Soft, calm narrative tone for deep space or psychological suspense.",
    },
    "aura-angus-en": {
        "gender": "male",
        "style": "rich_storyteller",
        "description": "Rich Irish/Celtic cadence with natural warmth and dramatic depth.",
    },
}

DEFAULT_DARKFACTORY_VOICE = "aura-helios-en"
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"
AURA_COST_PER_1K_CHARS = 0.015  # USD $0.015 per 1,000 characters


@dataclass
class VoiceSynthesisResult:
    """Result container for synthesized narration."""
    audio_path: Path
    filename: str
    duration_seconds: float
    filesize_bytes: int
    char_count: int
    word_count: int
    estimated_cost_usd: float
    voice_used: str
    subtitles_srt: Optional[str] = None
    subtitles_path: Optional[Path] = None
    is_commercial_licensed: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeepgramVoiceEngine:
    """Autonomous Text-to-Speech Engine using Deepgram Aura REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_voice: str = DEFAULT_DARKFACTORY_VOICE,
        output_dir: Optional[Path | str] = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY", "").strip()
        self.default_voice = default_voice
        self.timeout_seconds = timeout_seconds

        if output_dir:
            self.output_dir = Path(output_dir).resolve()
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.output_dir = base_dir / "data" / "staging" / "narration"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_available(self) -> bool:
        """Check if Deepgram API key is present."""
        return bool(self.api_key and len(self.api_key) > 10)

    @staticmethod
    def estimate_cost(char_count: int) -> float:
        """Calculate estimated cost in USD for Aura-1 models."""
        return round((char_count / 1000.0) * AURA_COST_PER_1K_CHARS, 6)

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        destination_path: Optional[Path | str] = None,
        generate_subtitles: bool = True,
    ) -> VoiceSynthesisResult:
        """Synthesize script to MP3 audio using Deepgram Aura API.

        Args:
            text: Script text to narrate.
            voice: Voice model identifier (e.g. 'aura-helios-en').
            speed: Playback tempo factor (1.0 = normal, 0.9 = slower, 1.1 = faster).
            destination_path: Optional explicit output path.
            generate_subtitles: Whether to generate matching .srt subtitles.

        Returns:
            VoiceSynthesisResult with audio path, duration, size and metadata.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Script text cannot be empty.")

        chosen_voice = voice or self.default_voice
        if chosen_voice not in DEEPGRAM_VOICE_CATALOG:
            logger.warning(
                f"Voice '{chosen_voice}' not in catalog. Falling back to '{self.default_voice}'."
            )
            chosen_voice = self.default_voice

        char_count = len(clean_text)
        word_count = len(clean_text.split())
        est_cost = self.estimate_cost(char_count)

        # Prepare destination file
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:10]
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if destination_path:
            out_file = Path(destination_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            voice_slug = chosen_voice.replace("aura-", "").replace("-en", "")
            out_file = self.output_dir / f"narration_{timestamp}_{voice_slug}_{content_hash}.mp3"

        if not self.is_available:
            raise RuntimeError(
                "DEEPGRAM_API_KEY is not configured in .env or environment."
            )

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StockCont-DarkFactory/3.0",
        }
        url = f"{DEEPGRAM_TTS_URL}?model={chosen_voice}"
        payload = {"text": clean_text}

        logger.info(
            f"Synthesizing voice via Deepgram Aura: {word_count} words ({char_count} chars) | "
            f"Voice: {chosen_voice} | Est. Cost: ${est_cost:.5f}"
        )

        # Execute HTTP POST with retry
        audio_content: Optional[bytes] = None
        for attempt in range(1, 4):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        audio_content = resp.content
                        break
                    elif resp.status_code == 429:
                        wait_sec = attempt * 2.0
                        logger.warning(f"Rate limited (429) by Deepgram. Backoff {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        err_text = resp.text[:300]
                        logger.error(f"Deepgram HTTP {resp.status_code}: {err_text}")
                        raise RuntimeError(f"Deepgram API error ({resp.status_code}): {err_text}")
            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                if attempt == 3:
                    raise RuntimeError(f"Deepgram network connection failure: {net_err}") from net_err
                time.sleep(attempt * 1.5)

        if not audio_content:
            raise RuntimeError("Failed to receive audio content from Deepgram.")

        # Write raw audio atomically (ADR-02)
        tmp_file = out_file.with_suffix(f".tmp.{os.getpid()}{out_file.suffix}")
        with open(tmp_file, "wb") as f:
            f.write(audio_content)

        tmp_file.replace(out_file)

        # Apply speed adjustment if requested via Complex Pro Warp
        final_file = out_file
        if abs(speed - 1.0) > 0.02:
            try:
                from src.video.ffmpeg_processor import time_stretch_audio_complex_pro
                warped_file = out_file.with_name(f"{out_file.stem}_speed{speed:.2f}{out_file.suffix}")
                time_stretch_audio_complex_pro(
                    input_audio_path=out_file,
                    output_audio_path=warped_file,
                    tempo=speed,
                    pitch=1.0,
                    preserve_formants=True,
                )
                final_file = warped_file
            except Exception as e:
                logger.warning(f"Could not apply Complex Pro warp: {e}. Keeping original speed.")

        # Measure duration via ffprobe or estimation
        duration_sec = self._probe_audio_duration(final_file, word_count)
        filesize = final_file.stat().st_size

        # Subtitles generation
        srt_content: Optional[str] = None
        srt_path: Optional[Path] = None
        if generate_subtitles:
            srt_content = self.generate_srt_subtitles(clean_text, duration_sec)
            srt_path = final_file.with_suffix(".srt")
            srt_path.write_text(srt_content, encoding="utf-8")

        result = VoiceSynthesisResult(
            audio_path=final_file,
            filename=final_file.name,
            duration_seconds=round(duration_sec, 2),
            filesize_bytes=filesize,
            char_count=char_count,
            word_count=word_count,
            estimated_cost_usd=est_cost,
            voice_used=chosen_voice,
            subtitles_srt=srt_content,
            subtitles_path=srt_path,
            is_commercial_licensed=True,
            metadata={
                "provider": "deepgram",
                "model": chosen_voice,
                "speed": speed,
                "timestamp": timestamp,
                "license": "Deepgram Commercial PAYG",
            },
        )
        logger.info(
            f"✅ Narration synthesized: {final_file.name} ({duration_sec:.1f}s, {filesize} bytes)"
        )
        return result

    def _probe_audio_duration(self, audio_file: Path, word_count: int) -> float:
        """Probe audio file for duration or estimate fallback."""
        try:
            from src.video.ffmpeg_processor import get_ffprobe_binary
            cmd = [
                get_ffprobe_binary(),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file),
            ]
            import subprocess
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0)
            if res.returncode == 0 and res.stdout.strip():
                return float(res.stdout.strip())
        except Exception:
            pass
        # Human speech average: ~150 words per minute = 2.5 words/sec
        return max(1.0, round(word_count / 2.5, 2))

    @staticmethod
    def generate_srt_subtitles(text: str, total_duration_seconds: float) -> str:
        """Generate high-retention synchronized SRT subtitles from text."""
        # Split text into bite-sized cinematic sentences/phrases (3-8 words each)
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        cues: List[str] = []
        for s in sentences:
            words = s.split()
            if len(words) > 10:
                mid = len(words) // 2
                cues.append(" ".join(words[:mid]))
                cues.append(" ".join(words[mid:]))
            elif words:
                cues.append(" ".join(words))

        if not cues:
            return ""

        total_words = sum(len(c.split()) for c in cues) or 1
        time_per_word = total_duration_seconds / total_words

        srt_blocks: List[str] = []
        current_time = 0.0

        def _fmt(sec: float) -> str:
            hrs = int(sec // 3600)
            mins = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int((sec - int(sec)) * 1000)
            return f"{hrs:02d}:{mins:02d}:{s:02d},{ms:03d}"

        for idx, cue in enumerate(cues, start=1):
            cue_words = len(cue.split())
            cue_duration = max(1.2, cue_words * time_per_word)
            start_time = current_time
            end_time = min(total_duration_seconds, start_time + cue_duration)
            current_time = end_time

            srt_blocks.append(
                f"{idx}\n{_fmt(start_time)} --> {_fmt(end_time)}\n{cue}\n"
            )

        return "\n".join(srt_blocks)
