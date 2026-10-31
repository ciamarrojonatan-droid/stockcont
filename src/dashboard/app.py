from typing import Optional
"""FastAPI Dashboard Application for StockCont.

Serves the dark-theme SPA and provides read-only REST API
endpoints for pipeline status, asset gallery, and phase execution.
"""

import logging
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import readers, runner, schemas

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
IMAGES_DIR = readers.FINAL_IMAGES_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clean up any orphan background processes
    runner.cleanup_orphan_processes()

    # Startup: Auto-pull all assets and upload history from Google Drive backup in background
    def _bg_restore():
        try:
            from src.backup.gdrive_backup import GoogleDriveBackup
            gdrive = GoogleDriveBackup()
            if gdrive.is_configured:
                logger.info("☁️ Google Drive configurado. Sincronizando backup em background...")
                gdrive.restore_assets()
        except Exception as e:
            logger.warning("Falha ao restaurar assets do Google Drive no startup: %s", e)

    import threading
    threading.Thread(target=_bg_restore, daemon=True, name="GDriveStartupRestore").start()

    yield
    # Shutdown: Clean up any child tasks running under this server instance
    for task_key in list(runner._running_tasks.keys()):
        runner.terminate_task(task_key)


app = FastAPI(
    title="StockCont Dashboard",
    description="Dashboard for the StockCont Autonomous Microstock Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── SPA Entry Point ──────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the single-page application."""
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/video", response_class=HTMLResponse)
async def video_dashboard():
    """Serve the dedicated Video Command Center SPA."""
    video_file = STATIC_DIR / "video.html"
    if not video_file.exists():
        video_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=video_file.read_text(encoding="utf-8"))


# ── Pipeline Status ──────────────────────────────────

@app.get("/api/status")
async def get_status():
    """Full pipeline status with KPIs, phases, agencies, and backup."""
    return readers.build_full_status()


# ── Prompt Queue ─────────────────────────────────────

