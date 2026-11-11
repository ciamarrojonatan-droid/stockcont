"""Unit tests for StockCont & DarkFactory YouTube Algorithm Booster & Compliance Bridge."""

import json
from pathlib import Path
import sys
import pytest

from src.video.youtube_booster import (
    YouTubeAlgorithmBoosterBridge,
    TriVariantThumbnail,
    run_youtube_booster_cli,
)


def test_tri_variant_thumbnails_generation():
    bridge = YouTubeAlgorithmBoosterBridge()
    variants = bridge.generate_tri_variant_thumbnails(project_title="test_doc")

    assert len(variants) == 3
    archetypes = [v["archetype"] for v in variants]
    assert "human_chiaroscuro_dread" in archetypes
    assert "tactical_macro_evidence" in archetypes
    assert "colossal_existential_scale" in archetypes

    for v in variants:
        assert v["word_count"] <= 4  # Strict 3-second packaging rule
        assert v["file_path"].endswith(".jpg")
        assert len(v["text_overlay"]) > 0


def test_seamless_outro_detection_and_remediation():
    bridge = YouTubeAlgorithmBoosterBridge()
    bad_script = "Petrov made his fateful choice. In conclusion, thank you for watching, and see you next time!"
    res = bridge.validate_and_enforce_seamless_outro(
        bad_script,
        next_episode_title="Cold War Declassified: Part 2",
        next_episode_hook="The Arctic Nuclear Submarine Incident",
    )

    assert res["has_retention_risk"] is True
    assert len(res["exit_cues_detected"]) >= 2
    assert "SEAMLESS BINGE BRIDGE" in res["remediated_script_outro"]
    assert "The Arctic Nuclear Submarine Incident" in res["remediated_script_outro"]


def test_seamless_outro_clean_script():
    bridge = YouTubeAlgorithmBoosterBridge()
    clean_script = "The second hand ticked past zero. The world remained alive, saved by human judgment."
    res = bridge.validate_and_enforce_seamless_outro(clean_script)
    assert res["has_retention_risk"] is False
    assert len(res["exit_cues_detected"]) == 0


def test_official_series_playlist():
    bridge = YouTubeAlgorithmBoosterBridge()
    res = bridge.generate_official_series_playlist(
        series_id="cold_war_series",
        series_title="Cold War Declassified",
        episode_index=2,
        total_episodes=8,
    )
    assert res["is_official_series"] is True
    assert res["episode_position"] == 2
    assert res["total_episodes"] == 8
    assert "Suggested Videos" in res["algorithmic_benefit"]


def test_codec_readiness_4k():
    bridge = YouTubeAlgorithmBoosterBridge()
    res_4k = bridge.verify_youtube_codec_readiness(width=3840, height=2160)
    assert res_4k["is_4k_or_1440p"] is True
    assert "VP09 / AV01" in res_4k["allocated_youtube_codec"]

    res_1080p = bridge.verify_youtube_codec_readiness(width=1920, height=1080)
    assert res_1080p["is_4k_or_1440p"] is False
    assert "AVC1" in res_1080p["allocated_youtube_codec"]


def test_self_certification_manifest():
    bridge = YouTubeAlgorithmBoosterBridge()
    manifest = bridge.generate_self_certification_manifest(
        project_id="test_cert_id",
        title="The 1983 Soviet Missile Crisis",
        description="Historical analysis of declassified early warning telemetry.",
    )
    assert manifest["project_id"] == "test_cert_id"
    assert "Green Dollar Sign" in manifest["projected_monetization_status"]
    assert manifest["rating_accuracy_tier"] == "High (Calibrated Trust Profile)"


def test_edsa_framing():
    bridge = YouTubeAlgorithmBoosterBridge()
    edsa = bridge.evaluate_edsa_framing(
        title="1983 Soviet False Nuclear Alarm",
        description="Historical archival documentary investigation into military telemetry.",
    )
    assert edsa["has_edsa_protection"] is True
    assert edsa["status"] == "EDSA_PROTECTED"
    assert edsa["edsa_score"] >= 60


def test_build_master_youtube_package(tmp_path):
    bridge = YouTubeAlgorithmBoosterBridge(output_dir=tmp_path)
    pkg = bridge.build_master_youtube_package(
        project_id="master_test_proj",
        title="The Petrov Crisis of 1983",
        description="A declassified documentary regarding Soviet early warning alarms.",
        duration_sec=720.0,
        width=3840,
        height=2160,
    )

    assert pkg["project_id"] == "master_test_proj"
    assert len(pkg["tri_variant_thumbnails"]) == 3
    assert pkg["official_series_playlist"]["is_official_series"] is True
    assert pkg["codec_readiness_audit"]["is_4k_or_1440p"] is True
    assert "Green Dollar Sign" in pkg["monetization_projection"]

    out_file = tmp_path / "master_test_proj_youtube_master_package.json"
    assert out_file.exists()
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["project_id"] == "master_test_proj"


