#!/usr/bin/env python3
"""Retroactively updates metadata across all backup assets for 100% microstock compliance.

Ensures:
1. IPTC Caption & EXIF ImageDescription contain 'Generative AI illustration. ...' (Dreamstime & Freepik requirement).
2. IPTC ObjectName & EXIF XPTitle contain the Title (capped at 64 octets without word truncation).
3. Keywords contain mandatory AI tags ('ai generated', 'generative ai', 'digital art', 'illustration') and are strictly capped at 50.
4. Windows EXIF XP Tags are null-terminated UTF-16LE byte strings.
5. Slices and synchronizes both CSVs (local and Google Drive backup).
6. Resets 'dreamstime' entries in upload_history.json so assets can be re-uploaded immediately.
"""

import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

# UTF-8 stdout on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env", override=True)

from src.cataloger.adobe_csv_maker import (
    format_description,
    normalize_keywords,
    embed_metadata,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ComplianceMigrator")

CSV_FILE = BASE_DIR / "data" / "processed" / "adobe_stock_upload.csv"
UPLOAD_HISTORY_FILE = BASE_DIR / "data" / "processed" / "upload_history.json"


def run_compliance_migration(reset_dreamstime_history: bool = True) -> int:
    """Updates metadata on all backup images and CSVs for microstock compliance."""
    backup_path_str = os.getenv("GOOGLE_DRIVE_LOCAL_PATH", "").strip()
    if not backup_path_str:
        logger.error("GOOGLE_DRIVE_LOCAL_PATH not set in .env")
        return 0

    backup_dir = Path(backup_path_str)
    if not backup_dir.exists():
        logger.error(f"Backup directory not found: {backup_dir}")
        return 0

    if not CSV_FILE.exists():
        logger.error(f"CSV file not found: {CSV_FILE}")
        return 0

    # 1. Load CSV data
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or ["Filename", "Title", "Keywords", "Category", "Releases"]
        csv_rows = list(reader)

    csv_by_filename: Dict[str, Dict[str, str]] = {r["Filename"]: r for r in csv_rows if "Filename" in r}

    # 2. Find all JPG images in backup folder
    image_files = sorted(list(backup_dir.glob("*.jpg")) + list(backup_dir.glob("*.jpeg")))
    if not image_files:
        logger.warning(f"No JPG images found in {backup_dir}")
        return 0

    logger.info(f"Found {len(image_files)} image files in {backup_dir} to bring into compliance.")

    success_count = 0
    updated_filenames = set()

    for idx, img_path in enumerate(image_files, 1):
        filename = img_path.name
        row = csv_by_filename.get(filename)
        if not row:
            logger.warning(f"[{idx}/{len(image_files)}] No CSV entry found for {filename}, skipping.")
            continue

        title = row.get("Title", "").strip()
        raw_kws = [k.strip() for k in row.get("Keywords", "").split(",") if k.strip()]

        clean_kws, keywords_str = normalize_keywords(raw_kws, max_keywords=50)
        description = format_description(title)

        try:
            # Re-embed compliant metadata directly into the image in the backup directory
            embed_metadata(img_path, img_path, title, clean_kws, description=description)

            # Update row in memory
            row["Keywords"] = keywords_str
            updated_filenames.add(filename)
            success_count += 1
            logger.info(f"[{idx}/{len(image_files)}] OK: {filename}")
        except Exception as e:
            logger.error(f"[{idx}/{len(image_files)}] Error updating {filename}: {e}")

    # 3. Save updated CSV locally and in backup folder
    if updated_filenames:
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        logger.info(f"Updated local CSV at {CSV_FILE}")

        backup_csv = backup_dir / "adobe_stock_upload.csv"
        try:
            with open(backup_csv, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
            logger.info(f"Updated backup CSV at {backup_csv}")
        except Exception as e:
            logger.warning(f"Could not write backup CSV to {backup_csv}: {e}")

    # 4. Reset Dreamstime upload history if requested
    if reset_dreamstime_history and UPLOAD_HISTORY_FILE.exists():
        try:
            with open(UPLOAD_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

            reset_count = 0
            for fname in updated_filenames:
                if fname in history and "dreamstime" in history[fname]:
                    del history[fname]["dreamstime"]
                    reset_count += 1

            with open(UPLOAD_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            logger.info(f"Reset 'dreamstime' history for {reset_count} files in {UPLOAD_HISTORY_FILE.name}")
        except Exception as e:
            logger.error(f"Error resetting upload history: {e}")

    logger.info(f"=== COMPLIANCE MIGRATION COMPLETE: {success_count}/{len(image_files)} assets updated ===")
    return success_count


if __name__ == "__main__":
    run_compliance_migration()
