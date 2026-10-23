import asyncio
from collections import deque
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


def test_api_task_detail_not_found(client):
    """Test /api/tasks/{task_id} returns 404 for non-existent task."""
    response = client.get("/api/tasks/non-existent-task-id")
    assert response.status_code == 404


def test_api_task_lifecycle(client):
    """Test task recording, retrieval, and status reporting."""
    runner._task_records["test-task-1"] = {
        "task_id": "test-task-1",
        "phase": 1,
        "status": "completed",
        "returncode": 0,
        "started_at": "2026-10-22T20:00:00Z",
        "completed_at": "2026-10-22T20:01:00Z",
        "logs": ["line 1", "line 2"],
        "last_log": "line 2",
    }

    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "test-task-1" in data
    assert data["test-task-1"]["status"] == "completed"
    assert data["test-task-1"]["returncode"] == 0
    assert data["test-task-1"]["logs"] == ["line 1", "line 2"]
    assert data["test-task-1"]["last_log"] == "line 2"

    detail_res = client.get("/api/tasks/test-task-1")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["task_id"] == "test-task-1"
    assert detail["status"] == "completed"

    stop_res = client.post("/api/tasks/test-task-1/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["task_id"] == "test-task-1"


def test_api_tasks_cleanup(client):
    """Test /api/tasks/cleanup endpoint returns count of killed processes."""
    response = client.post("/api/tasks/cleanup")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "killed_count" in data
    # In clean state with no orphan processes, killed_count must be 0
    assert data["killed_count"] == 0


def test_cleanup_orphan_no_false_positive():
    """Verify cleanup_orphan_processes does not self-match or kill PowerShell/active tasks."""
    count = runner.cleanup_orphan_processes()
    assert count == 0


def test_terminate_task_updates_record():
    """Verify terminate_task marks task record failed and sets informative last_log."""
    from unittest.mock import MagicMock, patch

    mock_proc = MagicMock()
    mock_proc.returncode = None
    mock_proc.pid = 99998

    task_key = "test-terminate-task"
    runner._running_tasks[task_key] = mock_proc
    runner._task_records[task_key] = {
        "task_id": task_key,
        "phase": 1,
        "status": "running",
        "returncode": None,
        "started_at": "2026-10-22T20:00:00Z",
        "completed_at": None,
        "logs": deque(maxlen=100),
        "last_log": "Running...",
    }

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        success = runner.terminate_task(task_key)
        assert success is True
        record = runner.get_task(task_key)
        assert record["status"] == "failed"
        assert "Process terminated by user" in record["last_log"]

    runner._running_tasks.pop(task_key, None)
    runner._task_records.pop(task_key, None)


def test_runner_streaming_mock():
    """Verify that _stream_pipe captures lines into the task record in real-time."""
    async def _test():
        task_key = "test-stream-key"
        runner._task_records[task_key] = {
            "task_id": task_key,
            "phase": 2,
            "status": "running",
            "returncode": None,
            "started_at": "2026-10-22T20:00:00Z",
            "completed_at": None,
            "logs": deque(maxlen=100),
            "last_log": "",
        }

        reader = asyncio.StreamReader()
        reader.feed_data(b"Real-time log line 1\nReal-time log line 2\n")
        reader.feed_eof()

        await runner._stream_pipe(reader, task_key, is_stderr=False)

        record = runner.get_task(task_key)
        assert record is not None
        assert "Real-time log line 1" in record["logs"]
        assert "Real-time log line 2" in record["logs"]
        assert record["last_log"] == "Real-time log line 2"

    asyncio.run(_test())


def test_run_phase_mocked(client):
    """Test run_phase launches subprocess and prevents duplicate execution while running."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_proc = MagicMock()
    mock_proc.returncode = None
    mock_proc.pid = 99999
    mock_proc.stdout = None
    mock_proc.stderr = None

    async def _test():
        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)) as mock_exec:
            runner._running_tasks.pop("phase-2", None)
            runner._task_records.pop("phase-2", None)

            res = await runner.run_phase(2)
            assert res["success"] is True
            assert res["task_id"] == "phase-2"

            # Check that env variables were set for UTF-8 and unbuffered output
            called_kwargs = mock_exec.call_args[1]
            called_env = called_kwargs.get("env", {})
            assert called_env.get("PYTHONUNBUFFERED") == "1"
            assert called_env.get("PYTHONIOENCODING") == "utf-8"
            assert called_env.get("PYTHONUTF8") == "1"

            # Check already running prevention while process is active
            res2 = await runner.run_phase(2)
            assert res2["success"] is False
            assert "already running" in res2["message"]

            # Clean up
            runner._running_tasks.pop("phase-2", None)
            runner._task_records.pop("phase-2", None)

    asyncio.run(_test())


def test_run_phase_platform_and_query_endpoints(client):
    """Test that platform, query, and mode parameters are properly routed."""
    from unittest.mock import AsyncMock, patch

    with patch("src.dashboard.runner.run_phase", new=AsyncMock(return_value={"success": True, "task_id": "phase-5"})) as mock_run:
        res = client.post("/api/run-phase/5?platform=adobe")
        assert res.status_code == 200
        mock_run.assert_called_once_with(5, extra_args=["--platform", "adobe"])

    with patch("src.dashboard.runner.run_phase", new=AsyncMock(return_value={"success": True, "task_id": "phase-1"})) as mock_run:
        res = client.post("/api/run-phase/1?query=nature&mode=search")
        assert res.status_code == 200
        mock_run.assert_called_once_with(1, extra_args=["--query", "nature", "--mode", "search"])



def test_api_mark_prompts_generated_endpoints(client):
    """Test marking prompts as generated via /api/prompts/mark-generated."""
    from unittest.mock import patch, MagicMock

    with patch("src.factory.prompt_queue.PromptQueueManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.mark_by_hashes.return_value = 3
        mock_mgr.mark_all_pending_generated.return_value = 10
        mock_mgr_cls.return_value = mock_mgr

        # By hashes
        res = client.post("/api/prompts/mark-generated", json={"hashes": ["hash1", "hash2", "hash3"]})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["marked_count"] == 3
        mock_mgr.mark_by_hashes.assert_called_once_with(["hash1", "hash2", "hash3"])

        # All pending
        res2 = client.post("/api/prompts/mark-generated", json={"all_pending": True})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["success"] is True
        assert data2["marked_count"] == 10
        mock_mgr.mark_all_pending_generated.assert_called_once()

        # Empty
        res3 = client.post("/api/prompts/mark-generated", json={})
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["success"] is False
        assert data3["marked_count"] == 0
