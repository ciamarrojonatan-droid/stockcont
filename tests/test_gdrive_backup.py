import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.backup.gdrive_backup import (
    GoogleDriveBackup,
    load_backup_history,
    save_backup_history,
    run_gdrive_backup,
)


def test_gdrive_unconfigured_defaults(monkeypatch):
    """Verify GoogleDriveBackup initializes safely when unconfigured."""
    monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CREDENTIALS_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_LOCAL_PATH", raising=False)

    backup = GoogleDriveBackup()
    assert not backup.is_configured
    assert backup.mode == "unconfigured"


def test_gdrive_local_sync_configuration(tmp_path, monkeypatch):
    """Verify local sync mode is recognized when local path exists."""
    sync_dir = tmp_path / "My_Drive_Backup"
    sync_dir.mkdir()

    monkeypatch.setenv("GOOGLE_DRIVE_LOCAL_PATH", str(sync_dir))
    monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", raising=False)

    backup = GoogleDriveBackup()
    assert backup.is_configured
    assert backup.mode == "local_sync"


def test_gdrive_service_account_configuration(monkeypatch):
    """Verify service account mode is recognized with json string."""
    fake_sa_json = json.dumps({"type": "service_account", "project_id": "test-project"})
    monkeypatch.setenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", fake_sa_json)
    monkeypatch.delenv("GOOGLE_DRIVE_LOCAL_PATH", raising=False)

    backup = GoogleDriveBackup()
    assert backup.is_configured
    assert backup.mode == "api_service_account"


def test_backup_history_persistence(tmp_path, monkeypatch):
    """Verify atomic ledger save and load for Google Drive backups."""
    hist_file = tmp_path / "gdrive_backup_history.json"
    proc_dir = tmp_path

    monkeypatch.setattr("src.backup.gdrive_backup.BACKUP_HISTORY_FILE", hist_file)
    monkeypatch.setattr("src.backup.gdrive_backup.PROCESSED_DIR", proc_dir)

    initial = load_backup_history()
    assert initial == {}

    sample_ledger = {
        "asset_123.jpg": {
            "status": "success",
            "mode": "api_service_account",
            "ref": "1gdrive_file_id_abc",
            "size_bytes": 4500000,
            "backup_time": "2026-10-13T04:30:00Z"
        }
    }
    save_backup_history(sample_ledger)

    reloaded = load_backup_history()
    assert reloaded == sample_ledger
    assert reloaded["asset_123.jpg"]["ref"] == "1gdrive_file_id_abc"


def test_local_sync_file_transfer(tmp_path, monkeypatch):
    """Verify local sync mode copies assets and records ledger."""
    src_images_dir = tmp_path / "final_images"
    src_images_dir.mkdir()
    dst_sync_dir = tmp_path / "Google_Drive_Sync"
    dst_sync_dir.mkdir()

    dummy_img = src_images_dir / "test_render.jpg"
    dummy_img.write_bytes(b"\xFF\xD8\xFF\xE0" + b"dummy_content_bytes" * 100)

    hist_file = tmp_path / "gdrive_backup_history.json"
    monkeypatch.setattr("src.backup.gdrive_backup.FINAL_IMAGES_DIR", src_images_dir)
    monkeypatch.setattr("src.backup.gdrive_backup.BACKUP_HISTORY_FILE", hist_file)
    monkeypatch.setattr("src.backup.gdrive_backup.PROCESSED_DIR", tmp_path)
    monkeypatch.setenv("GOOGLE_DRIVE_LOCAL_PATH", str(dst_sync_dir))

    backup = GoogleDriveBackup()
    result = backup.backup_assets(include_csv=False)

    assert result["status"] == "completed"
    assert result["uploaded"] == 1
    assert result["failed"] == 0

    copied_file = dst_sync_dir / "test_render.jpg"
    assert copied_file.exists()
    assert copied_file.stat().st_size == dummy_img.stat().st_size

    # Running a second time should skip because it is already in history
    result_second = backup.backup_assets(include_csv=False)
    assert result_second["uploaded"] == 0
    assert result_second["skipped"] == 1


def test_dry_run_simulation(tmp_path, monkeypatch):
    """Verify dry-run reports pending files without copying or modifying ledger."""
    src_images_dir = tmp_path / "final_images"
    src_images_dir.mkdir()
    dst_sync_dir = tmp_path / "Google_Drive_Sync"
    dst_sync_dir.mkdir()

    dummy_img = src_images_dir / "simulated_render.jpg"
    dummy_img.write_text("dummy")

    hist_file = tmp_path / "gdrive_backup_history.json"
    monkeypatch.setattr("src.backup.gdrive_backup.FINAL_IMAGES_DIR", src_images_dir)
    monkeypatch.setattr("src.backup.gdrive_backup.BACKUP_HISTORY_FILE", hist_file)
    monkeypatch.setattr("src.backup.gdrive_backup.PROCESSED_DIR", tmp_path)
    monkeypatch.setenv("GOOGLE_DRIVE_LOCAL_PATH", str(dst_sync_dir))

    backup = GoogleDriveBackup()
    result = backup.backup_assets(dry_run=True, include_csv=False)

    assert result["status"] == "dry_run"
    assert result["pending"] == 1
    assert result["uploaded"] == 0

    # Ensure no file was transferred
    copied_file = dst_sync_dir / "simulated_render.jpg"
    assert not copied_file.exists()
