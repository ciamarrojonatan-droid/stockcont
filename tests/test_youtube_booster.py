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
