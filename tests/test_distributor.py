import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.uploader.ftp_distributor import (
    AgencyConfig,
    get_available_agencies,
    load_upload_history,
    save_upload_history,
    get_ready_images,
    run_distributor,
    test_agency_connection as check_agency_connection,
)


def test_get_available_agencies_keys_and_protocols():
    """Verify that all 7 microstock agencies are registered with correct protocols."""
    agencies = get_available_agencies()
    assert "adobe" in agencies
    assert "freepik" in agencies
    assert "dreamstime" in agencies
    assert "pond5" in agencies
    assert "alamy" in agencies
    assert "vecteezy" in agencies
    assert "123rf" in agencies

    assert agencies["adobe"].protocol == "sftp"
    assert agencies["adobe"].port == 22

    assert agencies["freepik"].protocol == "ftp"
    assert agencies["freepik"].port == 21


def test_agency_is_configured_logic():
    """Verify is_configured property strictly validates non-empty credentials."""
    unconfigured = AgencyConfig(
        key="test",
        name="Test",
        protocol="ftp",
        host="ftp.test.com",
        port=21,
        username="",
        password="",
    )
    assert not unconfigured.is_configured

    whitespace_only = AgencyConfig(
        key="test",
        name="Test",
        protocol="ftp",
        host="ftp.test.com",
        port=21,
        username="   ",
        password="   ",
    )
    assert not whitespace_only.is_configured

    configured = AgencyConfig(
        key="test",
        name="Test",
        protocol="sftp",
        host="sftp.test.com",
        port=22,
        username="my_contributor_id",
        password="secure_password_123",
    )
    assert configured.is_configured


def test_upload_history_save_and_load(tmp_path, monkeypatch):
    """Verify atomic persistence and reading of upload history ledger."""
    history_file = tmp_path / "upload_history.json"
    processed_dir = tmp_path

    monkeypatch.setattr("src.uploader.ftp_distributor.UPLOAD_HISTORY_FILE", history_file)
    monkeypatch.setattr("src.uploader.ftp_distributor.PROCESSED_DIR", processed_dir)

    initial = load_upload_history()
    assert initial == {}

    sample_history = {
        "image_01.jpg": {"adobe": "2026-10-13T04:00:00Z"},
        "image_02.jpg": {"freepik": "2026-10-13T04:05:00Z"},
    }
    save_upload_history(sample_history)

    loaded = load_upload_history()
    assert loaded == sample_history
    assert "image_01.jpg" in loaded
    assert loaded["image_01.jpg"]["adobe"] == "2026-10-13T04:00:00Z"


def test_get_ready_images(tmp_path, monkeypatch):
    """Verify ready images discovery returns only .jpg and .jpeg files."""
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True)
    monkeypatch.setattr("src.uploader.ftp_distributor.FINAL_IMAGES_DIR", images_dir)

    # Create dummy files
    (images_dir / "asset1.jpg").write_text("dummy")
    (images_dir / "asset2.jpeg").write_text("dummy")
    (images_dir / "asset3.png").write_text("dummy")
    (images_dir / "metadata.txt").write_text("dummy")

    ready = get_ready_images()
    filenames = [p.name for p in ready]
    assert "asset1.jpg" in filenames
    assert "asset2.jpeg" in filenames
    assert "asset3.png" not in filenames
    assert "metadata.txt" not in filenames


def test_agency_connection_unconfigured():
    """Verify test_agency_connection handles unconfigured agency gracefully."""
    agency = AgencyConfig(
        key="test",
        name="Test",
        protocol="ftp",
        host="ftp.test.com",
        port=21,
        username="",
        password="",
    )
    success, msg = check_agency_connection(agency)
    assert not success
    assert "Credenciais ausentes" in msg


def test_run_distributor_dry_run_unconfigured():
    """Verify run_distributor exits cleanly when no agency is configured."""
    with patch("src.uploader.ftp_distributor.get_available_agencies") as mock_agencies:
        mock_agencies.return_value = {
            "adobe": AgencyConfig("adobe", "Adobe", "sftp", "host", 22, "", "")
        }
        res = run_distributor(dry_run=True)
        assert res == {}


def test_run_distributor_alamy_anti_ban_block(tmp_path, monkeypatch):
    """Verify that Alamy uploads are automatically blocked when AI images are dispatched."""
    from PIL import Image

    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True)
    ai_img = images_dir / "ai_generated_art.jpg"
    Image.new("RGB", (3840, 2160), color=(10, 20, 30)).save(ai_img, "JPEG")

    history_file = tmp_path / "upload_history.json"
    monkeypatch.setattr("src.uploader.ftp_distributor.UPLOAD_HISTORY_FILE", history_file)
    monkeypatch.setattr("src.uploader.ftp_distributor.PROCESSED_DIR", tmp_path)

    # Configure Alamy agency with dummy credentials
    alamy_agency = AgencyConfig(
        key="alamy",
        name="Alamy",
        protocol="ftp",
        host="upload.alamy.com",
        port=21,
        username="alamy_user",
        password="secret_password",
    )

    with patch("src.uploader.ftp_distributor.get_available_agencies") as mock_agencies,          patch("src.uploader.ftp_distributor.upload_via_ftp") as mock_ftp:
        mock_agencies.return_value = {"alamy": alamy_agency}

        # Run distributor targeting Alamy
        results = run_distributor(target_platform="alamy", dry_run=False, images_dir=images_dir)

        # Upload function should NEVER be called for Alamy with AI content!
        mock_ftp.assert_not_called()
        assert results.get("alamy", 0) == 0
