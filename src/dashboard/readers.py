"""Data readers and state managers for the StockCont Dashboard.

All pipeline telemetry and assets are inspected safely, with synchronized
atomic writes for the distribution matrix and prompt queue managers.
"""

import csv
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

_history_lock = threading.Lock()

# ── Data Paths ───────────────────────────────────
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FINAL_DIR = BASE_DIR / "data" / "final"

TRENDS_FILE = RAW_DIR / "trends.json"
RAW_IMAGES_DIR = RAW_DIR / "images"
PROMPTS_FILE = PROCESSED_DIR / "prompts.json"
CSV_FILE = PROCESSED_DIR / "adobe_stock_upload.csv"
HISTORY_FILE = PROCESSED_DIR / "generation_history.json"
UPLOAD_HISTORY_FILE = PROCESSED_DIR / "upload_history.json"
GDRIVE_HISTORY_FILE = PROCESSED_DIR / "gdrive_backup_history.json"
FINAL_IMAGES_DIR = FINAL_DIR / "images"
REJECTED_DIR = FINAL_DIR / "rejected"


# ── Low-Level Helpers ────────────────────────────

def _read_json(path: Path) -> Any:
    """Safely read a JSON file, returning None on any failure."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Error reading %s: %s", path.name, e)
        return None


def _count_dir_files(directory: Path, extensions: Set[str] | None = None) -> int:
    """Count files in a directory, optionally filtered by extensions."""
    if not directory.exists():
        return 0
    if extensions:
        return sum(1 for f in directory.iterdir() if f.is_file() and f.suffix.lower() in extensions)
    return sum(1 for f in directory.iterdir() if f.is_file())


# ── Individual Data Readers ──────────────────────

def read_trends() -> List[Dict[str, Any]]:
    data = _read_json(TRENDS_FILE)
    return data if isinstance(data, list) else []


def read_prompts() -> List[Dict[str, Any]]:
    data = _read_json(PROMPTS_FILE)
    return data if isinstance(data, list) else []


def read_generation_history() -> Dict[str, Any]:
    data = _read_json(HISTORY_FILE)
    return data if isinstance(data, dict) else {}


def get_gdrive_dir() -> Optional[Path]:
    """Return configured and existing local Google Drive directory, if any."""
    path_str = os.getenv("GOOGLE_DRIVE_LOCAL_PATH", "").strip()
    if path_str:
        p = Path(path_str)
        if p.exists() and p.is_dir():
            return p
    return None


def read_upload_history_dict() -> Dict[str, Dict[str, str]]:
    """Read upload history in native mapping format {filename: {agency: timestamp}}."""
    data = _read_json(UPLOAD_HISTORY_FILE)
    if isinstance(data, dict):
        return data
    return {}


def read_upload_history() -> List[Dict[str, Any]]:
    data = _read_json(UPLOAD_HISTORY_FILE)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        result: List[Dict[str, Any]] = []
        for fn, v in data.items():
            if isinstance(v, dict):
                for agency, ts in v.items():
                    result.append({"filename": fn, "agency": agency, "timestamp": ts})
            elif isinstance(v, list):
                result.extend(v)
        return result
    return []


def read_gdrive_history() -> Dict[str, Any]:
    data = _read_json(GDRIVE_HISTORY_FILE)
    return data if isinstance(data, dict) else {}


_metadata_cache: Dict[str, Any] = {}


def get_image_embedded_metadata(file_path: Path) -> Optional[Dict[str, str]]:
    """Extract embedded IPTC metadata directly from an image file, with mtime caching."""
    if not file_path.exists() or file_path.suffix.lower() not in {".jpg", ".jpeg"}:
        return None

    try:
        mtime = file_path.stat().st_mtime
        cache_key = str(file_path.resolve())
        if cache_key in _metadata_cache:
            cached_mtime, cached_val = _metadata_cache[cache_key]
            if cached_mtime == mtime:
                return cached_val

        import logging
        logging.getLogger("iptcinfo").setLevel(logging.ERROR)
        from iptcinfo3 import IPTCInfo
        info = IPTCInfo(str(file_path))
        if info:
            title_raw = info.get("object name") or info.get("caption/abstract")
            title = title_raw.decode("utf-8", errors="replace") if isinstance(title_raw, bytes) else (str(title_raw) if title_raw else None)
            kws_raw = info.get("keywords") or []
            kws = [k.decode("utf-8", errors="replace") if isinstance(k, bytes) else str(k) for k in kws_raw]
            if title or kws:
                res = {
                    "Filename": file_path.name,
                    "Title": title or file_path.stem.replace("-", " ").title(),
                    "Keywords": ", ".join(kws),
                    "Category": "3",
                    "Releases": ""
                }
                _metadata_cache[cache_key] = (mtime, res)
                return res

        _metadata_cache[cache_key] = (mtime, None)
    except Exception as e:
        logger.debug("Could not read embedded IPTC from %s: %s", file_path.name, e)

    return None


def read_csv_catalog() -> List[Dict[str, str]]:
    target_csv = CSV_FILE
    if not target_csv.exists():
        gdrive = get_gdrive_dir()
        if gdrive and (gdrive / "adobe_stock_upload.csv").exists():
            target_csv = gdrive / "adobe_stock_upload.csv"

    if not target_csv.exists():
        return []
    try:
        with open(target_csv, "r", encoding="utf-8", errors="replace") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.warning("Error reading CSV: %s", e)
        return []


# ── Composite Readers ────────────────────────────

def list_final_images() -> List[Dict[str, Any]]:
    """List all images in data/final/images/ (or Google Drive fallback) with catalog status."""
    target_dir = FINAL_IMAGES_DIR
    exts = {".jpg", ".jpeg", ".png"}
    if not target_dir.exists() or _count_dir_files(target_dir, exts) == 0:
        gdrive = get_gdrive_dir()
        if gdrive and _count_dir_files(gdrive, exts) > 0:
            target_dir = gdrive

    if not target_dir or not target_dir.exists():
        return []

    catalog = read_csv_catalog()
    cataloged_map: Dict[str, Dict[str, str]] = {}
    for row in catalog:
        fn = row.get("Filename", "")
        if fn:
            cataloged_map[fn] = row

    upload_map = read_upload_history_dict()

    images: List[Dict[str, Any]] = []
    for f in sorted(target_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not f.is_file() or f.suffix.lower() not in exts:
            continue
        stat = f.stat()
        row = cataloged_map.get(f.name)
        if not row:
            row = get_image_embedded_metadata(f)

        file_history = upload_map.get(f.name, {})
        uploaded_agencies = list(file_history.keys()) if isinstance(file_history, dict) else []

        images.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "is_cataloged": row is not None,
            "is_uploaded": len(uploaded_agencies) > 0,
            "uploaded_agencies": uploaded_agencies,
            "platforms": file_history,
            "title": row.get("Title") if row else None,
            "keywords": row.get("Keywords") if row else None,
            "category": row.get("Category") if row else None,
        })
    return images


def get_prompt_queue_stats() -> Dict[str, Any]:
    """Get prompt queue counters using the existing PromptQueueManager."""
    try:
        from src.factory.prompt_queue import PromptQueueManager
        mgr = PromptQueueManager(auto_reconcile=False)
        return mgr.get_stats()
    except Exception as e:
        logger.warning("Error reading queue stats: %s", e)
        return {"total": 0, "generated": 0, "pending": 0, "progress_percent": 0.0}


def get_prompt_queue_items() -> List[Dict[str, Any]]:
    """Get all prompt items with current status."""
    try:
        from src.factory.prompt_queue import PromptQueueManager
        mgr = PromptQueueManager(auto_reconcile=False)
        return [
            {
                "prompt_text": p.prompt_text[:200] + ("…" if len(p.prompt_text) > 200 else ""),
                "prompt_hash": p.prompt_hash[:12],
                "full_hash": p.prompt_hash,
                "source_id": p.source_id,
                "prompt_id": p.prompt_id,
                "concept": p.concept,
                "status": p.status,
                "generated_at": p.generated_at,
                "image_file": p.image_file,
            }
            for p in mgr.get_all_prompts()
        ]
    except Exception as e:
        logger.warning("Error reading queue items: %s", e)
        return []


def get_agency_status() -> List[Dict[str, Any]]:
    """Check agency configuration from environment variables."""
    agencies_def = [
        {"name": "Adobe Stock", "key": "adobe", "env_prefix": "ADOBE_SFTP", "protocol": "SFTP", "portal_url": "https://contributor.stock.adobe.com/en/uploads"},
        {"name": "Freepik", "key": "freepik", "env_prefix": "FREEPIK_FTP", "protocol": "FTP", "portal_url": "https://contributor.freepik.com/upload"},
        {"name": "Dreamstime", "key": "dreamstime", "env_prefix": "DREAMSTIME_FTP", "protocol": "FTP", "portal_url": "https://www.dreamstime.com/uploadfile"},
        {"name": "Pond5", "key": "pond5", "env_prefix": "POND5_FTP", "protocol": "FTP", "portal_url": "https://www.pond5.com/my-uploads"},
        {"name": "Alamy", "key": "alamy", "env_prefix": "ALAMY_FTP", "protocol": "FTP", "portal_url": "https://www.alamy.com/contributor/"},
        {"name": "Vecteezy", "key": "vecteezy", "env_prefix": "VECTEEZY_FTP", "protocol": "FTP", "portal_url": "https://contributor.vecteezy.com/"},
        {"name": "123RF", "key": "123rf", "env_prefix": "ONETWOTHREERF_FTP", "protocol": "FTP", "portal_url": "https://contributor.123rf.com/"},
        {"name": "Ingram", "key": "ingram", "env_prefix": "INGRAM_FTP", "protocol": "FTP", "portal_url": "https://www.ingrampublishing.com/"},
    ]

    upload_history = read_upload_history()

    result: List[Dict[str, Any]] = []
    for adef in agencies_def:
        user_val = os.getenv(f"{adef['env_prefix']}_USER", "").strip()
        configured = bool(user_val)

        uploads = 0
        last_upload = None
        for entry in upload_history:
            if not isinstance(entry, dict):
                continue
            entry_agency = str(entry.get("agency", entry.get("platform", ""))).lower()
            if adef["key"] in entry_agency:
                uploads += 1
                ts = entry.get("uploaded_at") or entry.get("timestamp")
                if ts and (last_upload is None or str(ts) > str(last_upload)):
                    last_upload = ts

        result.append({
            "name": adef["name"],
            "key": adef["key"],
            "configured": configured,
            "uploads": uploads,
            "last_upload": last_upload,
            "protocol": adef["protocol"],
            "portal_url": adef.get("portal_url", ""),
        })
    return result


def get_backup_status() -> Dict[str, Any]:
    """Get Google Drive backup status."""
    try:
        from src.backup.gdrive_backup import GoogleDriveBackup
        gdrive = GoogleDriveBackup()
        history = read_gdrive_history()
        return {
            "configured": gdrive.is_configured,
            "mode": getattr(gdrive, "mode", "") if gdrive.is_configured else "",
            "synced_count": len(history) if isinstance(history, dict) else 0,
            "last_sync": None,
        }
    except Exception as e:
        logger.warning("Error reading backup status: %s", e)
        return {"configured": False, "mode": "", "synced_count": 0, "last_sync": None}


# ── Full Status Builder ──────────────────────────

def build_full_status() -> Dict[str, Any]:
    """Build the complete pipeline status for the dashboard."""
    trends = read_trends()
    prompts_data = read_prompts()
    queue_stats = get_prompt_queue_stats()
    catalog = read_csv_catalog()
    uploads = read_upload_history()

    total_gen_prompts = sum(len(item.get("generated_prompts", [])) for item in prompts_data)
    raw_img_count = _count_dir_files(RAW_IMAGES_DIR)
    final_img_count = _count_dir_files(FINAL_IMAGES_DIR, {".jpg", ".jpeg", ".png"})
    if final_img_count == 0:
        gdrive = get_gdrive_dir()
        if gdrive:
            final_img_count = _count_dir_files(gdrive, {".jpg", ".jpeg", ".png"})

    api_key = os.getenv("GEMINI_API_KEY", "")

    images = list_final_images()
    actual_cataloged = sum(1 for i in images if i["is_cataloged"])
    cataloged_count = actual_cataloged if images else len(catalog)

    kpis = {
        "trends": len(trends),
        "raw_images": raw_img_count,
        "prompts_analyzed": len(prompts_data),
        "prompts_total": total_gen_prompts,
        "queue_generated": queue_stats.get("generated", 0),
        "queue_total": queue_stats.get("total", 0),
        "queue_pending": queue_stats.get("pending", 0),
        "queue_percent": queue_stats.get("progress_percent", 0.0),
        "final_images": final_img_count,
        "cataloged": cataloged_count,
        "distributed": len(uploads),
        "gemini_configured": bool(api_key and len(api_key) > 5),
    }

    phases = [
        {
            "phase": 1, "name": "Scout", "icon": "🔍",
            "count": len(trends), "total": None,
            "status": "ok" if len(trends) > 0 else "idle",
            "detail": f"{len(trends)} trends | {raw_img_count} images",
        },
        {
            "phase": 2, "name": "Director", "icon": "🎨",
            "count": total_gen_prompts, "total": None,
            "status": "ok" if total_gen_prompts > 0 else "idle",
            "detail": f"{len(prompts_data)} analyzed | {total_gen_prompts} prompts",
        },
        {
            "phase": 3, "name": "Factory", "icon": "🏭",
            "count": queue_stats.get("generated", 0),
            "total": queue_stats.get("total", 0),
            "status": (
                "ok" if queue_stats.get("pending", 0) == 0 and queue_stats.get("total", 0) > 0
                else ("warning" if queue_stats.get("pending", 0) > 0 else "idle")
            ),
            "detail": f"{queue_stats.get('generated', 0)}/{queue_stats.get('total', 0)} ({queue_stats.get('progress_percent', 0)}%)",
        },
        {
            "phase": 4, "name": "Cataloger", "icon": "📋",
            "count": cataloged_count, "total": final_img_count,
            "status": (
                "ok" if cataloged_count >= final_img_count and final_img_count > 0
                else ("warning" if final_img_count > cataloged_count else "idle")
            ),
            "detail": f"{cataloged_count} catalogados | {max(0, final_img_count - cataloged_count)} pendentes",
        },
        {
            "phase": 5, "name": "Distributor", "icon": "🚀",
            "count": len(uploads), "total": None,
            "status": "ok" if len(uploads) > 0 else "idle",
            "detail": f"{len(uploads)} uploads logged",
        },
    ]

    return {
        "kpis": kpis,
        "phases": phases,
        "agencies": get_agency_status(),
        "backup": get_backup_status(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_seasonal_forecast() -> Dict[str, Any]:
    try:
        from src.analyzer.seasonal_radar import get_target_procurement_window
        return get_target_procurement_window()
    except Exception as e:
        logger.warning('Error calculating seasonal forecast: %s', e)
        return {'recommended_niches': []}


# ── Distribution Matrix ──────────────────────────

AGENCY_KEYS = [
    {"key": "dreamstime", "name": "Dreamstime", "protocol": "FTP", "env_prefix": "DREAMSTIME_FTP"},
    {"key": "123rf", "name": "123RF", "protocol": "FTP", "env_prefix": "ONETWOTHREERF_FTP"},
    {"key": "adobe", "name": "Adobe Stock", "protocol": "SFTP", "env_prefix": "ADOBE_SFTP"},
    {"key": "pond5", "name": "Pond5", "protocol": "FTP", "env_prefix": "POND5_FTP"},
    {"key": "freepik", "name": "Freepik", "protocol": "FTP", "env_prefix": "FREEPIK_FTP"},
    {"key": "vecteezy", "name": "Vecteezy", "protocol": "FTP", "env_prefix": "VECTEEZY_FTP"},
    {"key": "alamy", "name": "Alamy", "protocol": "FTP", "env_prefix": "ALAMY_FTP"},
    {"key": "ingram", "name": "Ingram", "protocol": "FTP", "env_prefix": "INGRAM_FTP"},
]


def get_distribution_matrix() -> Dict[str, Any]:
    """Generate distribution matrix data matching images against upload ledger."""
    gdrive_dir = get_gdrive_dir()
    target_dir = gdrive_dir if gdrive_dir and _count_dir_files(gdrive_dir, {".jpg", ".jpeg", ".png"}) > 0 else FINAL_IMAGES_DIR

    cataloged = read_csv_catalog()
    cataloged_map = {row.get("Filename", "").strip(): row for row in cataloged if row.get("Filename")}

    raw_history = _read_json(UPLOAD_HISTORY_FILE)
    history_dict: Dict[str, Dict[str, str]] = raw_history if isinstance(raw_history, dict) else {}

    agencies = []
    for ag in AGENCY_KEYS:
        user_val = os.getenv(f"{ag['env_prefix']}_USER", "").strip()
        agencies.append({
            "key": ag["key"],
            "name": ag["name"],
            "protocol": ag["protocol"],
            "configured": bool(user_val),
        })

    exts = {".jpg", ".jpeg", ".png"}
    items: List[Dict[str, Any]] = []

    if target_dir and target_dir.exists():
        for f in sorted(target_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not f.is_file() or f.suffix.lower() not in exts:
                continue

            row = cataloged_map.get(f.name)
            if not row:
                row = get_image_embedded_metadata(f)

            file_history = history_dict.get(f.name, {})

            platforms = {}
            for ag in agencies:
                k = ag["key"]
                is_uploaded = k in file_history
                platforms[k] = {
                    "uploaded": is_uploaded,
                    "timestamp": file_history.get(k) if is_uploaded else None,
                }

            uploaded_count = sum(1 for p in platforms.values() if p["uploaded"])
            pending_configured = sum(1 for ag in agencies if ag["configured"] and not platforms[ag["key"]]["uploaded"])

            items.append({
                "filename": f.name,
                "title": (row.get("Title") if row else None) or f.stem.replace("-", " ").title(),
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "is_cataloged": row is not None,
                "platforms": platforms,
                "uploaded_count": uploaded_count,
                "pending_configured": pending_configured,
            })

    summary = {
        "total_images": len(items),
        "source_dir": str(target_dir) if target_dir else "",
        "total_uploads": sum(item["uploaded_count"] for item in items),
        "total_slots": len(items) * len(agencies) if items else 0,
    }

    return {
        "summary": summary,
        "agencies": agencies,
        "items": items,
    }


def update_matrix_cell(filename: str, agency: str, uploaded: bool) -> bool:
    """Toggle or set uploaded status for a specific file and agency."""
    safe_fn = Path(filename).name
    with _history_lock:
        if UPLOAD_HISTORY_FILE.exists():
            history = _read_json(UPLOAD_HISTORY_FILE)
            if history is None or not isinstance(history, dict):
                logger.error("Failed to safely read %s; aborting write to prevent data loss.", UPLOAD_HISTORY_FILE.name)
                return False
        else:
            history = {}

        if uploaded:
            if safe_fn not in history:
                history[safe_fn] = {}
            history[safe_fn][agency] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            if safe_fn in history and agency in history[safe_fn]:
                del history[safe_fn][agency]
                if not history[safe_fn]:
                    del history[safe_fn]

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = UPLOAD_HISTORY_FILE.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            tmp_file.replace(UPLOAD_HISTORY_FILE)
            gdrive_p = get_gdrive_dir()
            if gdrive_p and gdrive_p.exists():
                try:
                    import shutil
                    shutil.copy2(UPLOAD_HISTORY_FILE, gdrive_p / UPLOAD_HISTORY_FILE.name)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error("Error updating upload history cell: %s", e)
            return False
        finally:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass


def batch_update_matrix_agency(agency: str, action: str, filenames: Optional[List[str]] = None) -> int:
    """Batch mark or unmark an agency for given filenames or all images."""
    with _history_lock:
        if UPLOAD_HISTORY_FILE.exists():
            history = _read_json(UPLOAD_HISTORY_FILE)
            if history is None or not isinstance(history, dict):
                logger.error("Failed to safely read %s; aborting batch write to prevent data loss.", UPLOAD_HISTORY_FILE.name)
                return 0
        else:
            history = {}

        if filenames is None:
            matrix = get_distribution_matrix()
            filenames = [item["filename"] for item in matrix["items"]]

        updated_count = 0
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for fn in filenames:
            safe_fn = Path(fn).name
            if action == "mark_all":
                if safe_fn not in history:
                    history[safe_fn] = {}
                if agency not in history[safe_fn]:
                    history[safe_fn][agency] = now_ts
                    updated_count += 1
            elif action == "unmark_all":
                if safe_fn in history and agency in history[safe_fn]:
                    del history[safe_fn][agency]
                    updated_count += 1
                    if not history[safe_fn]:
                        del history[safe_fn]

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = UPLOAD_HISTORY_FILE.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            tmp_file.replace(UPLOAD_HISTORY_FILE)
            gdrive_p = get_gdrive_dir()
            if gdrive_p and gdrive_p.exists():
                try:
                    import shutil
                    shutil.copy2(UPLOAD_HISTORY_FILE, gdrive_p / UPLOAD_HISTORY_FILE.name)
                except Exception:
                    pass
            return updated_count
        except Exception as e:
            logger.error("Error batch updating upload history: %s", e)
            return 0
        finally:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass


# ── Quality Control (QC) Data Readers ───────────────

STAGING_DIR = BASE_DIR / "data" / "staging"
STAGING_IMAGES_DIR = STAGING_DIR / "images"
QC_MANIFEST_FILE = PROCESSED_DIR / "qc_manifest.json"
QC_CONFIG_FILE = PROCESSED_DIR / "qc_config.json"


def get_qc_stats() -> Dict[str, Any]:
    """Retrieve aggregate stats for the Quality Control pipeline."""
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    return inspector.get_stats()


def list_staging_images(filter_status: str = "all") -> List[Dict[str, Any]]:
    """Return list of images in data/staging/images/ with their QC evaluation state."""
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    inspector.scan_staging()
    manifest = inspector.get_manifest()

    items = list(manifest.values())

    if filter_status == "pending":
        items = [i for i in items if i.get("status") == "pending"]
    elif filter_status == "approved":
        items = [i for i in items if i.get("status") == "approved"]
    elif filter_status == "rejected":
        items = [i for i in items if i.get("status") == "rejected"]
    elif filter_status == "upscaled":
        items = [i for i in items if i.get("upscaled", False)]

    # Sort newest first
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items
