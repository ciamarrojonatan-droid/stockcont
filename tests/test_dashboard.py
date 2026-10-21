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


def test_index_page(client):
    """Test that the SPA root page is served successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "StockCont" in response.text
    assert "text/html" in response.headers["content-type"]


def test_api_status_endpoint(client):
    """Test that /api/status returns all pipeline KPIs and phase structures."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "phases" in data
    assert "agencies" in data
    assert "backup" in data

    # Verify KPI keys
    kpis = data["kpis"]
    assert "trends" in kpis
    assert "prompts_total" in kpis
    assert "queue_generated" in kpis
    assert "final_images" in kpis
    assert "cataloged" in kpis
    assert "distributed" in kpis

    # Verify 5 phases are listed
    assert len(data["phases"]) == 5
    phase_names = [p["name"] for p in data["phases"]]
    assert "Scout" in phase_names
    assert "Director" in phase_names
    assert "Factory" in phase_names
    assert "Cataloger" in phase_names
    assert "Distributor" in phase_names


def test_api_prompts_endpoint(client):
    """Test /api/prompts listing and filtering."""
    response = client.get("/api/prompts?per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)


def test_api_prompts_stats_endpoint(client):
    """Test /api/prompts/stats counters."""
    response = client.get("/api/prompts/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "generated" in data
    assert "pending" in data
    assert "progress_percent" in data


def test_api_images_endpoint(client):
    """Test /api/images listing."""
    response = client.get("/api/images")
    assert response.status_code == 200
    data = response.json()
    assert "images" in data
    assert "total" in data
    assert "cataloged" in data
    assert "uncataloged" in data
    assert isinstance(data["images"], list)


def test_api_agencies_endpoint(client):
    """Test /api/agencies lists the 7 supported stock agencies."""
    response = client.get("/api/agencies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    agency_keys = [a["key"] for a in data]
    for expected in ["adobe", "freepik", "dreamstime", "pond5", "alamy", "vecteezy", "123rf"]:
        assert expected in agency_keys


def test_api_timeline_endpoint(client):
    """Test /api/timeline returns chronological events."""
    response = client.get("/api/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_backup_endpoint(client):
    """Test /api/backup returns backup status."""
    response = client.get("/api/backup")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "synced_count" in data


def test_api_tasks_endpoint(client):
    """Test /api/tasks returns running tasks dict."""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_run_phase_invalid(client):
    """Test validation of phase range."""
    response = client.post("/api/run-phase/99")
    assert response.status_code == 400
