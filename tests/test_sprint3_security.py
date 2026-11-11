from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.orchestrator.daemon import AlertNotifier


def test_dashboard_auth_middleware_disabled_when_token_unset(monkeypatch):
    monkeypatch.delenv("DASHBOARD_ACCESS_TOKEN", raising=False)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/youtube/lint-package",
        json={"title": "Test Title Clean", "thumbnail_text": "SECRET"},
    )
    assert resp.status_code == 200


def test_dashboard_auth_middleware_enforced_when_token_configured(monkeypatch):
    monkeypatch.setenv("DASHBOARD_ACCESS_TOKEN", "stockcont-secret-token")
    client = TestClient(app)

    # Read-only status still accessible; mutable endpoint blocked without token
    unauth = client.post(
        "/api/v1/youtube/lint-package",
        json={"title": "Test Title Clean", "thumbnail_text": "SECRET"},
    )
    assert unauth.status_code == 401

    wrong = client.post(
        "/api/v1/youtube/lint-package",
        headers={"Authorization": "Bearer wrong-token"},
        json={"title": "Test Title Clean", "thumbnail_text": "SECRET"},
    )
    assert wrong.status_code == 401

    bearer_ok = client.post(
        "/api/v1/youtube/lint-package",
        headers={"Authorization": "Bearer stockcont-secret-token"},
        json={"title": "Test Title Clean", "thumbnail_text": "SECRET"},
    )
    assert bearer_ok.status_code == 200

    header_ok = client.post(
        "/api/v1/youtube/lint-package",
        headers={"X-Dashboard-Token": "stockcont-secret-token"},
        json={"title": "Test Title Clean", "thumbnail_text": "SECRET"},
    )
    assert header_ok.status_code == 200


def test_alert_notifier_state_transitions_only_without_spam():
    notifier = AlertNotifier(
        webhook_url="https://hooks.example.test/webhook",
        heartbeat_url="https://hc-ping.example.test/ping-uuid",
    )
    with patch("src.orchestrator.daemon.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        # First transition -> fires
        assert notifier.notify_transition("running", "Cycle started") is True
        # Identical state -> suppressed (no spam)
        assert notifier.notify_transition("running", "Cycle running") is False
        # State change to error -> fires
        assert notifier.notify_transition("error", "SFTP timeout") is True
        # Duplicate error -> suppressed
        assert notifier.notify_transition("error", "SFTP timeout again") is False
        # Recovery -> fires
        assert notifier.notify_transition("running", "Recovered") is True
        assert mock_post.call_count == 3

    with patch("src.orchestrator.daemon.httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        assert notifier.send_heartbeat_ping() is True
        assert mock_get.call_count == 1