def test_cli_runner_integration(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.video.youtube_booster.YOUTUBE_PACKAGES_DIR", tmp_path
    )
    out_file = run_youtube_booster_cli(
        title="Test CLI Episode",
        description="CLI Description for test.",
        duration=300.0,
        project_id="cli_test_case",
    )
    assert out_file.exists()


def test_parse_retention_csv_extracts_dropoffs_and_peaks():
    from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge

    csv_data = (
        "timestamp_sec,retention_pct\n"
        "0,100.0\n"
        "15,86.0\n"
        "30,82.5\n"
        "60,68.0\n"
        "120,64.0\n"
        "180,72.0\n"
        "240,59.0\n"
    )
    bridge = YouTubeAlgorithmBoosterBridge()
    report = bridge.parse_retention_csv(csv_data)

    assert report["sample_count"] == 7
    assert report["hook_30s_retention_pct"] == pytest.approx(82.5)
    assert report["avg_retention_pct"] > 70.0
    assert len(report["dropoff_events"]) >= 2
    assert any(d["timestamp_sec"] == 60 for d in report["dropoff_events"])
    assert len(report["peak_windows"]) >= 1


def test_lint_title_thumbnail_pair_flags_overlap_and_rewards_complementarity():
    from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge

    bridge = YouTubeAlgorithmBoosterBridge()

    bad = bridge.lint_title_thumbnail_pair(
        title="The Secret Operation That Changed Everything In Berlin",
        thumbnail_text="The Secret Operation Changed Everything Berlin",
    )
    assert bad["passed"] is False
    assert bad["overlap_ratio"] >= 0.5
    assert bad["thumbnail_word_count"] > 4
    assert len(bad["issues"]) >= 1

    good = bridge.lint_title_thumbnail_pair(
        title="The Forgotten 1961 Berlin Tunnel Protocol",
        thumbnail_text="LEAKED BLUEPRINT",
    )
    assert good["passed"] is True
    assert good["overlap_ratio"] == 0.0
    assert good["thumbnail_word_count"] == 2
    assert good["score"] >= 80.0


def test_validate_youtube_chapters_rules():
    from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge

    bridge = YouTubeAlgorithmBoosterBridge()

    valid_block = "00:00 Declassified Hook\n01:25 The Hidden Subway Shaft\n04:10 Midnight Discovery"
    ok = bridge.validate_youtube_chapters(valid_block, total_duration_sec=360.0)
    assert ok["valid"] is True
    assert ok["chapter_count"] == 3

    invalid_no_zero = "00:15 Late Start\n01:00 Middle\n02:00 End"
    bad = bridge.validate_youtube_chapters(invalid_no_zero, total_duration_sec=360.0)
    assert bad["valid"] is False
    assert any("00:00" in err for err in bad["errors"])


def test_extract_shorts_candidates_returns_15_to_58s_windows():
    from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge

    bridge = YouTubeAlgorithmBoosterBridge()
    segments = [
        {"start_sec": 10.0, "end_sec": 55.0, "tension_score": 0.94, "label": "Vault Breach"},
        {"start_sec": 90.0, "end_sec": 120.0, "tension_score": 0.72, "label": "Microfilm Clue"},
        {"start_sec": 180.0, "end_sec": 225.0, "tension_score": 0.89, "label": "Submarine Intercept"},
    ]
    shorts = bridge.extract_shorts_candidates(timeline_segments=segments, total_duration_sec=260.0, max_candidates=2)
    assert len(shorts) == 2
    assert shorts[0]["duration_sec"] <= 58.0
    assert shorts[0]["duration_sec"] >= 15.0
    assert shorts[0]["label"] == "Vault Breach"


def test_build_master_youtube_package_supports_closed_loop_extras(tmp_path):
    from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge

    bridge = YouTubeAlgorithmBoosterBridge(output_dir=tmp_path)
    pkg = bridge.build_master_youtube_package(
        project_id="yt_closed_loop",
        title="The Deep Sea Vault Nobody Dared Open",
        description="Complete historical breakdown.",
        duration_sec=420.0,
        thumbnail_text="NO EXIT",
        chapters="00:00 Hook\n01:30 Deep Descent\n05:10 Recovered Tape",
        retention_csv="timestamp_sec,retention_pct\n0,100\n30,84\n120,70",
    )
    assert "tri_variant_thumbnails" in pkg
    assert "title_thumbnail_lint" in pkg
    assert pkg["title_thumbnail_lint"]["passed"] is True
    assert pkg["chapters_audit"]["valid"] is True
    assert pkg["retention_audit"]["hook_30s_retention_pct"] == pytest.approx(84.0)
    assert len(pkg["shorts_candidates"]) >= 1


def test_dashboard_youtube_lint_endpoint():
    from fastapi.testclient import TestClient
    from src.dashboard.app import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/youtube/lint-package",
        json={
            "title": "Why The 1962 Radar Station Went Silent",
            "thumbnail_text": "04:12 AM",
            "chapters": "00:00 Cold Open\n01:20 Intercept\n03:45 Aftermath",
            "total_duration_sec": 480.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title_thumbnail_lint"]["passed"] is True
    assert data["chapters_audit"]["valid"] is True
    assert len(data["shorts_candidates"]) >= 1
