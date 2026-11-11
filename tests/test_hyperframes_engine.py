import json
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video
from src.video.hyperframes_engine import (
    ANATOMY_FOUR_TONE_PALETTE,
    MOTION_TEMPLATES,
    HyperFramesMotionEngine,
)
from src.video.otio_exporter import (
    TimelineClipRef,
    UniversalTimelineExporter,
)
from src.video.tactical_graphics import TacticalGraphicsEngine


def _make_synthetic_base_video(path: Path, width: int = 640, height: int = 360, duration_sec: float = 2.0, fps: int = 24) -> Path:
    """Create a deterministic tiny MP4 clip for real FFmpeg compositing tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_avi = path.with_suffix(".tmp.avi")
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(raw_avi), fourcc, float(fps), (width, height))
    total_frames = int(duration_sec * fps)
    for i in range(total_frames):
        frame = np.full((height, width, 3), (20, 28, 38), dtype=np.uint8)
        cv2.rectangle(frame, (20 + i, 40), (140 + i, 140), (45, 95, 160), -1)
        writer.write(frame)
    writer.release()

    ffmpeg_bin = get_ffmpeg_binary()
    import subprocess

    subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-i",
            str(raw_avi),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    raw_avi.unlink(missing_ok=True)
    return path


def test_motion_templates_registry_covers_darkfactory_and_stock_b2b():
    dark_templates = {"tactical_hud", "declassified_dossier", "lower_third", "anatomy_mechanical"}
    stock_templates = {
        "saas_fintech_telemetry_ui",
        "isometric_architecture_flow",
        "kinetic_grid_background",
        "hud_data_overlay_loop",
    }
    assert dark_templates.issubset(set(MOTION_TEMPLATES.keys()))
    assert stock_templates.issubset(set(MOTION_TEMPLATES.keys()))


def test_resolve_ffmpeg_env_injects_binary_directory():
    engine = HyperFramesMotionEngine()
    env = engine.resolve_ffmpeg_env()
    ffmpeg_dir = str(Path(get_ffmpeg_binary()).parent)
    assert ffmpeg_dir in env["PATH"].split(";" if ";" in env["PATH"] else ":")


def test_html_composition_enforces_hyperframes_seekable_contract():
    engine = HyperFramesMotionEngine()
    html = engine.build_composition_html(
        template="tactical_hud",
        title="OPERATION PAPERCLIP",
        subtitle="DECLASSIFIED FILE 1945-B",
        duration_sec=5.0,
        width=1280,
        height=720,
        fps=30,
    )
    assert "window.__timelines" in html
    assert "paused: true" in html
    assert 'data-start="0"' in html
    assert 'data-duration="5.0"' in html or 'data-duration="5"' in html
    assert "OPERATION PAPERCLIP" in html


def test_anatomy_isometric_svg_uses_four_tone_lighting_system():
    engine = HyperFramesMotionEngine()
    svg = engine.build_anatomy_isometric_svg(
        title="TURBINE CORE SCHEMATIC",
        subtitle="ISOMETRIC CAD VIEW",
        components=["Intake Valve", "Compressor Stage", "Rotor Shaft"],
    )
    assert "<svg" in svg
    assert ANATOMY_FOUR_TONE_PALETTE["top_face"] in svg
    assert ANATOMY_FOUR_TONE_PALETTE["left_face"] in svg
    assert ANATOMY_FOUR_TONE_PALETTE["right_face"] in svg
    assert ANATOMY_FOUR_TONE_PALETTE["line_ink"] in svg
    assert "Intake Valve" in svg
    assert "Compressor Stage" in svg


@pytest.mark.parametrize(
    "template",
    [
        "tactical_hud",
        "declassified_dossier",
        "lower_third",
        "anatomy_mechanical",
    ],
)
def test_render_motion_clip_all_darkfactory_templates_procedural(tmp_path, template):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)
    out_mp4 = tmp_path / f"{template}.mp4"
    result = engine.render_motion_clip(
        template=template,
        title=f"SECTOR {template.upper()}",
        subtitle="CLASSIFIED TELEMETRY UNIT",
        output_path=out_mp4,
        duration_sec=1.5,
        width=640,
        height=360,
        fps=24,
        force_procedural=True,
        muted=True,
    )
    assert result.success is True
    assert result.render_backend == "procedural_ffmpeg"
    assert out_mp4.exists()
    assert result.html_path is not None and result.html_path.exists()
    props = probe_video(out_mp4)
    assert props.width == 640
    assert props.height == 360
    assert props.has_audio is False
    assert props.duration_seconds >= 1.0


def test_render_preview_gate_clamps_to_20_seconds(tmp_path):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)
    out_mp4 = tmp_path / "gate_preview.mp4"
    result = engine.render_preview_gate(
        template="anatomy_mechanical",
        title="20S PREVIEW GATE",
        subtitle="FAST AUDIT",
        output_path=out_mp4,
        duration_sec=45.0,
        max_duration_sec=20.0,
        width=640,
        height=360,
        fps=12,
        force_procedural=True,
    )
    assert result.success is True
    assert result.is_preview_gate is True
    assert result.duration_sec <= 20.0


def test_render_motion_clip_unknown_template_raises(tmp_path):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)
    with pytest.raises(ValueError):
        engine.render_motion_clip(
            template="nonexistent_template",
            title="BAD",
            output_path=tmp_path / "bad.mp4",
        )


def test_otio_exporter_includes_v2_tactical_overlays_track(tmp_path):
    exporter = UniversalTimelineExporter(fps=24)
    v1_clip = tmp_path / "shot_01.mp4"
    v2_overlay = tmp_path / "hud_01.mp4"
    music_clip = tmp_path / "score.flac"
    v1_clip.write_bytes(b"v1")
    v2_overlay.write_bytes(b"v2")
    music_clip.write_bytes(b"music")

    timeline_dict = exporter.build_timeline_json(
        timeline_name="DarkFactory_Motion_Timeline",
        video_clips=[TimelineClipRef("Shot_01", str(v1_clip), 5.0)],
        audio_music_clips=[TimelineClipRef("Score_01", str(music_clip), 5.0)],
        overlay_clips=[TimelineClipRef("HUD_01", str(v2_overlay), 3.0)],
    )
    track_names = [t["name"] for t in timeline_dict["tracks"]["children"]]
    assert "V1_Master_Shots" in track_names
    assert "V2_Tactical_Overlays" in track_names
    assert "A2_Zimmer_Tension_Score" in track_names

    otio_file = tmp_path / "timeline.otio"
    exporter.export_to_file(
        output_path=otio_file,
        timeline_name="DarkFactory_Motion_Timeline",
        video_clips=[TimelineClipRef("Shot_01", str(v1_clip), 5.0)],
        audio_music_clips=[TimelineClipRef("Score_01", str(music_clip), 5.0)],
        overlay_clips=[TimelineClipRef("HUD_01", str(v2_overlay), 3.0)],
    )
    assert otio_file.exists()
    content = otio_file.read_text(encoding="utf-8")
    assert "V2_Tactical_Overlays" in content
    assert "A2_Zimmer_Tension_Score" in content


def test_tactical_graphics_composite_motion_overlay_end_to_end(tmp_path):
    base_video = _make_synthetic_base_video(tmp_path / "base.mp4", width=640, height=360, duration_sec=1.5, fps=24)
    hf_engine = HyperFramesMotionEngine(output_dir=tmp_path)
    overlay_mp4 = tmp_path / "overlay_hud.mp4"
    overlay_res = hf_engine.render_motion_clip(
        template="lower_third",
        title="BERLIN ARCHIVE 1961",
        subtitle="SECTOR A TELEMETRY",
        output_path=overlay_mp4,
        duration_sec=1.0,
        width=640,
        height=360,
        fps=24,
        force_procedural=True,
    )
    assert overlay_res.success is True

    gfx = TacticalGraphicsEngine()
    out_composited = tmp_path / "composited.mp4"
    ok = gfx.composite_motion_overlay(
        base_video_path=base_video,
        overlay_video_path=overlay_mp4,
        output_video_path=out_composited,
        start_time_sec=0.2,
        duration_sec=1.0,
    )
    assert ok is True
    assert out_composited.exists()
    props = probe_video(out_composited)
    assert props.width == 640
    assert props.height == 360


def test_dashboard_motion_overlay_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("src.video.hyperframes_engine.DEFAULT_MOTION_OUTPUT_DIR", tmp_path)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/video/motion-overlay",
        json={
            "template": "tactical_hud",
            "title": "BUNKER DIAGNOSTIC",
            "subtitle": "PRESSURE NOMINAL",
            "duration_sec": 1.0,
            "width": 640,
            "height": 360,
            "fps": 12,
            "force_procedural": True,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["template"] == "tactical_hud"
    assert Path(payload["output_video_path"]).exists()
