"""HyperFrames Motion Engine & Isometric Anatomy Vector Generator.

Deterministic motion graphics engine unifying:
1. HyperFrames HTML/CSS/GSAP seekable composition authoring (`window.__timelines`,
   `paused: true`, `data-start`, `data-duration`) with optional local CLI render.
2. Four-tone isometric mechanical/CAD SVG generator inspired by wheresryan22/anatomy.
3. Fast offline procedural OpenCV/Pillow + FFmpeg vector renderer for instant,
   zero-OOM overlays and 4K B2B motion loops with Windows FFmpeg PATH injection.
"""

from __future__ import annotations

import logging
import math
import os
import random
import re
import shutil
import subprocess
import uuid
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.video.ffmpeg_processor import (
    get_ffmpeg_binary,
    get_ffprobe_binary,
    probe_video,
)

logger = logging.getLogger("hyperframes_engine")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_MOTION_OUTPUT_DIR = DATA_DIR / "final" / "motion_overlays"
DEFAULT_STOCK_VIDEOS_DIR = DATA_DIR / "final" / "videos"

ANATOMY_FOUR_TONE_PALETTE: Dict[str, str] = {
    "bg_blueprint": "#0B1524",
    "grid_line": "#1A3250",
    "top_face": "#DDE8F3",
    "left_face": "#8CA6C2",
    "right_face": "#4C6B8A",
    "line_ink": "#0A111A",
    "callout_accent": "#38BDF8",
    "text_primary": "#F1F5F9",
}

MOTION_PERSONALITIES: Dict[str, Dict[str, Any]] = {
    "cold_war_noir": {
        "duration_band": (1.2, 2.4),
        "easing_css": "cubic-bezier(0.22, 1.0, 0.36, 1.0)",
        "max_overshoot_pct": 0.0,
        "min_motion_delta": 0.10,
        "allowed_properties": ("transform", "opacity"),
        "description": "Measured archival tension with zero bounce and deliberate easing.",
    },
    "clinical_fintech": {
        "duration_band": (0.6, 1.4),
        "easing_css": "cubic-bezier(0.4, 0.0, 0.2, 1.0)",
        "max_overshoot_pct": 0.02,
        "min_motion_delta": 0.18,
        "allowed_properties": ("transform", "opacity"),
        "description": "Crisp analytical SaaS telemetry snap with tight deceleration.",
    },
    "executive_corporate": {
        "duration_band": (0.8, 1.8),
        "easing_css": "cubic-bezier(0.16, 1.0, 0.3, 1.0)",
        "max_overshoot_pct": 0.03,
        "min_motion_delta": 0.14,
        "allowed_properties": ("transform", "opacity"),
        "description": "Balanced boardroom clarity tuned for B2B copy-space loops.",
    },
    "high_energy_hook": {
        "duration_band": (0.35, 0.9),
        "easing_css": "cubic-bezier(0.34, 1.56, 0.64, 1.0)",
        "max_overshoot_pct": 0.08,
        "min_motion_delta": 0.30,
        "allowed_properties": ("transform", "opacity"),
        "description": "Fast punchy opening beat engineered for sub-second scroll stops.",
    },
}

MOTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # DarkFactory Documentary Overlays
    "tactical_hud": {
        "category": "darkfactory",
        "personality": "cold_war_noir",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 5.0,
        "muted": True,
        "accent_hex": "#38BDF8",
        "bg_hex": "#070D17",
        "description": "Classified military/radar HUD with rotating reticle and live telemetry bars.",
    },
    "declassified_dossier": {
        "category": "darkfactory",
        "personality": "cold_war_noir",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 6.0,
        "muted": True,
        "accent_hex": "#EF4444",
        "bg_hex": "#13100E",
        "description": "Archival declassified dossier with sliding redaction bars and stamp reveal.",
    },
    "lower_third": {
        "category": "darkfactory",
        "personality": "cold_war_noir",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 4.0,
        "muted": True,
        "accent_hex": "#F59E0B",
        "bg_hex": "#0A0F18",
        "description": "Editorial documentary lower-third title card with sliding accent bar.",
    },
    "anatomy_mechanical": {
        "category": "darkfactory",
        "personality": "clinical_fintech",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 6.0,
        "muted": True,
        "accent_hex": "#38BDF8",
        "bg_hex": ANATOMY_FOUR_TONE_PALETTE["bg_blueprint"],
        "description": "Exploded 4-tone isometric CAD diagram with callout leader lines.",
    },
    # Sprint 4 Zero-Blob Procedural Style Plates (anidoodle-inspired)
    "blueprint_notebook": {
        "category": "darkfactory",
        "personality": "cold_war_noir",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 6.0,
        "muted": True,
        "accent_hex": "#38BDF8",
        "bg_hex": "#0A192F",
        "description": "Procedural drafting blueprint plate with seeded calibration marks and CAD arrows.",
    },
    "risograph_declassified": {
        "category": "darkfactory",
        "personality": "cold_war_noir",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 6.0,
        "muted": True,
        "accent_hex": "#FB7185",
        "bg_hex": "#141210",
        "description": "Procedural dual-ink risograph halftone plate with deterministic paper grain.",
    },
    "cut_paper_editorial": {
        "category": "stock_b2b",
        "personality": "executive_corporate",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#F59E0B",
        "bg_hex": "#0F172A",
        "description": "Zero-blob stepped cut-paper architectural planes with 40% editorial copy-space.",
    },
    "deconstructed_emblem_vector": {
        "category": "darkfactory",
        "personality": "clinical_fintech",
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 5.0,
        "muted": True,
        "accent_hex": "#38BDF8",
        "bg_hex": "#0B1524",
        "description": "Semantic raster-to-SVG deconstructed vector assembly with Faithful Landing verification.",
    },
    # StockCont Sprint 2 B2B 4K Silent Motion Loops
    "saas_fintech_telemetry_ui": {
        "category": "stock_b2b",
        "personality": "clinical_fintech",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#10B981",
        "bg_hex": "#09111E",
        "description": "Clean isometric FinTech analytics UI cards with real-time growth curves.",
    },
    "isometric_architecture_flow": {
        "category": "stock_b2b",
        "personality": "executive_corporate",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#60A5FA",
        "bg_hex": "#0B1524",
        "description": "4-tone isometric cloud architecture nodes with animated data conduits.",
    },
    "kinetic_grid_background": {
        "category": "stock_b2b",
        "personality": "executive_corporate",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#818CF8",
        "bg_hex": "#0F172A",
        "description": "Minimalist geometric corporate kinetic grid motion backdrop.",
    },
    "hud_data_overlay_loop": {
        "category": "stock_b2b",
        "personality": "high_energy_hook",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#22D3EE",
        "bg_hex": "#060E17",
        "description": "Enterprise HUD data telemetry loop engineered with 40% central copy-space.",
    },
    # Sprint 10 Vertical 9:16 Shorts & Social Templates
    "vertical_dossier_short": {
        "category": "shorts_social",
        "personality": "high_energy_hook",
        "default_width": 1080,
        "default_height": 1920,
        "default_fps": 30,
        "default_duration_sec": 15.0,
        "muted": False,
        "accent_hex": "#F59E0B",
        "bg_hex": "#090F1A",
        "description": "Vertical 9:16 DarkFactory signal dossier with top-safe headline and kinetic subtitle lane.",
    },
    "vertical_kinetic_quote": {
        "category": "shorts_social",
        "personality": "executive_corporate",
        "default_width": 1080,
        "default_height": 1920,
        "default_fps": 30,
        "default_duration_sec": 15.0,
        "muted": False,
        "accent_hex": "#38BDF8",
        "bg_hex": "#0B1324",
        "description": "Vertical 9:16 typographic reel backdrop preserving mobile safe-zones.",
    },
    # Sprint 11 Zero-Trademark B2B Promo & Demo Templates (4K silent -an stock ready)
    "onetake_bento_launch": {
        "category": "stock_b2b",
        "personality": "clinical_fintech",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#38BDF8",
        "bg_hex": "#070D19",
        "description": "Continuous zero-cut OneTake camera glide across abstract SaaS Bento UI modules (trademark-free).",
    },
    "cursor_spotlight_demo": {
        "category": "stock_b2b",
        "personality": "clinical_fintech",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#F59E0B",
        "bg_hex": "#0A101E",
        "description": "Animated cursor spotlight zooming across synthetic wireframe analytics charts (trademark-free).",
    },
    "kpi_metric_cascade": {
        "category": "stock_b2b",
        "personality": "executive_corporate",
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#10B981",
        "bg_hex": "#08141B",
        "description": "Sequential executive KPI growth cascade with spline trajectories and 40% editorial copy-space.",
    },
}


