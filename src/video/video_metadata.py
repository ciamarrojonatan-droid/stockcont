"""StockCont Video Metadata Injection Module.

Injects commercial microstock metadata (Title, Description, Keywords) directly into
video container atoms (MP4/MOV) using native FFmpeg with optional ExifTool deep tagging.
Ensures strict AI compliance guidelines across stock agencies.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.video.ffmpeg_processor import get_ffmpeg_binary

# UTF-8 safeguard (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("VideoMetadata")

MANDATORY_AI_VIDEO_KEYWORDS = ["ai generated", "generative ai", "footage", "b-roll", "4k", "cinematic"]


def sanitize_video_title(title: str, max_length: int = 120) -> str:
    """Format title according to microstock guidelines (under 120 chars, clean, capitalized)."""
    clean = re.sub(r"[\r\n\t]+", " ", title).strip()
    clean = re.sub(r"\s+", " ", clean)
    if len(clean) > max_length:
        clean = clean[:max_length].rsplit(" ", 1)[0]
    return clean.strip()


def format_video_caption(description: str) -> str:
    """Ensure mandatory Generative AI compliance prefix is present in the video caption."""
    clean = description.strip()
    prefix = "Generative AI footage."
    if not clean.lower().startswith("generative ai"):
        clean = f"{prefix} {clean}"
    return clean


def format_video_keywords(keywords: List[str], max_count: int = 49) -> List[str]:
    """Ensure mandatory AI keywords and format clean, unique, lowercase tags."""
    seen = set()
    cleaned_keywords: List[str] = []

    # Inject mandatory keywords first
    for kw in MANDATORY_AI_VIDEO_KEYWORDS:
        kw_clean = kw.strip().lower()
        if kw_clean and kw_clean not in seen:
            seen.add(kw_clean)
            cleaned_keywords.append(kw_clean)

    # Append input keywords
    for kw in keywords:
        kw_clean = kw.strip().lower()
        kw_clean = re.sub(r"[^\w\s-]", "", kw_clean)
        if kw_clean and kw_clean not in seen and len(kw_clean) > 1:
            seen.add(kw_clean)
            cleaned_keywords.append(kw_clean)
        if len(cleaned_keywords) >= max_count:
            break

    return cleaned_keywords


def get_exiftool_path() -> Optional[str]:
    """Find exiftool executable if available on system or in project bin."""
    path = shutil.which("exiftool")
    if path:
        return path
    
    # Check project local bin
    local_bin = Path(__file__).resolve().parent.parent.parent / "bin" / "exiftool.exe"
    if local_bin.is_file():
        return str(local_bin)
    
    return None


def inject_video_metadata_ffmpeg(
    video_path: Path | str,
    output_path: Path | str,
    title: str,
    description: str,
    keywords: List[str]
) -> Path:
    """Inject Title, Description, and Keywords into MP4/MOV container using native FFmpeg (Zero-reencode)."""
    in_path = Path(video_path).resolve()
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    clean_title = sanitize_video_title(title)
    clean_desc = format_video_caption(description)
    clean_kw_list = format_video_keywords(keywords)
    keywords_str = ", ".join(clean_kw_list)

    temp_out = out_path.with_suffix(f".tmp.{os.getpid()}{out_path.suffix}")

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-i", str(in_path),
        "-c", "copy",
        "-metadata", f"title={clean_title}",
        "-metadata", f"description={clean_desc}",
        "-metadata", f"synopsis={clean_desc}",
        "-metadata", f"comment={keywords_str}",
        "-metadata", f"keywords={keywords_str}",
        "-metadata:s:v", f"handler_name={clean_title}",
        "-movflags", "+faststart",
        str(temp_out)
    ]

    logger.info(f"Injecting metadata via FFmpeg into: {in_path.name}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60.0)
    if res.returncode != 0:
        if temp_out.exists():
            temp_out.unlink()
        err_msg = res.stderr.decode("utf-8", errors="ignore")
        logger.error(f"FFmpeg metadata injection failed: {err_msg}")
        raise RuntimeError(f"FFmpeg metadata injection failed for {in_path}: {err_msg[:300]}")

    temp_out.replace(out_path)
    return out_path


def inject_video_metadata_exiftool(
    video_path: Path | str,
    title: str,
    description: str,
    keywords: List[str]
) -> bool:
    """Deep inject QuickTime and XMP metadata into video container in-place via ExifTool if present."""
    exiftool = get_exiftool_path()
    if not exiftool:
        return False

    target_path = Path(video_path).resolve()
    clean_title = sanitize_video_title(title)
    clean_desc = format_video_caption(description)
    clean_kw_list = format_video_keywords(keywords)
    keywords_str = ", ".join(clean_kw_list)

    cmd = [
        exiftool,
        "-api", "LargeFileSupport=1",
        "-api", "QuickTimeUTC",
        "-overwrite_original",
        "-charset", "utf8",
        f"-Title={clean_title}",
        f"-Description={clean_desc}",
        f"-QuickTime:DisplayName={clean_title}",
        f"-QuickTime:Description={clean_desc}",
        f"-QuickTime:Keywords={keywords_str}",
        f"-XMP-dc:Title={clean_title}",
        f"-XMP-dc:Description={clean_desc}",
    ]

    for kw in clean_kw_list:
        cmd.append(f"-XMP-dc:Subject={kw}")

    cmd.append(str(target_path))

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30.0)
        return res.returncode == 0
    except Exception as e:
        logger.warning(f"ExifTool injection error: {e}")
        return False


def embed_video_metadata(
    video_path: Path | str,
    output_path: Optional[Path | str] = None,
    title: str = "",
    description: str = "",
    keywords: Optional[List[str]] = None
) -> Path:
    """Master video metadata embedder: native FFmpeg container tagging + optional ExifTool deep tagging."""
    in_path = Path(video_path).resolve()
    target_out = Path(output_path).resolve() if output_path else in_path

    if keywords is None:
        keywords = []

    # Step 1: Native FFmpeg container injection
    if target_out == in_path:
        temp_file = in_path.with_name(f"temp_meta_{in_path.name}")
        inject_video_metadata_ffmpeg(in_path, temp_file, title, description, keywords)
        temp_file.replace(in_path)
        final_path = in_path
    else:
        final_path = inject_video_metadata_ffmpeg(in_path, target_out, title, description, keywords)

    # Step 2: Try ExifTool deep tags if available
    if get_exiftool_path():
        inject_video_metadata_exiftool(final_path, title, description, keywords)

    logger.info(f"✅ Metadata successfully embedded into video: {final_path.name}")
    return final_path
