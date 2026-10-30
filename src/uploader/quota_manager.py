#!/usr/bin/env python3
"""StockCont Multi-Platform Weekly Quota Manager (Rolling 7-Day Window)

Enforces weekly submission volume caps per stock photography platform:
  - Rolling 7-day window calculation: counts uploads where timestamp >= (now - 7 days)
  - Configurable weekly limit per platform via environment variables (.env)
  - Time-to-next-slot projection: calculates exact time when oldest upload in the
    current window expires and frees a new upload slot.
  - Safe, atomic reading of upload_history.json.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

# UTF-8 encoding safeguard on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

PROCESSED_DIR = BASE_DIR / "data" / "processed"
UPLOAD_HISTORY_FILE = PROCESSED_DIR / "upload_history.json"

logger = logging.getLogger("QuotaManager")

DEFAULT_WEEKLY_LIMITS: Dict[str, int] = {
    "adobe": 100,
    "freepik": 100,
    "dreamstime": 100,
    "pond5": 100,
    "123rf": 100,
    "vecteezy": 100,
    "ingram": 100,
    "alamy": 0,  # 0 because Alamy has strict Anti-AI ban policy (ADR-05)
}

DEFAULT_WEEKLY_VIDEO_LIMITS: Dict[str, int] = {
    "adobe": 50,
    "pond5": 80,
    "freepik": 30,
    "dreamstime": 50,
    "123rf": 50,
    "vecteezy": 40,
    "ingram": 40,
    "alamy": 0,  # Strict Anti-Ban (ADR-05)
}


@dataclass
class PlatformQuotaReport:
    platform: str
    weekly_limit: int
    uploads_last_7_days: int
    slots_available: int
    is_quota_exhausted: bool
    oldest_upload_in_window: Optional[datetime] = None
    next_slot_available_at: Optional[datetime] = None
    seconds_until_next_slot: Optional[float] = None


def parse_timestamp(ts_val: Any) -> Optional[datetime]:
    """Parse various timestamp representations into timezone-aware UTC datetime."""
    if not ts_val:
        return None

    iso_str = ""
    if isinstance(ts_val, str):
        iso_str = ts_val.strip()
    elif isinstance(ts_val, dict):
        iso_str = str(ts_val.get("uploaded_at", "")).strip()

    if not iso_str:
        return None

    try:
        # Handle trailing Z for Python <= 3.10
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


class QuotaManager:
    """Manages multi-agency submission rate limits under a rolling 7-day window."""

    def __init__(
        self,
        history_path: Optional[Path] = None,
        custom_limits: Optional[Dict[str, int]] = None
    ) -> None:
        self.history_path = history_path or UPLOAD_HISTORY_FILE
        self._custom_limits = custom_limits or {}

    def get_weekly_limit(self, platform: str, asset_type: str = "image") -> int:
        """Fetch configured weekly limit for a platform.

        Priority:
          1. Explicit constructor overrides (_custom_limits)
          2. Environment variable: {PLATFORM}_WEEKLY_LIMIT or {PLATFORM}_VIDEO_WEEKLY_LIMIT
          3. Built-in defaults (DEFAULT_WEEKLY_LIMITS / DEFAULT_WEEKLY_VIDEO_LIMITS)
        """
        norm_key = platform.lower().strip()
        if norm_key in self._custom_limits:
            return self._custom_limits[norm_key]

        prefix = f"{norm_key.upper()}_VIDEO_WEEKLY_LIMIT" if asset_type == "video" else f"{norm_key.upper()}_WEEKLY_LIMIT"
        env_val = os.getenv(prefix)
        if env_val is not None:
            try:
                return max(0, int(env_val.strip()))
            except ValueError:
                logger.warning(f"Invalid integer in {prefix}='{env_val}'. Using default.")

        if asset_type == "video":
            return DEFAULT_WEEKLY_VIDEO_LIMITS.get(norm_key, 50)
        return DEFAULT_WEEKLY_LIMITS.get(norm_key, 100)

    def load_upload_history(self) -> Dict[str, Any]:
        """Read upload history safely from disk."""
        if not self.history_path.exists():
            return {}
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to read {self.history_path}: {e}")
            return {}

    def get_recent_uploads(
        self,
        platform: str,
        window_days: int = 7,
        reference_time: Optional[datetime] = None
    ) -> List[Tuple[str, datetime]]:
        """Return list of (filename, upload_datetime) within the rolling window sorted ascending."""
        norm_key = platform.lower().strip()
        now_utc = reference_time or datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(days=window_days)

        history = self.load_upload_history()
        recent: List[Tuple[str, datetime]] = []

        for filename, agency_map in history.items():
            if not isinstance(agency_map, dict):
                continue
            if norm_key not in agency_map:
                continue

            ts_dt = parse_timestamp(agency_map[norm_key])
            if ts_dt and ts_dt >= cutoff:
                recent.append((filename, ts_dt))

        # Sort by timestamp ascending
        recent.sort(key=lambda x: x[1])
        return recent

    def check_platform_quota(
        self,
        platform: str,
        window_days: int = 7,
        reference_time: Optional[datetime] = None
    ) -> PlatformQuotaReport:
        """Compute quota report for a specific platform."""
        norm_key = platform.lower().strip()
        limit = self.get_weekly_limit(norm_key)
        now_utc = reference_time or datetime.now(timezone.utc)

        recent = self.get_recent_uploads(norm_key, window_days=window_days, reference_time=now_utc)
        count = len(recent)

        # 0 limit means completely disabled / blocked (e.g. Alamy anti-AI)
        if limit == 0:
            return PlatformQuotaReport(
                platform=norm_key,
                weekly_limit=0,
                uploads_last_7_days=count,
                slots_available=0,
                is_quota_exhausted=True,
                oldest_upload_in_window=None,
                next_slot_available_at=None,
                seconds_until_next_slot=None,
            )

        slots_avail = max(0, limit - count)
        is_exhausted = slots_avail == 0

        next_avail_at: Optional[datetime] = None
        secs_until_next: Optional[float] = None
        oldest_ts: Optional[datetime] = None

        if is_exhausted and recent:
            # The oldest upload in the current window will expire exactly window_days after it was uploaded
            oldest_ts = recent[0][1]
            next_avail_at = oldest_ts + timedelta(days=window_days)
            secs_until_next = max(0.0, (next_avail_at - now_utc).total_seconds())

        return PlatformQuotaReport(
            platform=norm_key,
            weekly_limit=limit,
            uploads_last_7_days=count,
            slots_available=slots_avail,
            is_quota_exhausted=is_exhausted,
            oldest_upload_in_window=oldest_ts,
            next_slot_available_at=next_avail_at,
            seconds_until_next_slot=secs_until_next,
        )

    def is_quota_available(self, platform: str, reference_time: Optional[datetime] = None) -> bool:
        """Check whether at least 1 upload slot is currently available."""
        report = self.check_platform_quota(platform, reference_time=reference_time)
        return report.slots_available > 0

    def get_available_slots(self, platform: str) -> int:
        """Get the number of available upload slots for the platform."""
        report = self.check_platform_quota(platform)
        return report.slots_available

    def get_all_reports(self, platforms: Optional[List[str]] = None) -> Dict[str, PlatformQuotaReport]:
        """Compute quota reports for all provided or default platforms."""
        target_platforms = platforms or list(DEFAULT_WEEKLY_LIMITS.keys())
        return {p: self.check_platform_quota(p) for p in target_platforms}

    def format_countdown(self, seconds: Optional[float]) -> str:
        """Format seconds into a human-readable countdown string (e.g. 1d 4h 32m)."""
        if seconds is None or seconds <= 0:
            return "Imediato (Vaga disponível)"
        total_seconds = int(seconds)
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)


def print_quotas_summary(quota_manager: Optional[QuotaManager] = None) -> None:
    """Print a terminal summary of all agency quotas and waiting slots."""
    qm = quota_manager or QuotaManager()
    reports = qm.get_all_reports()

    print("\n" + "=" * 68)
    print("      📊 STOCKCONT — RELATÓRIO DE COTAS SEMANAIS (ROLLING 7 DIAS)")
    print("=" * 68)

    for key, rep in reports.items():
        if rep.weekly_limit == 0:
            status_tag = "⛔ BLOQUEADO / SEM COTA"
            bar = "[────────────────────] 0%"
            info_str = "Uploads desabilitados ou política anti-IA"
        else:
            pct = min(100, int((rep.uploads_last_7_days / rep.weekly_limit) * 100))
            filled = int((pct / 100) * 20)
            empty = 20 - filled
            bar = f"[{'█' * filled}{'░' * empty}] {pct}%"
            if rep.is_quota_exhausted:
                countdown = qm.format_countdown(rep.seconds_until_next_slot)
                status_tag = f"⏸️ COTA ATINGIDA (Próxima vaga em {countdown})"
            else:
                status_tag = f"🟢 ATIVO ({rep.slots_available} vagas disponíveis)"
            info_str = f"{rep.uploads_last_7_days}/{rep.weekly_limit} nos últimos 7 dias"

        print(f"\n  • {key.upper():<10} {bar}")
        print(f"    Status: {status_tag}")
        print(f"    Envios: {info_str}")

    print("\n" + "=" * 68 + "\n")
