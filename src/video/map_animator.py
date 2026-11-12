"""StockCont & DarkFactory — Editorial Vector Map Animator (Vox / Cold War Telemetry).

Generates deterministic, offline-capable geopolitical vector map animations as:
1. Semantic multi-layer SVG (<g id="grid">, <g id="landmass">, <g id="routes">, <g id="pins">, <g id="hud">)
2. Seekable HTML/GSAP timeline composition (window.__timelines, paused: true, optional 12fps editorial stutter)
3. Playable muted H.264 MP4 video with camera pan/zoom, drawn-on tactical routes, and pulsing coordinate pins.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_MAP_DIR = BASE_DIR / "data" / "final" / "motion_overlays" / "maps"

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _safe_hex(value: str, fallback: str = "#38BDF8") -> str:
    cleaned = (value or "").strip()
    return cleaned if _HEX_RE.match(cleaned) else fallback


def _hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    cleaned = _safe_hex(hex_color).lstrip("#")
    r = int(cleaned[0:2], 16)
    g = int(cleaned[2:4], 16)
    b = int(cleaned[4:6], 16)
    return (b, g, r)


def _escape_xml(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "map").strip().lower()).strip("_")
    return slug[:60] or "map"


def _atomic_write_text(path: Path, content: str) -> Path:
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


# Geopolitical theater bounds (min_lon, max_lon, min_lat, max_lat) + simplified schematic landmass polygons
THEATER_PRESETS: Dict[str, Dict[str, Any]] = {
    "europe_cold_war": {
        "bounds": (-12.0, 52.0, 34.0, 68.0),
        "bg_hex": "#0B111B",
        "land_hex": "#182436",
        "stroke_hex": "#334155",
        "accent_hex": "#EF4444",
        "polygons": [
            [(-9.0, 37.0), (-9.0, 43.0), (-2.0, 48.0), (2.0, 51.0), (9.0, 54.0), (14.0, 54.5), (22.0, 59.0), (30.0, 60.0), (32.0, 66.0), (48.0, 66.0), (50.0, 45.0), (40.0, 42.0), (29.0, 41.0), (24.0, 37.5), (16.0, 38.0), (12.0, 43.0), (4.0, 43.0), (-5.0, 36.0)],
            [(-6.0, 50.0), (-5.0, 58.0), (1.0, 57.0), (1.5, 51.0)],
            [(5.0, 59.0), (10.0, 64.0), (20.0, 67.5), (26.0, 65.0), (19.0, 56.0), (11.0, 57.5)],
        ],
    },
    "north_atlantic": {
        "bounds": (-90.0, 20.0, 20.0, 72.0),
        "bg_hex": "#07101C",
        "land_hex": "#16263A",
        "stroke_hex": "#2B4563",
        "accent_hex": "#38BDF8",
        "polygons": [
            [(-88.0, 25.0), (-82.0, 31.0), (-75.0, 38.0), (-67.0, 45.0), (-55.0, 52.0), (-64.0, 62.0), (-88.0, 65.0)],
            [(-48.0, 60.0), (-42.0, 70.0), (-20.0, 71.0), (-30.0, 62.0)],
            [(-9.0, 36.0), (-9.0, 44.0), (-4.0, 56.0), (12.0, 64.0), (19.0, 68.0), (19.0, 36.0)],
        ],
    },
    "pacific_theater": {
        "bounds": (100.0, 180.0, -10.0, 62.0),
        "bg_hex": "#08121E",
        "land_hex": "#192B3F",
        "stroke_hex": "#335275",
        "accent_hex": "#F59E0B",
        "polygons": [
            [(102.0, 12.0), (108.0, 22.0), (121.0, 31.0), (125.0, 40.0), (138.0, 53.0), (160.0, 60.0), (102.0, 60.0)],
            [(130.0, 31.5), (136.0, 34.5), (141.0, 39.0), (145.0, 44.0), (140.0, 44.5), (133.0, 36.0)],
            [(115.0, -7.0), (128.0, -4.0), (145.0, -6.0), (144.0, -9.0), (118.0, -9.0)],
        ],
    },
    "middle_east": {
        "bounds": (24.0, 64.0, 12.0, 44.0),
        "bg_hex": "#120F0B",
        "land_hex": "#28221A",
        "stroke_hex": "#544735",
        "accent_hex": "#F97316",
        "polygons": [
            [(25.0, 13.0), (25.0, 31.0), (33.0, 31.5), (36.0, 26.0), (43.0, 13.0)],
            [(34.0, 31.5), (36.0, 37.0), (44.0, 41.0), (62.0, 41.0), (62.0, 25.0), (57.0, 22.0), (52.0, 16.0), (44.0, 13.0), (39.0, 22.0)],
            [(26.0, 36.5), (27.0, 41.5), (41.0, 41.5), (41.0, 37.0)],
        ],
    },
    "arctic_corridor": {
        "bounds": (-165.0, 165.0, 52.0, 84.0),
        "bg_hex": "#060D17",
        "land_hex": "#172536",
        "stroke_hex": "#3B5573",
        "accent_hex": "#22D3EE",
        "polygons": [
            [(-162.0, 58.0), (-140.0, 70.0), (-85.0, 72.0), (-60.0, 62.0), (-162.0, 54.0)],
            [(5.0, 59.0), (28.0, 71.0), (75.0, 73.0), (135.0, 72.0), (162.0, 64.0), (162.0, 54.0), (5.0, 54.0)],
        ],
    },
    "global_overview": {
        "bounds": (-170.0, 175.0, -55.0, 75.0),
        "bg_hex": "#070D17",
        "land_hex": "#162235",
        "stroke_hex": "#2D425F",
        "accent_hex": "#38BDF8",
        "polygons": [
            [(-165.0, 62.0), (-125.0, 50.0), (-105.0, 20.0), (-80.0, 10.0), (-55.0, 50.0), (-85.0, 68.0)],
            [(-80.0, 10.0), (-50.0, 5.0), (-35.0, -8.0), (-52.0, -35.0), (-68.0, -52.0), (-76.0, -18.0)],
            [(-10.0, 36.0), (12.0, 64.0), (65.0, 70.0), (140.0, 62.0), (138.0, 34.0), (102.0, 12.0), (52.0, 22.0), (32.0, 32.0), (50.0, 12.0), (38.0, -28.0), (18.0, -34.0), (8.0, 5.0), (-16.0, 15.0)],
            [(114.0, -22.0), (136.0, -12.0), (152.0, -28.0), (142.0, -38.0), (116.0, -34.0)],
        ],
    },
}


@dataclass
class MapPin:
    """Geographic pin displayed on the tactical vector map."""

    label: str
    lat: float
    lon: float
    timestamp_sec: float = 0.3
    color_hex: str = "#EF4444"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MapRoute:
    """Great-circle / schematic trajectory drawn across the vector map."""

    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    label: str = ""
    start_sec: float = 0.5
    duration_sec: float = 1.5
    color_hex: str = "#38BDF8"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MapAnimationResult:
    """Output contract for generated SVG, HTML/GSAP, and MP4 map compositions."""

    success: bool
    theater: str
    title: str
    video_path: Optional[str] = None
    svg_path: Optional[str] = None
    html_path: Optional[str] = None
    duration_sec: float = 0.0
    width: int = 1280
    height: int = 720
    fps: int = 24
    editorial_12fps: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MapAnimator:
    """Deterministic offline editorial vector map animation engine."""

    def __init__(self, output_dir: Optional[Path | str] = None) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_MAP_DIR.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _project_point(
        lat: float,
        lon: float,
        bounds: Tuple[float, float, float, float],
        width: int,
        height: int,
        pad_ratio: float = 0.08,
    ) -> Tuple[float, float]:
        min_lon, max_lon, min_lat, max_lat = bounds
        lon_span = max(1e-3, max_lon - min_lon)
        lat_span = max(1e-3, max_lat - min_lat)
        pad_x = width * pad_ratio
        pad_y = height * pad_ratio
        usable_w = max(1.0, width - 2 * pad_x)
        usable_h = max(1.0, height - 2 * pad_y)
        nx = (float(lon) - min_lon) / lon_span
        ny = 1.0 - ((float(lat) - min_lat) / lat_span)
        x = pad_x + nx * usable_w
        y = pad_y + ny * usable_h
        return (round(x, 2), round(y, 2))

    def build_map_svg(
        self,
        title: str,
        subtitle: str = "",
        theater: str = "europe_cold_war",
        pins: Optional[Sequence[MapPin]] = None,
        routes: Optional[Sequence[MapRoute]] = None,
        width: int = 1280,
        height: int = 720,
    ) -> str:
        """Build a semantic multi-layer SVG vector map ready for animation."""
        spec = THEATER_PRESETS.get(theater, THEATER_PRESETS["europe_cold_war"])
        bounds = spec["bounds"]
        bg_hex = _safe_hex(spec["bg_hex"], "#0B111B")
        land_hex = _safe_hex(spec["land_hex"], "#182436")
        stroke_hex = _safe_hex(spec["stroke_hex"], "#334155")
        accent_hex = _safe_hex(spec["accent_hex"], "#38BDF8")

        grid_lines: List[str] = []
        for step in range(1, 12):
            gx = round((width / 12.0) * step, 1)
            grid_lines.append(
                f'<line x1="{gx}" y1="0" x2="{gx}" y2="{height}" stroke="{stroke_hex}" stroke-opacity="0.22" stroke-width="1" />'
            )
        for step in range(1, 7):
            gy = round((height / 7.0) * step, 1)
            grid_lines.append(
                f'<line x1="0" y1="{gy}" x2="{width}" y2="{gy}" stroke="{stroke_hex}" stroke-opacity="0.22" stroke-width="1" />'
            )

        land_paths: List[str] = []
        for idx, poly in enumerate(spec["polygons"]):
            pts = [self._project_point(lat, lon, bounds, width, height) for lon, lat in poly]
            pt_str = " ".join(f"{x},{y}" for x, y in pts)
            land_paths.append(
                f'<polygon id="land_{idx}" points="{pt_str}" fill="{land_hex}" stroke="{stroke_hex}" stroke-width="2" />'
            )

        route_elems: List[str] = []
        for idx, rt in enumerate(routes or ()):
            p0 = self._project_point(rt.origin_lat, rt.origin_lon, bounds, width, height)
            p1 = self._project_point(rt.dest_lat, rt.dest_lon, bounds, width, height)
            cx = round((p0[0] + p1[0]) / 2.0, 2)
            cy = round(min(p0[1], p1[1]) - max(35.0, abs(p1[0] - p0[0]) * 0.18), 2)
            rt_col = _safe_hex(rt.color_hex, accent_hex)
            route_elems.append(
                f'<path id="route_{idx}" class="map-route" data-start="{rt.start_sec}" data-duration="{rt.duration_sec}" '
                f'd="M {p0[0]} {p0[1]} Q {cx} {cy} {p1[0]} {p1[1]}" fill="none" stroke="{rt_col}" '
                f'stroke-width="3.5" stroke-dasharray="1200" stroke-dashoffset="1200" stroke-linecap="round" />'
            )

        pin_elems: List[str] = []
        for idx, pin in enumerate(pins or ()):
            px, py = self._project_point(pin.lat, pin.lon, bounds, width, height)
            p_col = _safe_hex(pin.color_hex, "#EF4444")
            pin_elems.append(
                f'<g class="map-pin" data-start="{pin.timestamp_sec}" transform="translate({px},{py})">'
                f'<circle r="14" fill="none" stroke="{p_col}" stroke-width="2" stroke-opacity="0.7" />'
                f'<circle r="5" fill="{p_col}" />'
                f'<text x="14" y="4" fill="#F8FAFC" font-family="Consolas, monospace" font-size="14" font-weight="700">'
                f"{_escape_xml(pin.label)}</text></g>"
            )

        hud_elems = [
            f'<rect x="28" y="24" width="520" height="68" rx="6" fill="{bg_hex}" fill-opacity="0.82" stroke="{accent_hex}" stroke-opacity="0.55" />',
            f'<text x="44" y="52" fill="#F8FAFC" font-family="Consolas, monospace" font-size="22" font-weight="700">{_escape_xml(title)}</text>',
            f'<text x="44" y="76" fill="{accent_hex}" font-family="Consolas, monospace" font-size="13">{_escape_xml(subtitle or theater.upper())}</text>',
        ]

        return "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
                f'  <rect width="{width}" height="{height}" fill="{bg_hex}" />',
                f'  <g id="grid">{"".join(grid_lines)}</g>',
                f'  <g id="landmass">{"".join(land_paths)}</g>',
                f'  <g id="routes">{"".join(route_elems)}</g>',
                f'  <g id="pins">{"".join(pin_elems)}</g>',
                f'  <g id="hud">{"".join(hud_elems)}</g>',
                "</svg>",
            ]
        )

    def build_map_html(
        self,
        svg_markup: str,
        duration_sec: float,
        editorial_12fps: bool = True,
    ) -> str:
        """Wrap semantic vector map SVG in a seekable HyperFrames GSAP HTML player."""
        step_expr = "SteppedEase.config(Math.max(6, Math.round(dur * 12)))" if editorial_12fps else '"power2.inOut"'
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\" />\n"
            "<title>StockCont Tactical Vector Map</title>\n"
            "<style>html,body{margin:0;padding:0;background:#070D17;overflow:hidden;width:100%;height:100%;}svg{display:block;width:100vw;height:100vh;}</style>\n"
            "</head>\n<body>\n"
            f'<div id="map-stage" data-start="0" data-duration="{duration_sec:.2f}">\n{svg_markup}\n</div>\n'
            "<script src=\"https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js\"></script>\n"
            "<script>\n"
            "window.__timelines = window.__timelines || [];\n"
            "(function() {\n"
            f"  const dur = {duration_sec:.2f};\n"
            "  if (typeof gsap === 'undefined') { window.__timelines.push({ paused: true, totalDuration: () => dur, seek: () => {} }); return; }\n"
            "  const tl = gsap.timeline({ paused: true });\n"
            "  tl.fromTo('#landmass', { scale: 1.0, transformOrigin: '50% 50%' }, { scale: 1.07, duration: dur, ease: "
            + step_expr
            + " }, 0);\n"
            "  document.querySelectorAll('.map-route').forEach((el) => {\n"
            "    const s = parseFloat(el.dataset.start || '0.4');\n"
            "    const d = parseFloat(el.dataset.duration || '1.4');\n"
            "    tl.to(el, { strokeDashoffset: 0, duration: d, ease: 'power2.out' }, s);\n"
            "  });\n"
            "  document.querySelectorAll('.map-pin').forEach((el) => {\n"
            "    const s = parseFloat(el.dataset.start || '0.2');\n"
            "    tl.fromTo(el, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1.0, duration: 0.35, ease: 'back.out(1.7)' }, s);\n"
            "  });\n"
            "  window.__timelines.push(tl);\n"
            "})();\n"
            "</script>\n</body>\n</html>\n"
        )

    def render_map_animation(
        self,
        title: str,
        subtitle: str = "",
        theater: str = "europe_cold_war",
        pins: Optional[Sequence[MapPin]] = None,
        routes: Optional[Sequence[MapRoute]] = None,
        duration_sec: float = 4.0,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
        editorial_12fps: bool = True,
        output_path: Optional[Path | str] = None,
    ) -> MapAnimationResult:
        """Render deterministic vector map SVG, seekable HTML, and playable muted MP4."""
        resolved_theater = theater if theater in THEATER_PRESETS else "europe_cold_war"
        spec = THEATER_PRESETS[resolved_theater]
        dur = max(0.5, float(duration_sec))
        target_fps = max(1, int(fps))
        w = max(320, int(width))
        h = max(240, int(height))

        out_video = (
            Path(output_path).resolve()
            if output_path
            else (self.output_dir / f"map_{resolved_theater}_{_slugify(title)}.mp4").resolve()
        )
        out_video.parent.mkdir(parents=True, exist_ok=True)
        svg_path = out_video.with_suffix(".svg")
        html_path = out_video.with_suffix(".html")

        svg_markup = self.build_map_svg(
            title=title,
            subtitle=subtitle,
            theater=resolved_theater,
            pins=pins,
            routes=routes,
            width=w,
            height=h,
        )
        html_markup = self.build_map_html(svg_markup, duration_sec=dur, editorial_12fps=editorial_12fps)
        _atomic_write_text(svg_path, svg_markup)
        _atomic_write_text(html_path, html_markup)

        ok, err_msg = self._render_map_mp4(
            spec=spec,
            title=title,
            subtitle=subtitle or resolved_theater.upper(),
            pins=list(pins or ()),
            routes=list(routes or ()),
            output_video=out_video,
            duration_sec=dur,
            width=w,
            height=h,
            fps=target_fps,
            editorial_12fps=editorial_12fps,
        )
        if ok and out_video.is_file():
            probe_video(out_video)

        return MapAnimationResult(
            success=ok,
            theater=resolved_theater,
            title=title,
            video_path=out_video.as_posix() if ok else None,
            svg_path=svg_path.as_posix(),
            html_path=html_path.as_posix(),
            duration_sec=dur,
            width=w,
            height=h,
            fps=target_fps,
            editorial_12fps=editorial_12fps,
            error=err_msg,
        )

    def _render_map_mp4(
        self,
        spec: Dict[str, Any],
        title: str,
        subtitle: str,
        pins: List[MapPin],
        routes: List[MapRoute],
        output_video: Path,
        duration_sec: float,
        width: int,
        height: int,
        fps: int,
        editorial_12fps: bool,
    ) -> Tuple[bool, Optional[str]]:
        bounds = spec["bounds"]
        bg_bgr = _hex_to_bgr(spec["bg_hex"])
        land_bgr = _hex_to_bgr(spec["land_hex"])
        stroke_bgr = _hex_to_bgr(spec["stroke_hex"])
        accent_bgr = _hex_to_bgr(spec["accent_hex"])

        total_frames = max(1, int(round(duration_sec * fps)))
        tmp_video = output_video.with_name(f"{output_video.stem}.tmp.{os.getpid()}{output_video.suffix}")

        cmd = [
            get_ffmpeg_binary(),
            "-y",
            "-v", "error",
            "-nostats",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "bgr24",
            "-r", str(fps),
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            tmp_video.as_posix(),
        ]

        proc: Optional[subprocess.Popen[bytes]] = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            assert proc.stdin is not None
            for idx in range(total_frames):
                raw_t = (idx / max(1, total_frames - 1)) * duration_sec
                # Editorial 12fps quantized motion preserves crisp stop-motion/Vox cadence
                if editorial_12fps:
                    t_sec = round(math.floor(raw_t * 12.0) / 12.0, 3)
                else:
                    t_sec = raw_t
                progress = min(1.0, t_sec / max(0.01, duration_sec))
                zoom = 1.0 + 0.08 * progress

                frame = np.full((height, width, 3), bg_bgr, dtype=np.uint8)

                # Coordinate grid lines
                for step in range(1, 12):
                    gx = int((width / 12.0) * step)
                    cv2.line(frame, (gx, 0), (gx, height), stroke_bgr, 1)
                for step in range(1, 7):
                    gy = int((height / 7.0) * step)
                    cv2.line(frame, (0, gy), (width, gy), stroke_bgr, 1)

                def _zoom_pt(pt: Tuple[float, float]) -> Tuple[int, int]:
                    cx, cy = width * 0.5, height * 0.5
                    return (
                        int(round(cx + (pt[0] - cx) * zoom)),
                        int(round(cy + (pt[1] - cy) * zoom)),
                    )

                # Landmass polygons
                for poly in spec["polygons"]:
                    pts = np.array(
                        [_zoom_pt(self._project_point(lat, lon, bounds, width, height)) for lon, lat in poly],
                        dtype=np.int32,
                    )
                    cv2.fillPoly(frame, [pts], land_bgr)
                    cv2.polylines(frame, [pts], isClosed=True, color=stroke_bgr, thickness=2, lineType=cv2.LINE_AA)

                # Animated great-circle routes
                for rt in routes:
                    if t_sec < rt.start_sec:
                        continue
                    rt_frac = min(1.0, (t_sec - rt.start_sec) / max(0.05, rt.duration_sec))
                    p0 = _zoom_pt(self._project_point(rt.origin_lat, rt.origin_lon, bounds, width, height))
                    p1 = _zoom_pt(self._project_point(rt.dest_lat, rt.dest_lon, bounds, width, height))
                    ctrl = (
                        int((p0[0] + p1[0]) * 0.5),
                        int(min(p0[1], p1[1]) - max(30, abs(p1[0] - p0[0]) * 0.18)),
                    )
                    steps = max(4, int(36 * rt_frac))
                    arc_pts: List[Tuple[int, int]] = []
                    for s_i in range(steps + 1):
                        u = (s_i / 36.0)
                        if u > rt_frac:
                            u = rt_frac
                        x = int((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * ctrl[0] + u**2 * p1[0])
                        y = int((1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * ctrl[1] + u**2 * p1[1])
                        arc_pts.append((x, y))
                    if len(arc_pts) >= 2:
                        cv2.polylines(
                            frame,
                            [np.array(arc_pts, dtype=np.int32)],
                            isClosed=False,
                            color=_hex_to_bgr(rt.color_hex),
                            thickness=3,
                            lineType=cv2.LINE_AA,
                        )

                # Coordinate pins with pulsing halo
                for pin in pins:
                    if t_sec < pin.timestamp_sec:
                        continue
                    px, py = _zoom_pt(self._project_point(pin.lat, pin.lon, bounds, width, height))
                    pin_bgr = _hex_to_bgr(pin.color_hex)
                    pulse_r = 9 + int(6 * abs(math.sin((t_sec - pin.timestamp_sec) * 5.0)))
                    cv2.circle(frame, (px, py), pulse_r, pin_bgr, 2, lineType=cv2.LINE_AA)
                    cv2.circle(frame, (px, py), 5, pin_bgr, -1, lineType=cv2.LINE_AA)
                    cv2.putText(
                        frame,
                        pin.label[:28],
                        (px + 12, py + 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.48,
                        (248, 250, 252),
                        1,
                        cv2.LINE_AA,
                    )

                # Tactical title box within safe zone
                cv2.rectangle(frame, (24, 20), (min(width - 24, 520), 82), bg_bgr, -1)
                cv2.rectangle(frame, (24, 20), (min(width - 24, 520), 82), accent_bgr, 1)
                cv2.putText(frame, title[:38], (36, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (248, 250, 252), 2, cv2.LINE_AA)
                cv2.putText(frame, subtitle[:46], (36, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.44, accent_bgr, 1, cv2.LINE_AA)

                proc.stdin.write(frame.tobytes())

            proc.stdin.close()
            proc.stdin = None
            stderr_bytes = proc.stderr.read() if proc.stderr else b""
            rc = proc.wait(timeout=120)
            if rc != 0:
                tmp_video.unlink(missing_ok=True)
                return False, f"FFmpeg map render error ({rc}): {stderr_bytes.decode('utf-8', errors='replace')[:240]}"
            tmp_video.replace(output_video)
            return True, None
        except Exception as exc:
            tmp_video.unlink(missing_ok=True)
            return False, str(exc)
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
