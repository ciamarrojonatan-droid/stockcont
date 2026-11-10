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

    async def execute_generation_workflow(
        self,
        prompt: str,
        project_name: Optional[str] = None,
        aspect_ratio: str = "16:9",
        auto_upscale: bool = True,
        output_dir: Optional[Path] = None,
        timeout_seconds: int = 180,
    ) -> Dict[str, Any]:
        """Execute end-to-end Google Flow studio creation, generation, upscale and download."""
        from playwright.async_api import async_playwright

        target_dir = output_dir or (Path(__file__).resolve().parent.parent.parent.parent / "data" / "final" / "videos")
        target_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            page = await self.open_page(p)
            logger.info("Opening Google Flow studio dashboard...")
            await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=40000)

            # 1. Click Novo projeto
            novo_proj_btn = await page.wait_for_selector(
                "button:has-text('Novo projeto'), [role='button']:has-text('Novo projeto')",
                timeout=25000,
            )
            logger.info("Creating new project on Google Flow...")
            await novo_proj_btn.click()
            
            # Wait for project URL transition
            try:
                await page.wait_for_url(lambda u: "/project/" in u, timeout=25000)
            except Exception:
                await asyncio.sleep(3.0)

            project_url = page.url
            project_id = project_url.split("/project/")[-1] if "/project/" in project_url else "unknown_project"
            logger.info(f"Project created: {project_id} ({project_url})")

            # 2. Focus prompt input and type with human-like delay
            prompt_input = await page.wait_for_selector(
                "div[aria-label='O que você quer criar?']",
                timeout=30000,
            )
            await prompt_input.click()
            await asyncio.sleep(0.5)
            logger.info(f"Typing prompt ({len(prompt)} chars)...")
            await page.keyboard.type(prompt, delay=12)
            await asyncio.sleep(1.0)

            # 3. Click Iniciar geração
            gen_btn = await page.query_selector("button[aria-label='Iniciar geração']")
            if not gen_btn:
                raise RuntimeError("Button 'Iniciar geração' not found.")

            logger.info("Triggering generation on Google Flow cloud GPU...")
            await gen_btn.click()

            # 4. Wait for generation to finish (Option 1 image/video appears)
            start_poll = time.time()
            opt1 = None
            last_progress = ""
            while (time.time() - start_poll) < timeout_seconds:
                opt1 = await page.query_selector(
                    "img[alt='Option 1'], [aria-label*='Option 1'], img[alt*='Bloco mostrando a imagem'], video"
                )
                if opt1:
                    logger.info("🎉 Generation variations completed by Google Flow!")
                    break

                try:
                    body_text = await page.inner_text("body")
                    for line in body_text.split("\n"):
                        s = line.strip()
                        if "%" in s and len(s) <= 5 and s != last_progress:
                            last_progress = s
                            logger.info(f"Google Flow GPU progress: {s}")
                            break
                except Exception:
                    pass

                await asyncio.sleep(2.5)

            if not opt1:
                raise TimeoutError("Timed out waiting for Google Flow generation variations.")

            # 5. Click Option 1 to open details dialog
            await opt1.click()
            await asyncio.sleep(2.0)

            # 6. Click Baixar mídia
            download_btn = await page.wait_for_selector(
                "button[aria-label='Baixar mídia']",
                timeout=15000,
            )
            await download_btn.click()
            await asyncio.sleep(1.5)

            # 7. Select resolution (2K Aprimorada if auto_upscale, else 1K)
            res_selector = "button:has-text('2K Aprimorada'), [role='menuitem']:has-text('2K Aprimorada')"
            if not auto_upscale:
                res_selector = "button:has-text('1K'), [role='menuitem']:has-text('1K')"

            target_res_btn = await page.query_selector(res_selector)
            if not target_res_btn:
                # Fallback to any download button in popup
                target_res_btn = await page.query_selector(".cdk-overlay-pane button, [role='menuitem']")

            if not target_res_btn:
                raise RuntimeError("Could not find download resolution option in popup.")

            logger.info("Downloading upscaled asset from Google Flow...")
            async with page.expect_download() as download_info:
                await target_res_btn.click()
            download = await download_info.value

            saved_file = target_dir / download.suggested_filename
            await download.save_as(str(saved_file))
            logger.info(f"✅ Real Google Flow asset saved: {saved_file.name} ({saved_file.stat().st_size} bytes)")

            await self.close()

            return {
                "project_id": project_id,
                "project_url": project_url,
                "file_path": str(saved_file),
                "file_size": saved_file.stat().st_size,
            }

    @staticmethod
    async def natural_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
        """Human-like micro-delay to prevent bot pattern detection."""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
