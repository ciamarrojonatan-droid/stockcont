#!/usr/bin/env python3
"""Unit tests for StockCont 24/7 Production Daemon."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.orchestrator.daemon import StockContDaemon


def test_daemon_initialization():
    daemon = StockContDaemon(pacing_interval=120, min_prompt_buffer=30, dry_run=True)
    assert daemon.pacing_interval == 120
    assert daemon.min_prompt_buffer == 30
    assert daemon.dry_run is True
    assert daemon.cycles_completed == 0
    assert not daemon.is_running


def test_daemon_update_state(tmp_path: Path, monkeypatch):
    state_file = tmp_path / "daemon_state.json"
    monkeypatch.setattr("src.orchestrator.daemon.DAEMON_STATE_FILE", state_file)
    monkeypatch.setattr("src.orchestrator.daemon.PROCESSED_DIR", tmp_path)

    daemon = StockContDaemon(dry_run=True)
    daemon.is_running = True
    daemon.update_state("Fase 1", "Minerando tendências...")

    assert state_file.exists()
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "running"
    assert data["current_phase"] == "Fase 1"
    assert data["current_action"] == "Minerando tendências..."
    assert "quotas" in data
    assert "vault" in data


def test_smart_auto_purge(tmp_path: Path, monkeypatch):
    final_dir = tmp_path / "images"
    final_dir.mkdir(parents=True)
    purged_file = tmp_path / "purged_history.json"

    # Create dummy image
    img1 = final_dir / "asset_done.jpg"
    img1.write_bytes(b"dummy image data")

    img2 = final_dir / "asset_pending.jpg"
    img2.write_bytes(b"dummy image data 2")

    monkeypatch.setattr("src.orchestrator.daemon.FINAL_IMAGES_DIR", final_dir)
    monkeypatch.setattr("src.orchestrator.daemon.PURGED_HISTORY_FILE", purged_file)
    monkeypatch.setattr("src.orchestrator.daemon.PROCESSED_DIR", tmp_path)

    # Mock GoogleDriveBackup
    mock_gdrive = MagicMock()
    mock_gdrive.is_configured = True
    monkeypatch.setattr("src.backup.gdrive_backup.GoogleDriveBackup", lambda: mock_gdrive)

    # Mock backup history: both are backed up in GDrive
    monkeypatch.setattr("src.backup.gdrive_backup.load_backup_history", lambda: {
        "asset_done.jpg": {"file_id": "gdrive_123"},
        "asset_pending.jpg": {"file_id": "gdrive_456"},
    })

    # Mock upload history: asset_done is uploaded to adobe, asset_pending is NOT
    monkeypatch.setattr("src.uploader.ftp_distributor.load_upload_history", lambda: {
        "asset_done.jpg": {"adobe": "2026-10-29T00:00:00Z"},
    })

    # Mock agencies: only adobe is configured
    from src.uploader.ftp_distributor import AgencyConfig
    mock_agencies = {
        "adobe": AgencyConfig("adobe", "Adobe", "sftp", "host", 22, "user", "pass"),
    }
    monkeypatch.setattr("src.uploader.ftp_distributor.get_available_agencies", lambda: mock_agencies)

    daemon = StockContDaemon(dry_run=False)
    purged = daemon.smart_auto_purge()

    # asset_done should be purged, asset_pending kept!
    assert purged == 1
    assert not img1.exists()
    assert img2.exists()


def test_execute_single_cycle_dry_run(monkeypatch):
    daemon = StockContDaemon(dry_run=True)

    with patch("src.factory.prompt_queue.PromptQueueManager.get_stats") as mock_stats:
        mock_stats.return_value = {"pending": 100, "generated": 0, "total": 100}
        daemon.execute_single_cycle()
        assert daemon.cycles_completed == 1
        assert daemon.consecutive_errors == 0
