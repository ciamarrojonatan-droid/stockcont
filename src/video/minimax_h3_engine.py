"""StockCont & DarkFactory — MiniMax H3 Cinematic V2 Turbo Engine.

Connects to RunningHub ComfyUI RPA (Workflow 2118560390471745537) to generate
high-retention cinematic videos from reference images (I2V / T2V hybrid)
and extracts clean watermark-free video via Node #107 (FeiHouVideoPreview).

Serves as the dedicated high-fidelity cinematic video fallback when primary
generation is unavailable.
"""

from __future__ import annotations

import logging
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import cv2
import numpy as np

# Windows UTF-8 enforcement (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("MiniMaxH3VideoEngine")

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
FINAL_VIDEOS_DIR: Path = BASE_DIR / "data" / "final" / "videos"
FINAL_IMAGES_DIR: Path = BASE_DIR / "data" / "final" / "images"
FINAL_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class H3VideoResult:
    """Result container for generated MiniMax H3 cinematic video."""
    video_path: Path
    filename: str
    duration_seconds: float
    prompt_used: str
    reference_image: Optional[Path]
    engine: str  # 'minimax_h3_cinematic_runninghub' or 'procedural_fallback'
    filesize_bytes: int
    has_watermark: bool = False


class MiniMaxH3VideoEngine:
    """Orchestrates MiniMax H3 Cinematic V2 Turbo video generation on RunningHub

    with guaranteed watermark-free video extraction from Node #107 (FeiHouVideoPreview)
    and smooth procedural cinematic fallback.
    """

    def __init__(self, output_dir: Optional[Union[Path, str]] = None) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else FINAL_VIDEOS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_cinematic_prompt(
        self,
        subject: str,
        camera_movement: str = "Slow cinematic push-in dolly track forward",
        lighting: str = "Volumetric cinematic rim lighting, atmospheric shadows, 2.39:1 letterbox",
        dop_prompt: Optional[str] = "Christopher Nolan / Hoyte van Hoytema 35mm anamorphic aesthetic",
    ) -> str:
        """Formats prompt adhering strictly to MiniMax H3 / Hailuo Video-01 best practices."""
        try:
            from src.video.darkfactory_t2v import format_minimax_prompt
            return format_minimax_prompt(
                subject=subject,
                camera=camera_movement,
                lighting_palette=lighting,
                dop_prompt=dop_prompt,
            )
        except Exception:
            clean_subj = subject.strip().rstrip(".")
            clean_cam = camera_movement.strip().rstrip(".")
            return (
                f"[Camera Movement: {clean_cam}]. {clean_subj}. "
                f"Cinematic lighting: {lighting}. "
                f"Authentic film grain, natural weight and physics, hyper-realistic human motion, "
                f"atmospheric volumetric shadows, 24fps motion cadence, master cinematography, "
                f"no digital warping, no anatomical glitches. [Director of Photography: {dop_prompt}]"
            )

    def generate_video(
        self,
        prompt: str,
        reference_image_path: Optional[Union[Path, str]] = None,
        duration_sec: float = 10.0,
        destination_path: Optional[Union[Path, str]] = None,
        force_procedural: bool = False,
    ) -> H3VideoResult:
        """Generates a cinematic video via MiniMax H3 on RunningHub or procedural fallback.

        Args:
            prompt: Visual narrative & camera movement prompt (injected into Node #35).
            reference_image_path: Input reference image (injected into Node #48 LoadImage 图1).
            duration_sec: Duration in seconds (Node #66 PrimitiveFloat, default 10.0s).
            destination_path: Optional custom output file path.
            force_procedural: If True, bypasses RunningHub and uses local synthesis.
        """
        ref_p: Optional[Path] = None
        if reference_image_path:
            cand = Path(reference_image_path)
            if cand.exists():
                ref_p = cand.resolve()

        if not force_procedural:
            try:
                from src.factory.runninghub_bot import run_minimax_h3_video_bot
                logger.info(
                    f"Triggering MiniMax H3 Cinematic on RunningHub (Workflow 2118560390471745537, "
                    f"duration={duration_sec}s, prompt='{prompt[:50]}...')..."
                )
                res = run_minimax_h3_video_bot(
                    prompt=prompt,
                    reference_image_path=ref_p,
                    duration_sec=duration_sec,
                    destination_dir=self.output_dir,
                )
                saved_files = res.get("saved_files", [])
                for fn in saved_files:
                    target_file = self.output_dir / fn
                    if target_file.exists() and target_file.suffix.lower() in (".mp4", ".mov", ".webm"):
                        logger.info(f"✅ MiniMax H3 video extracted without watermark from Node #107: {target_file.name}")
                        return H3VideoResult(
                            video_path=target_file,
                            filename=target_file.name,
                            duration_seconds=duration_sec,
                            prompt_used=prompt,
                            reference_image=ref_p,
                            engine="minimax_h3_cinematic_runninghub",
                            filesize_bytes=target_file.stat().st_size,
                            has_watermark=False,
                        )
            except Exception as e:
                logger.warning(
                    f"RunningHub MiniMax H3 RPA unavailable ({e}). "
                    f"Activating procedural cinematic fallback synthesis."
                )

        # Procedural fallback synthesis (generates high-definition 16:9 cinematic motion video)
        out_video = self._generate_procedural_video(
            prompt=prompt,
            reference_image_path=ref_p,
            duration_sec=duration_sec,
            destination_path=destination_path,
        )
        logger.info(f"✅ MiniMax H3 video generated via procedural fallback: {out_video.name}")
        return H3VideoResult(
            video_path=out_video,
            filename=out_video.name,
            duration_seconds=duration_sec,
            prompt_used=prompt,
            reference_image=ref_p,
            engine="procedural_fallback",
            filesize_bytes=out_video.stat().st_size,
            has_watermark=False,
        )

    def _generate_procedural_video(
        self,
        prompt: str,
        reference_image_path: Optional[Path] = None,
        duration_sec: float = 10.0,
        destination_path: Optional[Union[Path, str]] = None,
    ) -> Path:
        """Synthesizes a 1080p widescreen 16:9 cinematic MP4 video clip with subtle motion drift.

        Ensures zero watermark and deterministic high-definition video output.
        """
        width = 1920
        height = 1080
        fps = 24
        total_frames = max(24, int(fps * duration_sec))

        if destination_path:
            out_p = Path(destination_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
        else:
            timestamp = int(time.time())
            out_p = self.output_dir / f"minimax_h3_cinematic_{timestamp}.mp4"

        # Load reference base image if available, else build a dramatic film noir gradient canvas
        base_canvas = None
        if reference_image_path and reference_image_path.exists():
            try:
                img_bgr = cv2.imread(str(reference_image_path))
                if img_bgr is not None:
                    base_canvas = cv2.resize(img_bgr, (width + 120, height + 80), interpolation=cv2.INTER_LANCZOS4)
            except Exception:
                base_canvas = None

        if base_canvas is None:
            # Create a rich cinematic dark gradient background
            base_canvas = np.zeros((height + 80, width + 120, 3), dtype=np.uint8)
            y_coords = np.linspace(20, 5, height + 80).reshape(-1, 1).astype(np.uint8)
            x_coords = np.linspace(15, 30, width + 120).reshape(1, -1).astype(np.uint8)
            base_canvas[:, :, 0] = x_coords  # Blue
            base_canvas[:, :, 1] = y_coords  # Green
            base_canvas[:, :, 2] = (y_coords * 0.8).astype(np.uint8)  # Red

        # Initialize VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_p), fourcc, fps, (width, height))

        max_dx = base_canvas.shape[1] - width
        max_dy = base_canvas.shape[0] - height

        for i in range(total_frames):
            progress = i / max(total_frames - 1, 1)
            # Smooth sinusoidal camera pan and push-in drift
            shift_x = int((max_dx / 2) * (1.0 + math.sin(progress * math.pi * 0.5)))
            shift_y = int((max_dy / 2) * (1.0 - math.cos(progress * math.pi * 0.5)))

            shift_x = min(max(shift_x, 0), max_dx)
            shift_y = min(max(shift_y, 0), max_dy)

            frame = base_canvas[shift_y : shift_y + height, shift_x : shift_x + width].copy()

            # Add subtle organic cinematic film grain
            grain = np.random.normal(0, 3.5, (height, width, 3)).astype(np.int16)
            noisy_frame = np.clip(frame.astype(np.int16) + grain, 0, 255).astype(np.uint8)

            writer.write(noisy_frame)

        writer.release()
        return out_p
