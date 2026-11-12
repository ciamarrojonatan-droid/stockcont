import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_spa_static_markup_and_sprint6_widgets(monkeypatch):
    monkeypatch.delenv("DASHBOARD_ACCESS_TOKEN", raising=False)
    client = TestClient(app)

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "<html" in res_root.text.lower()

    res_video = client.get("/video")
    assert res_video.status_code == 200
    assert "StockCont Cinema" in res_video.text
    assert "Video & Motion Architecture" in res_video.text
    assert 'id="sprint6-telemetry-panel"' in res_video.text
    assert 'id="btn-s6-motion-qa"' in res_video.text
    assert 'id="btn-s6-refresh-telemetry"' in res_video.text
    assert 'id="sprint9-studio-panel"' in res_video.text
    assert 'id="btn-s9-map-demo"' in res_video.text
    assert 'id="btn-s9-storyboard-demo"' in res_video.text
    assert 'id="btn-s9-thumbs-demo"' in res_video.text
    assert "/static/js/video.js" in res_video.text

    res_js = client.get("/static/js/video.js")
    assert res_js.status_code == 200
    assert "bindSprint6TelemetryControls" in res_js.text
    assert "runSprint6MotionQADemo" in res_js.text
    assert "refreshSprint6TelemetryStatus" in res_js.text
    assert "bindSprint9StudioControls" in res_js.text


@pytest.mark.e2e
def test_playwright_spa_look_and_fix_audit():
    """Launch ephemeral FastAPI/Uvicorn subprocess and audit / and /video across desktop & mobile viewports."""
    playwright_sync = pytest.importorskip("playwright.sync_api")

    port = _find_free_port()
    env = os.environ.copy()
    env.pop("DASHBOARD_ACCESS_TOKEN", None)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.dashboard.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        ready = False
        for _ in range(120):
            if proc.poll() is not None:
                pytest.fail(f"Ephemeral Uvicorn server exited prematurely with code {proc.returncode}.")
            try:
                with urllib.request.urlopen(f"{base_url}/api/video/status", timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.1)

        if not ready:
            pytest.fail("Ephemeral FastAPI server failed to become ready within 12 seconds.")

        with playwright_sync.sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"Playwright Chromium unavailable in environment: {exc}")

            try:
                viewports = [
                    ("desktop", {"width": 1440, "height": 900}),
                    ("mobile", {"width": 390, "height": 844}),
                ]
                routes = ["/", "/video"]

                for vp_name, vp_size in viewports:
                    context = browser.new_context(viewport=vp_size)
                    try:
                        page = context.new_page()
                        console_errors = []
                        page_errors = []
                        server_errors = []

                        page.on(
                            "console",
                            lambda msg: console_errors.append(msg.text)
                            if msg.type == "error"
                            else None,
                        )
                        page.on("pageerror", lambda err: page_errors.append(str(err)))
                        page.on(
                            "response",
                            lambda r: server_errors.append(f"{r.status} {r.url}")
                            if r.status >= 500
                            else None,
                        )

                        for route in routes:
                            page.goto(f"{base_url}{route}", wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(400)

                            body_text = page.locator("body").inner_text().strip()
                            assert len(body_text) > 0, f"Empty body on {route} ({vp_name})"

                            overflow = page.evaluate(
                                "() => document.documentElement.scrollWidth > window.innerWidth + 2"
                            )
                            assert not overflow, f"Horizontal overflow detected on {route} ({vp_name})"

                            broken_imgs = page.evaluate(
                                """() => Array.from(document.querySelectorAll('img'))
                                    .filter(img => img.complete && img.src && img.naturalWidth === 0)
                                    .map(img => img.src)"""
                            )
                            assert broken_imgs == [], f"Broken images on {route} ({vp_name}): {broken_imgs}"

                            if route == "/video":
                                tab_btn = page.locator('[data-tab="timeline"], button:has-text("Timeline")')
                                if tab_btn.count() > 0:
                                    tab_btn.first.click()
                                    page.wait_for_timeout(250)
                                    assert page.locator("#sprint6-telemetry-panel").is_visible()
                                    assert page.locator("#sprint9-studio-panel").is_visible()

                        assert console_errors == [], f"Console errors on {vp_name}: {console_errors}"
                        assert page_errors == [], f"Page errors on {vp_name}: {page_errors}"
                        assert server_errors == [], f"HTTP >=500 errors on {vp_name}: {server_errors}"
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