@dataclass
class MotionCompositionResult:
    """Result contract for HyperFrames and procedural motion renders."""

    success: bool
    template: str
    category: str
    output_video_path: Optional[Path]
    html_path: Optional[Path]
    svg_path: Optional[Path]
    duration_sec: float
    width: int
    height: int
    fps: int
    render_backend: str
    is_preview_gate: bool = False
    has_audio: bool = False
    video_props: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    seed: Optional[int] = None
    personality: Optional[str] = None
    contact_sheet_path: Optional[Path] = None
    qa_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result with normalized POSIX paths."""
        data = asdict(self)
        for key in ("output_video_path", "html_path", "svg_path", "contact_sheet_path"):
            val = data.get(key)
            data[key] = val.as_posix() if isinstance(val, Path) else val
        return data


def _derive_seed(
    template: str,
    title: str,
    subtitle: str,
    explicit_seed: Optional[int] = None,
) -> int:
    """Compute a deterministic 32-bit seed cleanly eliminating Math.random() drift."""
    if explicit_seed is not None:
        return int(explicit_seed) & 0xFFFFFFFF
    payload = f"{template}|{title.strip()}|{subtitle.strip()}".encode("utf-8")
    return zlib.crc32(payload) & 0xFFFFFFFF


def _apply_easing(progress: float, personality_key: str) -> float:
    """Apply deterministic LottieFiles-inspired easing curves per motion personality."""
    t = max(0.0, min(1.0, float(progress)))
    if personality_key == "high_energy_hook":
        # Mild damped overshoot (~8%) inspired by snappy UI hooks
        c1 = 1.70158 * 0.45
        c3 = c1 + 1.0
        eased = 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)
        return max(0.0, min(1.08, eased))
    if personality_key == "clinical_fintech":
        # Fast out, sharp analytical settle
        return 1.0 - (1.0 - t) ** 3
    if personality_key == "executive_corporate":
        # Smooth ease-out quintic
        return 1.0 - (1.0 - t) ** 4
    # Default: cold_war_noir (linear-in, weighted cosine deceleration, zero bounce)
    return 0.5 * (1.0 - math.cos(math.pi * t))


def _hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    cleaned = hex_color.lstrip("#")
    r, g, b = int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16)
    return (b, g, r)


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    cleaned = hex_color.lstrip("#")
    return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower()).strip("_")
    return slug[:64] or "motion_clip"


def _atomic_write_text(path: Path, content: str) -> None:
    """Write UTF-8 text atomically via .tmp file (ADR-01, ADR-02)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


