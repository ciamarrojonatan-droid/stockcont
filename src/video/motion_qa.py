"""StockCont & DarkFactory — Deterministic Motion QA & Contact-Sheet Inspector.

Implements pre-release visual quality gates inspired by:
- alexgreensh/anidoodle (risk-window sampling, determinism & clipping checks)
- shinyobjectz/raea (`raea check`: WCAG contrast, title-safe margins, frozen frames)
- iart-ai/motion-skills & op7418/guizang-product-video-skill (Deliver-and-Verify contact sheets)
"""

from __future__ import annotations

import logging
import math
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.motion_qa")

PERSONALITY_MIN_MOTION_DELTAS: Dict[str, float] = {
    "cold_war_noir": 0.10,
    "clinical_fintech": 0.18,
    "executive_corporate": 0.14,
    "high_energy_hook": 0.30,
}


@dataclass
class MotionQAFinding:
    """Single automated QA finding for motion graphics or overlays."""

    code: str
    severity: str  # "error" | "warning"
    message: str
    frame_index: Optional[int] = None


@dataclass
class MotionQAReport:
    """Comprehensive pre-encode / post-preview Visual QA result."""

    passed: bool
    score: float
    video_path: str
    contact_sheet_path: Optional[str]
    contrast_ratio: float
    min_motion_delta: float
    max_motion_delta: float
    frozen_frame_pairs: int
    safe_margin_ok: bool
    sampled_frame_count: int
    findings: List[MotionQAFinding] = field(default_factory=list)
    vision_critique: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report with normalized POSIX paths."""
        payload = asdict(self)
        for key in ("video_path", "contact_sheet_path"):
            val = payload.get(key)
            if isinstance(val, Path):
                payload[key] = val.as_posix()
        return payload


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Expected 6-digit hex color, got '{hex_color}'")
    return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Compute WCAG 2.1 relative luminance for an sRGB triplet."""
    channels = []
    for channel in rgb:
        srgb = channel / 255.0
        if srgb <= 0.03928:
            channels.append(srgb / 12.92)
        else:
            channels.append(((srgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _load_qa_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _atomic_save_png(image: Image.Image, target_path: Path) -> Path:
    """Save PNG atomically via .tmp file + replace() (ADR-02)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}.png")
    try:
        image.save(tmp_path, format="PNG")
        tmp_path.replace(target_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return target_path


class MotionQAInspector:
    """Automated visual gatekeeper for HyperFrames clips, overlays, and contact sheets."""

    @staticmethod
    def compute_contrast_ratio(
        fg_rgb: Tuple[int, int, int],
        bg_rgb: Tuple[int, int, int],
    ) -> float:
        """Compute WCAG 2.1 contrast ratio between foreground and background RGB colors."""
        lum1 = _relative_luminance(fg_rgb)
        lum2 = _relative_luminance(bg_rgb)
        lighter, darker = max(lum1, lum2), min(lum1, lum2)
        return round((lighter + 0.05) / (darker + 0.05), 2)

    def inspect_palette_contrast(
        self,
        bg_hex: str,
        fg_hex: str = "#F1F5F9",
        accent_hex: Optional[str] = None,
        min_text_ratio: float = 4.5,
        min_accent_ratio: float = 3.0,
    ) -> Tuple[bool, float, List[MotionQAFinding]]:
        """Validate foreground/accent legibility before launching any video render."""
        findings: List[MotionQAFinding] = []
        bg_rgb = _hex_to_rgb(bg_hex)
        fg_rgb = _hex_to_rgb(fg_hex)
        text_ratio = self.compute_contrast_ratio(fg_rgb, bg_rgb)

        if text_ratio < min_text_ratio:
            findings.append(
                MotionQAFinding(
                    code="LOW_TEXT_CONTRAST",
                    severity="error",
                    message=(
                        f"Primary text contrast {text_ratio:.2f}:1 ({fg_hex} on {bg_hex}) "
                        f"is below WCAG {min_text_ratio:.1f}:1 threshold."
                    ),
                )
            )

        if accent_hex:
            accent_rgb = _hex_to_rgb(accent_hex)
            accent_ratio = self.compute_contrast_ratio(accent_rgb, bg_rgb)
            if accent_ratio < min_accent_ratio:
                findings.append(
                    MotionQAFinding(
                        code="LOW_ACCENT_CONTRAST",
                        severity="warning",
                        message=(
                            f"Accent color contrast {accent_ratio:.2f}:1 ({accent_hex} on {bg_hex}) "
                            f"is below {min_accent_ratio:.1f}:1 UI legibility threshold."
                        ),
                    )
                )

        passed = not any(f.severity == "error" for f in findings)
        return passed, text_ratio, findings

    def check_text_safe_area(
        self,
        title: str,
        subtitle: str,
        width: int,
        height: int,
        template: str = "tactical_hud",
        safe_margin_ratio: float = 0.05,
    ) -> Tuple[bool, List[MotionQAFinding]]:
        """Verify rendered title/subtitle bounds stay inside title-safe area (no edge clipping)."""
        findings: List[MotionQAFinding] = []
        probe_img = Image.new("RGB", (max(64, width), max(64, height)))
        draw = ImageDraw.Draw(probe_img)

        title_size = max(18, int(height * 0.055))
        sub_size = max(13, int(height * 0.032))
        title_font = _load_qa_font(title_size)
        sub_font = _load_qa_font(sub_size)

        if template == "lower_third":
            tx, ty = int(width * 0.09), int(height * 0.745)
        else:
            tx, ty = int(width * 0.07), int(height * 0.14)

        margin_x = int(width * safe_margin_ratio)
        margin_y = int(height * safe_margin_ratio)
        safe_right = width - margin_x
        safe_bottom = height - margin_y

        def _check_box(label: str, text_val: str, x: int, y: int, font: Any) -> None:
            if not text_val:
                return
            left, top, right, bottom = draw.textbbox((x, y), text_val, font=font)
            if left < margin_x or top < margin_y or right > safe_right or bottom > safe_bottom:
                findings.append(
                    MotionQAFinding(
                        code="TEXT_UNSAFE_MARGIN",
                        severity="error",
                        message=(
                            f"{label} bounding box ({left},{top})-({right},{bottom}) exceeds "
                            f"{safe_margin_ratio:.0%} title-safe zone in {width}x{height}."
                        ),
                    )
                )

        _check_box("Title", title[:64], tx, ty, title_font)
        if subtitle:
            _check_box("Subtitle", subtitle[:96], tx, ty + int(title_size * 1.32), sub_font)

        return len(findings) == 0, findings

    def sample_risk_window_frames(
        self,
        video_path: str | Path,
        num_tiles: int = 9,
    ) -> Tuple[List[Tuple[int, float, np.ndarray]], int]:
        """Extract evenly distributed frames plus start/landing risk-window frames."""
        vid_file = Path(video_path)
        if not vid_file.exists():
            raise FileNotFoundError(f"Video not found for Motion QA: {vid_file}")

        cap = cv2.VideoCapture(str(vid_file))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video stream via OpenCV: {vid_file}")

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 24.0

            # Fallback read if container lacks frame count header
            if total_frames <= 0:
                raw_frames: List[np.ndarray] = []
                while True:
                    ok, frm = cap.read()
                    if not ok:
                        break
                    raw_frames.append(frm)
                total_frames = len(raw_frames)
                if total_frames == 0:
                    return [], 0
                indices = self._build_risk_indices(total_frames, num_tiles)
                return [(idx, idx / fps, raw_frames[idx]) for idx in indices], total_frames

            indices = self._build_risk_indices(total_frames, num_tiles)
            sampled: List[Tuple[int, float, np.ndarray]] = []
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if ok and frame is not None:
                    sampled.append((idx, idx / fps, frame))
            return sampled, total_frames
        finally:
            cap.release()

    @staticmethod
    def _build_risk_indices(total_frames: int, num_tiles: int) -> List[int]:
        """Always include frame 0, frame 1 (early entry), middle beats, and final landing frame."""
        if total_frames <= 1:
            return [0]
        if total_frames <= num_tiles:
            return list(range(total_frames))

        core = [0, 1, total_frames - 2, total_frames - 1]
        lin = np.linspace(0, total_frames - 1, num=num_tiles, dtype=int).tolist()
        merged = sorted(set(core + lin))
        while len(merged) > num_tiles:
            # Trim interior redundancy while keeping endpoints 0, 1, N-2, N-1
            interior = [x for x in merged if x not in (0, 1, total_frames - 2, total_frames - 1)]
            if not interior:
                merged = merged[:num_tiles]
                break
            merged.remove(interior[len(interior) // 2])
        return merged

    def generate_contact_sheet(
        self,
        video_path: str | Path,
        output_png_path: Optional[str | Path] = None,
        num_tiles: int = 9,
        columns: int = 3,
        tile_width: int = 420,
    ) -> Tuple[Path, List[Tuple[int, float, np.ndarray]], int]:
        """Build a labeled NxM contact sheet PNG highlighting frame index and timestamp."""
        vid_file = Path(video_path)
        sampled, total_frames = self.sample_risk_window_frames(vid_file, num_tiles=num_tiles)
        if not sampled:
            raise RuntimeError(f"Zero decodable frames extracted from {vid_file}")

        out_png = (
            Path(output_png_path)
            if output_png_path
            else vid_file.with_name(f"{vid_file.stem}_contact_sheet.png")
        )

        first_h, first_w = sampled[0][2].shape[:2]
        tile_height = max(120, int(round(tile_width * (first_h / max(1, first_w)))))
        rows = max(1, math.ceil(len(sampled) / columns))
        pad = 12
        header_h = 34

        sheet_w = columns * tile_width + (columns + 1) * pad
        sheet_h = header_h + rows * tile_height + (rows + 1) * pad
        canvas = Image.new("RGB", (sheet_w, sheet_h), (10, 15, 24))
        draw = ImageDraw.Draw(canvas)
        header_font = _load_qa_font(15)
        badge_font = _load_qa_font(12)

        draw.text(
            (pad, 9),
            f"STOCKCONT MOTION QA SHEET | {vid_file.name} | {total_frames} FRAMES",
            fill=(241, 245, 249),
            font=header_font,
        )

        for tile_pos, (frame_idx, ts_sec, bgr_frame) in enumerate(sampled):
            row = tile_pos // columns
            col = tile_pos % columns
            x = pad + col * (tile_width + pad)
            y = header_h + pad + row * (tile_height + pad)

            rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            thumb = Image.fromarray(rgb).resize((tile_width, tile_height), Image.Resampling.LANCZOS)
            canvas.paste(thumb, (x, y))
            draw.rectangle([x, y, x + tile_width - 1, y + tile_height - 1], outline=(56, 189, 248), width=1)
            draw.rectangle([x + 6, y + 6, x + 132, y + 26], fill=(15, 23, 42))
            draw.text((x + 11, y + 9), f"F#{frame_idx:03d} {ts_sec:.2f}s", fill=(56, 189, 248), font=badge_font)

        _atomic_save_png(canvas, out_png)
        return out_png, sampled, total_frames

    def audit_video(
        self,
        video_path: str | Path,
        bg_hex: str = "#070D17",
        fg_hex: str = "#F1F5F9",
        accent_hex: Optional[str] = "#38BDF8",
        personality: str = "cold_war_noir",
        min_motion_delta: Optional[float] = None,
        safe_margin_ratio: float = 0.05,
        generate_sheet: bool = True,
        contact_sheet_path: Optional[str | Path] = None,
        vision_critique: bool = False,
        vision_callback: Optional[Callable[[Path], str]] = None,
    ) -> MotionQAReport:
        """Execute full Level-1 deterministic QA + optional Level-2 Gemini Vision critique."""
        vid_file = Path(video_path)
        findings: List[MotionQAFinding] = []

        palette_ok, contrast_ratio, palette_findings = self.inspect_palette_contrast(
            bg_hex=bg_hex,
            fg_hex=fg_hex,
            accent_hex=accent_hex,
        )
        findings.extend(palette_findings)

        sheet_path: Optional[Path] = None
        if generate_sheet:
            sheet_path, sampled, _ = self.generate_contact_sheet(
                vid_file,
                output_png_path=contact_sheet_path,
            )
        else:
            sampled, _ = self.sample_risk_window_frames(vid_file)

        if len(sampled) < 2:
            findings.append(
                MotionQAFinding(
                    code="INSUFFICIENT_FRAMES",
                    severity="error",
                    message=f"Only {len(sampled)} decodable frame(s) found; motion audit requires >= 2.",
                )
            )
            return MotionQAReport(
                passed=False,
                score=0.0,
                video_path=vid_file.as_posix(),
                contact_sheet_path=sheet_path.as_posix() if sheet_path else None,
                contrast_ratio=contrast_ratio,
                min_motion_delta=0.0,
                max_motion_delta=0.0,
                frozen_frame_pairs=0,
                safe_margin_ok=True,
                sampled_frame_count=len(sampled),
                findings=findings,
            )

        # Inter-frame delta detection across sampled timeline
        deltas: List[float] = []
        frozen_pairs = 0
        for i in range(1, len(sampled)):
            prev_f = sampled[i - 1][2].astype(np.float32)
            curr_f = sampled[i][2].astype(np.float32)
            diff = float(np.mean(np.abs(curr_f - prev_f)))
            deltas.append(diff)
            if diff < 0.02:
                frozen_pairs += 1

        observed_min_delta = round(min(deltas), 4)
        observed_max_delta = round(max(deltas), 4)
        required_delta = (
            float(min_motion_delta)
            if min_motion_delta is not None
            else PERSONALITY_MIN_MOTION_DELTAS.get(personality, 0.10)
        )

        if observed_max_delta < required_delta:
            findings.append(
                MotionQAFinding(
                    code="FROZEN_OR_STAGNANT_MOTION",
                    severity="error",
                    message=(
                        f"Peak motion delta {observed_max_delta:.3f} is below '{personality}' "
                        f"minimum ({required_delta:.3f}); video appears static or stalled."
                    ),
                )
            )
        elif frozen_pairs >= max(2, len(deltas) // 2):
            findings.append(
                MotionQAFinding(
                    code="REPEATED_FROZEN_SEGMENTS",
                    severity="warning",
                    message=f"Detected {frozen_pairs} near-identical frame transitions across sampled timeline.",
                )
            )

        # Bright foreground pixel intrusion check inside extreme border strip (<2% margin)
        safe_margin_ok = True
        bg_luma = sum(_hex_to_rgb(bg_hex)) / 3.0
        border_strip_ratio = min(0.02, safe_margin_ratio * 0.5)
        for frame_idx, _, bgr in sampled:
            h, w = bgr.shape[:2]
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            bx = max(2, int(w * border_strip_ratio))
            by = max(2, int(h * border_strip_ratio))
            edge_pixels = np.concatenate(
                [
                    gray[:by, :].ravel(),
                    gray[h - by :, :].ravel(),
                    gray[:, :bx].ravel(),
                    gray[:, w - bx :].ravel(),
                ]
            )
            high_bright_ratio = float(np.mean(edge_pixels > max(180.0, bg_luma + 140.0)))
            if high_bright_ratio > 0.12:
                safe_margin_ok = False
                findings.append(
                    MotionQAFinding(
                        code="EDGE_BORDER_CLIPPING",
                        severity="warning",
                        frame_index=frame_idx,
                        message=(
                            f"High-luminance elements occupy {high_bright_ratio:.1%} of extreme outer border "
                            f"at frame #{frame_idx}; check title-safe margin."
                        ),
                    )
                )
                break

        critique_text: Optional[str] = None
        if vision_critique and sheet_path is not None:
            if vision_callback is not None:
                try:
                    critique_text = vision_callback(sheet_path)
                except Exception as exc:
                    logger.warning("Vision critique callback failed gracefully: %s", exc)
            else:
                critique_text = self._run_gemini_contact_sheet_critique(sheet_path)

        error_count = sum(1 for f in findings if f.severity == "error")
        warn_count = sum(1 for f in findings if f.severity == "warning")
        score = max(0.0, round(100.0 - error_count * 35.0 - warn_count * 10.0, 1))
        passed = palette_ok and error_count == 0

        return MotionQAReport(
            passed=passed,
            score=score,
            video_path=vid_file.as_posix(),
            contact_sheet_path=sheet_path.as_posix() if sheet_path else None,
            contrast_ratio=contrast_ratio,
            min_motion_delta=observed_min_delta,
            max_motion_delta=observed_max_delta,
            frozen_frame_pairs=frozen_pairs,
            safe_margin_ok=safe_margin_ok,
            sampled_frame_count=len(sampled),
            findings=findings,
            vision_critique=critique_text,
        )

    @staticmethod
    def _run_gemini_contact_sheet_critique(sheet_path: Path) -> Optional[str]:
        """Optional Level-2 Deliver-and-Verify critique on contact sheet via Gemini Vision."""
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            return None
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            img_bytes = sheet_path.read_bytes()
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    (
                        "Inspect this 3x3 motion graphics contact sheet. List any typography clipping, "
                        "low contrast, alignment drift, or frozen progression in max 3 short bullet points."
                    ),
                ],
            )
            return (resp.text or "").strip() or None
        except Exception as exc:
            logger.warning("Optional Gemini Vision contact-sheet critique skipped: %s", exc)
            return None
