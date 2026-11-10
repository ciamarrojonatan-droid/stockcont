"""Test Suite for Google Flow Industrial REST API & Automation Engine.

Covers models validation, session auth manager, RPC client, QC curator,
downloader with SHA-256 ledger recording, service orchestration, and FastAPI endpoints.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.integrations.google_flow.api_server import create_app
from src.integrations.google_flow.auth_manager import GoogleFlowAuthManager
from src.integrations.google_flow.config import (
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_DURATIONS,
    SUPPORTED_MODES,
    SUPPORTED_VIDEO_MODELS,
)
from src.integrations.google_flow.downloader import GoogleFlowDownloader
from src.integrations.google_flow.models import (
    AuthStatusResponse,
    GenerationMode,
    GenerationRequest,
    JobStatus,
    JobStatusResponse,
    MediaCandidate,
    ProjectCreateRequest,
    ProjectResponse,
    UpscaleRequest,
)
from src.integrations.google_flow.qc_curator import GoogleFlowQCCurator
from src.integrations.google_flow.rpc_client import GoogleFlowRPCClient
from src.integrations.google_flow.service import GoogleFlowService


# ══════════════════════════════════════════════════════
# 1. Models & Validation Tests
# ══════════════════════════════════════════════════════

def test_project_create_request_validation():
    """Test project creation request schema and aspect ratio constraints."""
    req = ProjectCreateRequest(name="ColdWar_Project", default_aspect_ratio="16:9")
    assert req.name == "ColdWar_Project"
    assert req.default_aspect_ratio == "16:9"

    with pytest.raises(ValueError, match="Invalid aspect_ratio"):
        ProjectCreateRequest(name="Invalid_Project", default_aspect_ratio="99:1")


def test_generation_request_validation():
    """Test validation of prompt, mode, aspect ratio, duration, and variations."""
    req = GenerationRequest(
        prompt="Cinematic 4K shot of Stanislav Petrov in military bunker",
        mode="t2v",
        model="veo-2.0",
        aspect_ratio="16:9",
        duration_seconds=5,
        variations_count=2,
        auto_upscale=True,
        selection_strategy="best_by_ai",
    )
    assert req.duration_seconds == 5
    assert req.variations_count == 2
    assert req.mode == "t2v"
    assert req.model == "veo-3.1-quality"

    # Reject invalid duration
    with pytest.raises(ValueError, match="Invalid duration"):
        GenerationRequest(prompt="Test prompt", duration_seconds=12)

    # Reject invalid variations
    with pytest.raises(ValueError, match="Invalid variations_count"):
        GenerationRequest(prompt="Test prompt", variations_count=3)

    # Reject invalid selection strategy
    with pytest.raises(ValueError, match="Invalid selection_strategy"):
        GenerationRequest(prompt="Test prompt", selection_strategy="random_pick")

    # Target resolution validation
    req_4k = GenerationRequest(prompt="Test prompt", target_resolution="4k")
    assert req_4k.target_resolution == "4k"

    with pytest.raises(ValueError, match="Invalid target_resolution"):
        GenerationRequest(prompt="Test prompt", target_resolution="8k")


# ══════════════════════════════════════════════════════
# 2. Auth Manager Tests
# ══════════════════════════════════════════════════════

def test_auth_manager_unauthenticated_state(tmp_path):
    """Test that empty session directory reports unauthenticated status."""
    auth = GoogleFlowAuthManager(session_dir=tmp_path)
    status = auth.get_status()
    assert not status.authenticated
    assert status.cookies_count == 0
    assert "No session tokens found" in status.message


def test_auth_manager_token_persistence(tmp_path):
    """Test atomic saving and loading of session tokens and cookies."""
    auth = GoogleFlowAuthManager(session_dir=tmp_path)
    tokens = {
        "user_email": "director@darkfactory.com",
        "headers": {
            "Authorization": "Bearer test_oauth_token_123",
            "Cookie": "__Secure-1PSID=valid_cookie_value;",
        },
        "cookies": [
            {"name": "__Secure-1PSID", "value": "valid_cookie_value"},
            {"name": "SAPISID", "value": "valid_sapisid_value"},
        ],
    }
    auth.save_tokens(tokens)

    loaded = auth.get_persisted_tokens()
    assert loaded is not None
    assert loaded["user_email"] == "director@darkfactory.com"

    status = auth.get_status()
    assert status.authenticated
    assert status.cookies_count == 2
    assert status.user_email == "director@darkfactory.com"

    headers = auth.get_auth_headers()
    assert headers["Authorization"] == "Bearer test_oauth_token_123"


# ══════════════════════════════════════════════════════
# 3. RPC Client & Candidate Generation Tests
# ══════════════════════════════════════════════════════

def test_rpc_client_create_project(tmp_path):
    """Test project creation via RPC client."""
    async def _run():
        auth = GoogleFlowAuthManager(session_dir=tmp_path)
        client = GoogleFlowRPCClient(auth_manager=auth)

        proj = await client.create_project(name="Stanislav_Petrov_Doc", default_aspect_ratio="16:9")
        assert proj.project_id.startswith("flow_proj_")
        assert proj.name == "Stanislav_Petrov_Doc"
        assert "project=" in proj.flow_url

    asyncio.run(_run())


def test_rpc_client_submit_generation_and_poll(tmp_path):
    """Test generation submission and status polling."""
    async def _run():
        auth = GoogleFlowAuthManager(session_dir=tmp_path)
        client = GoogleFlowRPCClient(auth_manager=auth)

        req = GenerationRequest(
            prompt="Cinematic drone descent over frozen Siberian bunker",
            mode="t2v",
            model="veo-2.0",
            aspect_ratio="16:9",
            duration_seconds=5,
            variations_count=2,
        )

        gen_id, candidates = await client.submit_generation("proj_123", req)
        assert gen_id.startswith("gen_")
        assert len(candidates) == 2
        assert candidates[0].candidate_id.endswith("_cand_1")
        assert candidates[1].candidate_id.endswith("_cand_2")

        poll = await client.poll_generation_status("proj_123", gen_id)
        assert poll["status"] == "COMPLETED"
        assert poll["progressPercent"] == 100.0

    asyncio.run(_run())


# ══════════════════════════════════════════════════════
# 4. QC Curator Tests
# ══════════════════════════════════════════════════════

def test_qc_curator_strategies():
    """Test selection strategies (first, upscale_all, best_by_ai)."""
    curator = GoogleFlowQCCurator()
    cands = [
        MediaCandidate(candidate_id="cand_1", variation_index=0),
        MediaCandidate(candidate_id="cand_2", variation_index=1),
    ]

    # Strategy: first
    first_pick = curator.select_candidates_for_upscale(cands, strategy="first")
    assert len(first_pick) == 1
    assert first_pick[0].candidate_id == "cand_1"
    assert first_pick[0].is_winner

    # Strategy: upscale_all
    all_picks = curator.select_candidates_for_upscale(cands, strategy="upscale_all")
    assert len(all_picks) == 2
    assert all(c.is_winner for c in all_picks)

    # Strategy: best_by_ai
    winner = curator.select_candidates_for_upscale(cands, strategy="best_by_ai")
    assert len(winner) == 1
    assert winner[0].is_winner
    assert winner[0].qc_score is not None


# ══════════════════════════════════════════════════════
# 5. Downloader & SHA-256 Ledger Tests
# ══════════════════════════════════════════════════════

def test_downloader_and_ledger_recording(tmp_path):
    """Test file download, SHA-256 calculation, and ledger write."""
    async def _run():
        videos_dir = tmp_path / "videos"
        images_dir = tmp_path / "images"
        ledger_file = tmp_path / "ledger.json"

        downloader = GoogleFlowDownloader(
            videos_dir=videos_dir,
            images_dir=images_dir,
            ledger_file=ledger_file,
        )

        cand = MediaCandidate(
            candidate_id="test_cand_99",
            preview_url="https://labs.google/flow/previews/test.mp4",
            media_type="video",
        )

        saved_path = await downloader.download_candidate(
            candidate=cand,
            prompt="Cinematic shot in nuclear silo",
            project_id="proj_alpha",
            job_id="job_omega",
            strip_audio=False,
        )

        assert saved_path is not None
        assert saved_path.exists()
        assert cand.sha256 is not None
        assert len(cand.sha256) == 64

        # Verify ledger entry
        with open(ledger_file, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        assert cand.sha256 in ledger
        entry = ledger[cand.sha256]
        assert entry["candidate_id"] == "test_cand_99"
        assert entry["job_id"] == "job_omega"
        assert entry["prompt"] == "Cinematic shot in nuclear silo"

    asyncio.run(_run())


# ══════════════════════════════════════════════════════
# 6. Service & End-to-End Orchestration Tests
# ══════════════════════════════════════════════════════

def test_service_enqueue_and_execution(tmp_path):
    """Test full asynchronous execution of a generation job in service."""
    async def _run():
        auth = GoogleFlowAuthManager(session_dir=tmp_path / "session")
        downloader = GoogleFlowDownloader(
            videos_dir=tmp_path / "videos",
            images_dir=tmp_path / "images",
            ledger_file=tmp_path / "ledger.json",
        )
        service = GoogleFlowService(auth_manager=auth, downloader=downloader)

        req = GenerationRequest(
            prompt="Cold War emergency alarm blaring in Soviet underground installation",
            mode="t2v",
            model="veo-2.0",
            aspect_ratio="16:9",
            duration_seconds=5,
            variations_count=1,
            auto_upscale=True,
            project_name="Petrov_Test_Batch",
        )

        job = await service.enqueue_generation(req)
        assert job.status in [JobStatus.QUEUED, JobStatus.CREATING_PROJECT]

        # Wait for background pipeline to complete
        for _ in range(80):
            await asyncio.sleep(0.1)
            curr = service.get_job(job.job_id)
            if curr and curr.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                break

        finished = service.get_job(job.job_id)
        assert finished is not None
        assert finished.status == JobStatus.COMPLETED
        assert finished.progress_percent == 100.0
        assert len(finished.final_output_paths) == 1
        assert Path(finished.final_output_paths[0]).exists()

    asyncio.run(_run())


# ══════════════════════════════════════════════════════
# 7. FastAPI Endpoints & Swagger Tests
# ══════════════════════════════════════════════════════

def test_fastapi_endpoints(tmp_path):
    """Test REST API endpoints using FastAPI TestClient."""
    auth = GoogleFlowAuthManager(session_dir=tmp_path / "session")
    downloader = GoogleFlowDownloader(
        videos_dir=tmp_path / "videos",
        images_dir=tmp_path / "images",
        ledger_file=tmp_path / "ledger.json",
    )
    service = GoogleFlowService(auth_manager=auth, downloader=downloader)
    app = create_app(service=service)
    client = TestClient(app)

    # 1. Healthcheck
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "veo-2.0" in data["supported_video_models"]

    # 2. Auth status
    res = client.get("/api/v1/auth/status")
    assert res.status_code == 200
    assert "authenticated" in res.json()

    # 3. Create Project
    res = client.post("/api/v1/projects", json={"name": "API_Test_Project", "default_aspect_ratio": "16:9"})
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["name"] == "API_Test_Project"

    # 4. Enqueue Generation
    gen_payload = {
        "prompt": "Cinematic shot of deep space satellite telemetry",
        "mode": "t2v",
        "model": "veo-2.0",
        "aspect_ratio": "16:9",
        "duration_seconds": 5,
        "variations_count": 1,
        "auto_upscale": True,
    }
    res = client.post("/api/v1/generate", json=gen_payload)
    assert res.status_code == 202
    job_data = res.json()
    job_id = job_data["job_id"]
    assert job_id.startswith("job_flow_")

    # 5. Poll Job Status
    res = client.get(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    assert res.json()["job_id"] == job_id

    # 6. List Jobs
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 7. Non-existent job returns 404
    res = client.get("/api/v1/jobs/non_existent_job_123")
    assert res.status_code == 404

    # 8. Query Models Capabilities
    res = client.get("/api/v1/models")
    assert res.status_code == 200
    models_data = res.json()
    assert "veo-2.0" in models_data["video_models"]
    assert any(r["ratio"] == "16:9" for r in models_data["aspect_ratios"])

    # 9. Query Ledger History
    res = client.get("/api/v1/history")
    assert res.status_code == 200
    assert isinstance(res.json(), dict)
