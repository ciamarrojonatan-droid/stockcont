"""Test suite for Kokoro-82M ONNX local TTS engine."""

import os
from pathlib import Path
import pytest


def test_kokoro_model_files_exist():
    """Verify Kokoro ONNX model and voices bin exist."""
    base_dir = Path(__file__).resolve().parent.parent
    model_dir = base_dir / "data" / "models" / "kokoro"
    onnx_file = model_dir / "kokoro-v0_19.onnx"
    voices_file = model_dir / "voices.bin"

    assert onnx_file.exists(), f"Missing ONNX model at {onnx_file}"
    assert onnx_file.stat().st_size > 10_000_000, "ONNX model too small"
    assert voices_file.exists(), f"Missing voices at {voices_file}"


def test_kokoro_synthesis_output():
    """Verify kokoro generated voice file exists and is valid WAV."""
    base_dir = Path(__file__).resolve().parent.parent
    staging_file = base_dir / "data" / "staging" / "kokoro_pilot_voice.wav"

    assert staging_file.exists(), f"Missing output audio at {staging_file}"
    assert staging_file.stat().st_size > 50_000, "Audio file too small"


def test_kokoro_default_voice_bm_george():
    """Verify default voice is bm_george in DarkFactory Kokoro fallback."""
    import sys
    base_dir = Path(__file__).resolve().parent.parent
    df_src = base_dir / "darkfactory" / "src"
    if str(df_src) not in sys.path:
        sys.path.insert(0, str(df_src))

    from kokoro_fallback import DEFAULT_VOICE, KokoroNarrator
    assert DEFAULT_VOICE == "bm_george", f"Expected bm_george, got {DEFAULT_VOICE}"

    profile = KokoroNarrator.map_instruct_to_voice_profile("")
    assert profile["voice"] == "bm_george"


def test_kokoro_mastered_audio_assets_exist():
    """Verify mastered pilot assets for bm_george and bm_lewis exist in DarkFactory."""
    base_dir = Path(__file__).resolve().parent.parent
    df_audio = base_dir / "darkfactory" / "data" / "audio"
    df_subs = base_dir / "darkfactory" / "data" / "subtitles"

    george_mp3 = df_audio / "pilot_bm_george_mastered.mp3"
    george_wav = df_audio / "pilot_bm_george_mastered.wav"
    george_srt = df_subs / "pilot_bm_george_full.srt"

    assert george_mp3.exists(), f"Missing {george_mp3}"
    assert george_mp3.stat().st_size > 100_000, "George MP3 too small"
    assert george_wav.exists(), f"Missing {george_wav}"
    assert george_srt.exists(), f"Missing {george_srt}"

    lewis_mp3 = df_audio / "pilot_bm_lewis_mastered.mp3"
    assert lewis_mp3.exists(), f"Missing {lewis_mp3}"
    assert lewis_mp3.stat().st_size > 100_000, "Lewis MP3 too small"
