"""Stealth Automation Driver for Google Flow.

Provides anti-bot evasion scripts, browser fingerprint consistency,
and automated fallback interaction for Google Flow (labs.google / flow.google).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.integrations.google_flow.config import GOOGLE_FLOW_SESSION_DIR, GOOGLE_FLOW_WEB_URL

logger = logging.getLogger("GoogleFlowStealthDriver")

# Evasion script injected into every page/frame
STEALTH_EVASION_JS = """
// Overwrite navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Mock Chrome runtime
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// Mock Notification permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Mock WebGL Vendor and Renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Google Inc. (NVIDIA)';
    }
    if (parameter === 37446) {
        return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
    }
    return getParameter.apply(this, arguments);
};
"""


class GoogleFlowStealthDriver:
    """Stealth driver managing automated Chromium context and DOM interactions."""

    def __init__(self, session_dir: Path = GOOGLE_FLOW_SESSION_DIR, headless: bool = True):
        self.session_dir = session_dir
        self.headless = headless
        self._context = None
        self._page = None

    def get_launch_args(self) -> List[str]:
        """Return Chromium flags for stealth operation."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
        ]

    async def open_page(self, playwright_instance: Any) -> Any:
        """Launch or reuse persistent context with evasion scripts injected."""
        self._context = await playwright_instance.chromium.launch_persistent_context(
            user_data_dir=str(self.session_dir),
            headless=self.headless,
            args=self.get_launch_args(),
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.6613.138 Safari/537.36"
            ),
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        await self._page.add_init_script(STEALTH_EVASION_JS)
        return self._page

    async def close(self) -> None:
        """Safely close browser context."""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None

    @staticmethod
    async def natural_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
        """Human-like micro-delay to prevent bot pattern detection."""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
