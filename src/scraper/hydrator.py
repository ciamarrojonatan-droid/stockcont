"""Raw Reference Hydrator for StockCont.

Synchronizes and downloads missing raw reference images listed in data/raw/trends.json
concurrently at high speed, resilient to ephemeral Windows Sandbox restarts.
"""

import concurrent.futures
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

# Paths & Defaults
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_TRENDS_FILE = BASE_DIR / "data" / "raw" / "trends.json"
DEFAULT_IMAGES_DIR = BASE_DIR / "data" / "raw" / "images"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("Hydrator")


def _resolve_item_target_file(item: Dict[str, Any], target_dir: Path) -> Path:
    """Determine the destination file path for a reference item."""
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(item.get("id") or "")).strip()
    if not safe_id:
        safe_id = f"unknown_{int(time.time())}"

    url = item.get("original_url") or item.get("thumbnail_url") or ""
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower() if parsed.path else ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"

    return target_dir / f"{safe_id}{ext}"


def _download_single_item(
    client: httpx.Client,
    item: Dict[str, Any],
    target_dir: Path,
    retries: int = 2
) -> bool:
    """Download a single reference image with retries and atomic write."""
    item_id = str(item.get("id") or "").strip()
    url = item.get("original_url") or item.get("thumbnail_url")

    if not url:
        logger.warning(f"Item {item_id} has no valid URL in trends.json")
        return False

    dest_file = _resolve_item_target_file(item, target_dir)
    tmp_file = target_dir / f".tmp_{dest_file.name}.{os.getpid()}"

    for attempt in range(1, retries + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()

            if not resp.content:
                logger.warning(f"Empty response for item {item_id} (Attempt {attempt}/{retries})")
                continue

            with open(tmp_file, "wb") as f:
                f.write(resp.content)

            tmp_file.replace(dest_file)
            return True

        except (httpx.HTTPError, httpx.TimeoutException) as net_err:
            if attempt == retries:
                logger.warning(f"Network error downloading reference {item_id} from {url}: {net_err}")
            else:
                time.sleep(0.5 * attempt)
        except OSError as fs_err:
            logger.error(f"Filesystem error saving reference {item_id}: {fs_err}")
            break
        except Exception as unexpected:
            logger.error(f"Unexpected error for {item_id}: {unexpected}")
            break
        finally:
            if tmp_file.is_file():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    return False


def hydrate_raw_references(
    trends_file: Optional[Path] = None,
    target_dir: Optional[Path] = None,
    max_workers: int = 8,
    force: bool = False
) -> Dict[str, int]:
    """
    Scans trends.json and downloads missing reference images concurrently.

    Args:
        trends_file: Path to trends.json (defaults to data/raw/trends.json)
        target_dir: Path to directory for images (defaults to data/raw/images)
        max_workers: Number of concurrent threads for downloading
        force: If True, re-downloads even if the file already exists

    Returns:
        Dictionary with hydration statistics: total, needed, downloaded, already_present, failed.
    """
    trends_path = Path(trends_file or DEFAULT_TRENDS_FILE)
    images_dir = Path(target_dir or DEFAULT_IMAGES_DIR)

    stats = {
        "total": 0,
        "needed": 0,
        "downloaded": 0,
        "already_present": 0,
        "failed": 0
    }

    if not trends_path.is_file():
        logger.warning(f"Trends file {trends_path} not found. Nothing to hydrate.")
        return stats

    try:
        with open(trends_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            logger.error(f"Invalid format in {trends_path}: expected JSON list.")
            return stats
    except Exception as e:
        logger.error(f"Failed to read trends file {trends_path}: {e}")
        return stats

    stats["total"] = len(items)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Classify items: needed vs already present
    items_to_download: List[Dict[str, Any]] = []

    for item in items:
        dest_file = _resolve_item_target_file(item, images_dir)
        # Check standard destinations and extensions
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(item.get("id") or "")).strip()
        existing_match = None
        if not force:
            if dest_file.is_file() and dest_file.stat().st_size > 0:
                existing_match = dest_file
            elif safe_id:
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    candidate = images_dir / f"{safe_id}{ext}"
                    if candidate.is_file() and candidate.stat().st_size > 0:
                        existing_match = candidate
                        break

        if existing_match:
            stats["already_present"] += 1
        else:
            url = item.get("original_url") or item.get("thumbnail_url")
            if url:
                items_to_download.append(item)
            else:
                stats["failed"] += 1

    stats["needed"] = len(items_to_download)

    if not items_to_download:
        logger.info(
            f"⚡ Hydration check complete: All {stats['already_present']} reference images are present. "
            f"No downloads required."
        )
        return stats

    logger.info(
        f"🚀 Starting concurrent hydration: {len(items_to_download)} missing images to download "
        f"({stats['already_present']} already present, {max_workers} parallel workers)..."
    )

    start_time = time.time()
    successful = 0
    failed = 0

    with httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": "StockCont/3.0"}) as client:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(_download_single_item, client, item, images_dir): item
                for item in items_to_download
            }

            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    if future.result():
                        successful += 1
                    else:
                        failed += 1
                except Exception as err:
                    logger.warning(f"Worker exception for item {item.get('id')}: {err}")
                    failed += 1

    elapsed = time.time() - start_time
    stats["downloaded"] = successful
    stats["failed"] += failed

    logger.info(
        f"✅ Hydration completed in {elapsed:.2f}s: "
        f"{successful} downloaded, {stats['already_present']} pre-existing, {stats['failed']} failed."
    )

    return stats


if __name__ == "__main__":
    hydrate_raw_references()
