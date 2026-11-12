"""Sprint 4 unit and integration tests for Motion Personalities, Style Plates, Motion QA & 5s Copy Gate."""

from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image
import pytest

from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video
from src.video.hyperframes_engine import (
    MOTION_PERSONALITIES,
    MOTION_TEMPLATES,
    HyperFramesMotionEngine,
)
from src.video.motion_qa import MotionQAInspector
from src.video.story_validator import DarkFactoryStoryValidator
from src.video.tactical_graphics import TacticalGraphicsEngine
from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge


def _make_frozen_mp4(path: Path, width: int = 320, height: int = 180, frames: int = 24, fps: int = 24) -> Path:
    """Create a completely stagnant synthetic video to test frozen-frame QA detection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    avi_path = path.with_suffix(".frozen.avi")
    writer = cv2.VideoWriter(str(avi_path), cv2.VideoWriter_fourcc(*"MJPG"), float(fps), (width, height))
    static_frame = np.full((height, width, 3), (12, 18, 28), dtype=np.uint8)
    cv2.rectangle(static_frame, (40, 40), (140, 120), (56, 189, 248), 2)
    for _ in range(frames):
        writer.write(static_frame)
    writer.release()

    subprocess.run(
        [
            get_ffmpeg_binary(),
            "-y",
            "-i",
            str(avi_path),
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
    avi_path.unlink(missing_ok=True)
    return path


def test_zero_blob_style_plates_and_personalities_deterministic_html():
    assert {"cold_war_noir", "clinical_fintech", "executive_corporate", "high_energy_hook"}.issubset(
        set(MOTION_PERSONALITIES.keys())
    )
    assert {"blueprint_notebook", "risograph_declassified", "cut_paper_editorial"}.issubset(
        set(MOTION_TEMPLATES.keys())
    )

    engine = HyperFramesMotionEngine()
    html_a = engine.build_composition_html(
        template="blueprint_notebook",
        title="SERPUKHOV RADAR CALIBRATION",
        subtitle="SPEC 1983-09",
        duration_sec=4.0,
        seed=424242,
        personality="cold_war_noir",
    )
    html_b = engine.build_composition_html(
        template="blueprint_notebook",
        title="SERPUKHOV RADAR CALIBRATION",
        subtitle="SPEC 1983-09",
        duration_sec=4.0,
        seed=424242,
        personality="cold_war_noir",
    )
    assert html_a == html_b
    assert "window.__hfRng" in html_a
    assert "Math.random" not in html_a
    assert "transition-property: transform, opacity" in html_a
    assert 'data-personality="cold_war_noir"' in html_a
    assert 'data-seed="424242"' in html_a


@pytest.mark.parametrize(
    "template",
    ["blueprint_notebook", "risograph_declassified", "cut_paper_editorial"],
)
def test_render_zero_blob_plates_with_preview_qa_gate(tmp_path, template):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)
    out_mp4 = tmp_path / f"{template}.mp4"
    res = engine.render_preview_gate(
        template=template,
        title=f"PLATE {template.upper()}",
        subtitle="DETERMINISTIC ZERO-BLOB PLATE",
        output_path=out_mp4,
        duration_sec=1.2,
        width=640,
        height=360,
        fps=12,
        seed=1337,
        force_procedural=True,
        run_qa_gate=True,
    )
    assert res.success is True
    assert res.is_preview_gate is True
    assert res.seed == 1337
    assert res.qa_report is not None
    assert res.qa_report["passed"] is True
    assert res.qa_report["contrast_ratio"] >= 4.5
    assert res.contact_sheet_path is not None and res.contact_sheet_path.exists()
    with Image.open(res.contact_sheet_path) as sheet_img:
        assert sheet_img.width > 600 and sheet_img.height > 400
    assert probe_video(out_mp4).width == 640


def test_motion_qa_detects_low_contrast_and_unsafe_text_margins():
    inspector = MotionQAInspector()

    contrast_ok, ratio, findings = inspector.inspect_palette_contrast(
        bg_hex="#1E293B",
        fg_hex="#334155",
    )
    assert contrast_ok is False
    assert ratio < 4.5
    assert any(f.code == "LOW_TEXT_CONTRAST" for f in findings)

    safe_ok, margin_findings = inspector.check_text_safe_area(
        title="EXTREMELY LONG UNBOUNDED HEADLINE TITLE THAT WILL OVERFLOW THE RIGHT BORDER MARGIN COMPLETELY",
        subtitle="SUB",
        width=400,
        height=240,
        template="tactical_hud",
        safe_margin_ratio=0.05,
    )
    assert safe_ok is False
    assert any(f.code == "TEXT_UNSAFE_MARGIN" for f in margin_findings)


def test_motion_qa_detects_frozen_video_stream(tmp_path):
    frozen_vid = _make_frozen_mp4(tmp_path / "frozen.mp4")
    inspector = MotionQAInspector()
    report = inspector.audit_video(
        video_path=frozen_vid,
        personality="cold_war_noir",
        generate_sheet=True,
    )
    assert report.passed is False
    assert report.frozen_frame_pairs >= 1
    assert any(f.code == "FROZEN_OR_STAGNANT_MOTION" for f in report.findings)
    assert report.contact_sheet_path is not None and Path(report.contact_sheet_path).exists()


def test_motion_qa_optional_vision_critique_callback(tmp_path):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)
    res = engine.render_motion_clip(
        template="tactical_hud",
        title="BERLIN ARCHIVE",
        subtitle="SECTOR ALPHA",
        output_path=tmp_path / "hud.mp4",
        duration_sec=1.0,
        width=640,
        height=360,
        fps=12,
        force_procedural=True,
    )
    assert res.success is True
    called = []

    def fake_vision(sheet_path: Path) -> str:
        called.append(sheet_path)
        return "- Contrast clear\n- Zero clipping"

    report = MotionQAInspector().audit_video(
        video_path=res.output_video_path,
        vision_critique=True,
        vision_callback=fake_vision,
    )
    assert len(called) == 1
    assert "Contrast clear" in (report.vision_critique or "")


def test_tactical_graphics_legibility_and_qa_precheck(tmp_path):
    gfx = TacticalGraphicsEngine()
    legibility = gfx.validate_overlay_legibility(fg_hex="#F1F5F9", bg_hex="#0A0F18")
    assert legibility["passed"] is True
    assert legibility["contrast_ratio"] >= 10.0

    bad_legibility = gfx.validate_overlay_legibility(fg_hex="#222222", bg_hex="#111111")
    assert bad_legibility["passed"] is False

    base_vid = _make_frozen_mp4(tmp_path / "base.mp4", width=640, height=360, frames=16, fps=16)
    frozen_ov = _make_frozen_mp4(tmp_path / "frozen_ov.mp4", width=640, height=360, frames=16, fps=16)
    ok = gfx.composite_motion_overlay(
        base_video_path=base_vid,
        overlay_video_path=frozen_ov,
        output_video_path=tmp_path / "blocked.mp4",
        qa_check=True,
        strict_qa=True,
    )
    assert ok is False
    assert not (tmp_path / "blocked.mp4").exists()


def test_copy_clarity_5s_linter_and_youtube_booster_integration(tmp_path):
    validator = DarkFactoryStoryValidator()
    good = validator.audit_5s_hook_clarity(
        "At 00:23 UTC, Moscow radar logged five incoming nuclear warheads."
    )
    assert good.passed is True
    assert good.opening_word_count <= 15
    assert good.estimated_spoken_sec <= 5.0

    bad = validator.audit_5s_hook_clarity(
        "In today's fast-paced world, let us dive deep into this revolutionary game changer that will unlock the secrets of history for everyone."
    )
    assert bad.passed is False
    assert len(bad.filler_buzzwords) >= 3
    assert bad.opening_word_count > 15

    # Regression check: later-episode buzzwords in sentence 2 must not penalize crisp 5s opening hook
    episode_script = (
        "At 00:23 UTC, Moscow radar logged five incoming warheads. "
        "Later in the chapter we dive deep into this revolutionary game changer."
    )
    isolated = validator.audit_5s_hook_clarity(episode_script)
    assert isolated.passed is True
    assert isolated.filler_buzzwords == []

    bridge = YouTubeAlgorithmBoosterBridge(output_dir=tmp_path)
    pkg = bridge.build_master_youtube_package(
        project_id="sprint4_copy_test",
        title="The 20-Minute Radar Glitch That Nearly Ended Europe",
        description="Serpukhov-15 archive logs show an unprecedented orbital reflection error in September 1983.",
        script_text="At 00:23 UTC, Moscow radar logged five incoming warheads. Duty officer Petrov had three minutes.",
        duration_sec=480.0,
    )
    assert "copy_clarity_audit" in pkg
    assert pkg["copy_clarity_audit"]["passed"] is True
