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
    upload_image_to_node,
    upload_zip_to_node,
    dismiss_runninghub_popups,
    click_runninghub_execute,
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
        assert cfg.get("upload_wait_sec") == 30

    def test_account_3_upload_wait_sec_default(self):
        """Account 3 must default to 30 seconds wait for Node #164 Load Image upload."""
        cfg = get_account_config(3)
        assert cfg.get("upload_wait_sec") == 30

    def test_account_3_execute_mode_is_lite_plus(self):
        """Account 3 must default to 'lite_plus' execute mode (the middle button)."""
        cfg = get_account_config(3)
        assert cfg.get("execute_mode") == "lite_plus" 

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


class TestNodeUploadRobustness:
    """Verify robust multi-tier upload and anti-validation failure mechanisms for ComfyUI nodes."""

    def test_upload_image_to_node_api_success(self, tmp_path):
        """Test upload_image_to_node succeeds when ComfyUI native API returns success."""
        dummy_img = tmp_path / "reference_test.jpg"
        dummy_img.write_bytes(b"dummy image bytes content 12345")

        mock_page = MagicMock()
        mock_frame = MagicMock()
        mock_page.main_frame = mock_frame
        mock_page.frames = [mock_frame]

        # Simulate ComfyUI API success
        mock_frame.evaluate.return_value = {
            "apiSuccess": True,
            "uploadedName": "reference_test.jpg",
            "backendConfirmed": True,
            "nodeConfigured": True,
            "log": ["Upload via app.api.uploadImage com sucesso"],
            "errors": [],
        }

        res = upload_image_to_node(mock_page, mock_frame, node_id=164, image_path=dummy_img)
        assert res is True
        mock_frame.evaluate.assert_called_once()

    def test_upload_image_to_node_file_chooser_fallback(self, tmp_path):
        """Test upload_image_to_node falls back to Playwright FileChooser if API evaluate returns no upload."""
        dummy_img = tmp_path / "reference_test_fc.jpg"
        dummy_img.write_bytes(b"dummy image bytes for file chooser")

        mock_page = MagicMock()
        mock_frame = MagicMock()
        mock_page.main_frame = mock_frame
        mock_page.frames = [mock_frame]

        # First evaluate (API upload) fails to upload
        # Second evaluate (button_coords) returns coordinates
        mock_frame.evaluate.side_effect = [
            {"apiSuccess": False, "nodeConfigured": False, "errors": ["upload failed"]},
            {"x": 450, "y": 320},
        ]

        mock_fc = MagicMock()
        mock_fc_info = MagicMock()
        mock_fc_info.value = mock_fc
        mock_page.expect_file_chooser.return_value.__enter__.return_value = mock_fc_info

        res = upload_image_to_node(mock_page, mock_frame, node_id=164, image_path=dummy_img)
        assert res is True
        mock_fc.set_files.assert_called_once_with(str(dummy_img))

    def test_upload_zip_to_node_api_success(self, tmp_path):
        """Test upload_zip_to_node succeeds with ZIP API upload and ComfyUI options synchronization."""
        dummy_zip = tmp_path / "approved_batch.zip"
        dummy_zip.write_bytes(b"PK fake zip content for testing 1234")

        mock_page = MagicMock()
        mock_frame = MagicMock()
        mock_page.main_frame = mock_frame
        mock_page.frames = [mock_frame]

        mock_frame.evaluate.return_value = {
            "apiSuccess": True,
            "uploadedName": "approved_batch.zip",
            "backendConfirmed": True,
            "nodeConfigured": True,
            "log": ["ZIP upload via app.api.uploadImage com sucesso"],
            "errors": [],
        }

        res = upload_zip_to_node(mock_page, mock_frame, node_id=5, zip_path=dummy_zip)
        assert res is True
        mock_frame.evaluate.assert_called_once()

    def test_dismiss_runninghub_popups_handles_validation_error(self):
        """Verify dismiss_runninghub_popups detects and closes ComfyUI validation failure popups."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_btn = MagicMock()
        mock_btn.is_visible.return_value = True
        mock_locator.nth.return_value = mock_btn

        mock_page.locator.return_value = mock_locator
        mock_page.frames = []

        dismissed = dismiss_runninghub_popups(mock_page)
        assert dismissed is True
        mock_btn.click.assert_called()

    def test_click_runninghub_execute_lite_plus_evaluate(self):
        """Verify click_runninghub_execute uses DOM evaluate to target Lite/Plus and triggers mouse click."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = {
            "success": True,
            "method": "middle_of_three_top_bar",
            "x": 725.0,
            "y": 48.0
        }

        res = click_runninghub_execute(mock_page, mode="lite_plus")
        assert res is True
        mock_page.evaluate.assert_called_once()
        mock_page.mouse.click.assert_called_once_with(725.0, 48.0)

    def test_click_runninghub_execute_lite_plus_fallback_middle_button(self):
        """Verify fallback selects the MIDDLE button (index 1) when evaluate fails."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = {"success": False}

        # Sibling/ancestor selectors return no matches
        mock_locator = MagicMock()
        mock_locator.count.return_value = 0

        # But 'button:has-text("Executar")' returns 3 buttons
        mock_exec_locator = MagicMock()
        mock_exec_locator.count.return_value = 3
        mock_btn_left = MagicMock()
        mock_btn_mid = MagicMock()
        mock_btn_right = MagicMock()
        mock_btn_mid.is_visible.return_value = True

        def locator_side_effect(sel):
            if "has-text('Executar')" in sel:
                return mock_exec_locator
            return mock_locator

        mock_page.locator.side_effect = locator_side_effect
        mock_exec_locator.nth.side_effect = lambda idx: [mock_btn_left, mock_btn_mid, mock_btn_right][idx]

        res = click_runninghub_execute(mock_page, mode="lite_plus")
        assert res is True
        # Must click the middle button (index 1), NEVER index 0!
        mock_btn_mid.click.assert_called_once()
        mock_btn_left.click.assert_not_called()
        mock_btn_right.click.assert_not_called()


    def test_get_node_videos_ignores_pre_existing_videos(self):
        """get_node_videos must extract strictly from node 157 and ignore data-pre-existing videos."""
        mock_page = MagicMock()
        mock_frame = MagicMock()
        mock_frame.evaluate.return_value = ["/view?filename=new_render_4k.mp4&type=output"]
        mock_page.frames = [mock_frame]

        vids = get_node_videos(mock_page, 157)
        assert len(vids) == 1
        assert "new_render_4k.mp4" in vids[0]
        mock_frame.evaluate.assert_called_once()


    def test_optimize_reference_image_for_video_resizes_8k(self, tmp_path):
        """optimize_reference_image_for_video must downscale 8K images to <= 1920x1080 multiples of 8."""
        from PIL import Image
        from src.factory.runninghub_bot import optimize_reference_image_for_video

        # Create synthetic 8K image
        img_8k = tmp_path / "huge_8k.jpg"
        im = Image.new("RGB", (8192, 6144), color=(100, 150, 200))
        im.save(img_8k, "JPEG")

        optimized = optimize_reference_image_for_video(img_8k, aspect_ratio="16:9")
        assert optimized.exists()
        assert optimized != img_8k

        with Image.open(optimized) as opt_im:
            w, h = opt_im.size
            assert w <= 1920
            assert h <= 1080
            assert w % 8 == 0
            assert h % 8 == 0

    def test_optimize_reference_image_for_video_keeps_1080p(self, tmp_path):
        """optimize_reference_image_for_video must return original if already <= 1920."""
        from PIL import Image
        from src.factory.runninghub_bot import optimize_reference_image_for_video

        img_hd = tmp_path / "normal_1080p.jpg"
        im = Image.new("RGB", (1920, 1080), color=(50, 50, 50))
        im.save(img_hd, "JPEG")

        res = optimize_reference_image_for_video(img_hd, aspect_ratio="16:9")
        assert res == img_hd

    def test_click_runninghub_execute_ultra_mode(self):
        """Verify click_runninghub_execute with mode='ultra' targets the third button (index 2)."""
        from unittest.mock import MagicMock
        from src.factory.runninghub_bot import click_runninghub_execute

        mock_page = MagicMock()
        mock_page.evaluate.return_value = {"success": False}

        mock_locator = MagicMock()
        mock_locator.count.return_value = 0

        mock_exec_locator = MagicMock()
        mock_exec_locator.count.return_value = 3
        mock_btn_0 = MagicMock()
        mock_btn_1 = MagicMock()
        mock_btn_2 = MagicMock()
        mock_btn_2.is_visible.return_value = True

        def locator_side_effect(sel):
            if "has-text('Executar')" in sel:
                return mock_exec_locator
            return mock_locator

        mock_page.locator.side_effect = locator_side_effect
        mock_exec_locator.nth.side_effect = lambda idx: [mock_btn_0, mock_btn_1, mock_btn_2][idx]

        res = click_runninghub_execute(mock_page, mode="ultra")
        assert res is True
        mock_btn_2.click.assert_called_once()
        mock_btn_0.click.assert_not_called()
        mock_btn_1.click.assert_not_called()
