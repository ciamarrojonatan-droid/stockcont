"""Sprint 9 TDD Suite: 0.5s Overlay Overlap Auditor, Storyboard Compiler & Dual Monetization."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from src.dashboard.app import app
from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video


def _make_sample_master_mp4(path: Path, duration_sec: float = 4.0, width: int = 640, height: int = 360, fps: int = 12) -> Path:
    """Create a short muxed A/V master MP4 so -an audio stripping is strictly proven."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_frames = bytearray()
    total_frames = int(round(duration_sec * fps))
    for i in range(total_frames):
        frm = np.full((height, width, 3), (18, 28 + (i * 3) % 80, 48 + (i * 4) % 90), dtype=np.uint8)
        cv2.rectangle(frm, (40 + i * 5, 60), (220 + i * 5, 240), (56, 189, 248), 3)
        raw_frames.extend(frm.tobytes())

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_sec:.2f}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        path.as_posix(),
    ]
    res = subprocess.run(cmd, input=bytes(raw_frames), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    assert res.returncode == 0, res.stderr.decode("utf-8", errors="replace")[:300]
    return path


def test_motion_qa_audits_05s_overlay_overlaps_and_bounds():
    from src.video.motion_qa import MotionQAInspector, OverlayPlacement

    inspector = MotionQAInspector()

    # Case 1: colliding placements at bottom edge around t=1.0s
    colliding = [
        OverlayPlacement(overlay_id="lt_1", label="Lower Third", start_sec=0.0, end_sec=3.0, x=0.05, y=0.76, width=0.55, height=0.16),
        OverlayPlacement(overlay_id="ticker_1", label="Bottom Banner", start_sec=0.5, end_sec=2.5, x=0.35, y=0.80, width=0.45, height=0.12),
    ]
    res_bad = inspector.audit_overlay_overlaps(colliding, total_duration_sec=3.0, step_sec=0.5)
    assert res_bad.passed is False
    assert res_bad.time_step_sec == 0.5
    assert res_bad.samples_checked >= 6
    assert len(res_bad.collisions) >= 1
    assert res_bad.collisions[0]["overlay_a"] == "lt_1"
    assert res_bad.collisions[0]["overlay_b"] == "ticker_1"

    # Case 2: out-of-bounds horizontal clip
    out_of_bounds = [
        OverlayPlacement(overlay_id="badge_oob", label="Wide Stamp", start_sec=0.0, end_sec=2.0, x=0.78, y=0.08, width=0.32, height=0.14),
    ]
    res_oob = inspector.audit_overlay_overlaps(out_of_bounds, total_duration_sec=2.0, step_sec=0.5)
    assert res_oob.passed is False
    assert len(res_oob.bounds_violations) >= 1

    # Case 3: clean non-overlapping HUD layout
    clean = [
        OverlayPlacement(overlay_id="stamp_top", label="Classified Badge", start_sec=0.0, end_sec=3.0, x=0.68, y=0.06, width=0.25, height=0.14),
        OverlayPlacement(overlay_id="lt_clean", label="Lower Third", start_sec=0.0, end_sec=3.0, x=0.06, y=0.78, width=0.52, height=0.15),
    ]
    res_ok = inspector.audit_overlay_overlaps(clean, total_duration_sec=3.0, step_sec=0.5)
    assert res_ok.passed is True
    assert res_ok.collisions == []
    assert res_ok.bounds_violations == []


def test_storyboard_compiler_builds_validated_budgeted_manifest(tmp_path):
    from src.video.storyboard_compiler import StoryboardCompiler

    script = (
        "In 1983 Soviet warning satellites signaled five incoming missiles over Serpukhov bunker. "
        "Duty officer Petrov stared at glowing amber alarms while radar computers demanded instant retaliation. "
        "Yet orbital geometry exposed a reflection blinding every optical sensor over the horizon. "
        "Minutes remained before automated launch protocols locked Eurasia into nuclear winter."
    )
    compiler = StoryboardCompiler(output_dir=tmp_path / "storyboards")
    res = compiler.compile_storyboard(
        title="The 1983 Orbital False Alarm",
        script=script,
        target_niche="industrial_automation",
        target_duration_sec=20.0,
    )

    assert res.success is True
    assert len(res.scenes) >= 4
    assert res.overlap_audit["passed"] is True
    assert res.hook_audit["opening_word_count"] > 0
    assert res.story_audit["overall_retention_score"] > 0
    assert res.budget_estimate["total_production_cost_usd"] > 0
    assert Path(res.manifest_path).is_file()
    saved = json.loads(Path(res.manifest_path).read_text(encoding="utf-8"))
    assert saved["title"] == "The 1983 Orbital False Alarm"


def test_youtube_booster_renders_physical_thumbnails_and_muted_stock_brolls(tmp_path):
    from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge

    master_mp4 = _make_sample_master_mp4(tmp_path / "master_episode.mp4", duration_sec=4.0)
    assert probe_video(master_mp4).has_audio is True

    bridge = YouTubeAlgorithmBoosterBridge(output_dir=tmp_path / "yt_pack")
    thumbs = bridge.render_tri_variant_thumbnails(
        project_id="serpukhov_test",
        title="The 1983 Soviet Glitch",
        subtitle="DECLASSIFIED TELEMETRY",
        output_dir=tmp_path / "thumbs",
    )
    assert len(thumbs) == 3
    for item in thumbs:
        img_p = Path(item["image_path"])
        assert img_p.is_file()
        with Image.open(img_p) as im:
            assert im.size == (1280, 720)
            assert im.format == "JPEG"

    broll_res = bridge.extract_monetizable_stock_brolls(
        master_video_path=master_mp4,
        output_dir=tmp_path / "stock_brolls",
        count=3,
        clip_duration_sec=1.1,
        target_width=1280,
        target_height=720,
    )
    assert len(broll_res["clips"]) >= 3
    assert broll_res["alamy_blocked"] is True
    assert "alamy" not in broll_res["eligible_agencies"]
    assert "adobe" in broll_res["eligible_agencies"]
    assert Path(broll_res["catalog_manifest_path"]).is_file()
    for c in broll_res["clips"]:
        clip_path = Path(c["clip_path"])
        assert clip_path.is_file()
        props = probe_video(clip_path)
        assert props.has_audio is False  # Strict B-roll -an enforcement


def test_sprint9_endpoints_and_path_containment():
    client = TestClient(app)
    created_manifest: Path | None = None

    try:
        res_sb = client.post(
            "/api/v1/video/storyboard-compile",
            json={
                "title": "Operation Able Archer Telemetry",
                "script": "In November 1983 encrypted NATO dispatches triggered maximum alert across Eastern Bloc radar bunkers. Analysts tracked bomber wings across darkened Baltic airspace.",
                "target_niche": "industrial_automation",
                "target_duration_sec": 16.0,
            },
        )
        assert res_sb.status_code == 200
        body_sb = res_sb.json()
        assert body_sb["success"] is True
        assert body_sb["overlap_audit"]["passed"] is True
        created_manifest = Path(body_sb["manifest_path"])
        assert created_manifest.is_file()

        # Path traversal blocked on master_video_path
        res_bad = client.post(
            "/api/v1/youtube/render-monetization-pack",
            json={
                "project_id": "traversal_guard",
                "title": "Security Boundary Test",
                "master_video_path": "../../Windows/System32/drivers/etc/hosts",
            },
        )
        assert res_bad.status_code == 400
    finally:
        if created_manifest is not None:
            created_manifest.unlink(missing_ok=True)
