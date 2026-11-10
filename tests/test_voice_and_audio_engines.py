"""Unit tests for StockCont & DarkFactory Voice Engine (Deepgram) and Audio Engine."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.video.audio_engine import (
    ACOUSTIC_PROFILES,
    DarkFactoryAudioEngine,
    SoundtrackResult,
)
from src.video.voice_engine import (
    DEEPGRAM_VOICE_CATALOG,
    DEFAULT_DARKFACTORY_VOICE,
    DeepgramVoiceEngine,
    VoiceSynthesisResult,
)


def test_deepgram_voice_catalog():
    """Verify default voices exist and have correct metadata."""
    assert DEFAULT_DARKFACTORY_VOICE in DEEPGRAM_VOICE_CATALOG
    assert "aura-helios-en" in DEEPGRAM_VOICE_CATALOG
    assert "aura-asteria-en" in DEEPGRAM_VOICE_CATALOG
    assert DEEPGRAM_VOICE_CATALOG["aura-helios-en"]["gender"] == "male"


def test_deepgram_cost_estimation():
    """Verify cost calculation matches $0.015 per 1,000 characters."""
    engine = DeepgramVoiceEngine(api_key="mock_key")
    cost_1k = engine.estimate_cost(1000)
    assert cost_1k == 0.015
    cost_5k = engine.estimate_cost(5000)
    assert cost_5k == 0.075


def test_deepgram_availability_check(monkeypatch):
    """Verify is_available responds correctly to API key presence."""
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    e1 = DeepgramVoiceEngine(api_key="")
    assert not e1.is_available

    e2 = DeepgramVoiceEngine(api_key="valid_test_key_123456789")
    assert e2.is_available


def test_deepgram_empty_script_validation():
    """Verify synthesis raises ValueError on empty or whitespace script."""
    engine = DeepgramVoiceEngine(api_key="dummy_key")
    with pytest.raises(ValueError, match="Script text cannot be empty"):
        engine.synthesize("   ")


def test_deepgram_srt_generation():
    """Verify SRT subtitle generation matches formatting standards."""
    text = "Stanislav Petrov averted nuclear war. The siren echoed through the command bunker."
    srt = DeepgramVoiceEngine.generate_srt_subtitles(text, total_duration_seconds=5.0)

    assert "1\n" in srt
    assert "-->" in srt
    assert "00:00:00,000" in srt
    assert "Petrov" in srt


def test_deepgram_synthesize_mocked_success(tmp_path):
    """Test successful synthesis using mocked HTTP response."""
    engine = DeepgramVoiceEngine(api_key="test_api_key_123456789", output_dir=tmp_path)

    dummy_audio_bytes = b"ID3" + b"\x00" * 4000  # Fake MP3 bytes

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = dummy_audio_bytes

    with patch("httpx.Client.post", return_value=mock_resp), \
         patch.object(engine, "_probe_audio_duration", return_value=3.2):
        result = engine.synthesize(
            text="The nuclear alarm sounded in Moscow.",
            voice="aura-helios-en",
            speed=1.0,
            generate_subtitles=True,
        )

        assert isinstance(result, VoiceSynthesisResult)
        assert result.audio_path.exists()
        assert result.filesize_bytes == len(dummy_audio_bytes)
        assert result.duration_seconds == 3.2
        assert result.voice_used == "aura-helios-en"
        assert result.is_commercial_licensed is True
        assert result.subtitles_path is not None
        assert result.subtitles_path.exists()


def test_deepgram_retry_on_429(tmp_path):
    """Verify retry logic handles 429 backoff."""
    engine = DeepgramVoiceEngine(api_key="test_api_key_123456789", output_dir=tmp_path)

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.content = b"ID3" + b"\x00" * 1000

    responses = [mock_resp_429, mock_resp_200]

    with patch("httpx.Client.post", side_effect=responses), \
         patch("time.sleep", return_value=None), \
         patch.object(engine, "_probe_audio_duration", return_value=2.0):
        result = engine.synthesize("Retry test script.")
        assert result.filesize_bytes == 1003


def test_audio_engine_procedural_soundbed(tmp_path):
    """Verify procedural soundbed generation produces valid WAV audio."""
    engine = DarkFactoryAudioEngine(output_dir=tmp_path, sample_rate=22050)

    res = engine.generate_procedural_soundbed(
        duration_seconds=1.5,
        profile_name="cold_war_espionage",
    )

    assert isinstance(res, SoundtrackResult)
    assert res.audio_path.exists()
    assert res.filesize_bytes > 10_000
    assert res.sample_rate == 22050
    assert res.profile_used == "cold_war_espionage"


def test_audio_engine_acoustic_profiles():
    """Verify all defined acoustic profiles have required sound architecture keys."""
    for name, p in ACOUSTIC_PROFILES.items():
        assert "base_freq_hz" in p
        assert "overtone_freq_hz" in p
        assert "lfo_rate_hz" in p
        assert "tick_bpm" in p
        assert "description" in p


def test_audio_engine_mixing_mocked(tmp_path):
    """Verify mix_voice_and_soundtrack executes FFmpeg correctly."""
    engine = DarkFactoryAudioEngine(output_dir=tmp_path)

    v_file = tmp_path / "voice.mp3"
    m_file = tmp_path / "music.wav"
    out_file = tmp_path / "final_mix.mp3"

    v_file.write_bytes(b"dummy voice")
    m_file.write_bytes(b"dummy music")

    def mock_subprocess_run(cmd, **kwargs):
        # Emulate ffmpeg creating output
        out_file.write_bytes(b"mastered mix audio")
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        mixed = engine.mix_voice_and_soundtrack(
            voice_path=v_file,
            soundtrack_path=m_file,
            output_path=out_file,
            ducking=True,
        )
        assert mixed.exists()
        assert mixed.stat().st_size > 0