@app.get("/api/prompts")
async def get_prompts(filter: str = "all", page: int = 1, per_page: int = 50):
    """Paginated list of prompts with status filter."""
    items = readers.get_prompt_queue_items()
    if filter == "pending":
        items = [i for i in items if i["status"] == "pending"]
    elif filter == "generated":
        items = [i for i in items if i["status"] == "generated"]

    total = len(items)
    start = (page - 1) * per_page
    return {
        "items": items[start:start + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@app.get("/api/prompts/stats")
async def get_prompts_stats():
    """Quick counters: total, pending, generated, percent."""
    return readers.get_prompt_queue_stats()


@app.post("/api/prompts/mark-generated")
async def mark_prompts_generated(req: schemas.MarkGeneratedRequest):
    """Mark specific prompts (by hash) or all pending prompts as generated."""
    from src.factory.prompt_queue import PromptQueueManager
    mgr = PromptQueueManager(auto_reconcile=False)

    if req.all_pending:
        count = mgr.mark_all_pending_generated()
        return {
            "success": True,
            "marked_count": count,
            "message": f"{count} prompts pendentes marcados como gerados.",
        }
    elif req.hashes:
        count = mgr.mark_by_hashes(req.hashes)
        return {
            "success": True,
            "marked_count": count,
            "message": f"{count} prompt(s) marcado(s) como gerado(s).",
        }
    else:
        return {
            "success": False,
            "marked_count": 0,
            "message": "Nenhum prompt foi selecionado.",
        }


@app.post("/api/prompts/mark-pending")
async def mark_prompts_pending(req: schemas.MarkPendingRequest):
    """Mark specific prompts (by hash) or all generated prompts as pending."""
    from src.factory.prompt_queue import PromptQueueManager
    mgr = PromptQueueManager(auto_reconcile=False)

    if req.all_generated:
        count = mgr.mark_all_generated_pending()
        return {
            "success": True,
            "marked_count": count,
            "message": f"{count} prompts gerados foram revertidos para pendentes.",
        }
    elif req.hashes:
        count = mgr.mark_pending_by_hashes(req.hashes)
        return {
            "success": True,
            "marked_count": count,
            "message": f"{count} prompt(s) revertido(s) para pendente(s).",
        }
    else:
        return {
            "success": False,
            "marked_count": 0,
            "message": "Nenhum prompt foi selecionado.",
        }


# ── Image Gallery ────────────────────────────────────

@app.get("/api/images")
async def get_images(
    filter: str = "all",
    tier: Optional[str] = None,
    niche: Optional[str] = None,
    copyspace: Optional[bool] = None,
    sort: str = "sales_score",
    q: Optional[str] = None,
):
    """List images with multi-factor sales potential filtering, sorting, and search."""
    all_images = readers.list_final_images()
    images = all_images

    # 1. Status Filter (cataloged / uncataloged / uploaded / pending_upload)
    if filter == "cataloged":
        images = [i for i in images if i.get("is_cataloged")]
    elif filter == "uncataloged":
        images = [i for i in images if not i.get("is_cataloged")]
    elif filter == "uploaded":
        images = [i for i in images if i.get("is_uploaded")]
    elif filter == "pending_upload":
        images = [i for i in images if i.get("is_cataloged") and not i.get("is_uploaded")]

    # 2. Sales Tier Filter
    if tier and tier != "all":
        t = tier.lower()
        if t == "top_sellers":
            images = [i for i in images if i.get("sales_score", 0.0) >= 80.0]
        elif t in {"tier_s", "s"}:
            images = [i for i in images if i.get("sales_tier_key") == "tier_s"]
        elif t in {"tier_a", "a"}:
            images = [i for i in images if i.get("sales_tier_key") == "tier_a"]
        elif t in {"tier_b", "b"}:
            images = [i for i in images if i.get("sales_tier_key") == "tier_b"]
        elif t in {"tier_c", "c"}:
            images = [i for i in images if i.get("sales_tier_key") == "tier_c"]

    # 3. Commercial Niche Filter
    if niche and niche != "all":
        n = niche.lower()
        images = [
            i for i in images
            if i.get("niche_key") == n or n in str(i.get("niche", "")).lower()
        ]

    # 4. Copy-Space Filter
    if copyspace is not None:
        images = [i for i in images if bool(i.get("has_copyspace")) == copyspace]

    # 5. Free Text Search (q)
    if q and q.strip():
        query_words = q.strip().lower().split()
        def matches_query(img):
            corpus = f"{img.get('filename', '')} {img.get('title', '')} {img.get('keywords', '')} {img.get('niche', '')} {img.get('buyer_intent', '')}".lower()
            return all(w in corpus for w in query_words)
        images = [i for i in images if matches_query(i)]

    # 6. Sorting
    if sort == "sales_score":
        images.sort(key=lambda i: (i.get("sales_score", 0.0), i.get("created_at", "")), reverse=True)
    elif sort == "date_desc":
        images.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    elif sort == "name_asc":
        images.sort(key=lambda i: str(i.get("filename", "")).lower())
    elif sort == "size_desc":
        images.sort(key=lambda i: i.get("size_bytes", 0), reverse=True)

    cataloged_count = sum(1 for i in all_images if i.get("is_cataloged"))
    uploaded_count = sum(1 for i in all_images if i.get("is_uploaded"))

    return {
        "images": images,
        "total": len(images),
        "total_unfiltered": len(all_images),
        "cataloged": cataloged_count,
        "uncataloged": len(all_images) - cataloged_count,
        "uploaded": uploaded_count,
        "pending_upload": cataloged_count - uploaded_count,
    }


@app.get("/api/images/analytics")
async def get_images_analytics():
    """Returns consolidated commercial sales potential breakdown across final images."""
    return readers.get_images_sales_analytics()


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _resolve_image_path(filename: str) -> Path:
    """Safely locate image file in IMAGES_DIR or Google Drive directory."""
    safe_name = Path(filename).name
    if safe_name != filename or not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if Path(safe_name).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido")

    candidate = IMAGES_DIR / safe_name
    if candidate.exists() and candidate.is_file():
        try:
            candidate.resolve().relative_to(IMAGES_DIR.resolve())
            return candidate
        except ValueError:
            pass

    gdrive_dir = readers.get_gdrive_dir()
    if gdrive_dir:
        candidate_gd = gdrive_dir / safe_name
        if candidate_gd.exists() and candidate_gd.is_file():
            try:
                candidate_gd.resolve().relative_to(gdrive_dir.resolve())
                return candidate_gd
            except ValueError:
                pass

    raise HTTPException(status_code=404, detail="Image not found")


@app.get("/api/images/{filename}")
async def get_image_file(filename: str):
    """Serve an original image file."""
    file_path = _resolve_image_path(filename)
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    return FileResponse(str(file_path), media_type=media.get(file_path.suffix.lower(), "application/octet-stream"))


@app.get("/api/images/{filename}/thumb")
async def get_image_thumbnail(filename: str):
    """Serve a resized thumbnail (max 400px) for gallery performance."""
    file_path = _resolve_image_path(filename)

    try:
        import io
        from PIL import Image

        img = Image.open(file_path)
        img.thumbnail((400, 400), Image.LANCZOS)
        buf = io.BytesIO()
        fmt = "PNG" if file_path.suffix.lower() == ".png" else "JPEG"
        img.save(buf, format=fmt, quality=85)
        buf.seek(0)
        media = "image/png" if fmt == "PNG" else "image/jpeg"
        return StreamingResponse(buf, media_type=media)
    except Exception:
        return FileResponse(str(file_path))


@app.get("/api/images/{filename}/meta")
async def get_image_metadata(filename: str):
    """Read IPTC/EXIF metadata embedded in a cataloged JPG."""
    file_path = _resolve_image_path(filename)

    meta: dict = {"filename": filename, "iptc": {}, "exif": {}}

    # IPTC
    try:
        from iptcinfo3 import IPTCInfo
        info = IPTCInfo(str(file_path))
        if info:
            title = info["object name"]
            if title:
                meta["iptc"]["title"] = title.decode("utf-8", errors="replace") if isinstance(title, bytes) else str(title)
            caption = info["caption/abstract"]
            if caption:
                meta["iptc"]["caption"] = caption.decode("utf-8", errors="replace") if isinstance(caption, bytes) else str(caption)
            keywords = info["keywords"]
            if keywords:
                meta["iptc"]["keywords"] = [
                    k.decode("utf-8", errors="replace") if isinstance(k, bytes) else str(k)
                    for k in keywords
                ]
    except Exception as e:
        meta["iptc"]["error"] = str(e)

    # EXIF
    try:
        import piexif
        exif_dict = piexif.load(str(file_path))
        if exif_dict:
            zeroth = exif_dict.get("0th", {})
            desc = zeroth.get(piexif.ImageIFD.ImageDescription)
            if desc:
                meta["exif"]["description"] = desc.decode("utf-8", errors="replace") if isinstance(desc, bytes) else str(desc)
            xp_title = zeroth.get(0x9C9B)
            if xp_title:
                meta["exif"]["xp_title"] = xp_title.decode("utf-16le", errors="replace").rstrip("\x00") if isinstance(xp_title, bytes) else str(xp_title)
            xp_kw = zeroth.get(0x9C9E)
            if xp_kw:
                meta["exif"]["xp_keywords"] = xp_kw.decode("utf-16le", errors="replace").rstrip("\x00") if isinstance(xp_kw, bytes) else str(xp_kw)
    except Exception as e:
        meta["exif"]["error"] = str(e)

    upload_dict = readers.read_upload_history_dict()
    file_hist = upload_dict.get(filename, {})
    meta["uploaded_agencies"] = list(file_hist.keys()) if isinstance(file_hist, dict) else []
    meta["platforms"] = file_hist

    try:
        from src.analyzer.commercial_scorer import evaluate_sales_potential
        cand_dict = {
            "filename": filename,
            "title": meta.get("iptc", {}).get("title") or meta.get("exif", {}).get("xp_title"),
            "keywords": meta.get("iptc", {}).get("keywords", []),
        }
        meta["commercial"] = evaluate_sales_potential(cand_dict)
    except Exception as e:
        logger.warning("Error evaluating commercial metadata for %s: %s", filename, e)

    return meta


# ── Agencies ─────────────────────────────────────────

@app.get("/api/agencies")
async def get_agencies():
    """Configuration and upload stats per agency."""
    return readers.get_agency_status()


@app.get("/api/uploads")
async def get_uploads():
    """Raw upload history entries."""
    return readers.read_upload_history()


# ── Distribution Matrix ──────────────────────────────

@app.get("/api/matrix")
async def get_distribution_matrix():
    """Return distribution matrix matching images with stock agencies."""
    return readers.get_distribution_matrix()


@app.post("/api/matrix/toggle")
async def toggle_matrix_cell(req: schemas.MatrixToggleRequest):
    """Toggle or update an agency upload status for a single image."""
    success = readers.update_matrix_cell(req.filename, req.agency, req.uploaded)
    return {"success": success, "filename": req.filename, "agency": req.agency, "uploaded": req.uploaded}


@app.post("/api/matrix/batch-set")
async def batch_matrix_set(req: schemas.MatrixBatchRequest):
    """Batch mark or unmark an agency for images."""
    count = readers.batch_update_matrix_agency(req.agency, req.action, req.filenames)
    return {"success": True, "agency": req.agency, "action": req.action, "updated_count": count}


@app.post("/api/matrix/upload-pending")
async def trigger_matrix_upload(platform: str = "all"):
    """Trigger Phase 5 distribution upload for pending files."""
    args = ["--platform", platform]
    return await runner.run_phase(5, extra_args=args)


# ── Backup ───────────────────────────────────────────

@app.get("/api/backup")
async def get_backup():
    return readers.get_backup_status()


@app.post("/api/backup/sync")
async def sync_backup():
    return await runner.run_backup()


@app.post("/api/backup/pull")
async def pull_backup():
    """Manually pull and restore all assets, CSV, and upload history from Google Drive."""
    from src.backup.gdrive_backup import GoogleDriveBackup
    gdrive = GoogleDriveBackup()
    if not gdrive.is_configured:
        return {"success": False, "message": "Google Drive não está configurado no .env"}
    result = gdrive.restore_assets()
    return {"success": True, "details": result}


# ── Timeline ─────────────────────────────────────────

@app.get("/api/timeline")
async def get_timeline():
    """Unified timeline from generation and upload histories."""
    events: list = []

    for _hash, entry in readers.read_generation_history().items():
        if isinstance(entry, dict) and entry.get("generated_at"):
            events.append({
                "timestamp": entry["generated_at"],
                "phase": 3,
                "icon": "🖼️",
                "message": f"Generated: {entry.get('concept') or entry.get('image_file') or _hash[:8]}",
                "type": "success",
            })

    for entry in readers.read_upload_history():
        if not isinstance(entry, dict):
            continue
        ts = entry.get("uploaded_at") or entry.get("timestamp", "")
        agency = entry.get("agency") or entry.get("platform", "unknown")
        fn = entry.get("filename") or entry.get("file", "")
        events.append({
            "timestamp": ts,
            "phase": 5,
            "icon": "🚀",
            "message": f"Uploaded {fn} → {agency}",
            "type": "success",
        })

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:100]


# ── Predictive Intelligence ──────────────────────────

@app.get("/api/seasonal")
async def get_seasonal():
    """Get dynamic seasonal radar recommendations for D+60 to D+90."""
    return readers.get_seasonal_forecast()


@app.get("/api/saturation")
async def get_saturation(query: str, downloads: float = 250.0, indexed: int = 15000):
    """Calculate market saturation index for a given keyword."""
    from src.analyzer.saturation_index import calculate_saturation_index
    report = calculate_saturation_index(query=query, average_downloads=downloads, total_indexed_assets=indexed)
    return report.to_dict()


# ── Phase Runner ─────────────────────────────────────

@app.get("/api/tasks")
async def get_tasks():
    return runner.get_running_tasks()


@app.get("/api/tasks/{task_id}")
async def get_task_detail(task_id: str):
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    success = runner.terminate_task(task_id)
    return {"success": success, "task_id": task_id}


@app.post("/api/tasks/cleanup")
async def cleanup_tasks():
    killed = runner.cleanup_orphan_processes()
    return {"success": True, "killed_count": killed}


@app.post("/api/run-phase/{phase}")
async def run_phase(phase: int, query: Optional[str] = None, mode: Optional[str] = None, platform: Optional[str] = None):
    if phase not in (1, 2, 3, 4, 5):
        raise HTTPException(status_code=400, detail="Phase must be 1–5")
    extra_args = []
    if query:
        extra_args.extend(["--query", query])
    if mode:
        extra_args.extend(["--mode", mode])
    if platform:
        extra_args.extend(["--platform", platform])
    return await runner.run_phase(phase, extra_args=extra_args if extra_args else None)


# ── Quality Control (QC) & Curation ──────────────────

def _resolve_staging_image_path(filename: str) -> Path:
    safe_name = Path(filename).name
    if safe_name != filename or not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if Path(safe_name).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido")
    candidate = readers.STAGING_IMAGES_DIR / safe_name
    if candidate.exists() and candidate.is_file():
        try:
            candidate.resolve().relative_to(readers.STAGING_IMAGES_DIR.resolve())
            return candidate
        except ValueError:
            pass
    raise HTTPException(status_code=404, detail="Staging image not found")


@app.get("/api/qc/config")
async def get_qc_config():
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    return inspector.get_config()


@app.post("/api/qc/config")
async def set_qc_config(req: schemas.QCConfigRequest):
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    return inspector.set_config(mode=req.mode, min_score=req.min_score, auto_upscale=req.auto_upscale)


@app.get("/api/qc/stats")
async def get_qc_stats():
    return readers.get_qc_stats()


@app.get("/api/qc/images")
async def get_qc_images(filter: str = "all"):
    images = readers.list_staging_images(filter_status=filter)
    stats = readers.get_qc_stats()
    return {
        "images": images,
        "total": len(images),
        "stats": stats,
    }


@app.post("/api/qc/evaluate")
async def evaluate_qc_images(req: schemas.QCEvaluateRequest):
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    results = inspector.run_batch_qc(filenames=req.filenames)
    return {"success": True, "evaluated_count": len(results), "items": results}


@app.post("/api/qc/set-status")
async def set_qc_status(req: schemas.QCSetStatusRequest):
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    item = inspector.set_status(req.filename, req.status, notes=req.notes or "")
    return {"success": True, "item": item}


@app.post("/api/qc/batch-set-status")
async def batch_set_qc_status(req: schemas.QCBatchStatusRequest):
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    count = inspector.batch_set_status(req.filenames, req.status)
    return {"success": True, "updated_count": count}


@app.post("/api/qc/package-zip")
async def package_qc_zip(req: Optional[schemas.QCPackageZipRequest] = None):
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    pack_size = req.pack_size if req and req.pack_size else 10
    only_unproc = req.only_unprocessed if req and req.only_unprocessed is not None else True
    
    result = inspector.package_approved_packs(pack_size=pack_size, only_unprocessed=only_unproc)
    
    if req and req.auto_run:
        conta2_res = await runner.run_conta2(mode="window", batch_size=pack_size)
        result["run_conta2"] = conta2_res
        
    return {"success": True, "data": result}


@app.post("/api/qc/run-conta2")
async def trigger_run_conta2(req: Optional[schemas.QCRunConta2Request] = None):
    mode = req.mode if req and req.mode else "window"
    batch_size = req.batch_size if req and req.batch_size else 10
    result = await runner.run_conta2(mode=mode, batch_size=batch_size)
    return result


@app.get("/api/qc/packs")
async def get_qc_packs():
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    return inspector.get_packs_info()


@app.post("/api/qc/upscale")
async def trigger_qc_upscale(req: Optional[schemas.QCUpscaleRequest] = None):
    """Redirects upscale requests to RunningHub Conta 2 (SeedVR 8K). Native upscale was removed."""
    res = await runner.run_conta2(mode="window", batch_size=10)
    return {"success": True, "message": "Upscale direcionado para RunningHub Conta 2 (SeedVR 8K)", "details": res}


@app.get("/api/qc/staging/{filename}")
async def get_staging_image_file(filename: str):
    file_path = _resolve_staging_image_path(filename)
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(str(file_path), media_type=media.get(file_path.suffix.lower(), "application/octet-stream"))


@app.get("/api/qc/staging/{filename}/thumb")
async def get_staging_image_thumb(filename: str):
    file_path = _resolve_staging_image_path(filename)
    try:
        import io
        from PIL import Image

        img = Image.open(file_path)
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/jpeg")
    except Exception as e:
        logger.warning("Error generating staging thumbnail for %s: %s", filename, e)
        return FileResponse(str(file_path))


# ── Compatibility Aliases ────────────────────────────

@app.get("/api/radar/forecast")
async def get_radar_forecast_compat():
    """Compatibility alias for /api/seasonal."""
    return readers.get_seasonal_forecast()


@app.get("/api/gallery/images")
async def get_gallery_images_compat(filter: str = "all"):
    """Compatibility alias for /api/images."""
    return await get_images(filter=filter)


@app.get("/api/qc/status")
async def get_qc_status_compat():
    """Compatibility alias for QC stats."""
    return readers.get_qc_stats()


@app.get("/api/qc/staging")
async def get_qc_staging_compat(filter: str = "all"):
    """Compatibility alias for /api/qc/images."""
    return await get_qc_images(filter=filter)


# ── Server Launcher ──────────────────────────────────

def start_dashboard(port: int = 8501, open_browser: bool = True) -> None:
    """Start the uvicorn server and optionally open the browser."""
    import uvicorn

    logger.info("🚀 Starting StockCont Dashboard on http://localhost:%d", port)

    if open_browser:
        import threading
        import time

        def _open() -> None:
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")



# ── 24/7 Production Daemon & Quotas ──────────────────

@app.get("/api/quotas")
async def get_quotas():
    """Return rolling 7-day quota status for all platforms."""
    from src.uploader.ftp_distributor import get_all_quota_status
    return get_all_quota_status()


@app.get("/api/daemon/status")
async def get_daemon_status():
    """Return daemon heartbeat state, active phase and vault stats."""
    state_file = readers.PROCESSED_DIR / "daemon_state.json"
    if state_file.exists():
        try:
            import json
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading daemon_state.json: %s", e)

    # Fallback to default stopped state
    from src.uploader.ftp_distributor import get_all_quota_status
    return {
        "status": "stopped",
        "current_phase": "idle",
        "current_action": "Daemon 24/7 não iniciado",
        "cycles_completed": 0,
        "last_heartbeat": None,
        "quotas": get_all_quota_status(),
        "vault": {
            "total_local_assets": 0,
            "pending_distribution": 0,
            "fully_distributed": 0,
            "gdrive_backed_up": 0,
            "purged_from_local_ssd": 0,
        }
    }


@app.post("/api/daemon/start")
async def start_daemon_endpoint(mode: str = "background", interval: int = 300, min_buffer: int = 50):
    """Start the 24/7 autonomous production daemon."""
    return await runner.run_daemon_task(mode=mode, interval=interval, min_buffer=min_buffer)


@app.post("/api/daemon/stop")
async def stop_daemon_endpoint():
    """Stop the running 24/7 daemon task."""
    terminated = runner.terminate_task("daemon")
    return {"success": terminated, "message": "Comando de parada do Daemon enviado"}


# ── Video Dedicated Endpoints ────────────────────────

ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".webm"}


