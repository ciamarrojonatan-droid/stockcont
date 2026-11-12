"""StockCont & DarkFactory — Kinetic Word-Timed Caption Engine (Sprint 10).

Synchronizes word-by-word karaoke / Hormozi pop / terminal captions directly from
`VoiceAligner` `WordTiming` telemetry inside 9:16 social UI safe-zones (YouTube Shorts,
TikTok, Instagram Reels), preventing bottom-bar or right-rail UI collisions.
"""

from __future__ import annotations

import functools
import logging
import math
import os
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video
from src.video.motion_qa import PLATFORM_SAFE_ZONES, MotionQAInspector, OverlayPlacement

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.kinetic_captions")

CAPTION_STYLES: Dict[str, Dict[str, Any]] = {
    "editorial_karaoke": {
        "highlight_rgb": (245, 158, 11),
        "text_rgb": (248, 250, 252),
        "pill_rgba": (9, 14, 24, 215),
        "max_words": 4,
        "uppercase": False,
        "description": "Balanced documentary karaoke highlight with slate backdrop.",
    },
    "hormozi_pop": {
        "highlight_rgb": (56, 189, 248),
        "text_rgb": (255, 255, 255),
        "pill_rgba": (6, 10, 18, 232),
        "max_words": 3,
        "uppercase": True,
        "description": "High-contrast 2-3 word punchy vertical hook captions.",
    },
    "terminal_typewriter": {
        "highlight_rgb": (16, 185, 129),
        "text_rgb": (209, 250, 229),
        "pill_rgba": (4, 16, 12, 226),
        "max_words": 4,
        "uppercase": True,
        "description": "Monospace classified dossier readout with progressive word cursor.",
    },
}


@dataclass
class CaptionPhraseSegment:
    """Short 2-4 word rhythmic subtitle phrase synchronized to audio words."""

    index: int
    start_sec: float
    end_sec: float
    text: str
    words: List[Dict[str, Any]] = field(default_factory=list)
    highlighted_keyword: Optional[str] = None
    y_norm: float = 0.62

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KineticCaptionResult:
    """Output contract of kinetic subtitle generation and burn-in composition."""

    success: bool
    style: str
    phrase_count: int
    word_count: int
    video_path: Optional[str] = None
    ass_path: Optional[str] = None
    safe_zone_profile: str = "youtube_shorts"
    safe_zone_box: Dict[str, float] = field(default_factory=dict)
    overlap_audit: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _atomic_write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(content)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


