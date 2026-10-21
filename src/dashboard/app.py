from typing import Optional
"""FastAPI Dashboard Application for StockCont.

Serves the dark-theme SPA and provides read-only REST API
endpoints for pipeline status, asset gallery, and phase execution.
"""

import logging
import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import readers, runner

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
IMAGES_DIR = readers.FINAL_IMAGES_DIR

app = FastAPI(
    title="StockCont Dashboard",
    description="Dashboard for the StockCont Autonomous Microstock Pipeline",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── SPA Entry Point ──────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the single-page application."""
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


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


# ── Image Gallery ────────────────────────────────────

@app.get("/api/images")
async def get_images(filter: str = "all"):
    """List images in data/final/images/ with catalog info."""
    images = readers.list_final_images()
    if filter == "cataloged":
        images = [i for i in images if i["is_cataloged"]]
    elif filter == "uncataloged":
        images = [i for i in images if not i["is_cataloged"]]

    cataloged = sum(1 for i in images if i["is_cataloged"])
    return {
        "images": images,
        "total": len(images),
        "cataloged": cataloged,
        "uncataloged": len(images) - cataloged,
    }


@app.get("/api/images/{filename}")
async def get_image_file(filename: str):
    """Serve an original image file."""
    file_path = IMAGES_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    # Security: ensure path stays within IMAGES_DIR
    try:
        file_path.resolve().relative_to(IMAGES_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    return FileResponse(str(file_path), media_type=media.get(file_path.suffix.lower(), "application/octet-stream"))


@app.get("/api/images/{filename}/thumb")
async def get_image_thumbnail(filename: str):
    """Serve a resized thumbnail (max 400px) for gallery performance."""
    file_path = IMAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        file_path.resolve().relative_to(IMAGES_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

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
    file_path = IMAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

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


# ── Backup ───────────────────────────────────────────

@app.get("/api/backup")
async def get_backup():
    return readers.get_backup_status()


@app.post("/api/backup/sync")
async def sync_backup():
    return await runner.run_backup()


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


@app.post("/api/run-phase/{phase}")
async def run_phase(phase: int):
    if phase not in (1, 2, 3, 4, 5):
        raise HTTPException(status_code=400, detail="Phase must be 1–5")
    return await runner.run_phase(phase)


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
