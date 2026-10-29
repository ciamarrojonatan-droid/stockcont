#!/usr/bin/env python3
"""Unit tests for StockCont QuotaManager (Rolling 7-day window)."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.uploader.quota_manager import QuotaManager, parse_timestamp, DEFAULT_WEEKLY_LIMITS


def test_parse_timestamp():
    # Valid ISO strings
    dt1 = parse_timestamp("2026-10-28T12:00:00Z")
    assert dt1 is not None
    assert dt1.tzinfo is not None

    dt2 = parse_timestamp({"uploaded_at": "2026-10-28T14:30:00+00:00"})
    assert dt2 is not None
    assert dt2.hour == 14

    # Invalid / empty
    assert parse_timestamp(None) is None
    assert parse_timestamp("") is None
    assert parse_timestamp("invalid-date") is None


def test_quota_manager_rolling_calculation(tmp_path: Path):
    history_file = tmp_path / "upload_history.json"
    now_utc = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Mock history:
    # 2 uploads 2 days ago (inside 7d window)
    # 1 upload 8 days ago (outside 7d window)
    d_inside1 = (now_utc - timedelta(days=2)).isoformat()
    d_inside2 = (now_utc - timedelta(days=5)).isoformat()
    d_outside = (now_utc - timedelta(days=8)).isoformat()

    history = {
        "img1.jpg": {"adobe": d_inside1, "freepik": d_inside1},
        "img2.jpg": {"adobe": d_inside2},
        "img3.jpg": {"adobe": d_outside},
    }

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f)

    qm = QuotaManager(history_path=history_file, custom_limits={"adobe": 3, "freepik": 2})

    # For adobe: limit is 3, 2 inside window -> 1 available
    rep_adobe = qm.check_platform_quota("adobe", reference_time=now_utc)
    assert rep_adobe.weekly_limit == 3
    assert rep_adobe.uploads_last_7_days == 2
    assert rep_adobe.slots_available == 1
    assert not rep_adobe.is_quota_exhausted
    assert qm.is_quota_available("adobe") is True

    # For freepik: limit is 2, 1 inside window -> 1 available
    rep_freepik = qm.check_platform_quota("freepik", reference_time=now_utc)
    assert rep_freepik.uploads_last_7_days == 1
    assert rep_freepik.slots_available == 1


def test_quota_exhausted_and_countdown(tmp_path: Path):
    history_file = tmp_path / "upload_history.json"
    now_utc = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Limit = 2. 2 uploads inside 7 days.
    # Oldest was 6 days ago (at 12:00:00). It should expire in exactly 1 day.
    d_oldest = (now_utc - timedelta(days=6)).isoformat()
    d_newest = (now_utc - timedelta(days=1)).isoformat()

    history = {
        "img1.jpg": {"adobe": d_oldest},
        "img2.jpg": {"adobe": d_newest},
    }
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f)

    qm = QuotaManager(history_path=history_file, custom_limits={"adobe": 2})

    rep = qm.check_platform_quota("adobe", reference_time=now_utc)
    assert rep.is_quota_exhausted is True
    assert rep.slots_available == 0
    assert qm.is_quota_available("adobe") is False

    # Oldest was 6 days ago, so in 1 day (86400 seconds) a slot opens
    assert rep.seconds_until_next_slot is not None
    assert int(rep.seconds_until_next_slot) == 86400

    fmt = qm.format_countdown(rep.seconds_until_next_slot)
    assert "1d" in fmt


def test_zero_limit_is_exhausted(tmp_path: Path):
    history_file = tmp_path / "upload_history.json"
    history_file.write_text("{}", encoding="utf-8")

    qm = QuotaManager(history_path=history_file, custom_limits={"alamy": 0})
    rep = qm.check_platform_quota("alamy")
    assert rep.weekly_limit == 0
    assert rep.slots_available == 0
    assert rep.is_quota_exhausted is True
    assert qm.is_quota_available("alamy") is False
