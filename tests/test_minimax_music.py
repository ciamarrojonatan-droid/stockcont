"""Tests for MiniMax Music 3 Cinematic Soundtrack Engine."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.factory.runninghub_bot import (
    CONTA_MINIMAX_MUSIC_CONFIG,
    get_account_config,
)
from src.video.minimax_music_engine import (
    MiniMaxMusicEngine,
    MusicTrackResult,
    MUSIC_PRESETS,
)


class TestMiniMaxMusicTopology:
    """Validate RunningHub ComfyUI topology for MiniMax Music 3 (Workflow 2120003151633174529)."""

    def test_workflow_id_and_url(self):
        assert CONTA_MINIMAX_MUSIC_CONFIG["workflow_id"] == "2120003151633174529"
        assert "2120003151633174529" in CONTA_MINIMAX_MUSIC_CONFIG["workflow_url"]

    def test_node_topology(self):
        assert CONTA_MINIMAX_MUSIC_CONFIG["style_node"] == 15
        assert CONTA_MINIMAX_MUSIC_CONFIG["structure_node"] == 16
        assert CONTA_MINIMAX_MUSIC_CONFIG["duration_node"] == 14
        assert CONTA_MINIMAX_MUSIC_CONFIG["output_audio_node"] == 7
        assert CONTA_MINIMAX_MUSIC_CONFIG["output_node"] == 7
        assert CONTA_MINIMAX_MUSIC_CONFIG["execute_mode"] == "lite_plus"

    @pytest.mark.parametrize("acc_key", ["minimax_music", "minimax", "music", "soundtrack", 5])
    def test_get_account_config_mapping(self, acc_key):
        cfg = get_account_config(acc_key)
        assert cfg["role"] == "soundtrack_minimax_music"
        assert cfg["output_node"] == 7
        assert cfg["execute_mode"] == "lite_plus"


class TestMiniMaxMusicEngine:
    """Test MiniMaxMusicEngine prompt generation, fallback, and mocked execution."""

    def test_presets_exist_and_have_4part_structure(self):
        engine = MiniMaxMusicEngine()
        for preset_name in ["hans_zimmer_tension", "ludwig_goransson_action", "cold_war_espionage", "cyber_warfare"]:
            style, struct = engine.build_prompts(preset_name=preset_name)
            assert len(style) > 30
            assert "[Intro" in struct
            assert "[Tension" in struct
            assert "[Climax" in struct
            assert "[Outro" in struct

    def test_procedural_fallback_synthesis(self, tmp_path):
        engine = MiniMaxMusicEngine(output_dir=tmp_path)
        track = engine.generate_soundtrack(
            preset_name="hans_zimmer_tension",
            duration_sec=3.0,
            force_procedural=True,
        )
        assert isinstance(track, MusicTrackResult)
        assert track.engine == "procedural_fallback"
        assert track.audio_path.exists()
        assert track.filesize_bytes > 1000
        assert track.duration_seconds == 3.0

    @patch("src.factory.runninghub_bot.run_minimax_music_bot")
    def test_mocked_runninghub_generation(self, mock_bot, tmp_path):
        mock_file = tmp_path / "soundtrack_minimax_test.flac"
        mock_file.write_bytes(b"RIFF" + b"\x00" * 2000)
        mock_bot.return_value = {
            "saved_files": [mock_file.name],
            "total_images_saved": 1,
        }

        engine = MiniMaxMusicEngine(output_dir=tmp_path)
        track = engine.generate_soundtrack(
            preset_name="hans_zimmer_tension",
            duration_sec=180.0,
            force_procedural=False,
        )
        assert track.engine == "minimax_music_3"
        assert track.filename == mock_file.name
        assert track.duration_seconds == 180.0
        mock_bot.assert_called_once()
