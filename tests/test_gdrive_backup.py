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
    run_gdrive_restore,
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


def test_restore_assets_unconfigured(monkeypatch):
    """Verify restore_assets returns unconfigured when not setup."""
    monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CREDENTIALS_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_LOCAL_PATH", raising=False)

    backup = GoogleDriveBackup()
    res = backup.restore_assets()
    assert res["status"] == "unconfigured"
    assert res["restored_images"] == 0


def test_local_sync_restore_assets(tmp_path, monkeypatch):
    """Verify local sync restore copies images, restores CSV, and merges upload history."""
    final_images = tmp_path / "final_images"
    final_images.mkdir()
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    gdrive_sync = tmp_path / "GDrive_Sync"
    gdrive_sync.mkdir()

    # Create dummy image in backup
    backup_img = gdrive_sync / "asset_99.jpg"
    backup_img.write_bytes(b"\xFF\xD8\xFF\xE0" + b"dummy_backup_bytes" * 50)

    # Create dummy upload history in backup
    backup_history = gdrive_sync / "upload_history.json"
    backup_history.write_text(json.dumps({
        "asset_99.jpg": {"123rf": "2026-10-25T12:00:00Z", "pond5": "2026-10-25T12:05:00Z"}
    }), encoding="utf-8")

    # Create dummy csv in backup
    backup_csv = gdrive_sync / "adobe_stock_upload.csv"
    backup_csv.write_text("Filename,Title,Keywords,Category\nasset_99.jpg,Test Title,test,1", encoding="utf-8")

    target_upload_history = processed_dir / "upload_history.json"
    target_csv = processed_dir / "adobe_stock_upload.csv"

    monkeypatch.setattr("src.backup.gdrive_backup.FINAL_IMAGES_DIR", final_images)
    monkeypatch.setattr("src.backup.gdrive_backup.PROCESSED_DIR", processed_dir)
    monkeypatch.setattr("src.backup.gdrive_backup.UPLOAD_HISTORY_FILE", target_upload_history)
    monkeypatch.setattr("src.backup.gdrive_backup.CSV_FILE", target_csv)
    monkeypatch.setenv("GOOGLE_DRIVE_LOCAL_PATH", str(gdrive_sync))

    backup = GoogleDriveBackup()
    assert backup.mode == "local_sync"

    # First run: should restore image, CSV, and merge history
    result = backup.restore_assets()
    assert result["status"] == "completed"
    assert result["restored_images"] == 1
    assert result["restored_metadata"] == 2
    assert result["skipped"] == 0

    assert (final_images / "asset_99.jpg").exists()
    assert target_csv.exists()
    assert target_upload_history.exists()

    with open(target_upload_history, "r", encoding="utf-8") as f:
        loaded_history = json.load(f)
    assert "asset_99.jpg" in loaded_history
    assert loaded_history["asset_99.jpg"]["123rf"] == "2026-10-25T12:00:00Z"

    # Second run without overwrite: image should be skipped
    result2 = backup.restore_assets(overwrite=False)
    assert result2["restored_images"] == 0
    assert result2["skipped"] == 1


def test_run_gdrive_restore_entrypoint(tmp_path, monkeypatch):
    """Verify run_gdrive_restore helper functions correctly."""
    gdrive_sync = tmp_path / "GDrive_Sync"
    gdrive_sync.mkdir()

    monkeypatch.setattr("src.backup.gdrive_backup.FINAL_IMAGES_DIR", tmp_path / "final_images")
    monkeypatch.setattr("src.backup.gdrive_backup.PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setenv("GOOGLE_DRIVE_LOCAL_PATH", str(gdrive_sync))

    res = run_gdrive_restore()
    assert res["status"] == "completed"
