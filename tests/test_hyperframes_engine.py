from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video
from src.video.hyperframes_engine import (
    ANATOMY_FOUR_TONE_PALETTE,
    MOTION_TEMPLATES,
    HyperFramesMotionEngine,
)


def test_motion_templates_registry_covers_stock_b2b():
    stock_templates = {
        "saas_fintech_telemetry_ui",
        "isometric_architecture_flow",
        "kinetic_grid_background",
        "hud_data_overlay_loop",
        "cut_paper_editorial",
        "onetake_bento_launch",
        "cursor_spotlight_demo",
        "kpi_metric_cascade",
    }
    assert stock_templates.issubset(set(MOTION_TEMPLATES.keys()))
    for removed in ("tactical_hud", "declassified_dossier", "lower_third", "anatomy_mechanical"):
        assert removed not in MOTION_TEMPLATES


def test_resolve_ffmpeg_env_injects_binary_directory():
    engine = HyperFramesMotionEngine()
    env = engine.resolve_ffmpeg_env()
    ffmpeg_dir = str(Path(get_ffmpeg_binary()).parent)
    assert ffmpeg_dir in env["PATH"].split(";" if ";" in env["PATH"] else ":")


def test_html_composition_enforces_hyperframes_seekable_contract():
    engine = HyperFramesMotionEngine()
    html = engine.build_composition_html(
        template="saas_fintech_telemetry_ui",
        title="GLOBAL TREASURY TELEMETRY",
        subtitle="REALTIME LIQUIDITY ARCHITECTURE",
        duration_sec=5.0,
        width=1280,
        height=720,
        fps=30,
    )
    assert "window.__timelines" in html
    assert "paused: true" in html
    assert 'data-start="0"' in html
    assert 'data-duration="5.0"' in html or 'data-duration="5"' in html
    assert "GLOBAL TREASURY TELEMETRY" in html


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
        "saas_fintech_telemetry_ui",
        "isometric_architecture_flow",
        "kinetic_grid_background",
        "hud_data_overlay_loop",
        "cut_paper_editorial",
    ],
)
def test_render_motion_clip_stock_b2b_templates_procedural(tmp_path, template):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)
    out_mp4 = tmp_path / f"{template}.mp4"
    result = engine.render_motion_clip(
        template=template,
        title=f"SECTOR {template.upper()}",
        subtitle="ENTERPRISE B2B TELEMETRY",
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
        template="isometric_architecture_flow",
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


def test_dashboard_motion_overlay_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("src.video.hyperframes_engine.DEFAULT_MOTION_OUTPUT_DIR", tmp_path)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/video/motion-overlay",
        json={
            "template": "saas_fintech_telemetry_ui",
            "title": "TREASURY DIAGNOSTIC",
            "subtitle": "LATENCY NOMINAL",
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
    assert payload["template"] == "saas_fintech_telemetry_ui"
    assert Path(payload["output_video_path"]).exists()
