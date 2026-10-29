"""StockCont Phase 4: Video Cataloger & Metadata Master.

Discovers rendered video footage in data/final/videos/, extracts representative poster frames,
queries Gemini Vision for high-converting commercial titles and keywords, masters the video
(audio stripping, Rec.709, faststart), injects QuickTime/MP4 container metadata,
and updates atomic upload CSVs for Adobe Stock Video and Pond5.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from dotenv import load_dotenv

from src.video.ffmpeg_processor import (
    extract_poster_frame,
    probe_video,
    transcode_to_h264_master,
    transcode_to_prores_master,
)
from src.video.video_metadata import embed_video_metadata, format_video_caption, sanitize_video_title

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

FINAL_VIDEOS_DIR = BASE_DIR / "data" / "final" / "videos"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ADOBE_VIDEO_CSV = PROCESSED_DIR / "adobe_stock_video_upload.csv"
POND5_VIDEO_CSV = PROCESSED_DIR / "pond5_video_upload.csv"
POSTERS_DIR = FINAL_VIDEOS_DIR / "posters"

logger = logging.getLogger("VideoCataloger")

PREFERRED_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

CSV_HEADERS_ADOBE = ["Filename", "Title", "Keywords", "Category", "Releases"]
CSV_HEADERS_POND5 = ["Filename", "Title", "Description", "Keywords", "PriceTier", "Resolution", "AudioOption", "ModelRelease"]


def load_cataloged_filenames(csv_path: Path) -> Set[str]:
    """Read CSV and return set of already cataloged video filenames."""
    if not csv_path.exists():
        return set()
    cataloged = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fname = row.get("Filename")
                if fname:
                    cataloged.add(fname.strip())
    except Exception as e:
        logger.warning(f"Error reading cataloged CSV {csv_path.name}: {e}")
    return cataloged


def append_csv_row_atomic(csv_path: Path, headers: List[str], row_data: Dict[str, Any]) -> None:
    """Atomically append a row to CSV file (ADR-02)."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception:
            rows = []

    rows.append(row_data)

    tmp_path = csv_path.with_suffix(f".tmp.{os.getpid()}")
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    tmp_path.replace(csv_path)


def generate_video_metadata_with_gemini(
    poster_path: Path,
    api_key: str
) -> Optional[Dict[str, Any]]:
    """Query Gemini Vision on the extracted poster frame to get Title, Description, and Keywords."""
    from src.analyzer.video_director import encode_image_to_base64

    img_b64 = encode_image_to_base64(poster_path)
    if not img_b64:
        return None

    prompt = (
        "You are an expert commercial microstock footage cataloger. "
        "Analyze this representative frame from a stock video and generate: "
        "1. A commercial, buyer-intent Title (max 100 chars, no AI prefix in title). "
        "2. A detailed Description (starting strictly with 'Generative AI footage. '). "
        "3. Exactly 45 to 49 unique keywords in English, ordered from most relevant to general, "
        "including mandatory tags: 'generative ai', 'ai generated', 'footage', 'b-roll', '4k', 'cinematic'. "
        "Return ONLY a JSON object: "
        "{\"title\": \"...\", \"description\": \"...\", \"keywords\": [\"...\"]}"
    )

    client = httpx.Client(timeout=45.0)
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.4
        }
    }

    for model in PREFERRED_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            res = client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)
            elif res.status_code == 429:
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Error calling {model} for video cataloging: {e}")

    return None


