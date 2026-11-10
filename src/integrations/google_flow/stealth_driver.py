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
        target_resolution: str = "2k",
        mode: str = "t2v",
        model: str = "veo-2.0",
        duration_seconds: int = 5,
        variations_count: int = 1,
        strip_audio: bool = False,
        output_dir: Optional[Path] = None,
        timeout_seconds: int = 180,
    ) -> Dict[str, Any]:
        """Execute end-to-end Google Flow studio creation, generation, upscale and download."""
        from playwright.async_api import async_playwright

        is_video = mode in ["t2v", "i2v"] or "veo" in model.lower()
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        target_dir = output_dir or (base_dir / "data" / "final" / ("videos" if is_video else "images"))
        target_dir.mkdir(parents=True, exist_ok=True)

        # 0. Format prompt directives for Google Flow AI Agent
        dispatch_prompt = prompt.strip()
        if is_video and not any(k in dispatch_prompt.lower() for k in ["vídeo", "video", "veo"]):
            dispatch_prompt = (
                f"Crie um vídeo cinemático em {aspect_ratio} ({duration_seconds}s) usando Veo 2: {dispatch_prompt}"
            )
        elif not is_video and not any(k in dispatch_prompt.lower() for k in ["imagem", "image", "foto", "photo"]):
            dispatch_prompt = (
                f"Crie uma imagem conceitual comercial em {aspect_ratio}: {dispatch_prompt}"
            )

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

            # 1.1 Rename project if requested
            if project_name:
                try:
                    title_input = await page.query_selector(
                        "input.editable-text-input, input[aria-label='Texto editável']"
                    )
                    if title_input:
                        await title_input.click()
                        await page.keyboard.press("Control+A")
                        await page.keyboard.type(project_name, delay=10)
                        await page.keyboard.press("Enter")
                        logger.info(f"Project renamed to: {project_name}")
                except Exception as rename_err:
                    logger.debug(f"Project title rename skipped: {rename_err}")

            # 2. Focus prompt input and type with human-like delay
            prompt_input = await page.wait_for_selector(
                "div[aria-label='O que você quer criar?']",
                timeout=30000,
            )
            await prompt_input.click()
            await asyncio.sleep(0.5)
            logger.info(f"Typing prompt ({len(dispatch_prompt)} chars): {dispatch_prompt[:70]}...")
            await page.keyboard.type(dispatch_prompt, delay=12)
            await asyncio.sleep(1.0)

            # 3. Click Iniciar geração
            gen_btn = await page.query_selector("button[aria-label='Iniciar geração']")
            if not gen_btn:
                raise RuntimeError("Button 'Iniciar geração' not found.")

            # Ensure Angular form control registered input event
            try:
                is_disabled = await gen_btn.is_disabled()
                if is_disabled:
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            logger.info("Triggering generation on Google Flow cloud GPU...")
            await gen_btn.click()

            # 4. Wait for generation to finish (Option 1 image/video appears)
            start_poll = time.time()
            opt1 = None
            last_progress = ""
            while (time.time() - start_poll) < timeout_seconds:
                opt1 = await page.query_selector(
                    "img[alt='Option 1'], [aria-label*='Option 1'], img[alt*='Bloco mostrando a imagem'], video, flow-grid-tile-container"
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

            # 7. Select resolution (4K, 2K Aprimorada, or 1K Original)
            res_clean = (target_resolution or "2k").lower().strip()
            if not auto_upscale or res_clean == "1k":
                res_selector = "button:has-text('1K'), [role='menuitem']:has-text('1K')"
            elif res_clean == "4k":
                res_selector = "button:has-text('4K Aprimorada'), button:has-text('4K'), [role='menuitem']:has-text('4K')"
            else:
                res_selector = "button:has-text('2K Aprimorada'), button:has-text('2K'), [role='menuitem']:has-text('2K')"

            target_res_btn = await page.query_selector(res_selector)
            if not target_res_btn and res_clean == "4k":
                # Fallback to 2K if 4K is not yet rendered for this item
                target_res_btn = await page.query_selector("button:has-text('2K Aprimorada'), [role='menuitem']:has-text('2K')")

            if not target_res_btn:
                # Fallback to any download button in popup
                target_res_btn = await page.query_selector(".cdk-overlay-pane button, [role='menuitem']")

            if not target_res_btn:
                raise RuntimeError("Could not find download resolution option in popup.")

            logger.info(f"Downloading asset ({res_clean.upper()}) from Google Flow...")
            async with page.expect_download() as download_info:
                await target_res_btn.click()
            download = await download_info.value

            saved_file = target_dir / download.suggested_filename
            await download.save_as(str(saved_file))
            logger.info(f"✅ Real Google Flow asset saved: {saved_file.name} ({saved_file.stat().st_size} bytes)")

            # Optional audio stripping (-an) for stock compliance if video
            if is_video and strip_audio and saved_file.suffix.lower() in [".mp4", ".webm", ".mov"]:
                from src.integrations.google_flow.downloader import GoogleFlowDownloader
                downloader = GoogleFlowDownloader(videos_dir=target_dir)
                downloader._strip_audio_inplace(saved_file)

            await self.close()

            return {
                "project_id": project_id,
                "project_url": project_url,
                "file_path": str(saved_file),
                "file_size": saved_file.stat().st_size,
                "resolution": res_clean,
                "media_type": "video" if is_video else "image",
            }

    @staticmethod
    async def natural_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
        """Human-like micro-delay to prevent bot pattern detection."""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
