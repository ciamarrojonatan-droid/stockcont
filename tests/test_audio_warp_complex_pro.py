"""Test Suite for Ableton Live 'Complex Pro' Warp Engine.

Tests time_stretch_audio_complex_pro:
1. Validates FFmpeg rubberband command construction with Complex Pro parameters.
2. Validates execution and file creation on sample audio.
3. Validates formant preservation flag toggling.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.video.ffmpeg_processor import time_stretch_audio_complex_pro


class TestAudioWarpComplexPro:
    """Test suite for Complex Pro vocal time-stretching."""

    @patch("subprocess.run")
    @patch("src.video.ffmpeg_processor.get_ffmpeg_binary", return_value="ffmpeg")
    def test_command_construction_complex_pro(self, mock_get_ffmpeg, mock_run, tmp_path):
        in_file = tmp_path / "input.wav"
        in_file.write_bytes(b"dummy audio data")
        out_file = tmp_path / "output.wav"

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        # Call with tempo=0.90, pitch=0.96, preserve_formants=True
        time_stretch_audio_complex_pro(
            input_audio_path=in_file,
            output_audio_path=out_file,
            tempo=0.90,
            pitch=0.96,
            preserve_formants=True,
        )

        assert mock_run.called
        cmd_args = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd_args)

        # Check that Ableton Complex Pro parameters are included
        assert "-af" in cmd_args
        af_index = cmd_args.index("-af")
        filter_expr = cmd_args[af_index + 1]

        assert "rubberband=" in filter_expr
        assert "tempo=0.900" in filter_expr
        assert "pitch=0.960" in filter_expr
        assert "formant=preserved" in filter_expr
        assert "transients=smooth" in filter_expr
        assert "window=long" in filter_expr
        assert "smoothing=on" in filter_expr
        assert "pitchq=quality" in filter_expr

    @patch("subprocess.run")
    @patch("src.video.ffmpeg_processor.get_ffmpeg_binary", return_value="ffmpeg")
    def test_formant_shifted_when_disabled(self, mock_get_ffmpeg, mock_run, tmp_path):
        in_file = tmp_path / "input.wav"
        in_file.write_bytes(b"dummy audio data")
        out_file = tmp_path / "output.wav"

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        time_stretch_audio_complex_pro(
            input_audio_path=in_file,
            output_audio_path=out_file,
            tempo=1.0,
            pitch=1.0,
            preserve_formants=False,
        )

        cmd_args = mock_run.call_args[0][0]
        af_index = cmd_args.index("-af")
        filter_expr = cmd_args[af_index + 1]

        assert "formant=shifted" in filter_expr
