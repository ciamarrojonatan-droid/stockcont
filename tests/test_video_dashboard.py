"""Unit and integration tests for the dedicated Video Dashboard (http://localhost:8501/video)."""

import json
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.dashboard.app import app
from src.dashboard import readers, runner


@pytest.fixture
def client():
    return TestClient(app)


def test_video_page_served(client):
    """Test that GET /video serves the dedicated video SPA successfully."""
    response = client.get("/video")
    assert response.status_code == 200
    assert "StockCont Cinema" in response.text
    assert "Video & Motion Architecture" in response.text
    assert "text/html" in response.headers["content-type"]


def test_video_status_endpoint(client):
    """Test GET /api/video/status returns video KPIs, phases, and agencies."""
    response = client.get("/api/video/status")
    assert response.status_code == 200
    data = response.json()

    assert "kpis" in data
    assert "phases" in data
    assert "agencies" in data

    kpis = data["kpis"]
    assert "prompts_total" in kpis
    assert "queue_pending" in kpis
    assert "queue_generated" in kpis
    assert "videos_total" in kpis
    assert "videos_cataloged" in kpis
    assert "videos_distributed" in kpis

    # Verify 5 video phases
    assert len(data["phases"]) == 5
    phase_names = [p["name"] for p in data["phases"]]
    assert any("Olheiro" in name for name in phase_names)
    assert any("Diretor" in name for name in phase_names)
    assert any("Fábrica" in name for name in phase_names)
    assert any("Catalogador" in name for name in phase_names)
    assert any("Distribuidor" in name for name in phase_names)

    # Verify video agencies
    agencies = data["agencies"]
    agency_keys = [a["key"] for a in agencies]
    assert "adobe" in agency_keys
    assert "pond5" in agency_keys


def test_video_prompts_endpoint(client, tmp_path, monkeypatch):
    """Test GET /api/video/prompts and filtering."""
    # Mock video prompts file
    sample_prompts = [
        {
            "system_version": "1.0-video",
            "source_id": "test_asset_01",
            "source_title": "Biotech Lab",
            "created_at": 1700000000,
            "derivative_prompts": [
                {
                    "id": 1,
                    "concept": "Biotech Dolly In",
                    "aspect_ratio": "16:9",
                    "format_type": "landscape_broll",
                    "target_duration_sec": 8,
                    "target_fps": 24,
                    "camera_motion": "smooth_dolly_in",
                    "copy_space_zone": "left_third",
                    "prompt": "Cinematic 4K shot of biotech lab dolly in...",
                    "status": "pending"
                },
                {
                    "id": 2,
                    "concept": "Biotech Mobile Story",
                    "aspect_ratio": "9:16",
                    "format_type": "vertical_reels",
                    "target_duration_sec": 8,
                    "target_fps": 24,
                    "camera_motion": "tilt_down",
                    "copy_space_zone": "upper_half",
                    "prompt": "Vertical 9:16 social footage of lab scientist...",
                    "status": "generated"
                }
            ]
        }
    ]

    mock_prompts_file = tmp_path / "video_prompts.json"
    mock_prompts_file.write_text(json.dumps(sample_prompts), encoding="utf-8")
    monkeypatch.setattr(readers, "VIDEO_PROMPTS_FILE", mock_prompts_file)

    # All prompts
    res = client.get("/api/video/prompts")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Filter aspect ratio 9:16
    res_vertical = client.get("/api/video/prompts?aspect=9:16")
    assert res_vertical.status_code == 200
    assert len(res_vertical.json()["items"]) == 1
    assert res_vertical.json()["items"][0]["aspect_ratio"] == "9:16"

    # Filter status pending
    res_pending = client.get("/api/video/prompts?filter=pending")
    assert res_pending.status_code == 200
    assert len(res_pending.json()["items"]) == 1
    assert res_pending.json()["items"][0]["status"] == "pending"


def test_video_prompts_stats(client, tmp_path, monkeypatch):
    """Test GET /api/video/prompts/stats."""
    mock_prompts_file = tmp_path / "video_prompts.json"
    sample_prompts = [
        {
            "source_id": "test_01",
            "derivative_prompts": [
                {"id": 1, "prompt": "Prompt 1 text", "status": "pending"},
                {"id": 2, "prompt": "Prompt 2 text", "status": "generated"},
            ]
        }
    ]
    mock_prompts_file.write_text(json.dumps(sample_prompts), encoding="utf-8")
    monkeypatch.setattr(readers, "VIDEO_PROMPTS_FILE", mock_prompts_file)

    res = client.get("/api/video/prompts/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total"] == 2
    assert stats["pending"] == 1
    assert stats["generated"] == 1
    assert stats["percent"] == 50.0


def test_video_prompts_mark_endpoints(client, tmp_path, monkeypatch):
    """Test marking video prompts as generated and pending."""
    mock_prompts_file = tmp_path / "video_prompts.json"
    sample_prompts = [
        {
            "source_id": "test_01",
            "derivative_prompts": [
                {"id": 1, "prompt": "Special video prompt to test", "status": "pending"},
            ]
        }
    ]
    mock_prompts_file.write_text(json.dumps(sample_prompts), encoding="utf-8")
    monkeypatch.setattr(readers, "VIDEO_PROMPTS_FILE", mock_prompts_file)

    # Mark all pending as generated
    res = client.post("/api/video/prompts/mark-generated", json={"all_pending": True})
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["marked_count"] == 1

    # Check updated status
    stats = client.get("/api/video/prompts/stats").json()
    assert stats["generated"] == 1
    assert stats["pending"] == 0

    # Mark all generated back to pending
    res_pend = client.post("/api/video/prompts/mark-pending", json={"all_generated": True})
    assert res_pend.status_code == 200
    assert res_pend.json()["success"] is True

    stats_after = client.get("/api/video/prompts/stats").json()
    assert stats_after["pending"] == 1
    assert stats_after["generated"] == 0


def test_video_items_endpoint(client):
    """Test GET /api/video/items."""
    res = client.get("/api/video/items")
    assert res.status_code == 200
    data = res.json()
    assert "videos" in data
    assert "total" in data
    assert isinstance(data["videos"], list)


def test_video_matrix_endpoint(client):
    """Test GET /api/video/matrix."""
    res = client.get("/api/video/matrix")
    assert res.status_code == 200
    data = res.json()
    assert "agencies" in data
    assert "rows" in data
    assert "total_videos" in data


def test_video_reference_images_endpoint(client):
    """Test GET /api/video/reference-images returns 8K images for I2V."""
    res = client.get("/api/video/reference-images")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        assert "filename" in first
        assert "stem" in first
        assert "has_video_prompts" in first


def test_video_run_phase_endpoint(client, monkeypatch):
    """Test POST /api/video/run-phase/2 triggers background task."""
    async def mock_run_video_phase(phase, extra_args=None):
        return {"success": True, "message": f"Video Phase {phase} started mock", "task_id": f"mock-video-{phase}"}

    monkeypatch.setattr(runner, "run_video_phase", mock_run_video_phase)

    res = client.post("/api/video/run-phase/2?max_items=3")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "mock-video-2" in data["task_id"]
