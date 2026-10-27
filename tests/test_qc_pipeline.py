"""Tests for the Quality Control (QC) Inspector, Upscaler, and Dashboard API."""

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.analyzer.qc_inspector import QCInspector
from src.dashboard.app import app
from src.factory.upscaler import Upscaler


@pytest.fixture
def temp_qc_env(tmp_path):
    """Set up temporary staging and processed directories for testing."""
    staging_dir = tmp_path / "staging" / "images"
    staging_dir.mkdir(parents=True, exist_ok=True)
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    final_dir = tmp_path / "final" / "images"
    final_dir.mkdir(parents=True, exist_ok=True)

    config_file = processed_dir / "qc_config.json"
    manifest_file = processed_dir / "qc_manifest.json"

    # Create dummy staging image
    dummy_img = Image.new("RGB", (1024, 768), color=(73, 109, 137))
    dummy_img_path = staging_dir / "raw_test_01.png"
    dummy_img.save(str(dummy_img_path))

    inspector = QCInspector(
        staging_dir=staging_dir,
        config_file=config_file,
        manifest_file=manifest_file,
    )
    upscaler = Upscaler(
        staging_dir=staging_dir,
        final_dir=final_dir,
        target_min_dim=7680,
    )

    return {
        "staging_dir": staging_dir,
        "processed_dir": processed_dir,
        "final_dir": final_dir,
        "config_file": config_file,
        "manifest_file": manifest_file,
        "dummy_img_path": dummy_img_path,
        "inspector": inspector,
        "upscaler": upscaler,
    }


def test_qc_config_defaults_and_toggle(temp_qc_env):
    inspector = temp_qc_env["inspector"]

    # 1. Default should be 'auto' as requested
    cfg = inspector.get_config()
    assert cfg["mode"] == "auto"
    assert cfg["min_score"] == 7.5
    assert cfg["auto_upscale"] is False

    # 2. Toggle to 'manual'
    updated = inspector.set_config(mode="manual", min_score=8.0, auto_upscale=True)
    assert updated["mode"] == "manual"
    assert updated["min_score"] == 8.0
    assert updated["auto_upscale"] is True

    # 3. Reload from disk
    reloaded = inspector.get_config()
    assert reloaded["mode"] == "manual"


def test_scan_staging_registers_images(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    items = inspector.scan_staging()

    assert len(items) == 1
    item = items[0]
    assert item["filename"] == "raw_test_01.png"
    assert item["status"] == "pending"
    assert item["score"] is None


def test_manual_set_status(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    inspector.scan_staging()

    # Approve manually
    updated = inspector.set_status("raw_test_01.png", "approved", notes="Manually verified")
    assert updated["status"] == "approved"
    assert updated["manual_override"] is True
    assert updated["manual_notes"] == "Manually verified"

    stats = inspector.get_stats()
    assert stats["approved"] == 1
    assert stats["pending"] == 0


def test_batch_set_status(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    inspector.scan_staging()

    count = inspector.batch_set_status(["raw_test_01.png"], "rejected")
    assert count == 1

    stats = inspector.get_stats()
    assert stats["rejected"] == 1
    assert stats["approved"] == 0


def test_evaluate_image_auto_mode_approved(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    inspector.set_config(auto_upscale=True)
    inspector.scan_staging()

    mock_gemini_response = {
        "score": 9.0,
        "decision": "approve",
        "anatomy_score": 9.5,
        "composition_score": 9.0,
        "copy_space_score": 8.5,
        "commercial_viability_score": 9.0,
        "flaws": [],
        "strengths": ["Clean rule of thirds", "Excellent lighting"],
        "summary": "Excelente fotografia stock comercial.",
    }

    with patch.object(inspector, "_call_gemini_vision_audit", return_value=mock_gemini_response):
        with patch("src.factory.upscaler.Upscaler.upscale_image", return_value=Path("dummy_final.jpg")):
            result = inspector.evaluate_image("raw_test_01.png")

    assert result["score"] == 9.0
    assert result["decision"] == "approve"
    assert result["status"] == "approved"
    assert result["upscaled"] is True


def test_evaluate_image_auto_mode_rejected(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    inspector.scan_staging()

    mock_gemini_response = {
        "score": 5.2,
        "decision": "reject",
        "anatomy_score": 4.0,
        "composition_score": 6.0,
        "copy_space_score": 5.0,
        "commercial_viability_score": 5.0,
        "flaws": ["Deformed left hand with 6 fingers"],
        "strengths": [],
        "summary": "Reprovado por deformidade anatômica severa.",
    }

    with patch.object(inspector, "_call_gemini_vision_audit", return_value=mock_gemini_response):
        result = inspector.evaluate_image("raw_test_01.png")

    assert result["score"] == 5.2
    assert result["decision"] == "reject"
    assert result["status"] == "rejected"
    assert result["upscaled"] is False


def test_evaluate_image_manual_mode_remains_pending(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    inspector.set_config(mode="manual")
    inspector.scan_staging()

    mock_gemini_response = {
        "score": 8.8,
        "decision": "approve",
        "flaws": [],
        "strengths": ["High commercial readiness"],
        "summary": "Recomendado para aprovação manual.",
    }

    with patch.object(inspector, "_call_gemini_vision_audit", return_value=mock_gemini_response):
        result = inspector.evaluate_image("raw_test_01.png")

    assert result["score"] == 8.8
    # In manual mode, it remains 'pending' awaiting human review in Dashboard
    assert result["status"] == "pending"


def test_upscaler_execution(temp_qc_env):
    upscaler = temp_qc_env["upscaler"]
    out_path = upscaler.upscale_image("raw_test_01.png")

    assert out_path is not None
    assert out_path.exists()

    with Image.open(out_path) as upscaled_img:
        w, h = upscaled_img.size
        assert max(w, h) >= 7680
        assert upscaled_img.format == "JPEG"


def test_dashboard_qc_api():
    client = TestClient(app)

    # 1. Config endpoint
    resp = client.get("/api/qc/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "min_score" in data

    # 2. Update config endpoint
    resp = client.post("/api/qc/config", json={"mode": "manual", "min_score": 8.2})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "manual"
    assert resp.json()["min_score"] == 8.2

    # Reset back to auto default
    resp = client.post("/api/qc/config", json={"mode": "auto", "min_score": 7.5})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "auto"

    # 3. Stats endpoint
    resp = client.get("/api/qc/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_staging" in stats
    assert "approved" in stats
    assert "mode" in stats

    # 4. Images list
    resp = client.get("/api/qc/images?filter=all")
    assert resp.status_code == 200
    assert "images" in resp.json()


def test_package_approved_images_zip(temp_qc_env):
    inspector = temp_qc_env["inspector"]
    # Register and approve image
    inspector.register_staging_image("raw_test_01.png")
    inspector.set_status("raw_test_01.png", "approved")

    zip_path, files = inspector.package_approved_images()
    assert zip_path is not None
    assert zip_path.exists()
    assert len(files) == 1
    assert "raw_test_01.png" in files

    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zf:
        assert "raw_test_01.png" in zf.namelist()
