"""Sprint 10 TDD Suite: Mobile UI Safe-Zones, Kinetic Captions & 9:16 Vertical Shorts Repurposer."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video
from src.video.kinetic_captions import CAPTION_STYLES, KineticCaptionEngine
from src.video.motion_qa import PLATFORM_SAFE_ZONES, MotionQAInspector, OverlayPlacement
from src.video.shorts_repurposer import ShortsRepurposerEngine


def _make_sample_16x9_master(
    path: Path,
    duration_sec: float = 3.0,
    width: int = 640,
    height: int = 360,
    fps: int = 12,
    salient_x_ratio: float = 0.78,
) -> Path:
    """Synthesize a 16:9 muxed A/V MP4 with high-contrast target shifted horizontally."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_frames = bytearray()
    total_frames = int(round(duration_sec * fps))
    cx = int(round(width * salient_x_ratio))
    cy = height // 2

    for i in range(total_frames):
        frm = np.full((height, width, 3), (12, 16, 22), dtype=np.uint8)
        shift = (i % 6) * 2
        cv2.rectangle(frm, (cx - 48, cy - 80 + shift), (cx + 48, cy + 80 + shift), (245, 190, 40), -1)
        cv2.circle(frm, (cx, cy), 22, (255, 255, 255), 3)
        raw_frames.extend(frm.tobytes())

    cmd = [
        get_ffmpeg_binary(),
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
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration_sec:.2f}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        path.as_posix(),
    ]
    proc = subprocess.run(cmd, input=bytes(raw_frames), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")[:300]
    return path


def test_motion_qa_mobile_safe_zones_enforced():
    inspector = MotionQAInspector()
    assert {"none", "youtube_shorts", "tiktok", "instagram_reels"}.issubset(PLATFORM_SAFE_ZONES.keys())

    # Bottom captions positioned inside YouTube Shorts bottom description UI deadzone
    bottom_deadzone = [
        OverlayPlacement(overlay_id="cap_bottom", label="Bottom Caption", start_sec=0.0, end_sec=3.0, x=0.08, y=0.80, width=0.65, height=0.14),
    ]
    audit_yt_bad = inspector.audit_overlay_overlaps(
        bottom_deadzone,
        total_duration_sec=3.0,
        step_sec=0.5,
        safe_zone_profile="youtube_shorts",
    )
    assert audit_yt_bad.passed is False
    assert any(b.get("code") == "SAFE_ZONE_VIOLATION" for b in audit_yt_bad.bounds_violations)

    # Engagement icon column violation on TikTok right rail
    right_rail = [
        OverlayPlacement(overlay_id="badge_right", label="Right Stamp", start_sec=0.0, end_sec=2.0, x=0.86, y=0.52, width=0.11, height=0.14),
    ]
    audit_tt_bad = inspector.audit_overlay_overlaps(
        right_rail,
        total_duration_sec=2.0,
        step_sec=0.5,
        safe_zone_profile="tiktok",
    )
    assert audit_tt_bad.passed is False
    assert any(b.get("code") == "SAFE_ZONE_VIOLATION" for b in audit_tt_bad.bounds_violations)

    # Clean safe-zone centered caption band works across all mobile platforms
    safe_band = [
        OverlayPlacement(overlay_id="cap_safe", label="Safe Kinetic Caption", start_sec=0.0, end_sec=3.0, x=0.08, y=0.56, width=0.70, height=0.13),
    ]
    for profile in ("youtube_shorts", "tiktok", "instagram_reels"):
        audit_ok = inspector.audit_overlay_overlaps(
            safe_band,
            total_duration_sec=3.0,
            step_sec=0.5,
            safe_zone_profile=profile,
        )
        assert audit_ok.passed is True, f"Expected clean pass for {profile}, got {audit_ok.bounds_violations}"


def test_kinetic_captions_renders_all_styles_and_ass(tmp_path):
    from src.video.kinetic_captions import _format_ass_ts

    # Verify centisecond rollover prevents invalid 0:00:60.00 timecodes
    assert _format_ass_ts(59.997) == "0:01:00.00"
    assert _format_ass_ts(3599.997) == "1:00:00.00"

    engine = KineticCaptionEngine()
    raw_mp4 = _make_sample_16x9_master(tmp_path / "portrait_seed.mp4", duration_sec=2.0, width=360, height=640, fps=12, salient_x_ratio=0.5)
    timings = engine.timings_from_script(
        "Orbital radar flagged critical anomalous telemetry across every sector.",
        total_duration_sec=2.0,
    )
    assert len(timings) >= 6

    # Verify ASS delimiter neutralization strips { } \ \n tokens
    ass_injected = engine.generate_ass_subtitles(
        segments=engine.build_phrase_segments(
            [{"word": "{\\pos(0,0)}Signal\nInjected", "start_sec": 0.0, "end_sec": 0.6}],
            style="editorial_karaoke",
        ),
        output_ass_path=tmp_path / "sanitized.ass",
        width=540,
        height=960,
        style="editorial_karaoke",
    )
    ass_text = ass_injected.read_text(encoding="utf-8")
    assert "\\pos" not in ass_text
    assert "\nInjected" not in ass_text

    for style in CAPTION_STYLES:
        out_mp4 = tmp_path / f"captioned_{style}.mp4"
        res = engine.render_captioned_video(
            input_video_path=raw_mp4,
            output_video_path=out_mp4,
            word_timings=timings,
            style=style,
            safe_zone_profile="youtube_shorts",
            trigger_keywords=["critical", "radar"],
        )
        assert res.success is True, res.error
        assert res.style == style
        assert res.phrase_count >= 2
        assert Path(res.video_path).is_file()
        assert Path(res.ass_path).is_file()
        assert "Dialogue:" in Path(res.ass_path).read_text(encoding="utf-8")
        assert res.overlap_audit.get("passed") is True
        props = probe_video(Path(res.video_path))
        assert props.width == 360 and props.height == 640


def test_shorts_repurposer_crops_16x9_with_salience_and_clean_broll(tmp_path):
    master = _make_sample_16x9_master(
        tmp_path / "master_16x9.mp4",
        duration_sec=3.0,
        width=640,
        height=360,
        fps=12,
        salient_x_ratio=0.80,
    )
    assert probe_video(master).has_audio is True

    engine = ShortsRepurposerEngine(output_dir=tmp_path / "shorts_out")
    res = engine.repurpose_to_vertical_short(
        title="Orbital Telemetry Breach",
        script="Declassified sensors recorded acute electromagnetic interference over northern silos.",
        source_video_path=master,
        style="hormozi_pop",
        safe_zone_profile="tiktok",
        target_duration_sec=2.0,
        width=540,
        height=960,
        fps=12,
        export_microstock_broll=True,
    )

    assert res.success is True, res.error
    assert res.safe_zone_passed is True
    assert res.salient_center_x > 0.55
    assert res.alamy_blocked is True
    assert "alamy" not in res.eligible_agencies
    assert "adobe" in res.eligible_agencies

    short_props = probe_video(Path(res.short_video_path))
    assert short_props.width == 540
    assert short_props.height == 960
    assert short_props.has_audio is True

    assert res.stock_broll_path is not None
    assert res.stock_broll_muted is True
    broll_props = probe_video(Path(res.stock_broll_path))
    assert broll_props.width == 540
    assert broll_props.height == 960
    assert broll_props.has_audio is False

    manifest_data = json.loads(Path(res.manifest_path).read_text(encoding="utf-8"))
    assert manifest_data["alamy_blocked"] is True
    assert Path(res.ass_path).is_file()


def test_sprint10_endpoint_and_security_guards():
    client = TestClient(app)
    paths_to_clean: list[Path] = []

    try:
        res_ok = client.post(
            "/api/v1/video/repurpose-short",
            json={
                "title": "Sprint 10 Endpoint Test Short",
                "script": "Rapid telemetry sweep confirming clean vertical mobile safe zones.",
                "style": "terminal_typewriter",
                "safe_zone_profile": "instagram_reels",
                "target_duration_sec": 3.0,
                "width": 540,
                "height": 960,
                "fps": 12,
                "export_microstock_broll": True,
            },
        )
        assert res_ok.status_code == 200, res_ok.text
        body = res_ok.json()
        assert body["success"] is True
        assert body["safe_zone_passed"] is True
        assert body["alamy_blocked"] is True
        assert body["stock_broll_muted"] is True

        for key in ("short_video_path", "ass_path", "stock_broll_path", "manifest_path"):
            val = body.get(key)
            if val:
                p = Path(val)
                assert p.is_file()
                paths_to_clean.append(p)
                if key == "short_video_path":
                    raw_variant = p.with_name(f"{p.stem.replace('_captioned', '')}_raw.mp4")
                    paths_to_clean.append(raw_variant)
                elif key == "stock_broll_path":
                    paths_to_clean.append(p.with_suffix(".html"))
                    paths_to_clean.append(p.with_name(f"{p.stem}_contact_sheet.png"))

        # Traversal attempt rejected at boundary
        res_trav = client.post(
            "/api/v1/video/repurpose-short",
            json={
                "title": "Traversal Guard",
                "source_video_path": "../../Windows/System32/drivers/etc/hosts",
            },
        )
        assert res_trav.status_code == 400

        # Invalid style / whitespace title rejected with 400
        res_style = client.post(
            "/api/v1/video/repurpose-short",
            json={"title": "Bad Style", "style": "invalid_style_name"},
        )
        assert res_style.status_code == 400

        res_ws = client.post(
            "/api/v1/video/repurpose-short",
            json={"title": "   "},
        )
        assert res_ws.status_code == 400
    finally:
        for p in paths_to_clean:
            p.unlink(missing_ok=True)
