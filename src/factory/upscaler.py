"""StockCont Image Upscaler & Resolution Enhancer.

Upscales approved raw/staging images to commercial stock-grade 8K resolution
using high-fidelity Lanczos resampling and optical unsharp masking.
Updates generation_history.json and qc_manifest.json atomically.
Follows ADR-01 (UTF-8 encoding) and ADR-02 (Atomic write with .tmp).
"""

import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageFilter
from dotenv import load_dotenv

# Reconfigure stdout/stderr on Windows for UTF-8 safety
if sys.platform.startswith("win"):
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

STAGING_DIR = BASE_DIR / "data" / "staging" / "images"
FINAL_DIR = BASE_DIR / "data" / "final" / "images"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

HISTORY_FILE = PROCESSED_DIR / "generation_history.json"
QC_MANIFEST_FILE = PROCESSED_DIR / "qc_manifest.json"

logger = logging.getLogger("Upscaler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Atomic write complying with ADR-02."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise e


class Upscaler:
    """Manages high-fidelity 8K upscaling for QC-approved images."""

    def __init__(
        self,
        staging_dir: Optional[Path] = None,
        final_dir: Optional[Path] = None,
        target_min_dim: int = 7680,
    ):
        self.staging_dir = staging_dir or STAGING_DIR
        self.final_dir = final_dir or FINAL_DIR
        self.target_min_dim = target_min_dim
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir.mkdir(parents=True, exist_ok=True)

    def upscale_image(
        self,
        staging_filename: str,
        target_long_edge: Optional[int] = None,
    ) -> Optional[Path]:
        """Upscale a single staging image to 8K and save into data/final/images/."""
        long_edge_target = target_long_edge or self.target_min_dim
        src_path = self.staging_dir / staging_filename

        if not src_path.exists():
            logger.error("Staging image not found for upscale: %s", src_path)
            return None

        dest_name = f"upscaled_{Path(staging_filename).stem}.jpg"
        dest_path = self.final_dir / dest_name

        try:
            with Image.open(src_path) as img:
                orig_w, orig_h = img.size
                current_long_edge = max(orig_w, orig_h)

                if img.mode != "RGB":
                    img = img.convert("RGB")

                if current_long_edge < long_edge_target:
                    scale = long_edge_target / float(current_long_edge)
                    new_w = int(round(orig_w * scale))
                    new_h = int(round(orig_h * scale))

                    logger.info("Upscaling %s from (%dx%d) to 8K (%dx%d)...", staging_filename, orig_w, orig_h, new_w, new_h)
                    resampled = img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
                    # Subtle optical detail enhancement
                    enhanced = resampled.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
                else:
                    logger.info("Image %s already meets long edge (%dx%d >= %d). Optimizing...", staging_filename, orig_w, orig_h, long_edge_target)
                    enhanced = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=40, threshold=2))

                # Save with 300 DPI and JPEG Quality 98
                enhanced.save(
                    str(dest_path),
                    format="JPEG",
                    quality=98,
                    subsampling=0,
                    dpi=(300, 300),
                )

            logger.info("✅ 8K Upscale saved: %s", dest_path.name)
            self._update_ledgers(staging_filename, dest_name, dest_path)
            return dest_path

        except Exception as e:
            logger.error("Failed to upscale %s: %s", staging_filename, e)
            return None

    def _update_ledgers(self, staging_filename: str, dest_name: str, dest_path: Path) -> None:
        """Update qc_manifest.json and generation_history.json."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Update QC Manifest
        if QC_MANIFEST_FILE.exists():
            try:
                with open(QC_MANIFEST_FILE, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                if staging_filename in manifest:
                    manifest[staging_filename]["upscaled"] = True
                    manifest[staging_filename]["final_image"] = dest_name
                    manifest[staging_filename]["upscaled_at"] = now_iso
                    _atomic_write_json(QC_MANIFEST_FILE, manifest)
            except Exception as e:
                logger.warning("Error updating QC manifest after upscale: %s", e)

        # 2. Update Generation History
        try:
            history: Dict[str, Any] = {}
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        history = data

            # Compute image content hash or dummy key
            with open(dest_path, "rb") as f:
                img_hash = hashlib.sha256(f.read()).hexdigest()[:16]

            history[img_hash] = {
                "generated_at": now_iso,
                "image_file": dest_name,
                "resolution": "8K",
                "source_staging": staging_filename,
                "qc_status": "approved",
            }
            _atomic_write_json(HISTORY_FILE, history)
        except Exception as e:
            logger.warning("Error updating generation history after upscale: %s", e)

    def upscale_all_approved(self) -> List[Path]:
        """Find all approved, non-upscaled images in QC manifest and upscale them."""
        if not QC_MANIFEST_FILE.exists():
            logger.info("No QC manifest found. Nothing to upscale.")
            return []

        try:
            with open(QC_MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            logger.error("Could not read QC manifest: %s", e)
            return []

        approved_pending = [
            fname for fname, item in manifest.items()
            if item.get("status") == "approved" and not item.get("upscaled", False)
        ]

        logger.info("Found %d approved image(s) awaiting 8K upscale.", len(approved_pending))
        upscaled_paths: List[Path] = []

        for fname in approved_pending:
            out_path = self.upscale_image(fname)
            if out_path:
                upscaled_paths.append(out_path)

        return upscaled_paths
