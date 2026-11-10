"""Tests for MiniMax H3 Cinematic V2 Turbo Video Fallback Engine (Workflow 2118560390471745537)."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.factory.runninghub_bot import (
    CONTA_MINIMAX_H3_CONFIG,
    get_account_config,
)
from src.video.minimax_h3_engine import (
    MiniMaxH3VideoEngine,
    H3VideoResult,
)
from src.dashboard.app import app


class TestMiniMaxH3Topology:
    """Validate RunningHub ComfyUI topology for MiniMax H3 Cinematic (Workflow 2118560390471745537)."""

    def test_workflow_id_and_url(self):
        assert CONTA_MINIMAX_H3_CONFIG["workflow_id"] == "2118560390471745537"
        assert "2118560390471745537" in CONTA_MINIMAX_H3_CONFIG["workflow_url"]

    def test_node_topology(self):
        assert CONTA_MINIMAX_H3_CONFIG["prompt_node"] == 35          # PrimitiveStringMultiline
        assert CONTA_MINIMAX_H3_CONFIG["input_image_node"] == 48     # LoadImage (图1)
        assert CONTA_MINIMAX_H3_CONFIG["duration_node"] == 66        # PrimitiveFloat
        assert CONTA_MINIMAX_H3_CONFIG["resolution_node"] == 62      # ResolutionSelector
        # MANDATÓRIO: Nó #107 FeiHouVideoPreview para salvar vídeo sem marca d'água!
        assert CONTA_MINIMAX_H3_CONFIG["output_video_node"] == 107
        assert CONTA_MINIMAX_H3_CONFIG["output_node"] == 107
        assert CONTA_MINIMAX_H3_CONFIG["execute_mode"] == "lite_plus"

    @pytest.mark.parametrize("acc_key", ["minimax_h3", "minimax_video", "h3", "h3_cinematic", 7])
    def test_get_account_config_mapping(self, acc_key):
        cfg = get_account_config(acc_key)
        assert cfg["role"] == "video_minimax_h3_cinematic"
        assert cfg["output_video_node"] == 107
        assert cfg["execute_mode"] == "lite_plus"


class TestMiniMaxH3VideoEngine:
    """Test MiniMaxH3VideoEngine prompt formatting, procedural fallback, and mocked RPA execution."""

    def test_build_cinematic_prompt(self):
        engine = MiniMaxH3VideoEngine()
        p = engine.build_cinematic_prompt(
            subject="Soviet duty officer staring at pulsating red alarms",
            camera_movement="Slow push-in dolly track",
            lighting="Volumetric red sirens and CRT green glow",
        )
        assert "Camera Movement: Slow push-in dolly track" in p
        assert "Soviet duty officer" in p
        assert "Volumetric red sirens" in p
        assert "no digital warping" in p

    def test_procedural_fallback_synthesis(self, tmp_path):
        engine = MiniMaxH3VideoEngine(output_dir=tmp_path)
        result = engine.generate_video(
            prompt="Cinematic tracking shot across server room",
            duration_sec=1.0,  # Short duration for quick test execution
            force_procedural=True,
        )
        assert isinstance(result, H3VideoResult)
        assert result.engine == "procedural_fallback"
        assert result.video_path.exists()
        assert result.filesize_bytes > 1000
        assert result.has_watermark is False
        assert result.duration_seconds == 1.0
        assert result.has_audio is True
        assert result.audio_codec == "aac"

    def test_procedural_fallback_4_seconds_with_audio(self, tmp_path):
        engine = MiniMaxH3VideoEngine(output_dir=tmp_path)
        result = engine.generate_video(
            prompt="Soviet duty officer inside bunker 4 seconds",
            duration_sec=4.0,
            force_procedural=True,
        )
        assert isinstance(result, H3VideoResult)
        assert result.engine == "procedural_fallback"
        assert result.duration_seconds == 4.0
        assert result.has_audio is True
        assert result.audio_codec == "aac"
        assert result.has_watermark is False

    def test_procedural_fallback_with_reference_image(self, tmp_path):
        # Create a dummy reference image
        import numpy as np
        import cv2

        dummy_img = tmp_path / "ref_test.jpg"
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:, :] = (40, 20, 80)
        cv2.imwrite(str(dummy_img), img)

        engine = MiniMaxH3VideoEngine(output_dir=tmp_path)
        result = engine.generate_video(
            prompt="Cinematic camera drift",
            reference_image_path=dummy_img,
            duration_sec=1.0,
            force_procedural=True,
        )
        assert result.video_path.exists()
        assert result.filesize_bytes > 1000
        assert result.has_watermark is False

    @patch("src.factory.runninghub_bot.run_minimax_h3_video_bot")
    def test_mocked_runninghub_generation_watermark_free(self, mock_bot, tmp_path):
        mock_video = tmp_path / "minimax_h3_cinematic_test123.mp4"
        mock_video.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 8000)

        mock_bot.return_value = {
            "saved_files": [mock_video.name],
            "total_images_saved": 1,
        }

        engine = MiniMaxH3VideoEngine(output_dir=tmp_path)
        result = engine.generate_video(
            prompt="High stakes historical documentary shot",
            duration_sec=10.0,
            force_procedural=False,
        )
        assert result.engine == "minimax_h3_cinematic_runninghub"
        assert result.filename == mock_video.name
        assert result.has_watermark is False
        mock_bot.assert_called_once()


class TestMiniMaxH3DashboardEndpoint:
    """Test REST API endpoint /api/v1/video/minimax_h3."""

    def test_generate_minimax_h3_endpoint_procedural(self):
        client = TestClient(app)
        payload = {
            "prompt": "Stanislav Petrov inside nuclear bunker under red strobe",
            "camera_movement": "Slow cinematic push-in dolly track forward",
            "lighting": "Volumetric rim lighting and CRT phosphor green",
            "duration_sec": 1.0,
            "use_runninghub": False,
        }
        response = client.post("/api/v1/video/minimax_h3", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["video_file"].endswith(".mp4")
        assert data["has_watermark"] is False
        assert "minimax_h3" in data["video_file"]