def _resolve_video_path(filename: str) -> Path:
    safe_name = Path(filename).name
    if safe_name != filename or not filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")
    if Path(safe_name).suffix.lower() not in ALLOWED_VIDEO_EXTS:
        raise HTTPException(status_code=400, detail="Formato de vídeo não suportado")
    candidate = readers.FINAL_VIDEOS_DIR / safe_name
    if candidate.exists() and candidate.is_file():
        return candidate
    raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado")


@app.get("/api/video/status")
async def get_video_status():
    """Full pipeline status dedicated to video assets."""
    return readers.build_full_video_status()


@app.get("/api/video/prompts")
async def get_video_prompts(filter: str = "all", aspect: str = "all", page: int = 1, per_page: int = 50):
    """Paginated list of 4D video prompts with filters."""
    items = readers.get_video_prompt_queue_items()
    if filter == "pending":
        items = [i for i in items if i["status"] == "pending"]
    elif filter == "generated":
        items = [i for i in items if i["status"] == "generated"]
    if aspect in ("16:9", "9:16"):
        items = [i for i in items if i["aspect_ratio"] == aspect]

    total = len(items)
    start = (page - 1) * per_page
    return {
        "items": items[start:start + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@app.get("/api/video/prompts/stats")
async def get_video_prompts_stats():
    """Quick counters for video prompts."""
    return readers.get_video_prompt_queue_stats()


@app.post("/api/video/prompts/mark-generated")
async def mark_video_prompts_generated(req: schemas.VideoPromptMarkRequest):
    """Mark video prompt(s) as generated."""
    count = readers.mark_video_prompts(hashes=req.hashes, target_status="generated", all_matching=bool(req.all_pending))
    return {"success": True, "marked_count": count, "message": f"{count} prompt(s) de vídeo marcados como gerados."}


@app.post("/api/video/prompts/mark-pending")
async def mark_video_prompts_pending(req: schemas.VideoPromptMarkRequest):
    """Mark video prompt(s) as pending."""
    count = readers.mark_video_prompts(hashes=req.hashes, target_status="pending", all_matching=bool(req.all_generated))
    return {"success": True, "marked_count": count, "message": f"{count} prompt(s) de vídeo revertidos para pendentes."}


@app.get("/api/video/items")
async def get_video_items():
    """List all rendered videos in data/final/videos/."""
    videos = readers.list_final_videos()
    return {"videos": videos, "total": len(videos)}


@app.get("/api/video/stream/{filename}")
async def stream_video_file(filename: str):
    """Serve video file with range request support for seeking in HTML5 players."""
    path = _resolve_video_path(filename)
    media = "video/quicktime" if path.suffix.lower() == ".mov" else "video/mp4"
    return FileResponse(str(path), media_type=media)


@app.get("/api/video/poster/{filename}")
async def get_video_poster(filename: str):
    """Return or generate poster thumbnail frame for video."""
    path = _resolve_video_path(filename)
    poster_path = readers.VIDEO_POSTERS_DIR / f"{path.stem}_poster.jpg"
    if not poster_path.exists():
        readers.VIDEO_POSTERS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            from src.video.ffmpeg_processor import extract_poster_frame
            extract_poster_frame(path, poster_path, time_offset_percent=0.5)
        except Exception as e:
            logger.warning("Failed to extract poster for %s: %s", filename, e)
    if poster_path.exists():
        return FileResponse(str(poster_path), media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Poster frame não encontrado")


@app.get("/api/video/meta/{filename}")
async def get_video_meta(filename: str):
    """Inspect technical ffprobe properties, stock CSV metadata, and upload history."""
    path = _resolve_video_path(filename)
    tech_info: dict = {}
    try:
        from src.video.ffmpeg_processor import probe_video
        props = probe_video(path)
        tech_info = {
            "width": props.width,
            "height": props.height,
            "duration_seconds": round(props.duration_seconds, 2),
            "fps": round(props.fps, 2),
            "video_codec": props.video_codec,
            "audio_codec": props.audio_codec,
            "has_audio": props.has_audio,
            "bitrate_kbps": props.bitrate_kbps,
            "aspect_ratio": props.aspect_ratio,
            "is_4k": props.is_4k,
            "is_vertical": props.is_vertical,
        }
    except Exception as e:
        tech_info = {"error": str(e)}

    adobe_cat = readers.load_cataloged_video_csv(readers.ADOBE_VIDEO_CSV).get(filename, {})
    pond5_cat = readers.load_cataloged_video_csv(readers.POND5_VIDEO_CSV).get(filename, {})
    upload_hist = readers.read_upload_history_dict().get(filename, {})

    return {
        "filename": filename,
        "technical": tech_info,
        "adobe_csv": adobe_cat,
        "pond5_csv": pond5_cat,
        "upload_history": upload_hist,
    }


@app.get("/api/video/matrix")
async def get_video_matrix():
    """Return distribution matrix matching videos with stock agencies."""
    return readers.get_video_distribution_matrix()


@app.post("/api/video/matrix/toggle")
async def toggle_video_matrix_cell(req: schemas.VideoMatrixToggleRequest):
    """Toggle video upload status in upload history."""
    success = readers.update_matrix_cell(req.filename, req.agency, req.uploaded)
    return {"success": success, "filename": req.filename, "agency": req.agency, "uploaded": req.uploaded}


@app.post("/api/video/matrix/batch-set")
async def batch_video_matrix_set(req: schemas.VideoMatrixBatchRequest):
    """Batch mark or unmark an agency for videos."""
    count = readers.batch_update_matrix_agency(req.agency, req.action, req.filenames)
    return {"success": True, "agency": req.agency, "action": req.action, "updated_count": count}


@app.post("/api/video/matrix/upload-pending")
async def trigger_video_matrix_upload(platform: str = "all"):
    """Trigger Phase 5 distribution upload for videos."""
    args = ["--platform", platform]
    return await runner.run_video_phase(5, extra_args=args)


@app.post("/api/video/run-phase/{phase}")
async def run_video_phase_endpoint(
    phase: int,
    query: Optional[str] = None,
    platform: Optional[str] = None,
    max_items: Optional[int] = None,
    prores: Optional[bool] = False,
    account: Optional[int] = 3,
    execute_mode: Optional[str] = None,
):
    """Trigger video pipeline phases (1, 2, 3, 4, 5)."""
    if phase not in (1, 2, 3, 4, 5):
        raise HTTPException(status_code=400, detail="Video phase must be 1, 2, 3, 4, or 5")
    extra_args = []
    if phase == 3:
        extra_args.extend(["--account", str(account or 3)])
        if execute_mode:
            extra_args.extend(["--execute-mode", execute_mode])
    if query:
        extra_args.extend(["--query", query])
    if platform:
        extra_args.extend(["--platform", platform])
    if max_items:
        extra_args.extend(["--max-items", str(max_items)])
    if prores and phase == 4:
        extra_args.append("--prores")
    return await runner.run_video_phase(phase, extra_args=extra_args)


@app.get("/api/video/reference-images")
async def get_reference_images_for_i2v():
    """List 8K master images available for Image-to-Video (I2V) prompt synthesis."""
    return readers.list_reference_images_for_i2v()


@app.post("/api/video/director/from-image")
async def synthesize_video_from_image(req: schemas.VideoI2VRequest):
    """Synthesize 4D video prompts for a specific 8K image via Gemini Vision."""
    return await runner.run_video_i2v_synthesis(req.image_stem)
