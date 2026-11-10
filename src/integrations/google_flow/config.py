"""Configuration and constants for Google Flow Industrial API Engine.

Manages filesystem paths, model registries, timeout settings, and persistent
session directory mappings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

# Windows console UTF-8 reconfig (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Root Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
FINAL_DIR = DATA_DIR / "final"

# Target asset directories
FINAL_VIDEOS_DIR = FINAL_DIR / "videos"
FINAL_IMAGES_DIR = FINAL_DIR / "images"
STAGING_DIR = DATA_DIR / "staging"

# Google Flow Session & Ledgers
GOOGLE_FLOW_SESSION_DIR = BASE_DIR / "google_flow_session"
GOOGLE_FLOW_HISTORY_FILE = PROCESSED_DIR / "google_flow_history.json"
GOOGLE_VEO_QUEUE_FILE = PROCESSED_DIR / "google_veo_queue.json"

# URLs
GOOGLE_FLOW_WEB_URL = os.getenv("GOOGLE_FLOW_WEB_URL", "https://labs.google/fx/tools/flow")
GOOGLE_FLOW_RPC_BASE_URL = os.getenv(
    "GOOGLE_FLOW_RPC_BASE_URL",
    "https://alkalimakersuite-pa.clients6.google.com/v1alpha"
)

# Network & Execution Defaults
DEFAULT_API_HOST = os.getenv("GOOGLE_FLOW_HOST", "127.0.0.1")
DEFAULT_API_PORT = int(os.getenv("GOOGLE_FLOW_PORT", "8000"))
POLL_INTERVAL_SECONDS = float(os.getenv("GOOGLE_FLOW_POLL_INTERVAL", "4.0"))
JOB_TIMEOUT_SECONDS = float(os.getenv("GOOGLE_FLOW_JOB_TIMEOUT", "360.0"))
HEARTBEAT_INTERVAL_MINUTES = int(os.getenv("GOOGLE_FLOW_HEARTBEAT_MINUTES", "45"))

# Model Registries & Constraints
SUPPORTED_VIDEO_MODELS: List[str] = ["veo-2.0", "veo-3.0", "veo-fast"]
SUPPORTED_IMAGE_MODELS: List[str] = ["imagen-3.0", "imagen-3.0-generate-002"]
SUPPORTED_MODES: List[str] = ["t2v", "i2v", "frames2v", "t2i"]
SUPPORTED_ASPECT_RATIOS: List[str] = ["16:9", "9:16", "1:1", "4:3", "2.39:1"]
SUPPORTED_DURATIONS: List[int] = [5, 8]
SUPPORTED_VARIATIONS: List[int] = [1, 2, 4]
SUPPORTED_SELECTION_STRATEGIES: List[str] = ["best_by_ai", "upscale_all", "first"]

# Create prerequisite directories
for d in [PROCESSED_DIR, FINAL_VIDEOS_DIR, FINAL_IMAGES_DIR, GOOGLE_FLOW_SESSION_DIR]:
    d.mkdir(parents=True, exist_ok=True)
