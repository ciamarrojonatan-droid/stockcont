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
