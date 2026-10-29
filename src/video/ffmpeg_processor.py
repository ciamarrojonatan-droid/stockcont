"""StockCont Video Processing Engine using FFmpeg & FFprobe.

Provides high-performance video validation, audio stripping, transcoding (H.264 & ProRes),
poster extraction, and seamless perfect loop creation.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("FFmpegProcessor")


@dataclass
class VideoProperties:
    """Technical properties extracted from a video file via ffprobe."""
    path: Path
    width: int
    height: int
    duration_seconds: float
    fps: float
    video_codec: str
    audio_codec: Optional[str]
    has_audio: bool
    bitrate_kbps: int
    filesize_bytes: int
    aspect_ratio: str  # e.g., "16:9", "9:16", "custom"

    @property
    def is_4k(self) -> bool:
        return (self.width >= 3840 and self.height >= 2160) or (self.width >= 2160 and self.height >= 3840)

    @property
    def is_fhd(self) -> bool:
        return (self.width >= 1920 and self.height >= 1080) or (self.width >= 1080 and self.height >= 1920)

    @property
    def is_vertical(self) -> bool:
        return self.height > self.width


def get_ffmpeg_binary() -> str:
    """Return the path to the ffmpeg executable."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FileNotFoundError("FFmpeg executable not found in system PATH.")
    return ffmpeg_path


def get_ffprobe_binary() -> str:
    """Return the path to the ffprobe executable."""
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise FileNotFoundError("FFprobe executable not found in system PATH.")
    return ffprobe_path


