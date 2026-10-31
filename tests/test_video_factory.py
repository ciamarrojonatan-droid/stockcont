"""Unit and Integration Tests for RunningHub Video Factory Pipeline (4K Generation & Upscale)."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.dashboard.app import app
from src.dashboard.readers import build_full_video_status
from src.factory.prompt_queue import PromptItem, PromptQueueManager
from src.factory.runninghub_bot import (
    CONTA_VIDEO_CONFIG,
    get_account_config,
    get_node_videos,
    save_video_from_src,
)
from src.factory.stealth_profile import CONTA_3_FINGERPRINT, get_stealth_fingerprint


class TestVideoFactoryTopology:
    """Verify ComfyUI Node topology and RunningHub bot configuration for Video 4K."""

    def test_account_3_config_values(self):
        """Account 3 must match user specifications for Workflow, Node 164, Node 17, Node 157."""
        cfg = get_account_config(3)
        assert cfg["workflow_id"] == "2115926169974812674"
        assert "2115926169974812674" in cfg["workflow_url"]
        assert cfg["input_image_node"] == 164  # Load Image: node #164
        assert cfg["prompt_node"] == 17        # Prompt: node #17
        assert cfg["output_video_node"] == 157 # Save video/video combine: node #157
        assert cfg["output_node"] == 157
        assert cfg["role"] == "video_generator_4k"
        assert cfg["save_mode"] == "video_output"

    def test_account_video_string_alias(self):
        """String aliases 'video' or 'video_4k' must resolve to CONTA_VIDEO_CONFIG."""
        cfg_alias = get_account_config("video")
        assert cfg_alias["account"] == 3
        assert cfg_alias["workflow_id"] == "2115926169974812674"

    def test_stealth_profile_for_video(self):
        """Stealth profile for account 3 must be isolated with 4K screen and dedicated session dir."""
        fp = get_stealth_fingerprint(3)
        assert fp.account == 3
        assert fp.screen_width == 3840
        assert fp.screen_height == 2160
        assert fp.session_dir == "playwright_session_video"
        assert "RTX 4090" in fp.webgl_renderer


class TestVideoPromptQueue:
    """Verify video prompt queue and history tracking for video generation."""

    def test_video_queue_lifecycle(self, tmp_path):
        """Test video queue loading, pending filtering, and atomic marking as generated."""
        video_prompts_file = tmp_path / "video_prompts.json"
        video_history_file = tmp_path / "video_generation_history.json"
        videos_dir = tmp_path / "final_videos"
        videos_dir.mkdir(parents=True)

        sample_prompts = [
            {
                "source_id": "test_ref_001",
                "source_title": "Biotech Lab",
                "reference_image": "data/final/images/ref_001.jpg",
                "derivative_prompts": [
                    {
                        "id": 1,
                        "concept": "Camera Dolly Lab",
                        "aspect_ratio": "16:9",
                        "prompt": "Cinematic 4K camera track across modern biotechnology laboratory pipetting robots.",
                        "status": "pending",
                    },
                    {
                        "id": 2,
                        "concept": "Vertical Macro Drone",
                        "aspect_ratio": "9:16",
                        "prompt": "Vertical 9:16 drone descent through cleanroom facility with high contrast lighting.",
                        "status": "pending",
                    },
                ],
            }
        ]
        video_prompts_file.write_text(json.dumps(sample_prompts, indent=2), encoding="utf-8")

        mgr = PromptQueueManager(
            video_prompts_file=video_prompts_file,
            video_history_file=video_history_file,
            videos_dir=videos_dir,
            auto_reconcile=False,
        )

        all_v = mgr.get_all_video_prompts()
        assert len(all_v) == 2
        assert all_v[0].status == "pending"
        assert all_v[0].asset_type == "video"
        assert all_v[0].reference_image == "data/final/images/ref_001.jpg"

        pending_v = mgr.get_pending_video_prompts(batch_size=1)
        assert len(pending_v) == 1
        assert pending_v[0].concept == "Camera Dolly Lab"

        # Mark as generated
        saved_video_name = "final_4k_video_test123.mp4"
        marked = mgr.mark_video_prompts_generated(pending_v, saved_videos=[saved_video_name])
        assert marked == 1

        # Check ledger update
        assert video_history_file.exists()
        history_data = json.loads(video_history_file.read_text(encoding="utf-8"))
        assert pending_v[0].prompt_hash in history_data
        assert history_data[pending_v[0].prompt_hash]["video_file"] == saved_video_name

        # Re-query pending
        new_pending = mgr.get_pending_video_prompts(batch_size=10)
        assert len(new_pending) == 1
        assert new_pending[0].concept == "Vertical Macro Drone"


class TestVideoSaveHelper:
    """Test video saving and downloading helper."""

    def test_save_video_from_data_url(self, tmp_path):
        """Simulate saving base64 video data URL."""
        import base64
        dummy_content = b"fake video bytes " * 4000  # > 50KB to pass size validation
        b64_content = base64.b64encode(dummy_content).decode("utf-8")
        data_url = f"data:video/mp4;base64,{b64_content}"

        mock_page = MagicMock()
        saved_name = save_video_from_src(
            mock_page,
            src=data_url,
            destination_dir=tmp_path,
            prefix="test_video_4k"
        )
        assert saved_name is not None
        assert saved_name.startswith("test_video_4k_")
        assert saved_name.endswith(".mp4")
        saved_file = tmp_path / saved_name
        assert saved_file.exists()
        assert saved_file.stat().st_size == len(dummy_content)


class TestDashboardVideoPhase3:
    """Verify Dashboard API accepts Phase 3 Video execution and exposes factory topology."""

    def test_video_status_includes_factory_topology(self):
        """Status endpoint should include RunningHub Video workflow and node topology."""
        status = build_full_video_status()
        assert "factory_config" in status
        f_cfg = status["factory_config"]
        assert f_cfg["workflow_id"] == "2115926169974812674"
        assert f_cfg["input_image_node"] == 164
        assert f_cfg["prompt_node"] == 17
        assert f_cfg["output_video_node"] == 157
        assert f_cfg["account"] == 3

    def test_api_video_run_phase_3_endpoint(self):
        """POST /api/video/run-phase/3 must return success and launch task."""
        client = TestClient(app)
        with patch("src.dashboard.runner.run_video_phase") as mock_run:
            mock_run.return_value = {"success": True, "task_id": "video-phase-3", "message": "Video Phase 3 started"}
            resp = client.post("/api/video/run-phase/3")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["task_id"] == "video-phase-3"
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == 3
            assert kwargs["extra_args"] == ["--account", "3"]
