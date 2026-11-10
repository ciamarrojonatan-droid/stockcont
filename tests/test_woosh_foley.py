"""Tests for Sony Woosh Foley & SFX Engine."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.factory.runninghub_bot import (
    CONTA_WOOSH_FOLEY_CONFIG,
    get_account_config,
)
from src.video.woosh_foley_engine import (
    SonyWooshFoleyEngine,
    FoleyResult,
    FOLEY_PRESETS,
)


class TestSonyWooshTopology:
    """Validate RunningHub ComfyUI topology for Sony Woosh Foley (Workflow 2119999521484034049)."""

    def test_workflow_id_and_url(self):
        assert CONTA_WOOSH_FOLEY_CONFIG["workflow_id"] == "2119999521484034049"
        assert "2119999521484034049" in CONTA_WOOSH_FOLEY_CONFIG["workflow_url"]

    def test_node_topology(self):
        assert CONTA_WOOSH_FOLEY_CONFIG["input_video_node"] == 34
        assert CONTA_WOOSH_FOLEY_CONFIG["prompt_node"] == 46
        assert CONTA_WOOSH_FOLEY_CONFIG["duration_node"] == 37
        assert CONTA_WOOSH_FOLEY_CONFIG["output_audio_node"] == 9
        # MANDATÓRIO: Nó #94 FeiHouVideoPreview para salvar vídeo sem marca d'água
        assert CONTA_WOOSH_FOLEY_CONFIG["output_video_node"] == 94
        assert CONTA_WOOSH_FOLEY_CONFIG["output_node"] == 94
        assert CONTA_WOOSH_FOLEY_CONFIG["execute_mode"] == "lite_plus"

    @pytest.mark.parametrize("acc_key", ["woosh_foley", "woosh", "foley", "sfx", 6])
    def test_get_account_config_mapping(self, acc_key):
        cfg = get_account_config(acc_key)
        assert cfg["role"] == "foley_sony_woosh"
        assert cfg["output_video_node"] == 94
        assert cfg["execute_mode"] == "lite_plus"


class TestSonyWooshFoleyEngine:
    """Test SonyWooshFoleyEngine synthesis, watermark-free video extraction, and fallback."""

    def test_presets_exist(self):
        assert "espionage_bunker" in FOLEY_PRESETS
        assert "cyber_warfare" in FOLEY_PRESETS
        assert "deep_space" in FOLEY_PRESETS
        assert "cinematic_impact" in FOLEY_PRESETS

    def test_procedural_fallback_synthesis(self, tmp_path):
        engine = SonyWooshFoleyEngine(audio_output_dir=tmp_path, video_output_dir=tmp_path)
        foley = engine.generate_foley(
            mode="t2a",
            sfx_prompt="sub-bass boom, distant bunker siren, metallic latch",
            force_procedural=True,
        )
        assert isinstance(foley, FoleyResult)
        assert foley.engine == "procedural_fallback"
        assert foley.audio_path.exists()
        assert foley.filesize_bytes > 1000
        assert foley.mode == "t2a"

    @patch("src.factory.runninghub_bot.run_woosh_foley_bot")
    def test_mocked_runninghub_generation_with_watermark_free_video(self, mock_bot, tmp_path):
        mock_audio = tmp_path / "woosh_foley_audio_123.wav"
        mock_audio.write_bytes(b"RIFF" + b"\x00" * 3000)
        mock_video = tmp_path / "woosh_foley_preview_123.mp4"
        mock_video.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 5000)

        mock_bot.return_value = {
            "saved_files": [mock_audio.name, mock_video.name],
            "total_images_saved": 2,
        }

        engine = SonyWooshFoleyEngine(audio_output_dir=tmp_path, video_output_dir=tmp_path)
        foley = engine.generate_foley(
            mode="v2a",
            video_path=tmp_path / "source.mp4",
            sfx_prompt="heavy typewriter keystrokes",
            force_procedural=False,
        )
        assert foley.engine == "sony_woosh_vflow"
        assert foley.audio_path.name == mock_audio.name
        assert foley.video_path is not None
        assert foley.video_path.name == mock_video.name
        assert foley.mode == "v2a"
        mock_bot.assert_called_once()
