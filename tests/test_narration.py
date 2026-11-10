"""Unit tests for CosyVoice Audio Narration and REST API."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.dashboard import schemas, readers
from src.factory.runninghub_bot import (
    get_account_config,
    CONTA_COSYVOICE_CONFIG,
    save_audio_from_src,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_cosyvoice_account_config():
    """Verify CosyVoice topology and node mappings."""
    cfg = get_account_config(4)
    assert cfg["role"] == "audio_narration_cosyvoice"
    assert cfg["script_node"] == 345
    assert cfg["emotion_node"] == 355
    assert cfg["output_audio_node"] == 346
    assert cfg["output_node"] == 346
    assert cfg["save_mode"] == "audio_output"
    assert cfg["execute_mode"] == "lite_plus"

    # Also test by string name
    cfg_named = get_account_config("cosyvoice")
    assert cfg_named["role"] == "audio_narration_cosyvoice"
    assert cfg_named["output_audio_node"] == 346


def test_narration_schemas():
    """Verify Pydantic request and response schemas."""
    req = schemas.NarrationRequest(
        script="Stanislav Petrov averted nuclear disaster.",
        emotion="Tense documentary voice",
        speed=1.0,
    )
    assert req.script == "Stanislav Petrov averted nuclear disaster."
    assert req.speed == 1.0

    resp = schemas.NarrationResponse(
        success=True,
        message="Ok",
        audio_file="narration_123.flac",
        audio_url="/api/audio/file/narration_123.flac",
        duration_sec=5.2,
        size_bytes=10240,
    )
    assert resp.success is True
    assert resp.audio_file == "narration_123.flac"


def test_readers_get_audio_items(tmp_path, monkeypatch):
    """Test get_audio_items correctly enumerates audio files."""
    test_audio_dir = tmp_path / "audio"
    test_audio_dir.mkdir()
    (test_audio_dir / "narration_sample.mp3").write_bytes(b"dummy mp3 content")
    (test_audio_dir / "narration_test.flac").write_bytes(b"dummy flac content")
    (test_audio_dir / "not_audio.txt").write_text("ignore me")

    monkeypatch.setattr(readers, "FINAL_AUDIO_DIR", test_audio_dir)
    items = readers.get_audio_items()
    assert len(items) == 2
    filenames = [i["filename"] for i in items]
    assert "narration_sample.mp3" in filenames
    assert "narration_test.flac" in filenames


def test_save_audio_from_src_data_uri(tmp_path):
    """Test saving base64 data:audio URI."""
    import base64
    raw = b"RIFF" + b"\x00" * 6000
    b64 = base64.b64encode(raw).decode("utf-8")
    data_uri = f"data:audio/wav;base64,{b64}"

    mock_page = MagicMock()
    saved = save_audio_from_src(mock_page, data_uri, destination_dir=tmp_path, prefix="test")
    assert saved is not None
    saved_file = tmp_path / saved
    assert saved_file.exists()
    assert saved_file.stat().st_size == len(raw)


def test_api_narration_items(client, tmp_path, monkeypatch):
    """Test GET /api/narration/items endpoint."""
    test_audio_dir = tmp_path / "audio"
    test_audio_dir.mkdir()
    (test_audio_dir / "narration_demo.mp3").write_bytes(b"sample" * 100)
    monkeypatch.setattr(readers, "FINAL_AUDIO_DIR", test_audio_dir)

    resp = client.get("/api/narration/items")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["filename"] == "narration_demo.mp3"


def test_api_v1_narrate_endpoint(client, tmp_path, monkeypatch):
    """Test POST /api/v1/narrate mocked execution."""
    test_audio_dir = tmp_path / "audio"
    test_audio_dir.mkdir()
    sample_file = test_audio_dir / "narration_mock_abc.flac"
    sample_file.write_bytes(b"mock audio bytes" * 100)

    monkeypatch.setattr(readers, "FINAL_AUDIO_DIR", test_audio_dir)

    mock_result = {
        "batches_completed": 1,
        "total_images_saved": 1,
        "saved_files": [sample_file.name],
    }

    with patch("src.factory.runninghub_bot.run_narration_bot", return_value=mock_result):
        resp = client.post(
            "/api/v1/narrate",
            json={
                "script": "Testing Soviet nuclear siren narration.",
                "emotion": "Deep baritone rising dread",
                "speed": 1.0,
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["success"] is True
        assert payload["audio_file"] == sample_file.name
        assert "/api/audio/file/" in payload["audio_url"]