@functools.lru_cache(maxsize=32)
def _load_caption_font(size: int, monospace: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            "C:/Windows/Fonts/consolab.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        ]
        if monospace
        else [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    )
    for cand in candidates:
        try:
            return ImageFont.truetype(cand, size=max(14, int(size)))
        except OSError:
            continue
    return ImageFont.load_default()


def _format_ass_ts(sec: float) -> str:
    total_cs = max(0, int(round(float(sec) * 100.0)))
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _coerce_word_dict(item: Any) -> Optional[Dict[str, Any]]:
    if hasattr(item, "to_dict"):
        d = item.to_dict()
    elif isinstance(item, dict):
        d = dict(item)
    else:
        return None
    word = str(d.get("word", "")).strip()
    if not word:
        return None
    start = float(d.get("start_sec", 0.0))
    end = max(start + 0.06, float(d.get("end_sec", start + 0.25)))
    return {"word": word, "start_sec": start, "end_sec": end}


class KineticCaptionEngine:
    """Renders word-synced kinetic captions respecting vertical platform UI safe-zones."""

    # Safe vertical subtitle bounding box: clears 22% bottom meta, 16% right rail, 9% top header.
    DEFAULT_SAFE_BOX: Tuple[float, float, float, float] = (0.06, 0.61, 0.76, 0.12)

    @staticmethod
    def _validate_style(style: str) -> str:
        key = (style or "editorial_karaoke").strip().lower()
        if key not in CAPTION_STYLES:
            raise ValueError(f"Unknown caption style '{style}'. Valid: {sorted(CAPTION_STYLES)}")
        return key

    @staticmethod
    def timings_from_script(script: str, total_duration_sec: float) -> List[Dict[str, Any]]:
        """Synthesize even word-timing entries when raw audio alignment is unavailable."""
        tokens = [t for t in re.findall(r"\S+", script or "") if t.strip()]
        if not tokens:
            return []
        dur = max(0.5, float(total_duration_sec))
        weights = [max(1, len(re.sub(r"[^a-zA-Z0-9]", "", tok))) for tok in tokens]
        total_w = max(1, sum(weights))
        cursor = 0.05
        avail = max(0.3, dur - 0.10)
        timings: List[Dict[str, Any]] = []
        for tok, w in zip(tokens, weights):
            span = avail * (w / total_w)
            timings.append(
                {
                    "word": tok,
                    "start_sec": round(cursor, 3),
                    "end_sec": round(min(dur, cursor + max(0.08, span)), 3),
                }
            )
            cursor += span
        return timings

    def build_phrase_segments(
        self,
        word_timings: Iterable[Any],
        max_words_per_phrase: Optional[int] = None,
        trigger_keywords: Optional[Iterable[str]] = None,
        style: str = "editorial_karaoke",
    ) -> List[CaptionPhraseSegment]:
        """Group word timings into crisp 2-4 word phrases breaking naturally on punctuation."""
        style_key = self._validate_style(style)
        limit = max(2, int(max_words_per_phrase or CAPTION_STYLES[style_key]["max_words"]))
        kw_set = {k.strip().lower() for k in (trigger_keywords or []) if k.strip()}

        normalized: List[Dict[str, Any]] = []
        for raw in word_timings:
            coerced = _coerce_word_dict(raw)
            if coerced is not None:
                normalized.append(coerced)
        if not normalized:
            return []

        phrases: List[CaptionPhraseSegment] = []
        buf: List[Dict[str, Any]] = []
        for idx, wd in enumerate(normalized):
            buf.append(wd)
            pause_after = (
                idx + 1 < len(normalized)
                and (normalized[idx + 1]["start_sec"] - wd["end_sec"]) > 0.35
            )
            ends_punct = wd["word"].endswith((".", "!", "?", ",", ";", ":"))
            if len(buf) >= limit or pause_after or ends_punct or idx == len(normalized) - 1:
                text = " ".join(x["word"] for x in buf)
                if CAPTION_STYLES[style_key]["uppercase"]:
                    text = text.upper()
                matched_kw = next(
                    (
                        x["word"]
                        for x in buf
                        if re.sub(r"[^a-zA-Z0-9_-]", "", x["word"]).lower() in kw_set
                    ),
                    None,
                )
                phrases.append(
                    CaptionPhraseSegment(
                        index=len(phrases) + 1,
                        start_sec=round(buf[0]["start_sec"], 3),
                        end_sec=round(buf[-1]["end_sec"], 3),
                        text=text,
                        words=list(buf),
                        highlighted_keyword=matched_kw,
                    )
                )
                buf = []
        return phrases

    def generate_ass_subtitles(
        self,
        segments: List[CaptionPhraseSegment],
        output_ass_path: str | Path,
        width: int = 1080,
        height: int = 1920,
        style: str = "editorial_karaoke",
    ) -> Path:
        """Write atomic UTF-8 ASS karaoke subtitle script compatible with FFmpeg and NLEs."""
        style_key = self._validate_style(style)
        spec = CAPTION_STYLES[style_key]
        r, g, b = spec["highlight_rgb"]
        # ASS uses BGR hex
        ass_hl = f"&H00{b:02X}{g:02X}{r:02X}"
        margin_v = int(height * 0.28)  # Stay strictly above bottom 22% mobile HUD
        margin_r = int(width * 0.18)   # Clear right engagement rail

        header = "\n".join(
            [
                "[Script Info]",
                "ScriptType: v4.00+",
                f"PlayResX: {int(width)}",
                f"PlayResY: {int(height)}",
                "ScaledBorderAndShadow: yes",
                "",
                "[V4+ Styles]",
                (
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
                    "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
                    "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
                ),
                (
                    f"Style: Kinetic,Arial,{max(36, int(width * 0.048))},&H00F8FAFC,{ass_hl},"
                    f"&H00120E09,&HAA080D18,-1,0,0,0,100,100,0,0,3,3,0,2,48,{margin_r},{margin_v},1"
                ),
                "",
                "[Events]",
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            ]
        )

        events: List[str] = []
        for seg in segments:
            k_tokens: List[str] = []
            for wd in seg.words:
                dur_cs = max(8, int(round((wd["end_sec"] - wd["start_sec"]) * 100)))
                raw_tok = re.sub(r"[{}\r\n\\]+", " ", str(wd.get("word", ""))).strip()
                txt = raw_tok.upper() if spec["uppercase"] else raw_tok
                if txt:
                    k_tokens.append(f"{{\\k{dur_cs}}}{txt}")
            events.append(
                f"Dialogue: 0,{_format_ass_ts(seg.start_sec)},{_format_ass_ts(seg.end_sec)},"
                f"Kinetic,,0,0,0,,{' '.join(k_tokens)}"
            )

        out_path = Path(output_ass_path)
        _atomic_write_utf8(out_path, header + "\n" + "\n".join(events) + "\n")
        return out_path

    def draw_caption_on_frame(
        self,
        frame_bgr: np.ndarray,
        time_sec: float,
        segments: List[CaptionPhraseSegment],
        style: str = "editorial_karaoke",
    ) -> np.ndarray:
        """Composite word-highlighted caption pill cleanly inside vertical UI safe-zones."""
        style_key = self._validate_style(style)
        active = next(
            (s for s in segments if s.start_sec - 0.04 <= time_sec <= s.end_sec + 0.08),
            None,
        )
        if active is None or not active.words:
            return frame_bgr

        spec = CAPTION_STYLES[style_key]
        h, w = frame_bgr.shape[:2]
        x_norm, y_norm, box_w_norm, _ = self.DEFAULT_SAFE_BOX
        max_pill_w = int(w * box_w_norm)
        center_x = int(w * (x_norm + box_w_norm * 0.5))
        base_y = int(h * y_norm)

        font_size = max(18, int(min(w, h) * (0.046 if w < h else 0.042)))
        font = _load_caption_font(font_size, monospace=(style_key == "terminal_typewriter"))

        # Render RGBA caption plate using Pillow for crisp typography and alpha pill
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        display_words: List[Tuple[str, bool, bool]] = []
        for wd in active.words:
            txt = wd["word"].upper() if spec["uppercase"] else wd["word"]
            is_spoken = wd["start_sec"] - 0.03 <= time_sec <= wd["end_sec"] + 0.04
            already_seen = time_sec >= wd["start_sec"] - 0.03
            if style_key == "terminal_typewriter" and not already_seen:
                continue
            display_words.append((txt, is_spoken, already_seen))

        if not display_words:
            display_words = [(active.words[0]["word"].upper() if spec["uppercase"] else active.words[0]["word"], True, True)]

        space_w = max(6, int(font_size * 0.32))
        word_boxes: List[Tuple[str, int, int, bool]] = []
        total_text_w = 0
        max_text_h = font_size + 6
        for idx, (txt, is_spoken, _) in enumerate(display_words):
            bbox = draw.textbbox((0, 0), txt, font=font)
            tw = max(10, bbox[2] - bbox[0])
            th = max(font_size, bbox[3] - bbox[1])
            word_boxes.append((txt, tw, th, is_spoken))
            total_text_w += tw + (space_w if idx > 0 else 0)
            max_text_h = max(max_text_h, th)

        # Clamp pill width cleanly within 9:16 left-safe lane (clearing right engagement rail)
        pad_x = max(14, int(font_size * 0.55))
        pad_y = max(8, int(font_size * 0.30))
        pill_w = min(max_pill_w, total_text_w + 2 * pad_x)
        pill_h = min(int(h * 0.12), max_text_h + 2 * pad_y)
        px1 = max(int(w * 0.04), min(int(w * 0.82) - pill_w, center_x - pill_w // 2))
        px2 = px1 + pill_w
        py1 = base_y
        py2 = min(int(h * 0.75), py1 + pill_h)

        radius = max(8, pill_h // 5)
        draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=radius, fill=spec["pill_rgba"])

        # Subtle pop indicator bar during hormozi_pop
        if style_key == "hormozi_pop":
            pop = 0.5 + 0.5 * math.sin(time_sec * 10.0)
            border_rgba = (*spec["highlight_rgb"], int(170 + 70 * pop))
            draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=radius, outline=border_rgba, width=2)

        cursor_x = px1 + max(pad_x, (pill_w - total_text_w) // 2)
        text_y = py1 + max(4, (py2 - py1 - max_text_h) // 2)
        for txt, tw, _, is_spoken in word_boxes:
            if cursor_x + tw > px2 - 8:
                break
            fill_rgb = spec["highlight_rgb"] if is_spoken else spec["text_rgb"]
            draw.text((cursor_x, text_y), txt, fill=(*fill_rgb, 255), font=font)
            cursor_x += tw + space_w

        base_rgba = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
        composed = Image.alpha_composite(base_rgba, overlay).convert("RGB")
        return cv2.cvtColor(np.array(composed), cv2.COLOR_RGB2BGR)

    def render_captioned_video(
        self,
        input_video_path: str | Path,
        output_video_path: str | Path,
        word_timings: Iterable[Any],
        style: str = "editorial_karaoke",
        safe_zone_profile: str = "youtube_shorts",
        trigger_keywords: Optional[Iterable[str]] = None,
        audio_path: Optional[str | Path] = None,
    ) -> KineticCaptionResult:
        """Burn word-timed kinetic subtitles into video and audit UI safe-zone clearance."""
        style_key = self._validate_style(style)
        zone_key = (safe_zone_profile or "youtube_shorts").strip().lower()
        if zone_key not in PLATFORM_SAFE_ZONES:
            raise ValueError(
                f"Unknown safe_zone_profile '{safe_zone_profile}'. Valid: {sorted(PLATFORM_SAFE_ZONES)}"
            )
        src = Path(input_video_path)
        if not src.is_file():
            return KineticCaptionResult(
                success=False,
                style=style_key,
                phrase_count=0,
                word_count=0,
                safe_zone_profile=safe_zone_profile,
                error=f"Input video not found: {src}",
            )

        out_path = Path(output_video_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        props = probe_video(src)
        segments = self.build_phrase_segments(
            word_timings=word_timings,
            trigger_keywords=trigger_keywords,
            style=style_key,
        )
        ass_path = self.generate_ass_subtitles(
            segments=segments,
            output_ass_path=out_path.with_suffix(".ass"),
            width=props.width,
            height=props.height,
            style=style_key,
        )

        x_norm, y_norm, w_norm, h_norm = self.DEFAULT_SAFE_BOX
        audit = MotionQAInspector().audit_overlay_overlaps(
            placements=[
                OverlayPlacement(
                    overlay_id="kinetic_captions",
                    label=f"Kinetic Captions ({style_key})",
                    start_sec=0.0,
                    end_sec=max(0.5, float(props.duration_seconds)),
                    x=x_norm,
                    y=y_norm,
                    width=w_norm,
                    height=h_norm,
                )
            ],
            total_duration_sec=max(0.5, float(props.duration_seconds)),
            step_sec=0.5,
            canvas_width=props.width,
            canvas_height=props.height,
            safe_zone_profile=safe_zone_profile,
        )

        audio_src = Path(audio_path) if audio_path else None
        keep_audio = bool(audio_src and audio_src.is_file()) or props.has_audio

        cmd: List[str] = [
            get_ffmpeg_binary(),
            "-y",
            "-v",
            "error",
            "-nostats",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{props.width}x{props.height}",
            "-pix_fmt",
            "bgr24",
            "-r",
            f"{props.fps:.3f}",
            "-i",
            "-",
        ]
        if audio_src and audio_src.is_file():
            cmd.extend(["-i", audio_src.as_posix(), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-shortest"])
        elif props.has_audio:
            cmd.extend(["-i", src.as_posix(), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-shortest"])
        else:
            cmd.append("-an")

        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                out_path.as_posix(),
            ]
        )

        cap = cv2.VideoCapture(str(src))
        proc: Optional[subprocess.Popen[bytes]] = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            assert proc.stdin is not None
            fps_val = max(1.0, float(props.fps))
            max_frames = max(2, int(round(max(1.0, float(props.duration_seconds)) * fps_val)) + 60)
            frame_idx = 0
            while frame_idx < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame.shape[1] != props.width or frame.shape[0] != props.height:
                    frame = cv2.resize(frame, (props.width, props.height), interpolation=cv2.INTER_AREA)
                t_sec = frame_idx / fps_val
                rendered = self.draw_caption_on_frame(frame, time_sec=t_sec, segments=segments, style=style_key)
                proc.stdin.write(rendered.tobytes())
                frame_idx += 1

            proc.stdin.close()
            stderr_bytes = proc.stderr.read() if proc.stderr else b""
            proc.wait(timeout=180)
            if proc.returncode != 0 or not out_path.is_file() or out_path.stat().st_size == 0:
                err_txt = stderr_bytes.decode("utf-8", errors="replace")[-400:]
                return KineticCaptionResult(
                    success=False,
                    style=style_key,
                    phrase_count=len(segments),
                    word_count=sum(len(s.words) for s in segments),
                    ass_path=ass_path.as_posix(),
                    safe_zone_profile=safe_zone_profile,
                    overlap_audit=audit.to_dict(),
                    error=f"FFmpeg exited {proc.returncode}: {err_txt}",
                )
        except Exception as exc:
            logger.warning("Kinetic caption render failed: %s", exc)
            return KineticCaptionResult(
                success=False,
                style=style_key,
                phrase_count=len(segments),
                word_count=sum(len(s.words) for s in segments),
                ass_path=ass_path.as_posix(),
                safe_zone_profile=safe_zone_profile,
                overlap_audit=audit.to_dict(),
                error=str(exc),
            )
        finally:
            cap.release()
            if proc is not None:
                if proc.stdin and not proc.stdin.closed:
                    try:
                        proc.stdin.close()
                    except OSError:
                        pass
                if proc.poll() is None:
                    proc.kill()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        pass

        return KineticCaptionResult(
            success=out_path.is_file() and out_path.stat().st_size > 0,
            style=style_key,
            phrase_count=len(segments),
            word_count=sum(len(s.words) for s in segments),
            video_path=out_path.as_posix(),
            ass_path=ass_path.as_posix(),
            safe_zone_profile=safe_zone_profile,
            safe_zone_box={"x": x_norm, "y": y_norm, "width": w_norm, "height": h_norm},
            overlap_audit=audit.to_dict(),
        )