class HyperFramesMotionEngine:
    """Deterministic motion overlay & isometric diagram generator."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_MOTION_OUTPUT_DIR

    def resolve_ffmpeg_env(self) -> Dict[str, str]:
        """Return subprocess environment with FFmpeg/FFprobe directory injected into PATH."""
        env = dict(os.environ)
        ffmpeg_bin = get_ffmpeg_binary()
        ffprobe_bin = get_ffprobe_binary()
        ffmpeg_dir = str(Path(ffmpeg_bin).parent)
        ffprobe_dir = str(Path(ffprobe_bin).parent)

        sep = os.pathsep
        existing_parts = [p for p in env.get("PATH", "").split(sep) if p]
        for extra_dir in (ffprobe_dir, ffmpeg_dir):
            if extra_dir and extra_dir not in existing_parts:
                existing_parts.insert(0, extra_dir)
        env["PATH"] = sep.join(existing_parts)
        env["FFMPEG_PATH"] = ffmpeg_bin
        env["FFPROBE_PATH"] = ffprobe_bin
        return env

    def build_anatomy_isometric_svg(
        self,
        title: str,
        subtitle: str = "",
        components: Optional[List[str]] = None,
    ) -> str:
        """Build a 4-tone isometric schematic SVG inspired by wheresryan22/anatomy."""
        labels = components or ["Primary Core", "Conduit Array", "Thermal Shield"]
        p = ANATOMY_FOUR_TONE_PALETTE
        layers_svg: List[str] = []

        base_cx, base_cy = 560, 290
        for idx in range(3):
            y_shift = idx * 125
            layer_label = labels[idx] if idx < len(labels) else f"Assembly Stage {idx + 1}"
            top_pts = f"{base_cx},{base_cy + y_shift - 52} {base_cx + 150},{base_cy + y_shift} {base_cx},{base_cy + y_shift + 52} {base_cx - 150},{base_cy + y_shift}"
            left_pts = f"{base_cx - 150},{base_cy + y_shift} {base_cx},{base_cy + y_shift + 52} {base_cx},{base_cy + y_shift + 92} {base_cx - 150},{base_cy + y_shift + 40}"
            right_pts = f"{base_cx},{base_cy + y_shift + 52} {base_cx + 150},{base_cy + y_shift} {base_cx + 150},{base_cy + y_shift + 40} {base_cx},{base_cy + y_shift + 92}"

            callout_y = base_cy + y_shift + 18
            layers_svg.append(
                f"""  <g class="iso-layer" data-layer="{idx}" data-start="{idx * 0.4:.1f}" data-duration="3.0">
    <polygon points="{top_pts}" fill="{p['top_face']}" stroke="{p['line_ink']}" stroke-width="2.5"/>
    <polygon points="{left_pts}" fill="{p['left_face']}" stroke="{p['line_ink']}" stroke-width="2.5"/>
    <polygon points="{right_pts}" fill="{p['right_face']}" stroke="{p['line_ink']}" stroke-width="2.5"/>
    <polyline points="{base_cx + 115},{callout_y - 10} {base_cx + 255},{callout_y - 10}" fill="none" stroke="{p['callout_accent']}" stroke-width="2"/>
    <circle cx="{base_cx + 115}" cy="{callout_y - 10}" r="4.5" fill="{p['callout_accent']}"/>
    <text x="{base_cx + 265}" y="{callout_y - 5}" fill="{p['text_primary']}" font-family="Consolas, monospace" font-size="18">{self._escape_xml(layer_label)}</text>
  </g>"""
            )

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="100%" height="100%">\n'
            f'  <defs>\n'
            f'    <pattern id="isoGrid" width="40" height="40" patternUnits="userSpaceOnUse">\n'
            f'      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{p["grid_line"]}" stroke-width="1"/>\n'
            f'    </pattern>\n'
            f'  </defs>\n'
            f'  <rect width="1280" height="720" fill="{p["bg_blueprint"]}"/>\n'
            f'  <rect width="1280" height="720" fill="url(#isoGrid)" opacity="0.65"/>\n'
            f'  <text x="64" y="74" fill="{p["text_primary"]}" font-family="Arial, sans-serif" font-weight="bold" font-size="34">{self._escape_xml(title)}</text>\n'
            f'  <text x="64" y="106" fill="{p["callout_accent"]}" font-family="Consolas, monospace" font-size="18">{self._escape_xml(subtitle or "4-TONE ISOMETRIC SYSTEM SCHEMATIC")}</text>\n'
            + "\n".join(layers_svg)
            + "\n</svg>\n"
        )

    def build_composition_html(
        self,
        template: str,
        title: str,
        subtitle: str = "",
        duration_sec: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        data: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        personality: Optional[str] = None,
    ) -> str:
        """Generate deterministic HTML5/GSAP composition following HyperFrames timeline contract."""
        if template not in MOTION_TEMPLATES:
            raise ValueError(f"Unknown motion template '{template}'. Valid: {sorted(MOTION_TEMPLATES)}")

        spec = MOTION_TEMPLATES[template]
        extra = data or {}
        accent = spec["accent_hex"]
        bg = spec["bg_hex"]
        resolved_seed = _derive_seed(template, title, subtitle, explicit_seed=seed)
        personality_key = personality or spec.get("personality", "cold_war_noir")
        if personality_key not in MOTION_PERSONALITIES:
            raise ValueError(f"Unknown motion personality '{personality_key}'. Valid: {sorted(MOTION_PERSONALITIES)}")
        pers_spec = MOTION_PERSONALITIES[personality_key]

        inner_markup = ""
        if template == "deconstructed_emblem_vector" and extra.get("image_path"):
            from src.video.svg_deconstructor import RasterToAnimatedSVG

            vec_res = RasterToAnimatedSVG().deconstruct_raster(
                image_path=extra["image_path"],
                title=title,
                subtitle=subtitle or "SEMANTIC VECTOR RECONSTRUCTION",
                bg_hex=bg,
                stroke_hex=accent,
                canvas_width=width,
                canvas_height=height,
                duration_sec=duration_sec,
                seed=resolved_seed,
            )
            inner_markup = vec_res.svg_markup or self.build_anatomy_isometric_svg(
                title=title, subtitle=subtitle, components=extra.get("components")
            )
        elif template in ("anatomy_mechanical", "isometric_architecture_flow", "deconstructed_emblem_vector"):
            components = extra.get("components")
            inner_markup = self.build_anatomy_isometric_svg(title=title, subtitle=subtitle, components=components)
        else:
            inner_markup = (
                f'<div class="hud-frame" data-start="0" data-duration="{duration_sec}">\n'
                f'  <div class="accent-bar"></div>\n'
                f'  <h1 class="title">{self._escape_xml(title)}</h1>\n'
                f'  <p class="subtitle">{self._escape_xml(subtitle)}</p>\n'
                f'</div>'
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{self._escape_xml(title)}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: {width}px; height: {height}px; overflow: hidden;
      background: {bg}; color: #F8FAFC; font-family: Arial, Helvetica, sans-serif;
    }}
    #scene {{
      position: relative; width: 100%; height: 100%;
      display: flex; align-items: center; justify-content: center;
    }}
    .hud-frame, .iso-layer {{
      transition-property: transform, opacity;
      transition-timing-function: {pers_spec["easing_css"]};
      will-change: transform, opacity;
    }}
    .hud-frame {{
      width: 82%; border: 2px solid {accent}; padding: 42px;
      background: rgba(10, 17, 28, 0.88);
    }}
    .accent-bar {{ width: 96px; height: 6px; background: {accent}; margin-bottom: 18px; }}
    .title {{ font-size: 54px; letter-spacing: 0.04em; text-transform: uppercase; }}
    .subtitle {{ font-size: 24px; color: {accent}; margin-top: 12px; font-family: Consolas, monospace; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
</head>
<body>
  <div id="scene" data-template="{template}" data-personality="{personality_key}" data-seed="{resolved_seed}" data-fps="{fps}" data-start="0" data-duration="{duration_sec}">
    {inner_markup}
  </div>
  <script>
    window.__timelines = window.__timelines || [];
    window.__hfSeed = {resolved_seed};
    // Pure deterministic Mulberry32 PRNG (anidoodle Zero-Randomness contract)
    window.__hfRng = function(seedVal) {{
      let state = (seedVal >>> 0) || {resolved_seed};
      return function() {{
        state = (state + 0x6D2B79F5) >>> 0;
        let t = Math.imul(state ^ (state >>> 15), 1 | state);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      }};
    }};
    (function initHyperFramesContract() {{
      const totalDuration = {duration_sec};
      let tl;
      if (window.gsap) {{
        tl = window.gsap.timeline({{ paused: true }});
        tl.fromTo(".hud-frame, .iso-layer", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: Math.min(1.2, totalDuration * 0.4), stagger: 0.25 }});
      }} else {{
        let currentSec = 0;
        tl = {{
          paused: true,
          duration: () => totalDuration,
          seek: (sec) => {{ currentSec = Math.max(0, Math.min(totalDuration, Number(sec) || 0)); }},
          progress: () => (totalDuration > 0 ? currentSec / totalDuration : 0),
        }};
      }}
      window.__timelines.push(tl);
    }})();
  </script>
</body>
</html>
"""

    def render_preview_gate(
        self,
        template: str,
        title: str,
        subtitle: str = "",
        output_path: Optional[str | Path] = None,
        duration_sec: float = 20.0,
        max_duration_sec: float = 20.0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        use_hyperframes_cli: bool = False,
        force_procedural: bool = True,
        seed: Optional[int] = None,
        personality: Optional[str] = None,
        run_qa_gate: bool = True,
        vision_critique: bool = False,
    ) -> MotionCompositionResult:
        """Render a deterministic preview clamped strictly to <= 20s before full commitment."""
        capped_limit = min(float(max_duration_sec), 20.0)
        clamped_duration = max(0.5, min(float(duration_sec), capped_limit))
        result = self.render_motion_clip(
            template=template,
            title=title,
            subtitle=subtitle,
            output_path=output_path,
            duration_sec=clamped_duration,
            width=width,
            height=height,
            fps=fps,
            data=data,
            use_hyperframes_cli=use_hyperframes_cli,
            force_procedural=force_procedural,
            muted=True,
            seed=seed,
            personality=personality,
            run_qa_gate=run_qa_gate,
            vision_critique=vision_critique,
        )
        result.is_preview_gate = True
        return result

    def render_b2b_stock_clip(
        self,
        template: str,
        title: str,
        subtitle: str = "",
        output_dir: Optional[Path] = None,
        duration_sec: float = 8.0,
        resolution: Tuple[int, int] = (3840, 2160),
        fps: int = 30,
        force_procedural: bool = True,
        seed: Optional[int] = None,
        personality: Optional[str] = None,
        run_qa_gate: bool = False,
    ) -> MotionCompositionResult:
        """Render a silent (-an) 4K B2B motion asset destined for StockCont video agencies."""
        target_dir = Path(output_dir) if output_dir else DEFAULT_STOCK_VIDEOS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{_slugify(template)}_{_slugify(title)}.mp4"
        return self.render_motion_clip(
            template=template,
            title=title,
            subtitle=subtitle,
            output_path=out_path,
            duration_sec=duration_sec,
            width=resolution[0],
            height=resolution[1],
            fps=fps,
            force_procedural=force_procedural,
            muted=True,
            seed=seed,
            personality=personality,
            run_qa_gate=run_qa_gate,
        )

    def render_motion_clip(
        self,
        template: str,
        title: str,
        subtitle: str = "",
        output_path: Optional[str | Path] = None,
        duration_sec: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        use_hyperframes_cli: bool = False,
        force_procedural: bool = False,
        muted: bool = True,
        seed: Optional[int] = None,
        personality: Optional[str] = None,
        run_qa_gate: bool = False,
        vision_critique: bool = False,
        strict_qa: bool = False,
    ) -> MotionCompositionResult:
        """Render HTML/SVG contracts and encode the final MP4 motion clip."""
        if template not in MOTION_TEMPLATES:
            raise ValueError(f"Unknown motion template '{template}'. Valid: {sorted(MOTION_TEMPLATES)}")

        spec = MOTION_TEMPLATES[template]
        dur = max(0.5, float(duration_sec if duration_sec is not None else spec["default_duration_sec"]))
        w = int(width if width is not None else spec["default_width"])
        h = int(height if height is not None else spec["default_height"])
        target_fps = int(fps if fps is not None else spec["default_fps"])
        resolved_seed = _derive_seed(template, title, subtitle, explicit_seed=seed)
        personality_key = personality or spec.get("personality", "cold_war_noir")
        if personality_key not in MOTION_PERSONALITIES:
            raise ValueError(f"Unknown motion personality '{personality_key}'. Valid: {sorted(MOTION_PERSONALITIES)}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_video = Path(output_path) if output_path else self.output_dir / f"{_slugify(template)}_{_slugify(title)}.mp4"
        out_video.parent.mkdir(parents=True, exist_ok=True)

        html_path = out_video.with_suffix(".html")
        html_content = self.build_composition_html(
            template=template,
            title=title,
            subtitle=subtitle,
            duration_sec=dur,
            width=w,
            height=h,
            fps=target_fps,
            data=data,
            seed=resolved_seed,
            personality=personality_key,
        )
        _atomic_write_text(html_path, html_content)

        svg_path: Optional[Path] = None
        if template == "deconstructed_emblem_vector" and (data or {}).get("image_path"):
            from src.video.svg_deconstructor import RasterToAnimatedSVG

            svg_path = out_video.with_suffix(".svg")
            RasterToAnimatedSVG().deconstruct_raster(
                image_path=(data or {})["image_path"],
                output_svg_path=svg_path,
                title=title,
                subtitle=subtitle or "SEMANTIC VECTOR RECONSTRUCTION",
                bg_hex=spec["bg_hex"],
                stroke_hex=spec["accent_hex"],
                duration_sec=dur,
                seed=resolved_seed,
            )
        elif template in ("anatomy_mechanical", "isometric_architecture_flow", "deconstructed_emblem_vector"):
            svg_path = out_video.with_suffix(".svg")
            svg_content = self.build_anatomy_isometric_svg(
                title=title,
                subtitle=subtitle,
                components=(data or {}).get("components"),
            )
            _atomic_write_text(svg_path, svg_content)

        backend_used = "procedural_ffmpeg"
        rendered_ok = False
        error_msg: Optional[str] = None

        if use_hyperframes_cli and not force_procedural:
            rendered_ok = self._try_hyperframes_cli(html_path=html_path, output_video=out_video)
            if rendered_ok:
                backend_used = "hyperframes_cli"

        if not rendered_ok:
            rendered_ok, error_msg = self._render_procedural_mp4(
                template=template,
                title=title,
                subtitle=subtitle,
                output_video=out_video,
                duration_sec=dur,
                width=w,
                height=h,
                fps=target_fps,
                data=data,
                muted=muted,
                seed=resolved_seed,
                personality=personality_key,
            )
            backend_used = "procedural_ffmpeg"

        video_props_dict: Optional[Dict[str, Any]] = None
        has_audio_stream = False
        qa_report_dict: Optional[Dict[str, Any]] = None
        sheet_path: Optional[Path] = None

        if rendered_ok and out_video.exists():
            props = probe_video(out_video)
            video_props_dict = asdict(props)
            has_audio_stream = props.has_audio

            if run_qa_gate:
                from src.video.motion_qa import MotionQAInspector

                inspector = MotionQAInspector()
                qa_res = inspector.audit_video(
                    video_path=out_video,
                    bg_hex=spec["bg_hex"],
                    fg_hex="#F1F5F9",
                    accent_hex=spec["accent_hex"],
                    personality=personality_key,
                    generate_sheet=True,
                    vision_critique=vision_critique,
                )
                qa_report_dict = qa_res.to_dict()
                if qa_res.contact_sheet_path:
                    sheet_path = Path(qa_res.contact_sheet_path)
                if strict_qa and not qa_res.passed:
                    rendered_ok = False
                    error_msg = f"Motion QA Gate failed (score={qa_res.score}): {[f.code for f in qa_res.findings]}"

        return MotionCompositionResult(
            success=rendered_ok,
            template=template,
            category=spec["category"],
            output_video_path=out_video if rendered_ok else None,
            html_path=html_path,
            svg_path=svg_path,
            duration_sec=dur,
            width=w,
            height=h,
            fps=target_fps,
            render_backend=backend_used,
            is_preview_gate=False,
            has_audio=has_audio_stream,
            video_props=video_props_dict,
            error=error_msg,
            seed=resolved_seed,
            personality=personality_key,
            contact_sheet_path=sheet_path,
            qa_report=qa_report_dict,
        )

    def _try_hyperframes_cli(self, html_path: Path, output_video: Path) -> bool:
        """Attempt rendering via local HyperFrames CLI if installed."""
        hf_bin = shutil.which("hyperframes")
        cmd: Optional[List[str]] = None
        if hf_bin:
            cmd = [hf_bin, "render", html_path.as_posix(), "--output", output_video.as_posix()]
        else:
            npx_bin = shutil.which("npx")
            if npx_bin:
                cmd = [
                    npx_bin,
                    "--yes",
                    "@heygen/hyperframes",
                    "render",
                    html_path.as_posix(),
                    "--output",
                    output_video.as_posix(),
                ]
        if not cmd:
            return False

        try:
            proc = subprocess.run(
                cmd,
                env=self.resolve_ffmpeg_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
            )
            return proc.returncode == 0 and output_video.exists() and output_video.stat().st_size > 0
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("HyperFrames CLI fallback triggered (%s); using procedural renderer.", exc)
            return False

    def _render_procedural_mp4(
        self,
        template: str,
        title: str,
        subtitle: str,
        output_video: Path,
        duration_sec: float,
        width: int,
        height: int,
        fps: int,
        data: Optional[Dict[str, Any]],
        muted: bool,
        seed: Optional[int] = None,
        personality: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Render crisp procedural frames in memory and pipe directly to FFmpeg H.264."""
        ffmpeg_bin = get_ffmpeg_binary()
        total_frames = max(1, int(round(duration_sec * fps)))
        spec = MOTION_TEMPLATES[template]
        resolved_seed = _derive_seed(template, title, subtitle, explicit_seed=seed)
        personality_key = personality or spec.get("personality", "cold_war_noir")

        cmd: List[str] = [
            ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-nostats",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{width}x{height}",
            "-pix_fmt",
            "bgr24",
            "-r",
            str(fps),
            "-i",
            "-",
        ]
        if not muted:
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest", "-c:a", "aac"])
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
                output_video.as_posix(),
            ]
        )

        proc: Optional[subprocess.Popen[bytes]] = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=self.resolve_ffmpeg_env(),
            )
            assert proc.stdin is not None
            for idx in range(total_frames):
                progress = idx / max(1, total_frames - 1)
                frame = self._compose_frame(
                    template=template,
                    spec=spec,
                    title=title,
                    subtitle=subtitle,
                    width=width,
                    height=height,
                    progress=progress,
                    data=data or {},
                    seed=resolved_seed,
                    personality=personality_key,
                )
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            stderr_bytes = proc.stderr.read() if proc.stderr else b""
            proc.wait(timeout=120)
            if proc.returncode != 0 or not output_video.exists() or output_video.stat().st_size == 0:
                err_txt = stderr_bytes.decode("utf-8", errors="replace")[-500:]
                return False, f"FFmpeg exited {proc.returncode}: {err_txt}"
            return True, None
        except (OSError, subprocess.SubprocessError) as exc:
            err_detail = str(exc)
            if proc is not None and proc.stderr:
                try:
                    stderr_tail = proc.stderr.read().decode("utf-8", errors="replace")[-500:]
                    if stderr_tail.strip():
                        err_detail = f"{err_detail}: {stderr_tail}"
                except Exception:
                    pass
            return False, err_detail
        finally:
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

    def _compose_frame(
        self,
        template: str,
        spec: Dict[str, Any],
        title: str,
        subtitle: str,
        width: int,
        height: int,
        progress: float,
        data: Dict[str, Any],
        seed: Optional[int] = None,
        personality: Optional[str] = None,
    ) -> np.ndarray:
        """Render one BGR24 numpy frame parameterized by template family."""
        bg_hex = str((data or {}).get("bg_hex") or spec["bg_hex"])
        accent_hex = str((data or {}).get("accent_hex") or spec["accent_hex"])
        bg_bgr = _hex_to_bgr(bg_hex)
        accent_bgr = _hex_to_bgr(accent_hex)
        accent_rgb = _hex_to_rgb(accent_hex)
        resolved_seed = _derive_seed(template, title, subtitle, explicit_seed=seed)
        personality_key = personality or spec.get("personality", "cold_war_noir")
        eased = _apply_easing(progress, personality_key)

        frame = np.full((height, width, 3), bg_bgr, dtype=np.uint8)
        self._draw_blueprint_grid(frame, width, height, progress, template)

        if template in ("anatomy_mechanical", "isometric_architecture_flow"):
            self._draw_isometric_assembly(frame, width, height, eased, data.get("components"))
        elif template == "tactical_hud":
            self._draw_tactical_hud_graphics(frame, width, height, eased, accent_bgr)
        elif template == "declassified_dossier":
            self._draw_dossier_redactions(frame, width, height, eased, accent_bgr)
        elif template == "lower_third":
            self._draw_lower_third_plate(frame, width, height, eased, accent_bgr)
        elif template == "blueprint_notebook":
            self._draw_blueprint_notebook_plate(frame, width, height, eased, accent_bgr, resolved_seed)
        elif template == "risograph_declassified":
            self._draw_risograph_declassified_plate(frame, width, height, eased, accent_bgr, resolved_seed)
        elif template == "cut_paper_editorial":
            self._draw_cut_paper_editorial_plate(frame, width, height, eased, accent_bgr, resolved_seed)
        elif template in ("vertical_dossier_short", "vertical_kinetic_quote"):
            self._draw_vertical_dossier_plate(frame, width, height, eased, accent_bgr, resolved_seed)
        elif template == "onetake_bento_launch":
            self._draw_onetake_bento_plate(frame, width, height, eased, accent_bgr, resolved_seed, data)
        elif template == "cursor_spotlight_demo":
            self._draw_cursor_spotlight_plate(frame, width, height, eased, accent_bgr, resolved_seed, data)
        elif template == "kpi_metric_cascade":
            self._draw_kpi_metric_cascade_plate(frame, width, height, eased, accent_bgr, resolved_seed, data)
        else:
            self._draw_b2b_telemetry_cards(frame, width, height, eased, accent_bgr)

        return self._stamp_crisp_typography(
            frame=frame,
            template=template,
            title=title,
            subtitle=subtitle,
            width=width,
            height=height,
            progress=progress,
            accent_rgb=accent_rgb,
        )

    @staticmethod
    def _draw_blueprint_notebook_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
    ) -> None:
        """Render deterministic drafting CAD calibration vectors & callout brackets (Zero-Blob)."""
        rng = random.Random(seed)
        border_x = int(width * 0.06)
        border_y = int(height * 0.08)
        cv2.rectangle(frame, (border_x, border_y), (width - border_x, height - border_y), accent_bgr, 2)

        # Deterministic drafted measurement dimension arrows along bottom right
        base_y = int(height * 0.72)
        span_w = int(width * 0.44 * min(1.0, progress * 1.3 + 0.15))
        start_x = int(width * 0.46)
        cv2.line(frame, (start_x, base_y), (start_x + span_w, base_y), accent_bgr, 2)
        for tick in range(6):
            tx = start_x + int((width * 0.44) * (tick / 5.0))
            if tx <= start_x + span_w:
                tick_h = 18 if tick % 2 == 0 else 10
                cv2.line(frame, (tx, base_y - tick_h), (tx, base_y + tick_h), accent_bgr, 2)

        # Seeded drafting calibration crosshairs in peripheral safe zones (preserving central copy-space)
        for idx in range(5):
            px = int(width * (0.58 + rng.uniform(0.02, 0.30)))
            py = int(height * (0.28 + rng.uniform(0.02, 0.36)))
            r = max(6, int(min(width, height) * (0.015 + 0.01 * math.sin(progress * math.pi + idx))))
            cv2.circle(frame, (px, py), r, accent_bgr, 1)
            cv2.line(frame, (px - r - 4, py), (px + r + 4, py), accent_bgr, 1)

    @staticmethod
    def _draw_risograph_declassified_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
    ) -> None:
        """Render procedural dual-ink risograph halftone dots & misregistered paper frame."""
        rng = random.Random(seed ^ 0xA5A5)
        bone_bgr = (224, 234, 244)
        shift_x = int(4 * math.sin(progress * math.pi))
        rx1, ry1 = int(width * 0.08), int(height * 0.30)
        rx2, ry2 = int(width * 0.90), int(height * 0.86)
        cv2.rectangle(frame, (rx1 + shift_x, ry1), (rx2 + shift_x, ry2), accent_bgr, 2)
        cv2.rectangle(frame, (rx1, ry1 + 3), (rx2, ry2 + 3), bone_bgr, 1)

        # Halftone stochastic screen restricted to right telemetry zone
        step = max(14, width // 48)
        reveal_limit = int(width * (0.55 + 0.33 * min(1.0, progress * 1.25)))
        for gx in range(int(width * 0.54), reveal_limit, step):
            for gy in range(int(height * 0.36), int(height * 0.80), step):
                if rng.random() > 0.32:
                    dot_r = 2 if (gx + gy) % (step * 2) == 0 else 1
                    cv2.circle(frame, (gx, gy), dot_r, accent_bgr, -1)

    @staticmethod
    def _draw_cut_paper_editorial_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
    ) -> None:
        """Render layered stepped architectural planes with cast depth shadows (Zero-Blob)."""
        rng = random.Random(seed ^ 0x5A5A)
        layers = [
            ((30, 41, 59), 0.14),
            ((45, 62, 86), 0.24),
            ((64, 86, 118), 0.34),
        ]
        for idx, (bgr, x_frac) in enumerate(layers):
            slide = min(1.0, max(0.0, progress * 1.4 - idx * 0.14))
            jitter = rng.randint(-6, 6)
            x1 = int(width * (0.48 + x_frac * 0.55))
            y1 = int(height * (0.42 + idx * 0.09 + (1.0 - slide) * 0.22)) + jitter
            x2 = int(width * 0.92)
            y2 = int(height * 0.88)
            cv2.rectangle(frame, (x1 + 6, y1 + 8), (x2 + 6, y2 + 8), (8, 12, 20), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, -1)
            cv2.line(frame, (x1, y1), (x2, y1), accent_bgr if idx == 2 else (148, 163, 184), 2)

    @staticmethod
    def _draw_blueprint_grid(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        template: str,
    ) -> None:
        step = max(32, width // 24)
        offset = int(progress * step) % step if "grid" in template else 0
        line_color = (42, 62, 88) if "anatomy" in template or "isometric" in template else (28, 38, 52)
        for x in range(offset, width, step):
            cv2.line(frame, (x, 0), (x, height), line_color, 1)
        for y in range(offset, height, step):
            cv2.line(frame, (0, y), (width, y), line_color, 1)

    @staticmethod
    def _draw_isometric_assembly(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        components: Optional[List[str]],
    ) -> None:
        top_bgr = _hex_to_bgr(ANATOMY_FOUR_TONE_PALETTE["top_face"])
        left_bgr = _hex_to_bgr(ANATOMY_FOUR_TONE_PALETTE["left_face"])
        right_bgr = _hex_to_bgr(ANATOMY_FOUR_TONE_PALETTE["right_face"])
        ink_bgr = _hex_to_bgr(ANATOMY_FOUR_TONE_PALETTE["line_ink"])
        accent_bgr = _hex_to_bgr(ANATOMY_FOUR_TONE_PALETTE["callout_accent"])

        cx = int(width * 0.44)
        scale_x = max(60, int(width * 0.13))
        scale_y = max(24, int(height * 0.07))
        depth = max(20, int(height * 0.055))
        ease = math.sin(min(1.0, progress * 1.4) * (math.pi / 2))

        for layer_idx in range(3):
            explode_offset = int((layer_idx - 1) * (height * 0.17) * (0.55 + 0.45 * ease))
            cy = int(height * 0.54) + explode_offset

            top_poly = np.array([[cx, cy - scale_y], [cx + scale_x, cy], [cx, cy + scale_y], [cx - scale_x, cy]], np.int32)
            left_poly = np.array([[cx - scale_x, cy], [cx, cy + scale_y], [cx, cy + scale_y + depth], [cx - scale_x, cy + depth]], np.int32)
            right_poly = np.array([[cx, cy + scale_y], [cx + scale_x, cy], [cx + scale_x, cy + depth], [cx, cy + scale_y + depth]], np.int32)

            cv2.fillPoly(frame, [top_poly], top_bgr)
            cv2.fillPoly(frame, [left_poly], left_bgr)
            cv2.fillPoly(frame, [right_poly], right_bgr)
            for poly in (top_poly, left_poly, right_poly):
                cv2.polylines(frame, [poly], True, ink_bgr, 2)

            # Callout leader line
            if progress > 0.15:
                anchor = (cx + scale_x - 10, cy)
                end_pt = (cx + scale_x + max(50, int(width * 0.12)), cy)
                cv2.circle(frame, anchor, 5, accent_bgr, -1)
                cv2.line(frame, anchor, end_pt, accent_bgr, 2)

    @staticmethod
    def _draw_tactical_hud_graphics(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
    ) -> None:
        margin = max(20, int(min(width, height) * 0.05))
        arm = max(24, int(min(width, height) * 0.07))
        corners = [
            ((margin, margin), (margin + arm, margin), (margin, margin + arm)),
            ((width - margin, margin), (width - margin - arm, margin), (width - margin, margin + arm)),
            ((margin, height - margin), (margin + arm, height - margin), (margin, height - margin - arm)),
            ((width - margin, height - margin), (width - margin - arm, height - margin), (width - margin, height - margin - arm)),
        ]
        for corner, hx, vy in corners:
            cv2.line(frame, corner, hx, accent_bgr, 3)
            cv2.line(frame, corner, vy, accent_bgr, 3)

        center = (int(width * 0.78), int(height * 0.50))
        radius = max(36, int(min(width, height) * 0.18))
        cv2.circle(frame, center, radius, accent_bgr, 2)
        angle = progress * 2.0 * math.pi
        end_x = int(center[0] + radius * math.cos(angle))
        end_y = int(center[1] + radius * math.sin(angle))
        cv2.line(frame, center, (end_x, end_y), accent_bgr, 2)

    @staticmethod
    def _draw_dossier_redactions(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
    ) -> None:
        sheet_x1, sheet_y1 = int(width * 0.08), int(height * 0.12)
        sheet_x2, sheet_y2 = int(width * 0.92), int(height * 0.88)
        cv2.rectangle(frame, (sheet_x1, sheet_y1), (sheet_x2, sheet_y2), (26, 24, 22), -1)
        cv2.rectangle(frame, (sheet_x1, sheet_y1), (sheet_x2, sheet_y2), accent_bgr, 2)
        for row in range(3):
            y = int(height * (0.46 + row * 0.11))
            reveal_frac = min(1.0, max(0.0, progress * 1.6 - row * 0.25))
            bar_w = int((width * 0.62) * (1.0 - reveal_frac * 0.82))
            if bar_w > 8:
                cv2.rectangle(frame, (int(width * 0.14), y), (int(width * 0.14) + bar_w, y + max(16, height // 24)), (8, 8, 8), -1)

    @staticmethod
    def _draw_lower_third_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
    ) -> None:
        slide = min(1.0, progress * 2.5)
        plate_w = int(width * 0.64 * slide)
        y1, y2 = int(height * 0.72), int(height * 0.90)
        x1 = int(width * 0.06)
        if plate_w > 10:
            cv2.rectangle(frame, (x1, y1), (x1 + plate_w, y2), (18, 26, 40), -1)
            cv2.rectangle(frame, (x1, y1), (x1 + max(6, width // 120), y2), accent_bgr, -1)

    @staticmethod
    def _draw_vertical_dossier_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
    ) -> None:
        """Render vertical 9:16 dossier card preserving mobile bottom/right UI safe-zones."""
        rng = random.Random(seed ^ 0x1983)
        pad_x = int(width * 0.08)
        pad_y_top = int(height * 0.24)
        pad_y_bot = int(height * 0.56)
        cv2.rectangle(frame, (pad_x, pad_y_top), (width - pad_x, pad_y_bot), (18, 28, 46), -1)
        cv2.rectangle(frame, (pad_x, pad_y_top), (width - pad_x, pad_y_bot), accent_bgr, 2)

        # Animated horizontal waveform bars inside focal mid-canvas
        bar_count = 16
        avail_w = max(80, width - 2 * pad_x - 32)
        step_x = max(8, avail_w // bar_count)
        center_y = (pad_y_top + pad_y_bot) // 2
        for i in range(bar_count):
            phase = progress * 3.0 * math.pi + i * 0.55 + rng.uniform(0.0, 0.6)
            amp = max(8, int((pad_y_bot - pad_y_top) * 0.28 * (0.25 + 0.75 * abs(math.sin(phase)))))
            bx = pad_x + 18 + i * step_x
            cv2.rectangle(frame, (bx, center_y - amp), (bx + max(4, step_x - 4), center_y + amp), accent_bgr, -1)

    @staticmethod
    def _draw_onetake_bento_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render continuous zero-cut OneTake camera glide across generic Bento SaaS cards."""
        camera_vec = str((data or {}).get("camera_vector") or "pan_left")
        pan_shift_x = int(width * (0.10 - 0.20 * progress)) if "pan" in camera_vec else int(width * (0.04 * math.sin(progress * math.pi)))
        pan_shift_y = int(height * (0.06 - 0.12 * progress)) if "diagonal" in camera_vec else 0
        zoom = 1.0 + 0.12 * progress

        cards = [
            (0.42, 0.24, 0.23, 0.26),
            (0.68, 0.24, 0.24, 0.26),
            (0.42, 0.54, 0.30, 0.26),
            (0.75, 0.54, 0.17, 0.26),
        ]
        cx0, cy0 = width * 0.66, height * 0.50
        for idx, (xf, yf, wf, hf) in enumerate(cards):
            x1 = int(cx0 + (xf * width - cx0) * zoom + pan_shift_x)
            y1 = int(cy0 + (yf * height - cy0) * zoom + pan_shift_y)
            cw = max(30, int(wf * width * zoom))
            ch = max(24, int(hf * height * zoom))
            fill_bgr = (20 + idx * 6, 32 + idx * 5, 52 + idx * 4)
            cv2.rectangle(frame, (x1, y1), (x1 + cw, y1 + ch), fill_bgr, -1)
            cv2.rectangle(frame, (x1, y1), (x1 + cw, y1 + ch), accent_bgr if idx % 2 == 0 else (100, 116, 139), 2)
            # Abstract metric bar inside card
            pulse = 0.25 + 0.7 * min(1.0, max(0.0, progress * 1.4 - idx * 0.12))
            cv2.rectangle(
                frame,
                (x1 + 14, y1 + int(ch * 0.62)),
                (x1 + 14 + int((cw - 28) * pulse), y1 + int(ch * 0.78)),
                accent_bgr,
                -1,
            )

    @staticmethod
    def _draw_cursor_spotlight_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render generic wireframe analytics board with smooth cursor focus + zoom ring."""
        bx1, by1 = int(width * 0.44), int(height * 0.22)
        bx2, by2 = int(width * 0.92), int(height * 0.84)
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (18, 28, 44), -1)
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (71, 85, 105), 2)

        # Synthetic sparkline waypoints inside UI canvas
        pts: List[Tuple[int, int]] = []
        n_pts = 8
        for i in range(n_pts):
            px = bx1 + 28 + int((bx2 - bx1 - 56) * (i / (n_pts - 1)))
            py = by2 - 42 - int((by2 - by1 - 96) * (0.2 + 0.65 * (0.5 + 0.5 * math.sin(i * 0.9 + (seed % 7)))))
            pts.append((px, py))
        for i in range(1, len(pts)):
            cv2.line(frame, pts[i - 1], pts[i], accent_bgr, 3)

        # Smooth animated pointer hovering across chart waypoints + live telemetry bars
        cur_f = progress * (len(pts) - 1)
        i0 = min(len(pts) - 2, max(0, int(cur_f)))
        frac = cur_f - i0
        cx = int(pts[i0][0] + (pts[i0 + 1][0] - pts[i0][0]) * frac)
        cy = int(pts[i0][1] + (pts[i0 + 1][1] - pts[i0][1]) * frac)

        # Animated column bars under sparkline + sweeping cursor beam so motion delta clears high-energy QA
        bar_w = max(14, (bx2 - bx1 - 96) // n_pts)
        for bi, (px, py) in enumerate(pts):
            pulse = 0.55 + 0.45 * math.sin(progress * math.pi * 3.0 + bi * 0.7)
            col_top = max(by1 + 24, int(py + (by2 - 24 - py) * (0.45 - 0.28 * pulse)))
            is_focused = abs(px - cx) <= bar_w
            col_color = accent_bgr if is_focused else (36, 52, 74)
            cv2.rectangle(frame, (px - bar_w // 3, col_top), (px + bar_w // 3, by2 - 18), col_color, -1)

        cv2.line(frame, (cx, by1 + 14), (cx, by2 - 14), accent_bgr, 2)
        ring_r = max(16, int(min(width, height) * (0.05 + 0.02 * math.sin(progress * 4.0 * math.pi))))
        cv2.circle(frame, (cx, cy), ring_r, accent_bgr, 2)
        cursor_poly = np.array(
            [[cx, cy], [cx + 22, cy + 16], [cx + 9, cy + 20], [cx + 15, cy + 32], [cx + 8, cy + 35], [cx + 2, cy + 22], [cx - 6, cy + 28]],
            np.int32,
        )
        cv2.fillPoly(frame, [cursor_poly], (248, 250, 252))
        cv2.polylines(frame, [cursor_poly], True, (15, 23, 42), 2)

    @staticmethod
    def _draw_kpi_metric_cascade_plate(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
        seed: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render staggered abstract KPI rows + ascending spline leaving left 40% clean copy-space."""
        row_count = 4
        start_x = int(width * 0.48)
        end_x = int(width * 0.92)
        row_h = max(24, int(height * 0.11))
        for r in range(row_count):
            slide = min(1.0, max(0.0, progress * 1.5 - r * 0.16))
            rx1 = start_x + int((1.0 - slide) * width * 0.12)
            ry1 = int(height * (0.24 + r * 0.15))
            cv2.rectangle(frame, (rx1, ry1), (end_x, ry1 + row_h), (20, 34, 48), -1)
            cv2.rectangle(frame, (rx1, ry1), (rx1 + 8, ry1 + row_h), accent_bgr, -1)
            fill_w = max(20, int((end_x - rx1 - 40) * (0.40 + 0.14 * r) * slide))
            cv2.rectangle(frame, (rx1 + 24, ry1 + int(row_h * 0.35)), (rx1 + 24 + fill_w, ry1 + int(row_h * 0.70)), accent_bgr, -1)

    @staticmethod
    def _draw_b2b_telemetry_cards(
        frame: np.ndarray,
        width: int,
        height: int,
        progress: float,
        accent_bgr: Tuple[int, int, int],
    ) -> None:
        # Leave central 40% clean for B2B copy-space compliance
        bar_area_x = int(width * 0.66)
        bar_base_y = int(height * 0.78)
        bar_w = max(14, width // 36)
        for idx in range(5):
            bh = int(height * (0.12 + 0.07 * idx) * min(1.0, progress * 1.5 + 0.25))
            bx = bar_area_x + idx * (bar_w + max(8, width // 72))
            cv2.rectangle(frame, (bx, bar_base_y - bh), (bx + bar_w, bar_base_y), accent_bgr, -1)

    @staticmethod
    def _stamp_crisp_typography(
        frame: np.ndarray,
        template: str,
        title: str,
        subtitle: str,
        width: int,
        height: int,
        progress: float,
        accent_rgb: Tuple[int, int, int],
    ) -> np.ndarray:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(img)

        is_portrait = height > width
        base_dim = min(width, height) if is_portrait else height
        title_size = max(18, int(base_dim * 0.055))
        sub_size = max(13, int(base_dim * 0.032))
        title_font = _load_font(title_size)
        sub_font = _load_font(sub_size)

        if template == "lower_third":
            tx, ty = int(width * 0.09), int(height * 0.745)
        elif is_portrait:
            # Stay cleanly below 9% mobile top chrome and above right-rail UI
            tx, ty = int(width * 0.07), int(height * 0.115)
        else:
            tx, ty = int(width * 0.07), int(height * 0.14)

        max_title_chars = 32 if is_portrait else 64
        max_sub_chars = 48 if is_portrait else 96
        draw.text((tx, ty), title[:max_title_chars], fill=(241, 245, 249), font=title_font)
        if subtitle:
            draw.text((tx, ty + int(title_size * 1.32)), subtitle[:max_sub_chars], fill=accent_rgb, font=sub_font)

        # Timecode stamp inside safe header corner
        tc_text = f"HF-FRAME {int(progress * 100):03d}%"
        tc_x = int(width * 0.07) if is_portrait else int(width * 0.76)
        tc_y = int(height * 0.092) if is_portrait else int(height * 0.08)
        draw.text((tc_x, tc_y), tc_text, fill=accent_rgb, font=sub_font)

        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _escape_xml(value: Optional[str]) -> str:
        if not value:
            return ""
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
