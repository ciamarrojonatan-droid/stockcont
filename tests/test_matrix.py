"""Automated tests for Distribution Matrix reader and API endpoints."""

import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.dashboard.app import app
from src.dashboard import readers


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def isolated_matrix_env(tmp_path, monkeypatch):
    """Set up a clean temporary environment for testing matrix operations."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()

    # Create dummy images
    (images_dir / "img1.jpg").write_text("fake jpg 1")
    (images_dir / "img2.jpg").write_text("fake jpg 2")

    upload_history_file = processed_dir / "upload_history.json"
    csv_file = processed_dir / "adobe_stock_upload.csv"
    csv_file.write_text("Filename,Title,Keywords,Category\nimg1.jpg,Sample Title 1,test kw,3\n")

    monkeypatch.setattr(readers, "FINAL_IMAGES_DIR", images_dir)
    monkeypatch.setattr(readers, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(readers, "UPLOAD_HISTORY_FILE", upload_history_file)
    monkeypatch.setattr(readers, "CSV_FILE", csv_file)
    monkeypatch.setenv("GOOGLE_DRIVE_LOCAL_PATH", "")

    return {
        "images_dir": images_dir,
        "processed_dir": processed_dir,
        "upload_history_file": upload_history_file,
    }


def test_get_distribution_matrix_basic(isolated_matrix_env):
    """Verify distribution matrix structure and defaults."""
    matrix = readers.get_distribution_matrix()
    assert "summary" in matrix
    assert "agencies" in matrix
    assert "items" in matrix
    assert matrix["summary"]["total_images"] == 2
    assert matrix["summary"]["total_uploads"] == 0

    item1 = next(it for it in matrix["items"] if it["filename"] == "img1.jpg")
    assert item1["title"] == "Sample Title 1"
    assert item1["is_cataloged"] is True
    assert "dreamstime" in item1["platforms"]
    assert item1["platforms"]["dreamstime"]["uploaded"] is False


def test_update_matrix_cell_and_toggle(isolated_matrix_env):
    """Test updating and toggling individual matrix cells."""
    # Mark as uploaded
    ok = readers.update_matrix_cell("img1.jpg", "dreamstime", True)
    assert ok is True

    matrix = readers.get_distribution_matrix()
    item1 = next(it for it in matrix["items"] if it["filename"] == "img1.jpg")
    assert item1["platforms"]["dreamstime"]["uploaded"] is True
    assert item1["uploaded_count"] == 1
    assert matrix["summary"]["total_uploads"] == 1

    # Unmark
    ok2 = readers.update_matrix_cell("img1.jpg", "dreamstime", False)
    assert ok2 is True

    matrix2 = readers.get_distribution_matrix()
    item1_after = next(it for it in matrix2["items"] if it["filename"] == "img1.jpg")
    assert item1_after["platforms"]["dreamstime"]["uploaded"] is False
    assert matrix2["summary"]["total_uploads"] == 0


def test_batch_update_matrix_agency(isolated_matrix_env):
    """Test batch marking and unmarking a whole agency column."""
    count = readers.batch_update_matrix_agency("123rf", "mark_all")
    assert count == 2

    matrix = readers.get_distribution_matrix()
    assert matrix["summary"]["total_uploads"] == 2
    for it in matrix["items"]:
        assert it["platforms"]["123rf"]["uploaded"] is True

    # Batch unmark
    unmark_count = readers.batch_update_matrix_agency("123rf", "unmark_all")
    assert unmark_count == 2

    matrix_after = readers.get_distribution_matrix()
    assert matrix_after["summary"]["total_uploads"] == 0


def test_api_matrix_endpoints(client, isolated_matrix_env):
    """Test FastAPI /api/matrix REST endpoints."""
    # 1. GET /api/matrix
    res = client.get("/api/matrix")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_images"] == 2

    # 2. POST /api/matrix/toggle
    toggle_res = client.post("/api/matrix/toggle", json={
        "filename": "img1.jpg",
        "agency": "dreamstime",
        "uploaded": True,
    })
    assert toggle_res.status_code == 200
    assert toggle_res.json()["success"] is True

    # Verify change reflected in GET
    data_after = client.get("/api/matrix").json()
    assert data_after["summary"]["total_uploads"] == 1

    # 3. POST /api/matrix/batch-set
    batch_res = client.post("/api/matrix/batch-set", json={
        "agency": "pond5",
        "action": "mark_all",
    })
    assert batch_res.status_code == 200
    assert batch_res.json()["updated_count"] == 2


def test_image_path_traversal_protection(client):
    """Test security against directory traversal attacks."""
    res = client.get("/api/images/..%2F..%2Fmain.py")
    assert res.status_code in (400, 404, 422)


def test_image_extension_filtering(client):
    """Verify that non-image file extensions are rejected with HTTP 400."""
    res = client.get("/api/images/secrets.env")
    assert res.status_code == 400
    assert "não permitido" in res.json().get("detail", "")


def test_invalid_batch_action_rejected(client):
    """Verify that Pydantic rejects invalid actions with HTTP 422."""
    res = client.post("/api/matrix/batch-set", json={
        "agency": "pond5",
        "action": "invalid_action_xyz",
    })
    assert res.status_code == 422


def test_safe_recovery_on_corrupt_history(isolated_matrix_env):
    """Verify that corrupt JSON in history file causes write abort to protect data."""
    # Write invalid JSON into upload_history_file
    isolated_matrix_env["upload_history_file"].write_text("{CORRUPT_JSON_CONTENT")
    
    ok = readers.update_matrix_cell("img1.jpg", "dreamstime", True)
    assert ok is False
    # Verify the corrupt file was not clobbered with empty dict
    assert "{CORRUPT_JSON_CONTENT" in isolated_matrix_env["upload_history_file"].read_text()
