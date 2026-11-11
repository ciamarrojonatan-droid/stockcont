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
import re
import shutil
import subprocess
import uuid
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

MOTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # DarkFactory Documentary Overlays
    "tactical_hud": {
        "category": "darkfactory",
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
        "default_width": 1920,
        "default_height": 1080,
        "default_fps": 30,
        "default_duration_sec": 6.0,
        "muted": True,
        "accent_hex": "#38BDF8",
        "bg_hex": ANATOMY_FOUR_TONE_PALETTE["bg_blueprint"],
        "description": "Exploded 4-tone isometric CAD diagram with callout leader lines.",
    },
    # StockCont Sprint 2 B2B 4K Silent Motion Loops
    "saas_fintech_telemetry_ui": {
        "category": "stock_b2b",
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
        "default_width": 3840,
        "default_height": 2160,
        "default_fps": 30,
        "default_duration_sec": 8.0,
        "muted": True,
        "accent_hex": "#22D3EE",
        "bg_hex": "#060E17",
        "description": "Enterprise HUD data telemetry loop engineered with 40% central copy-space.",
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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result with normalized POSIX paths."""
        data = asdict(self)
        for key in ("output_video_path", "html_path", "svg_path"):
            val = data.get(key)
            data[key] = val.as_posix() if isinstance(val, Path) else val
        return data


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
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    tmp_path.replace(path)


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
    ) -> str:
        """Generate deterministic HTML5/GSAP composition following HyperFrames timeline contract."""
        if template not in MOTION_TEMPLATES:
            raise ValueError(f"Unknown motion template '{template}'. Valid: {sorted(MOTION_TEMPLATES)}")

        spec = MOTION_TEMPLATES[template]
        extra = data or {}
        accent = spec["accent_hex"]
        bg = spec["bg_hex"]

        inner_markup = ""
        if template in ("anatomy_mechanical", "isometric_architecture_flow"):
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
  <div id="scene" data-template="{template}" data-fps="{fps}" data-start="0" data-duration="{duration_sec}">
    {inner_markup}
  </div>
  <script>
    window.__timelines = window.__timelines || [];
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
    ) -> MotionCompositionResult:
        """Render HTML/SVG contracts and encode the final MP4 motion clip."""
        if template not in MOTION_TEMPLATES:
            raise ValueError(f"Unknown motion template '{template}'. Valid: {sorted(MOTION_TEMPLATES)}")

        spec = MOTION_TEMPLATES[template]
        dur = max(0.5, float(duration_sec if duration_sec is not None else spec["default_duration_sec"]))
        w = int(width if width is not None else spec["default_width"])
        h = int(height if height is not None else spec["default_height"])
        target_fps = int(fps if fps is not None else spec["default_fps"])

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
        )
        _atomic_write_text(html_path, html_content)

        svg_path: Optional[Path] = None
        if template in ("anatomy_mechanical", "isometric_architecture_flow"):
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
            )
            backend_used = "procedural_ffmpeg"

        video_props_dict: Optional[Dict[str, Any]] = None
        has_audio_stream = False
        if rendered_ok and out_video.exists():
            props = probe_video(out_video)
            video_props_dict = asdict(props)
            has_audio_stream = props.has_audio

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
    ) -> Tuple[bool, Optional[str]]:
        """Render crisp procedural frames in memory and pipe directly to FFmpeg H.264."""
        ffmpeg_bin = get_ffmpeg_binary()
        total_frames = max(1, int(round(duration_sec * fps)))
        spec = MOTION_TEMPLATES[template]

        cmd: List[str] = [
            ffmpeg_bin,
            "-y",
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
                stdout=subprocess.PIPE,
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
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
            return False, str(exc)

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
    ) -> np.ndarray:
        """Render one BGR24 numpy frame parameterized by template family."""
        bg_bgr = _hex_to_bgr(spec["bg_hex"])
        accent_bgr = _hex_to_bgr(spec["accent_hex"])
        accent_rgb = _hex_to_rgb(spec["accent_hex"])

        frame = np.full((height, width, 3), bg_bgr, dtype=np.uint8)
        self._draw_blueprint_grid(frame, width, height, progress, template)

        if template in ("anatomy_mechanical", "isometric_architecture_flow"):
            self._draw_isometric_assembly(frame, width, height, progress, data.get("components"))
        elif template == "tactical_hud":
            self._draw_tactical_hud_graphics(frame, width, height, progress, accent_bgr)
        elif template == "declassified_dossier":
            self._draw_dossier_redactions(frame, width, height, progress, accent_bgr)
        elif template == "lower_third":
            self._draw_lower_third_plate(frame, width, height, progress, accent_bgr)
        else:
            self._draw_b2b_telemetry_cards(frame, width, height, progress, accent_bgr)

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

        title_size = max(18, int(height * 0.055))
        sub_size = max(13, int(height * 0.032))
        title_font = _load_font(title_size)
        sub_font = _load_font(sub_size)

        if template == "lower_third":
            tx, ty = int(width * 0.09), int(height * 0.745)
        else:
            tx, ty = int(width * 0.07), int(height * 0.14)

        draw.text((tx, ty), title[:64], fill=(241, 245, 249), font=title_font)
        if subtitle:
            draw.text((tx, ty + int(title_size * 1.32)), subtitle[:96], fill=accent_rgb, font=sub_font)

        # Timecode stamp in top-right HUD corner
        tc_text = f"HF-FRAME {int(progress * 100):03d}%"
        draw.text((int(width * 0.76), int(height * 0.08)), tc_text, fill=accent_rgb, font=sub_font)

        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _escape_xml(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
