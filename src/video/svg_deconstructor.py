"""StockCont & DarkFactory — Raster-to-Animated Semantic SVG Deconstructor.

Converts static archival emblems, seals, patent schematics, or logos into clean
multi-layer semantic SVGs (<g id="grid">, <g id="mark">, <g id="callouts">,
<g id="wordmark">) with HyperFrames seekable stroke animation and Faithful Landing
IoU + smoothness hard gates (inspired by nolangz/pixel2motion).
"""

from __future__ import annotations

import logging
import math
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.svg_deconstructor")


@dataclass
class SVGDeconstructionResult:
    """Result contract for semantic raster-to-SVG deconstruction."""

    success: bool
    source_image_path: str
    svg_path: Optional[str]
    html_path: Optional[str]
    svg_markup: str
    semantic_groups: List[str] = field(default_factory=list)
    path_count: int = 0
    total_vertices: int = 0
    faithful_landing_iou: float = 0.0
    smoothness_gate_passed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class RasterToAnimatedSVG:
    """Deconstruct static raster emblems/diagrams into clean semantic animated SVGs."""

    def deconstruct_raster(
        self,
        image_path: str | Path,
        output_svg_path: Optional[str | Path] = None,
        output_html_path: Optional[str | Path] = None,
        title: str = "DECLASSIFIED ARTIFACT",
        subtitle: str = "SEMANTIC VECTOR RECONSTRUCTION",
        max_paths: int = 48,
        max_vertices: int = 600,
        epsilon_ratio: float = 0.008,
        bg_hex: str = "#0B1524",
        stroke_hex: str = "#38BDF8",
        fill_hex: str = "#DDE8F3",
        canvas_width: int = 1280,
        canvas_height: int = 720,
        duration_sec: float = 4.0,
        seed: Optional[int] = None,
    ) -> SVGDeconstructionResult:
        """Trace raster shape groups into semantic SVG layers + verify Faithful Landing IoU."""
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for col_name, col_val in (("bg_hex", bg_hex), ("stroke_hex", stroke_hex), ("fill_hex", fill_hex)):
            if not isinstance(col_val, str) or not hex_pattern.match(col_val.strip()):
                raise ValueError(f"Invalid hex color for {col_name}: '{col_val}'")

        src = Path(image_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source raster not found for SVG deconstruction: {src}")

        img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
        if img is None or img.size == 0:
            raise ValueError(f"Unable to decode raster image: {src}")

        mask = self._extract_foreground_mask(img)
        src_h, src_w = mask.shape[:2]
        min_area = max(16.0, (src_h * src_w) * 0.001)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
        filtered.sort(key=cv2.contourArea, reverse=True)
        selected = filtered[:max_paths]

        if not selected:
            return SVGDeconstructionResult(
                success=False,
                source_image_path=src.as_posix(),
                svg_path=None,
                html_path=None,
                svg_markup="",
                error="No discernible foreground geometry found in source raster.",
            )

        # Normalize contours cleanly into title-safe stage box
        stage_x1 = int(canvas_width * 0.14)
        stage_y1 = int(canvas_height * 0.22)
        stage_w = int(canvas_width * 0.72)
        stage_h = int(canvas_height * 0.64)
        scale = min(stage_w / max(1, src_w), stage_h / max(1, src_h))
        offset_x = stage_x1 + (stage_w - src_w * scale) * 0.5
        offset_y = stage_y1 + (stage_h - src_h * scale) * 0.5

        path_elements: List[str] = []
        callout_elements: List[str] = []
        reconstructed_mask = np.zeros((canvas_height, canvas_width), dtype=np.uint8)
        target_canvas_mask = np.zeros((canvas_height, canvas_width), dtype=np.uint8)

        scaled_src = cv2.resize(
            mask,
            (max(1, int(round(src_w * scale))), max(1, int(round(src_h * scale)))),
            interpolation=cv2.INTER_NEAREST,
        )
        tx1 = int(round(offset_x))
        ty1 = int(round(offset_y))
        tx2 = min(canvas_width, tx1 + scaled_src.shape[1])
        ty2 = min(canvas_height, ty1 + scaled_src.shape[0])
        target_canvas_mask[ty1:ty2, tx1:tx2] = scaled_src[: ty2 - ty1, : tx2 - tx1]

        total_vertices = 0
        for idx, cnt in enumerate(selected):
            peri = cv2.arcLength(cnt, True)
            eps = max(1.2, epsilon_ratio * peri)
            approx = cv2.approxPolyDP(cnt, eps, True)
            pts_f = approx.reshape(-1, 2).astype(np.float64)
            pts_f[:, 0] = pts_f[:, 0] * scale + offset_x
            pts_f[:, 1] = pts_f[:, 1] * scale + offset_y
            pts_int = np.round(pts_f).astype(np.int32)
            if len(pts_int) < 3:
                continue

            total_vertices += len(pts_int)
            cv2.fillPoly(reconstructed_mask, [pts_int], 255)

            path_len = int(max(10.0, cv2.arcLength(pts_int.reshape(-1, 1, 2), True)))
            cmds = [f"M {pts_int[0][0]} {pts_int[0][1]}"] + [
                f"L {pt[0]} {pt[1]}" for pt in pts_int[1:]
            ] + ["Z"]
            d_attr = " ".join(cmds)
            delay = idx * 0.12
            path_elements.append(
                f'    <path id="mark-path-{idx}" class="mark-stroke" d="{d_attr}" '
                f'fill="{fill_hex}" fill-opacity="0.18" stroke="{stroke_hex}" stroke-width="2.5" '
                f'stroke-dasharray="{path_len}" stroke-dashoffset="{path_len}" '
                f'data-path-len="{path_len}" data-start="{delay:.2f}" data-duration="{max(0.8, duration_sec * 0.65):.2f}" />'
            )

            if idx < 3:
                cx = int(np.mean(pts_int[:, 0]))
                cy = int(np.mean(pts_int[:, 1]))
                anchor_x = min(canvas_width - 180, max(120, cx + (140 if cx < canvas_width // 2 else -140)))
                callout_elements.append(
                    f'    <line x1="{cx}" y1="{cy}" x2="{anchor_x}" y2="{cy - 24}" stroke="{stroke_hex}" stroke-width="1.5" opacity="0.85" />'
                )
                callout_elements.append(
                    f'    <circle cx="{cx}" cy="{cy}" r="4" fill="{stroke_hex}" />'
                )
                callout_elements.append(
                    f'    <text x="{anchor_x + (8 if anchor_x >= cx else -96)}" y="{cy - 28}" fill="{fill_hex}" '
                    f'font-family="Consolas, monospace" font-size="14">PART-{idx + 1:02d}</text>'
                )

        # Faithful Landing IoU diagnostic metric (pixel2motion contract)
        target_bool = target_canvas_mask > 0
        recon_bool = reconstructed_mask > 0
        intersection = int(np.logical_and(target_bool, recon_bool).sum())
        union = int(np.logical_or(target_bool, recon_bool).sum())
        faithful_iou = round(intersection / max(1, union), 4)

        path_count = len(path_elements)
        smoothness_passed = 1 <= path_count <= max_paths and total_vertices <= max_vertices and faithful_iou >= 0.45

        semantic_groups = ["grid", "mark", "callouts", "wordmark"]
        svg_markup = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_width} {canvas_height}" width="100%" height="100%">\n'
            f'  <defs>\n'
            f'    <pattern id="vecGrid" width="40" height="40" patternUnits="userSpaceOnUse">\n'
            f'      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1A3250" stroke-width="1"/>\n'
            f'    </pattern>\n'
            f'  </defs>\n'
            f'  <rect width="{canvas_width}" height="{canvas_height}" fill="{bg_hex}"/>\n'
            f'  <g id="grid" data-semantic="background_grid">\n'
            f'    <rect width="{canvas_width}" height="{canvas_height}" fill="url(#vecGrid)" opacity="0.65"/>\n'
            f'  </g>\n'
            f'  <g id="mark" data-semantic="vector_mark">\n'
            + "\n".join(path_elements)
            + '\n  </g>\n'
            f'  <g id="callouts" data-semantic="technical_callouts">\n'
            + "\n".join(callout_elements)
            + '\n  </g>\n'
            f'  <g id="wordmark" data-semantic="title_wordmark">\n'
            f'    <text x="64" y="72" fill="{fill_hex}" font-family="Arial, sans-serif" font-weight="bold" font-size="34">{_escape_xml(title)}</text>\n'
            f'    <text x="64" y="106" fill="{stroke_hex}" font-family="Consolas, monospace" font-size="18">{_escape_xml(subtitle)}</text>\n'
            f'  </g>\n'
            f'</svg>\n'
        )

        # Validate well-formed XML deterministically
        ET.fromstring(svg_markup)

        svg_out: Optional[Path] = None
        if output_svg_path is not None:
            svg_out = _atomic_write_text(Path(output_svg_path), svg_markup)

        html_out: Optional[Path] = None
        if output_html_path is not None:
            resolved_seed = seed if seed is not None else (zlib.crc32(src.name.encode("utf-8")) & 0xFFFFFFFF)
            html_content = self.build_seekable_svg_html(
                svg_markup=svg_markup,
                title=title,
                duration_sec=duration_sec,
                width=canvas_width,
                height=canvas_height,
                seed=resolved_seed,
            )
            html_out = _atomic_write_text(Path(output_html_path), html_content)

        return SVGDeconstructionResult(
            success=True,
            source_image_path=src.as_posix(),
            svg_path=svg_out.as_posix() if svg_out else None,
            html_path=html_out.as_posix() if html_out else None,
            svg_markup=svg_markup,
            semantic_groups=semantic_groups,
            path_count=path_count,
            total_vertices=total_vertices,
            faithful_landing_iou=faithful_iou,
            smoothness_gate_passed=smoothness_passed,
        )

    @staticmethod
    def _extract_foreground_mask(img: np.ndarray) -> np.ndarray:
        """Extract clean binary foreground mask supporting RGBA transparency or gray contrast."""
        if img.ndim == 3 and img.shape[2] == 4:
            alpha = img[:, :, 3]
            if int(alpha.min()) < 245 and int(alpha.max()) > 32:
                return np.where(alpha > 32, 255, 0).astype(np.uint8)

        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        border_vals = np.concatenate([blurred[0, :], blurred[-1, :], blurred[:, 0], blurred[:, -1]])
        bg_is_light = float(np.median(border_vals)) > 127.0
        thresh_flag = cv2.THRESH_BINARY_INV if bg_is_light else cv2.THRESH_BINARY
        _, binary = cv2.threshold(blurred, 0, 255, thresh_flag | cv2.THRESH_OTSU)
        return binary

    @staticmethod
    def build_seekable_svg_html(
        svg_markup: str,
        title: str,
        duration_sec: float = 4.0,
        width: int = 1280,
        height: int = 720,
        seed: int = 1337,
    ) -> str:
        """Wrap semantic SVG inside a deterministic HyperFrames/GSAP seekable player."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{_escape_xml(title)}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: {width}px; height: {height}px; overflow: hidden; background: #0B1524; }}
    #vector-stage {{ width: 100%; height: 100%; }}
    .mark-stroke {{ transition-property: stroke-dashoffset, opacity; will-change: stroke-dashoffset, opacity; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
</head>
<body>
  <div id="vector-stage" data-seed="{seed}" data-start="0" data-duration="{duration_sec}">
    {svg_markup}
  </div>
  <script>
    window.__timelines = window.__timelines || [];
    window.__hfSeed = {seed};
    (function initSemanticVectorTimeline() {{
      const totalDuration = {duration_sec};
      let tl;
      if (window.gsap) {{
        tl = window.gsap.timeline({{ paused: true }});
        tl.to(".mark-stroke", {{ strokeDashoffset: 0, duration: totalDuration * 0.65, stagger: 0.12, ease: "power2.out" }});
      }} else {{
        let t = 0;
        tl = {{
          paused: true,
          duration: () => totalDuration,
          seek: (sec) => {{
            t = Math.max(0, Math.min(totalDuration, Number(sec) || 0));
            const pct = totalDuration > 0 ? Math.min(1, t / (totalDuration * 0.65)) : 1;
            document.querySelectorAll(".mark-stroke").forEach((el) => {{
              const full = Number(el.getAttribute("data-path-len") || 0);
              el.setAttribute("stroke-dashoffset", String(Math.round(full * (1 - pct))));
            }});
          }},
          progress: () => (totalDuration > 0 ? t / totalDuration : 0),
        }};
      }}
      window.__timelines.push(tl);
    }})();
  </script>
</body>
</html>
"""
