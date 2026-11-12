"""StockCont & DarkFactory — Multimodal Video Reverse-Engineer (Auto Mode).

Breaks down an existing reference video into shot segments, extracts 3-frame
contact sheets, analyzes camera/lighting/motion physics (via injected
vision callback, optional Gemini Vision, or deterministic OpenCV heuristics),
produces MiniMax H3 + Google Veo 2 prompts, and audits pacing/retention.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from src.video.darkfactory_t2v import format_google_veo_prompt, format_minimax_prompt
from src.video.ffmpeg_processor import probe_video
from src.video.pacing_analyzer import CinematicPacingAnalyzer
from src.video.story_validator import DarkFactoryStoryValidator

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.reverse_engineer")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_REVERSE_DIR = BASE_DIR / "data" / "processed" / "reverse_engineered"

VisionCallback = Callable[[Path, int, float], Dict[str, Any]]


@dataclass
class ReverseEngineeredShot:
    """Structured prompt & cinematic telemetry extracted from one video shot."""

    shot_id: int
    start_sec: float
    end_sec: float
    duration_sec: float
    generation_mode: str  # "T2VA" | "I2V" | "DUAL"
    subject: str
    camera_movement: str
    lighting_palette: str
    motion_score: float
    contact_sheet_path: str
    minimax_prompt: str
    google_veo_prompt: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoReverseResult:
    """Full breakdown report from reverse-engineering a reference video."""

    success: bool
    video_path: str
    topic: str
    mode: str
    total_duration_sec: float
    mean_shot_length: float
    shots: List[Dict[str, Any]] = field(default_factory=list)
    story_audit: Dict[str, Any] = field(default_factory=dict)
    manifest_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", (value or "video").strip().lower()).strip("_")[:60] or "video"


def _atomic_write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return path


class VideoReverseEngineer:
    """Deconstructs reference video clips into production-ready T2V/I2V prompt sheets."""

    def __init__(self, output_dir: Optional[Path | str] = None) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_REVERSE_DIR.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _extract_contact_sheet(
        cap: cv2.VideoCapture,
        fps: float,
        start_sec: float,
        end_sec: float,
        output_png: Path,
    ) -> Dict[str, Any]:
        """Extract 3 representative frames across a shot into one horizontal PNG contact sheet."""
        span = max(0.1, end_sec - start_sec)
        sample_times = [
            start_sec + span * 0.15,
            start_sec + span * 0.50,
            start_sec + span * 0.85,
        ]
        frames: List[np.ndarray] = []
        for ts in sample_times:
            frame_idx = max(0, int(round(ts * max(1.0, fps))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frm = cap.read()
            if not ok or frm is None:
                frm = np.zeros((180, 320, 3), dtype=np.uint8)
            thumb = cv2.resize(frm, (320, 180), interpolation=cv2.INTER_AREA)
            cv2.putText(
                thumb,
                f"t={ts:.2f}s",
                (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (56, 189, 248),
                2,
                cv2.LINE_AA,
            )
            frames.append(thumb)

        sheet = np.hstack(frames)
        output_png.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_png), sheet)

        # Deterministic physics heuristics: inter-frame pixel delta & luminance contrast
        diffs = [
            float(np.mean(np.abs(frames[i].astype(np.float32) - frames[i - 1].astype(np.float32))))
            for i in range(1, len(frames))
        ]
        motion_score = round(sum(diffs) / max(1, len(diffs)), 2)
        mean_bgr = np.mean(frames[1].reshape(-1, 3), axis=0)
        gray = cv2.cvtColor(frames[1], cv2.COLOR_BGR2GRAY)
        contrast = float(np.std(gray))

        if float(mean_bgr[2]) > float(mean_bgr[0]) * 1.25:
            tone = "Warm tungsten glow cutting through shadow amber haze"
        elif float(mean_bgr[0]) > float(mean_bgr[2]) * 1.25:
            tone = "Cold slate blue obsidian lighting with crisp rim highlights"
        else:
            tone = "Neutral documentary archival exposure with controlled chiaroscuro"

        if contrast > 48.0:
            tone += ", high-contrast chiaroscuro"

        if motion_score >= 18.0:
            auto_camera = "Dynamic tracking pan following rapid foreground motion"
            auto_mode = "T2VA"
        elif motion_score >= 5.0:
            auto_camera = "Slow measured dolly push-in across central focal geometry"
            auto_mode = "DUAL"
        else:
            auto_camera = "Locked-off tripod frame with micro atmospheric parallax"
            auto_mode = "I2V"

        return {
            "motion_score": motion_score,
            "lighting_palette": tone,
            "auto_camera": auto_camera,
            "auto_mode": auto_mode,
        }

    def _call_gemini_vision(self, sheet_path: Path, shot_idx: int, duration_sec: float) -> Optional[Dict[str, Any]]:
        """Optionally inspect a contact sheet with Gemini Vision when configured."""
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            return None
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=api_key)
            prompt = (
                "Analyze this 3-frame film shot contact sheet in JSON with keys: "
                "subject (concise physical description), camera (camera movement), "
                "lighting (color & shadow mood), recommended_mode (T2VA, I2V, or DUAL). "
                f"Shot index={shot_idx}, duration={duration_sec:.2f}s. Output valid JSON only."
            )
            img_bytes = sheet_path.read_bytes()
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, {"mime_type": "image/png", "data": img_bytes}],
            )
            raw = (resp.text or "").strip().strip("`")
            raw = re.sub(r"^json\s*", "", raw, flags=re.IGNORECASE)
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get("subject"):
                return parsed
        except Exception as exc:
            logger.debug("Gemini Vision inspection fallback triggered: %s", exc)
        return None

    def reverse_engineer_video(
        self,
        video_path: Path | str,
        topic: Optional[str] = None,
        mode: str = "AUTO",
        use_vision: bool = False,
        vision_callback: Optional[VisionCallback] = None,
    ) -> VideoReverseResult:
        """Analyze video shots, synthesize dual-engine prompts, and run StoryValidator audit."""
        src = Path(video_path).resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Video not found for reverse engineering: {src}")

        resolved_topic = (topic or src.stem.replace("_", " ")).strip() or "Reference Breakdown"
        slug = _slugify(resolved_topic)
        out_dir = self.output_dir / slug
        sheets_dir = out_dir / "contact_sheets"
        sheets_dir.mkdir(parents=True, exist_ok=True)

        props = probe_video(src)
        total_dur = max(0.5, float(props.duration_seconds))
        fps = max(1.0, float(props.fps or 24.0))

        pacing = CinematicPacingAnalyzer().analyze_pacing(src)
        boundaries: List[tuple[float, float]] = [
            (float(seg.start_sec), float(seg.end_sec))
            for seg in (pacing.shots or [])
            if float(seg.end_sec) - float(seg.start_sec) >= 0.2
        ]
        if not boundaries:
            # Uniform deterministic split fallback so single-take or synthetic clips yield multi-shot cards
            chunk = max(0.8, total_dur / 3.0)
            boundaries = []
            cur = 0.0
            while cur < total_dur - 0.15:
                nxt = min(total_dur, round(cur + chunk, 3))
                boundaries.append((round(cur, 3), nxt))
                cur = nxt

        cap = cv2.VideoCapture(str(src))
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open video: {src}")

        shots: List[ReverseEngineeredShot] = []
        requested_mode = (mode or "AUTO").strip().upper()
        if requested_mode not in {"AUTO", "T2VA", "I2V", "DUAL"}:
            requested_mode = "AUTO"

        try:
            for idx, (s_start, s_end) in enumerate(boundaries, start=1):
                dur = max(0.25, round(s_end - s_start, 3))
                sheet_png = sheets_dir / f"shot_{idx:02d}.png"
                telemetry = self._extract_contact_sheet(
                    cap=cap,
                    fps=fps,
                    start_sec=s_start,
                    end_sec=s_end,
                    output_png=sheet_png,
                )

                vision_data: Optional[Dict[str, Any]] = None
                if vision_callback is not None:
                    vision_data = vision_callback(sheet_png, idx, dur)
                elif use_vision:
                    vision_data = self._call_gemini_vision(sheet_png, idx, dur)

                subject = (
                    str(vision_data.get("subject"))
                    if vision_data and vision_data.get("subject")
                    else f"Archival foreground focus from '{resolved_topic}' shot #{idx} with tactile depth cues"
                )
                camera = (
                    str(vision_data.get("camera"))
                    if vision_data and vision_data.get("camera")
                    else str(telemetry["auto_camera"])
                )
                lighting = (
                    str(vision_data.get("lighting"))
                    if vision_data and vision_data.get("lighting")
                    else str(telemetry["lighting_palette"])
                )
                gen_mode = (
                    str(vision_data.get("recommended_mode", "")).upper()
                    if requested_mode == "AUTO" and vision_data and vision_data.get("recommended_mode")
                    else (str(telemetry["auto_mode"]) if requested_mode == "AUTO" else requested_mode)
                )
                if gen_mode not in {"T2VA", "I2V", "DUAL"}:
                    gen_mode = "DUAL"

                mm_prompt = format_minimax_prompt(
                    subject=subject,
                    camera=camera,
                    lighting_palette=lighting,
                    duration=dur,
                )
                veo_prompt = format_google_veo_prompt(
                    subject=subject,
                    camera=camera,
                    optics="35mm Panavision anamorphic prime f/2.0",
                    lighting_palette=lighting,
                )

                shots.append(
                    ReverseEngineeredShot(
                        shot_id=idx,
                        start_sec=s_start,
                        end_sec=s_end,
                        duration_sec=dur,
                        generation_mode=gen_mode,
                        subject=subject,
                        camera_movement=camera,
                        lighting_palette=lighting,
                        motion_score=float(telemetry["motion_score"]),
                        contact_sheet_path=sheet_png.as_posix(),
                        minimax_prompt=mm_prompt,
                        google_veo_prompt=veo_prompt,
                    )
                )
        finally:
            cap.release()

        # Pair shots into Dual-Shot A/B scenes for StoryValidator retention audit
        validator_scenes: List[Dict[str, Any]] = []
        for idx in range(0, len(shots), 2):
            shot_a = shots[idx]
            shot_b = shots[idx + 1] if (idx + 1) < len(shots) else shots[idx]
            validator_scenes.append(
                {
                    "scene_id": (idx // 2) + 1,
                    "narrative_beat": f"Beat {(idx // 2) + 1}",
                    "shot_a": {"duration": shot_a.duration_sec, "subject": shot_a.subject},
                    "shot_b": {"duration": shot_b.duration_sec, "subject": shot_b.subject},
                }
            )

        audit = DarkFactoryStoryValidator().audit_episode_manifest(
            project_title=resolved_topic,
            scenes=validator_scenes,
            script_narration_full=" ".join(s.subject for s in shots),
        )
        msl = round(total_dur / max(1, len(shots)), 3)

        manifest_file = out_dir / f"{slug}_reverse_manifest.json"
        payload = {
            "success": True,
            "video_path": src.as_posix(),
            "topic": resolved_topic,
            "mode": requested_mode,
            "total_duration_sec": round(total_dur, 3),
            "mean_shot_length": msl,
            "shots": [s.to_dict() for s in shots],
            "story_audit": audit.to_dict(),
        }
        _atomic_write_json(manifest_file, payload)

        return VideoReverseResult(
            success=True,
            video_path=src.as_posix(),
            topic=resolved_topic,
            mode=requested_mode,
            total_duration_sec=round(total_dur, 3),
            mean_shot_length=msl,
            shots=[s.to_dict() for s in shots],
            story_audit=audit.to_dict(),
            manifest_path=manifest_file.as_posix(),
        )