def catalog_single_video(
    video_path: Path,
    api_key: Optional[str] = None,
    master_audio_mute: bool = True,
    generate_prores: bool = False
) -> Dict[str, Any]:
    """Catalog a single video file: probe, poster extraction, Gemini tagging, audio strip, and CSV record."""
    v_path = Path(video_path).resolve()
    props = probe_video(v_path)

    # 1. Extract poster frame
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    poster_path = POSTERS_DIR / f"{v_path.stem}_poster.jpg"
    extract_poster_frame(v_path, poster_path, time_offset_percent=0.5)

    # 2. Get Metadata via Gemini or Fallback
    meta: Dict[str, Any] = {}
    if api_key:
        ai_meta = generate_video_metadata_with_gemini(poster_path, api_key)
        if ai_meta:
            meta = ai_meta

    if not meta:
        clean_title = v_path.stem.replace("_", " ").title()
        meta = {
            "title": f"Cinematic 4K Stock Footage of {clean_title}",
            "description": f"Generative AI footage. Cinematic slow motion scene depicting {clean_title}.",
            "keywords": ["generative ai", "ai generated", "footage", "b-roll", "4k", "cinematic", "commercial"]
        }

    title = sanitize_video_title(meta.get("title", ""))
    desc = format_video_caption(meta.get("description", ""))
    keywords_list = meta.get("keywords", [])
    keywords_str = ", ".join(keywords_list)

    # 3. Master video if needed (strip audio if master_audio_mute is True)
    if master_audio_mute and props.has_audio:
        logger.info(f"Stripping unwanted audio track from {v_path.name}...")
        temp_mute = v_path.with_name(f"mute_{v_path.name}")
        transcode_to_h264_master(v_path, temp_mute, mute_audio=True)
        temp_mute.replace(v_path)

    # 4. Inject metadata directly into MP4/MOV container
    embed_video_metadata(
        video_path=v_path,
        title=title,
        description=desc,
        keywords=keywords_list
    )

    # 5. Record to Adobe Stock Video CSV
    adobe_row = {
        "Filename": v_path.name,
        "Title": title,
        "Keywords": f'"{keywords_str}"',
        "Category": "8",  # Video / Animation
        "Releases": ""
    }
    append_csv_row_atomic(ADOBE_VIDEO_CSV, CSV_HEADERS_ADOBE, adobe_row)

    # 6. Record to Pond5 Video CSV
    res_str = "4K UHD" if props.is_4k else "Full HD"
    pond5_row = {
        "Filename": v_path.name,
        "Title": title,
        "Description": desc,
        "Keywords": f'"{keywords_str}"',
        "PriceTier": "Tier 4",
        "Resolution": res_str,
        "AudioOption": "No Audio",
        "ModelRelease": "No"
    }
    append_csv_row_atomic(POND5_VIDEO_CSV, CSV_HEADERS_POND5, pond5_row)

    # 7. Optional ProRes Generation for Pond5
    if generate_prores:
        prores_path = v_path.with_name(f"{v_path.stem}_prores.mov")
        transcode_to_prores_master(v_path, prores_path)
        embed_video_metadata(prores_path, title=title, description=desc, keywords=keywords_list)
        pond5_prores_row = dict(pond5_row)
        pond5_prores_row["Filename"] = prores_path.name
        append_csv_row_atomic(POND5_VIDEO_CSV, CSV_HEADERS_POND5, pond5_prores_row)

    logger.info(f"✅ Video successfully cataloged: {v_path.name}")
    return {
        "filename": v_path.name,
        "title": title,
        "keywords_count": len(keywords_list),
        "is_4k": props.is_4k,
        "duration": props.duration_seconds
    }


def run_video_cataloger(
    videos_dir: Path = FINAL_VIDEOS_DIR,
    max_items: Optional[int] = None,
    generate_prores: bool = False
) -> List[Dict[str, Any]]:
    """Process all uncataloged videos in the specified directory."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not videos_dir.exists():
        logger.warning(f"Videos directory not found: {videos_dir}")
        return []

    cataloged_adobe = load_cataloged_filenames(ADOBE_VIDEO_CSV)
    video_files = sorted(
        [f for f in videos_dir.iterdir() if f.is_file() and f.suffix.lower() in [".mp4", ".mov"] and not f.name.endswith("_prores.mov")],
        key=lambda p: p.stat().st_mtime
    )

    uncataloged = [v for v in video_files if v.name not in cataloged_adobe]
    if max_items:
        uncataloged = uncataloged[:max_items]

    logger.info(f"Found {len(uncataloged)} uncataloged videos in {videos_dir.name}.")
    results: List[Dict[str, Any]] = []

    for v in uncataloged:
        try:
            res = catalog_single_video(
                video_path=v,
                api_key=api_key,
                master_audio_mute=True,
                generate_prores=generate_prores
            )
            results.append(res)
        except Exception as e:
            logger.error(f"Failed to catalog {v.name}: {e}")

    logger.info(f"Video Cataloger complete. Processed {len(results)} videos.")
    return results


if __name__ == "__main__":
    run_video_cataloger()