def probe_video(video_path: Path | str) -> VideoProperties:
    """Inspect video properties via ffprobe JSON output."""
    path = Path(video_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")

    ffprobe_cmd = [
        get_ffprobe_binary(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]

    try:
        res = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=15.0
        )
        info = json.loads(res.stdout)
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to probe video {path}: {e}")
        raise RuntimeError(f"Error probing video {path}: {e}") from e

    video_stream: Optional[Dict[str, Any]] = None
    audio_stream: Optional[Dict[str, Any]] = None

    for stream in info.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video" and not video_stream:
            video_stream = stream
        elif codec_type == "audio" and not audio_stream:
            audio_stream = stream

    if not video_stream:
        raise ValueError(f"No video stream found in {path}")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # FPS parsing (e.g. "30/1" or "29.97")
    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(r_frame_rate)
    except Exception:
        fps = 30.0

    # Duration parsing
    duration_str = info.get("format", {}).get("duration") or video_stream.get("duration", "0")
    try:
        duration_sec = float(duration_str)
    except Exception:
        duration_sec = 0.0

    filesize = path.stat().st_size
    bitrate_str = info.get("format", {}).get("bit_rate", "0")
    try:
        bitrate_kbps = int(int(bitrate_str) / 1000)
    except Exception:
        bitrate_kbps = 0

    video_codec = video_stream.get("codec_name", "unknown")
    audio_codec = audio_stream.get("codec_name") if audio_stream else None
    has_audio = audio_stream is not None

    # Calculate aspect ratio string
    aspect_ratio = "custom"
    if width > 0 and height > 0:
        ratio = width / height
        if abs(ratio - (16 / 9)) < 0.05:
            aspect_ratio = "16:9"
        elif abs(ratio - (9 / 16)) < 0.05:
            aspect_ratio = "9:16"
        elif abs(ratio - (4 / 3)) < 0.05:
            aspect_ratio = "4:3"
        elif abs(ratio - 1.0) < 0.05:
            aspect_ratio = "1:1"

    return VideoProperties(
        path=path,
        width=width,
        height=height,
        duration_seconds=round(duration_sec, 2),
        fps=round(fps, 2),
        video_codec=video_codec,
        audio_codec=audio_codec,
        has_audio=has_audio,
        bitrate_kbps=bitrate_kbps,
        filesize_bytes=filesize,
        aspect_ratio=aspect_ratio,
    )


def extract_poster_frame(
    video_path: Path | str,
    output_image_path: Path | str,
    time_offset_percent: float = 0.5
) -> Path:
    """Extract a representative JPEG frame (poster) from video at time_offset_percent (default 50%)."""
    in_path = Path(video_path).resolve()
    out_path = Path(output_image_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    props = probe_video(in_path)
    seek_time = max(0.1, props.duration_seconds * time_offset_percent)

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-ss", f"{seek_time:.2f}",
        "-i", str(in_path),
        "-vframes", "1",
        "-q:v", "2",
        str(out_path)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20.0)
    if res.returncode != 0:
        logger.error(f"FFmpeg poster extraction failed: {res.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError(f"Failed to extract poster frame from {in_path}")

    return out_path


def transcode_to_h264_master(
    input_path: Path | str,
    output_path: Path | str,
    crf: int = 18,
    preset: str = "medium",
    mute_audio: bool = True
) -> Path:
    """Transcode/master video to high-quality H.264 MP4 (Rec.709, YUV420p, FastStart).

    Applies mandatory stock footage mastering:
      - Removes unwanted/noisy AI audio track (-an) if mute_audio=True
      - Conforms pixel format to standard yuv420p
      - Enables +faststart for instantaneous web streaming and agency metadata inspection
    """
    in_path = Path(input_path).resolve()
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    temp_out = out_path.with_suffix(f".tmp.{os.getpid()}{out_path.suffix}")

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-i", str(in_path),
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "5.1",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]

    if mute_audio:
        cmd.append("-an")
    else:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    cmd.append(str(temp_out))

    logger.info(f"Transcoding video to H.264 Master: {in_path.name} -> {out_path.name}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300.0)
    if res.returncode != 0:
        if temp_out.exists():
            temp_out.unlink()
        err_msg = res.stderr.decode("utf-8", errors="ignore")
        logger.error(f"FFmpeg transcode failed: {err_msg}")
        raise RuntimeError(f"FFmpeg transcode failed for {in_path}: {err_msg[:300]}")

    temp_out.replace(out_path)
    return out_path


def transcode_to_prores_master(
    input_path: Path | str,
    output_path: Path | str,
    profile: int = 3  # 3 = ProRes 422 HQ
) -> Path:
    """Transcode video to Apple ProRes 422 HQ MOV for premium footage marketplaces (Pond5).

    ProRes is preferred by broadcast editors and commands the highest microstock prices ($80-$250).
    """
    in_path = Path(input_path).resolve()
    out_path = Path(output_path).resolve()
    if out_path.suffix.lower() != ".mov":
        out_path = out_path.with_suffix(".mov")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    temp_out = out_path.with_suffix(f".tmp.{os.getpid()}.mov")

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-i", str(in_path),
        "-c:v", "prores_ks",
        "-profile:v", str(profile),
        "-pix_fmt", "yuv422p10le",
        "-an",
        str(temp_out)
    ]

    logger.info(f"Transcoding video to Apple ProRes 422 HQ: {in_path.name} -> {out_path.name}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600.0)
    if res.returncode != 0:
        if temp_out.exists():
            temp_out.unlink()
        err_msg = res.stderr.decode("utf-8", errors="ignore")
        logger.error(f"FFmpeg ProRes transcode failed: {err_msg}")
        raise RuntimeError(f"FFmpeg ProRes failed for {in_path}: {err_msg[:300]}")

    temp_out.replace(out_path)
    return out_path


def create_seamless_loop(
    input_path: Path | str,
    output_path: Path | str,
    crossfade_sec: float = 1.0
) -> Path:
    """Seamless Perfect Loop Engine: uses FFmpeg xfade filter to crossfade end into beginning.

    Creates an endless loop perfect for background video assets, UI animations, and motion textures.
    """
    in_path = Path(input_path).resolve()
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    props = probe_video(in_path)
    duration = props.duration_seconds
    if duration <= crossfade_sec * 2:
        raise ValueError(f"Video duration ({duration}s) too short for {crossfade_sec}s crossfade.")

    cut_time = duration - crossfade_sec
    temp_out = out_path.with_suffix(f".tmp.{os.getpid()}{out_path.suffix}")

    fps = props.fps or 30.0
    # FFmpeg filtergraph:
    # 1. split=2 avoids pipe deadlock on single input stream
    # 2. v1: beginning until cut_time with constant fps
    # 3. v2: last crossfade_sec with constant fps
    # 4. xfade: blend v2 into v1 over crossfade_sec
    filter_complex = (
        f"[0:v]split=2[in1][in2];"
        f"[in1]trim=0:{cut_time:.3f},setpts=PTS-STARTPTS,fps={fps}[v1];"
        f"[in2]trim={cut_time:.3f}:{duration:.3f},setpts=PTS-STARTPTS,fps={fps}[v2];"
        f"[v2][v1]xfade=transition=fade:duration={crossfade_sec:.3f}:offset=0[outv]"
    )

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-i", str(in_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart",
        str(temp_out)
    ]

    logger.info(f"Generating Seamless Loop ({crossfade_sec}s fade): {in_path.name}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180.0)
    if res.returncode != 0:
        if temp_out.exists():
            temp_out.unlink()
        err_msg = res.stderr.decode("utf-8", errors="ignore")
        logger.error(f"FFmpeg loop generation failed: {err_msg}")
        raise RuntimeError(f"FFmpeg loop generation failed: {err_msg[:300]}")

    temp_out.replace(out_path)
    return out_path
