"""Tests for StockCont Video Pipeline Expansion (FFmpeg, Metadata, Compliance, Queue, Cataloger)."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.cataloger.platform_compliance import (
    PLATFORM_RULES,
    ComplianceResult,
    validate_all_platforms_video,
    validate_video_compliance,
)
from src.factory.prompt_queue import PromptItem, PromptQueueManager
from src.video.ffmpeg_processor import (
    VideoProperties,
    create_seamless_loop,
    extract_poster_frame,
    get_ffmpeg_binary,
    get_ffprobe_binary,
    probe_video,
    transcode_to_h264_master,
    transcode_to_prores_master,
)
from src.video.video_metadata import (
    embed_video_metadata,
    format_video_caption,
    format_video_keywords,
    sanitize_video_title,
)


@pytest.fixture(scope="module")
def sample_4k_video(tmp_path_factory) -> Path:
    """Generate a lightweight synthetic 4K 6-second video using FFmpeg lavfi."""
    tmp_dir = tmp_path_factory.mktemp("video_test")
    out_video = tmp_dir / "sample_4k_test.mp4"

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-f", "lavfi",
        "-i", "color=c=navy:s=3840x2160:d=6.0:r=30",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "6.0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(out_video)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert res.returncode == 0, f"FFmpeg failed to create test video: {res.stderr.decode()}"
    return out_video


@pytest.fixture(scope="module")
def sample_vertical_video(tmp_path_factory) -> Path:
    """Generate a lightweight synthetic 9:16 vertical 5.5-second video."""
    tmp_dir = tmp_path_factory.mktemp("video_vertical_test")
    out_video = tmp_dir / "sample_vertical_test.mp4"

    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-f", "lavfi",
        "-i", "color=c=darkgreen:s=2160x3840:d=5.5:r=30",
        "-t", "5.5",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_video)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert res.returncode == 0, f"FFmpeg failed to create vertical video: {res.stderr.decode()}"
    return out_video


def test_ffmpeg_and_ffprobe_available():
    """Verify system FFmpeg and FFprobe binaries are found."""
    assert Path(get_ffmpeg_binary()).is_file()
    assert Path(get_ffprobe_binary()).is_file()


def test_probe_video_4k(sample_4k_video: Path):
    """Test video inspection via ffprobe JSON."""
    props = probe_video(sample_4k_video)
    assert props.width == 3840
    assert props.height == 2160
    assert props.is_4k is True
    assert props.is_vertical is False
    assert props.aspect_ratio == "16:9"
    assert props.duration_seconds >= 5.9
    assert props.fps == 30.0
    assert props.video_codec == "h264"
    assert props.has_audio is True


def test_probe_video_vertical(sample_vertical_video: Path):
    """Test 9:16 vertical video probing."""
    props = probe_video(sample_vertical_video)
    assert props.width == 2160
    assert props.height == 3840
    assert props.is_4k is True
    assert props.is_vertical is True
    assert props.aspect_ratio == "9:16"
    assert props.has_audio is False


def test_extract_poster_frame(sample_4k_video: Path, tmp_path: Path):
    """Test representative JPEG frame extraction at 50% time offset."""
    poster_path = tmp_path / "poster.jpg"
    extracted = extract_poster_frame(sample_4k_video, poster_path, time_offset_percent=0.5)
    assert extracted.is_file()
    assert extracted.stat().st_size > 1000


def test_transcode_to_h264_master_audio_strip(sample_4k_video: Path, tmp_path: Path):
    """Verify mastering removes noisy AI audio tracks (-an) and applies +faststart."""
    out_master = tmp_path / "master_muted.mp4"
    transcode_to_h264_master(sample_4k_video, out_master, preset="ultrafast", mute_audio=True)

    assert out_master.is_file()
    props = probe_video(out_master)
    assert props.has_audio is False
    assert props.video_codec == "h264"


def test_create_seamless_loop(tmp_path: Path):
    """Test Seamless Perfect Loop Engine crossfade on 1080p sample."""
    sample_loop_in = tmp_path / "sample_loop_in.mp4"
    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-f", "lavfi",
        "-i", "color=c=navy:s=1920x1080:d=6.0:r=30",
        "-t", "6.0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(sample_loop_in)
    ]
    subprocess.run(cmd, check=True)
    loop_out = tmp_path / "seamless_loop.mp4"
    create_seamless_loop(sample_loop_in, loop_out, crossfade_sec=1.0)

    assert loop_out.is_file()
    props = probe_video(loop_out)
    # 6s input minus 1s crossfade = 5s seamless loop
    assert 4.8 <= props.duration_seconds <= 5.2
    assert props.has_audio is False


def test_embed_video_metadata(sample_vertical_video: Path, tmp_path: Path):
    """Test metadata injection into MP4 container."""
    tagged_video = tmp_path / "tagged_video.mp4"
    embed_video_metadata(
        video_path=sample_vertical_video,
        output_path=tagged_video,
        title="Modern Biotech Laboratory Drone Shot",
        description="Cinematic vertical footage of genetics lab.",
        keywords=["biotech", "laboratory", "genetics", "science"]
    )

    assert tagged_video.is_file()
    props = probe_video(tagged_video)
    assert props.is_vertical is True


def test_format_video_helpers():
    """Test title, caption and keywords formatting rules."""
    title = sanitize_video_title("   A Very Long Commercial Title with lots of extra text " * 5, max_length=50)
    assert len(title) <= 50

    caption = format_video_caption("Modern architectural facade with sunlight.")
    assert caption.startswith("Generative AI footage.")

    kws = format_video_keywords(["biotech", "future", "lab"])
    assert "generative ai" in kws
    assert "ai generated" in kws
    assert "footage" in kws
    assert "biotech" in kws


def test_video_compliance_adobe(sample_4k_video: Path, tmp_path: Path):
    """Verify compliant 4K video passes Adobe Stock validation."""
    # First create a muted version
    muted_video = tmp_path / "adobe_test_muted.mp4"
    transcode_to_h264_master(sample_4k_video, muted_video, mute_audio=True)

    result = validate_video_compliance(muted_video, platform="adobe", is_ai_generated=True)
    assert result.is_compliant is True
    assert result.blocked is False
    assert len(result.errors) == 0


def test_video_compliance_alamy_auto_block(sample_4k_video: Path):
    """Verify Alamy Anti-Ban safety barrier immediately blocks AI video submissions."""
    result = validate_video_compliance(sample_4k_video, platform="alamy", is_ai_generated=True)
    assert result.is_compliant is False
    assert result.blocked is True
    assert "Anti-Ban Safety Barrier" in result.block_reason
    assert "proíbe estritamente qualquer vídeo gerado por IA" in result.block_reason


def test_video_compliance_too_short(tmp_path: Path):
    """Verify video shorter than 5.0 seconds triggers duration error."""
    short_video = tmp_path / "short_video.mp4"
    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-f", "lavfi",
        "-i", "color=c=red:s=1920x1080:d=3.0:r=30",
        "-t", "3.0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-an",
        str(short_video)
    ]
    subprocess.run(cmd, check=True)

    result = validate_video_compliance(short_video, platform="adobe", is_ai_generated=True)
    assert result.is_compliant is False
    assert any("Duração" in err for err in result.errors)


def test_prompt_queue_video_item():
    """Verify PromptItem handles video asset type and properties."""
    item = PromptItem(
        prompt_text="Cinematic 4K corporate dolly shot",
        prompt_hash="abc123hash",
        asset_type="video",
        aspect_ratio="16:9",
        video_file="corporate_dolly_01.mp4"
    )
    d = item.to_dict()
    assert d["asset_type"] == "video"
    assert d["aspect_ratio"] == "16:9"
    assert d["video_file"] == "corporate_dolly_01.mp4"


def test_video_cataloger_csv_atomic(tmp_path: Path):
    """Verify atomic appending of video metadata to CSV."""
    from src.cataloger.video_cataloger import append_csv_row_atomic, load_cataloged_filenames

    csv_file = tmp_path / "test_video_upload.csv"
    headers = ["Filename", "Title", "Keywords", "Category", "Releases"]

    row1 = {
        "Filename": "clip_01.mp4",
        "Title": "Modern office workspace",
        "Keywords": '"office, modern, business, 4k"',
        "Category": "8",
        "Releases": ""
    }
    append_csv_row_atomic(csv_file, headers, row1)

    cataloged = load_cataloged_filenames(csv_file)
    assert "clip_01.mp4" in cataloged

    row2 = {
        "Filename": "clip_02.mp4",
        "Title": "Drone over renewable solar panels",
        "Keywords": '"solar, green, renewable, 4k"',
        "Category": "8",
        "Releases": ""
    }
    append_csv_row_atomic(csv_file, headers, row2)

    cataloged_updated = load_cataloged_filenames(csv_file)
    assert "clip_01.mp4" in cataloged_updated
    assert "clip_02.mp4" in cataloged_updated
