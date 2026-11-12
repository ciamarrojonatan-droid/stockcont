"""StockCont & DarkFactory — Vertical 9:16 Shorts Repurposer & Microstock B-Roll Funnel (Sprint 10).

Converts 16:9 documentary masters or standalone scripts into vertical 9:16 Reels/Shorts
with salience-guided horizontal framing, word-synced kinetic captions inside mobile
UI safe-zones, and parallel clean muted (-an) vertical B-roll exports with ADR-05 Alamy protection.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.cataloger.platform_compliance import PLATFORM_RULES
from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_audio_duration, probe_video
from src.video.hyperframes_engine import HyperFramesMotionEngine
from src.video.kinetic_captions import KineticCaptionEngine
from src.video.motion_qa import PLATFORM_SAFE_ZONES
from src.video.promo_motion_director import PromoMotionDirector
from src.video.voice_aligner import VoiceAligner

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.shorts_repurposer")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SHORTS_DIR = BASE_DIR / "data" / "final" / "shorts"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")[:64] or "short_clip"


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


@dataclass
class ShortsRepurposeResult:
    """Complete output contract of a 9:16 Shorts & microstock repurpose run."""

    success: bool
    title: str
    style: str
    safe_zone_profile: str
    short_video_path: Optional[str] = None
    ass_path: Optional[str] = None
    stock_broll_path: Optional[str] = None
    stock_broll_muted: bool = True
    manifest_path: Optional[str] = None
    width: int = 1080
    height: int = 1920
    duration_sec: float = 0.0
    window_start_sec: float = 0.0
    window_end_sec: float = 0.0
    salient_center_x: float = 0.5
    safe_zone_passed: bool = False
    alamy_blocked: bool = True
    eligible_agencies: List[str] = field(default_factory=list)
    overlap_audit: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ShortsRepurposerEngine:
    """Repurposes 16:9 episodes or generates vertical 9:16 Shorts + clean microstock B-roll."""

    def __init__(self, output_dir: Optional[str | Path] = None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_SHORTS_DIR
        self.caption_engine = KineticCaptionEngine()

    @staticmethod
    def detect_salient_center_x(
        video_path: str | Path,
        start_sec: float = 0.0,
        window_sec: float = 10.0,
        samples: int = 6,
    ) -> float:
        """Compute normalized horizontal energy centroid [0.25..0.75] for smart 9:16 cropping."""
        src = Path(video_path)
        if not src.is_file():
            return 0.5

        cap = cv2.VideoCapture(str(src))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
            total_dur = frame_count / max(1.0, fps)
            if total_dur <= 0.05:
                return 0.5

            s0 = max(0.0, min(start_sec, max(0.0, total_dur - 0.5)))
            s1 = min(total_dur, s0 + max(0.5, window_sec))
            xs: List[float] = []
            for idx in range(max(2, samples)):
                t = s0 + (s1 - s0) * (idx / max(1, samples - 1))
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                energy = np.abs(gx) + np.abs(gy)
                col_profile = np.mean(energy, axis=0)
                total_e = float(np.sum(col_profile))
                if total_e > 1e-6:
                    coords = np.linspace(0.0, 1.0, len(col_profile), dtype=np.float32)
                    centroid = float(np.sum(coords * col_profile) / total_e)
                    xs.append(centroid)
            if not xs:
                return 0.5
            avg_x = sum(xs) / len(xs)
            return round(max(0.25, min(0.75, avg_x)), 4)
        finally:
            cap.release()

    @staticmethod
    def select_peak_window(
        word_timings: List[Dict[str, Any]],
        word_triggers: List[Dict[str, Any]],
        total_duration_sec: float,
        target_duration_sec: float = 25.0,
    ) -> Tuple[float, float]:
        """Select highest trigger/narrative density sub-window within a master video."""
        dur = max(0.5, float(total_duration_sec))
        win = min(dur, max(2.0, float(target_duration_sec)))
        if dur <= win + 0.5 or not word_triggers:
            return 0.0, round(win, 3)

        best_start = 0.0
        best_score = -1.0
        step = max(0.5, win / 6.0)
        cursor = 0.0
        while cursor + win <= dur + 1e-4:
            end = min(dur, cursor + win)
            trig_hits = sum(
                1
                for tr in word_triggers
                if cursor <= float(tr.get("timestamp_sec", -1.0)) <= end
            )
            word_hits = sum(
                1
                for wt in word_timings
                if cursor <= float(wt.get("start_sec", -1.0)) <= end
            )
            score = trig_hits * 5.0 + word_hits * 0.25
            if score > best_score:
                best_score = score
                best_start = cursor
            cursor += step
        return round(best_start, 3), round(min(dur, best_start + win), 3)

    @staticmethod
    def _eligible_microstock_agencies() -> List[str]:
        return sorted(
            name
            for name, spec in PLATFORM_RULES.items()
            if getattr(spec, "allows_ai", False) and name != "alamy"
        )

    @staticmethod
    def _crop_9x16_to_mp4(
        source_video: Path,
        output_video: Path,
        start_sec: float,
        duration_sec: float,
        center_x_norm: float,
        target_w: int,
        target_h: int,
        strip_audio: bool,
        audio_override: Optional[Path] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Crop source frame around salient center_x and scale to exact 9:16 MP4."""
        props = probe_video(source_video)
        src_w, src_h = max(2, props.width), max(2, props.height)
        target_ratio = target_w / max(1, target_h)
        crop_h = src_h
        crop_w = int(round(crop_h * target_ratio))
        if crop_w > src_w:
            crop_w = src_w
            crop_h = max(2, int(round(crop_w / target_ratio)))

        # Make crop dimensions even for yuv420p
        crop_w = max(2, crop_w - (crop_w % 2))
        crop_h = max(2, crop_h - (crop_h % 2))
        max_x = max(0, src_w - crop_w)
        cx_px = int(round(center_x_norm * src_w))
        crop_x = max(0, min(max_x, cx_px - crop_w // 2))
        crop_y = max(0, (src_h - crop_h) // 2)

        vf = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={int(target_w)}:{int(target_h)}:flags=lanczos"
        cmd: List[str] = [
            get_ffmpeg_binary(),
            "-y",
            "-v",
            "error",
            "-nostats",
            "-ss",
            f"{max(0.0, start_sec):.3f}",
            "-t",
            f"{max(0.5, duration_sec):.3f}",
            "-i",
            source_video.as_posix(),
        ]
        if strip_audio:
            cmd.extend(["-vf", vf, "-an"])
        elif audio_override and audio_override.is_file():
            cmd.extend(
                [
                    "-ss",
                    f"{max(0.0, start_sec):.3f}",
                    "-t",
                    f"{max(0.5, duration_sec):.3f}",
                    "-i",
                    audio_override.as_posix(),
                    "-vf",
                    vf,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:a",
                    "aac",
                    "-shortest",
                ]
            )
        else:
            cmd.extend(["-vf", vf])

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
                output_video.as_posix(),
            ]
        )

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=180,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return False, str(exc)
        if proc.returncode != 0 or not output_video.is_file() or output_video.stat().st_size == 0:
            err = proc.stderr.decode("utf-8", errors="replace")[-400:] if proc.stderr else "FFmpeg error"
            return False, err
        return True, None

    def repurpose_to_vertical_short(
        self,
        title: str,
        script: str = "",
        source_video_path: Optional[str | Path] = None,
        audio_path: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
        style: str = "editorial_karaoke",
        safe_zone_profile: str = "youtube_shorts",
        target_duration_sec: float = 15.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 24,
        word_timings: Optional[List[Dict[str, Any]]] = None,
        word_triggers: Optional[List[Dict[str, Any]]] = None,
        export_microstock_broll: bool = True,
    ) -> ShortsRepurposeResult:
        """Produce a 9:16 kinetic-captioned Short plus optional clean (-an) stock vertical B-roll."""
        if not title or not title.strip():
            raise ValueError("Short title cannot be empty.")

        style_key = self.caption_engine._validate_style(style)
        zone_key = (safe_zone_profile or "youtube_shorts").strip().lower()
        if zone_key not in PLATFORM_SAFE_ZONES:
            raise ValueError(
                f"Unknown safe_zone_profile '{safe_zone_profile}'. Valid: {sorted(PLATFORM_SAFE_ZONES)}"
            )
        safe_zone_profile = zone_key
        out_root = Path(output_dir) if output_dir else self.output_dir
        out_root.mkdir(parents=True, exist_ok=True)
        slug = _slugify(title)
        eligible = self._eligible_microstock_agencies()

        src_video = Path(source_video_path) if source_video_path else None
        if src_video is not None and not src_video.is_file():
            return ShortsRepurposeResult(
                success=False,
                title=title,
                style=style_key,
                safe_zone_profile=safe_zone_profile,
                alamy_blocked=True,
                eligible_agencies=eligible,
                error=f"Source video not found: {src_video}",
            )

        audio_file = Path(audio_path) if audio_path else None
        if audio_file is not None and not audio_file.is_file():
            return ShortsRepurposeResult(
                success=False,
                title=title,
                style=style_key,
                safe_zone_profile=safe_zone_profile,
                alamy_blocked=True,
                eligible_agencies=eligible,
                error=f"Audio file not found: {audio_file}",
            )

        if src_video is not None:
            master_props = probe_video(src_video)
            master_dur = max(0.5, float(master_props.duration_seconds))
        elif audio_file is not None:
            master_dur = max(1.0, probe_audio_duration(audio_file, fallback_word_count=len(script.split())))
        else:
            master_dur = max(2.0, float(target_duration_sec))

        resolved_timings: List[Dict[str, Any]] = list(word_timings or [])
        resolved_triggers: List[Dict[str, Any]] = list(word_triggers or [])
        if not resolved_timings:
            if audio_file is not None and script.strip():
                aligned = VoiceAligner().align_transcript(
                    audio_path=audio_file,
                    transcript=script,
                    save_srt=False,
                )
                resolved_timings = [wt.to_dict() for wt in aligned.word_timings]
                if not resolved_triggers:
                    resolved_triggers = [tr.to_dict() for tr in aligned.word_triggers]
            elif script.strip():
                resolved_timings = self.caption_engine.timings_from_script(script, total_duration_sec=master_dur)
            else:
                resolved_timings = self.caption_engine.timings_from_script(title, total_duration_sec=master_dur)

        win_start, win_end = self.select_peak_window(
            word_timings=resolved_timings,
            word_triggers=resolved_triggers,
            total_duration_sec=master_dur,
            target_duration_sec=target_duration_sec,
        )
        win_dur = max(0.5, round(win_end - win_start, 3))

        # Shift word timings to window-relative clock [0 .. win_dur]
        shifted_timings: List[Dict[str, Any]] = []
        for wt in resolved_timings:
            ws = float(wt.get("start_sec", 0.0))
            we = float(wt.get("end_sec", ws + 0.2))
            if we >= win_start and ws <= win_end:
                shifted_timings.append(
                    {
                        "word": wt["word"],
                        "start_sec": round(max(0.0, ws - win_start), 3),
                        "end_sec": round(max(0.06, min(win_dur, we - win_start)), 3),
                    }
                )
        if not shifted_timings:
            shifted_timings = self.caption_engine.timings_from_script(script or title, total_duration_sec=win_dur)

        stock_broll_path: Optional[Path] = None
        base_vertical_path = out_root / f"{slug}_vertical_base.mp4"
        salient_x = 0.5

        if src_video is not None:
            salient_x = self.detect_salient_center_x(src_video, start_sec=win_start, window_sec=win_dur)
            if export_microstock_broll:
                stock_broll_path = out_root / f"{slug}_stock_broll_9x16.mp4"
                ok_crop, crop_err = self._crop_9x16_to_mp4(
                    source_video=src_video,
                    output_video=stock_broll_path,
                    start_sec=win_start,
                    duration_sec=win_dur,
                    center_x_norm=salient_x,
                    target_w=width,
                    target_h=height,
                    strip_audio=True,
                )
                if not ok_crop:
                    return ShortsRepurposeResult(
                        success=False,
                        title=title,
                        style=style_key,
                        safe_zone_profile=safe_zone_profile,
                        salient_center_x=salient_x,
                        alamy_blocked=True,
                        eligible_agencies=eligible,
                        error=f"9:16 B-roll crop failed: {crop_err}",
                    )
                base_vertical_path = stock_broll_path
            else:
                ok_crop, crop_err = self._crop_9x16_to_mp4(
                    source_video=src_video,
                    output_video=base_vertical_path,
                    start_sec=win_start,
                    duration_sec=win_dur,
                    center_x_norm=salient_x,
                    target_w=width,
                    target_h=height,
                    strip_audio=True,
                )
                if not ok_crop:
                    return ShortsRepurposeResult(
                        success=False,
                        title=title,
                        style=style_key,
                        safe_zone_profile=safe_zone_profile,
                        salient_center_x=salient_x,
                        alamy_blocked=True,
                        eligible_agencies=eligible,
                        error=f"9:16 crop failed: {crop_err}",
                    )
        else:
            hf = HyperFramesMotionEngine(output_dir=out_root)
            clean_title, _ = PromoMotionDirector.sanitize_trademark_free(title)
            base_target = out_root / (f"{slug}_stock_broll_9x16.mp4" if export_microstock_broll else f"{slug}_vertical_base.mp4")
            comp = hf.render_motion_clip(
                template="vertical_dossier_short",
                title=clean_title.upper()[:32],
                subtitle="SIGNAL DOSSIER BRIEF",
                output_path=base_target,
                duration_sec=win_dur,
                width=width,
                height=height,
                fps=fps,
                force_procedural=True,
                muted=True,
            )
            if not comp.success or not comp.output_video_path:
                return ShortsRepurposeResult(
                    success=False,
                    title=title,
                    style=style_key,
                    safe_zone_profile=safe_zone_profile,
                    alamy_blocked=True,
                    eligible_agencies=eligible,
                    error=comp.error or "Procedural 9:16 render failed",
                )
            base_vertical_path = comp.output_video_path
            if export_microstock_broll:
                stock_broll_path = comp.output_video_path

        # Extract trimmed audio slice synced to [win_start .. win_end] so social Short keeps speech/SFX
        trimmed_audio_tmp: Optional[Path] = None
        effective_audio: Optional[Path] = audio_file
        try:
            audio_extract_src: Optional[Path] = None
            if audio_file is not None and win_start > 0.01:
                audio_extract_src = audio_file
            elif audio_file is None and src_video is not None and probe_video(src_video).has_audio:
                audio_extract_src = src_video

            if audio_extract_src is not None:
                trimmed_audio_tmp = out_root / f"{slug}_win_audio_{uuid.uuid4().hex[:6]}.m4a"
                extract_cmd = [
                    get_ffmpeg_binary(),
                    "-y",
                    "-v",
                    "error",
                    "-nostats",
                    "-ss",
                    f"{win_start:.3f}",
                    "-t",
                    f"{win_dur:.3f}",
                    "-i",
                    audio_extract_src.as_posix(),
                    "-vn",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    trimmed_audio_tmp.as_posix(),
                ]
                try:
                    aproc = subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
                    if aproc.returncode == 0 and trimmed_audio_tmp.is_file() and trimmed_audio_tmp.stat().st_size > 0:
                        effective_audio = trimmed_audio_tmp
                except (subprocess.SubprocessError, OSError) as exc:
                    logger.warning("Audio slice extraction skipped (%s)", exc)

            final_short_path = out_root / f"{slug}_short_9x16.mp4"
            caption_res = self.caption_engine.render_captioned_video(
                input_video_path=base_vertical_path,
                output_video_path=final_short_path,
                word_timings=shifted_timings,
                style=style_key,
                safe_zone_profile=safe_zone_profile,
                audio_path=effective_audio,
            )
        finally:
            if trimmed_audio_tmp is not None:
                trimmed_audio_tmp.unlink(missing_ok=True)
            if not export_microstock_broll and base_vertical_path.is_file():
                base_vertical_path.unlink(missing_ok=True)

        stock_muted = True
        if stock_broll_path and stock_broll_path.is_file():
            stock_muted = not probe_video(stock_broll_path).has_audio

        out_props = probe_video(final_short_path) if caption_res.success and final_short_path.is_file() else None
        manifest_path = out_root / f"{slug}_short_manifest.json"
        result = ShortsRepurposeResult(
            success=caption_res.success,
            title=title,
            style=style_key,
            safe_zone_profile=safe_zone_profile,
            short_video_path=caption_res.video_path,
            ass_path=caption_res.ass_path,
            stock_broll_path=stock_broll_path.as_posix() if stock_broll_path else None,
            stock_broll_muted=stock_muted,
            manifest_path=manifest_path.as_posix(),
            width=out_props.width if out_props else width,
            height=out_props.height if out_props else height,
            duration_sec=out_props.duration_seconds if out_props else win_dur,
            window_start_sec=win_start,
            window_end_sec=win_end,
            salient_center_x=salient_x,
            safe_zone_passed=bool(caption_res.overlap_audit.get("passed", False)),
            alamy_blocked=True,
            eligible_agencies=eligible,
            overlap_audit=caption_res.overlap_audit,
            error=caption_res.error,
        )
        _atomic_write_json(manifest_path, result.to_dict())
        return result
