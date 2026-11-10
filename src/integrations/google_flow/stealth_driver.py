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

from src.integrations.google_flow.config import (
    GOOGLE_FLOW_SESSION_DIR,
    GOOGLE_FLOW_WEB_URL,
    MODEL_DEFAULT_DURATIONS,
    MODEL_FORMAL_NAMES,
)

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
        model: str = "veo-3.1-quality",
        duration_seconds: int = 8,
        variations_count: int = 1,
        strip_audio: bool = False,
        output_dir: Optional[Path] = None,
        timeout_seconds: int = 360,
    ) -> Dict[str, Any]:
        """Execute end-to-end Google Flow studio creation, generation, upscale and download."""
        from playwright.async_api import async_playwright

        is_video = mode in ["t2v", "i2v"] or "veo" in model.lower() or "omni" in model.lower()
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        target_dir = output_dir or (base_dir / "data" / "final" / ("videos" if is_video else "images"))
        target_dir.mkdir(parents=True, exist_ok=True)

        # 0. Format prompt directives for Google Flow AI Agent
        dispatch_prompt = prompt.strip()
        model_key = model.lower().strip()
        formal_model = MODEL_FORMAL_NAMES.get(model_key, "Veo 3.1 - Quality")
        calibrated_duration = MODEL_DEFAULT_DURATIONS.get(model_key, duration_seconds)
        if "veo-3" in model_key and calibrated_duration < 8:
            calibrated_duration = 8

        if is_video and not any(k in dispatch_prompt.lower() for k in ["vídeo", "video", "veo", "omni"]):
            dispatch_prompt = (
                f"Crie um vídeo cinemático em {aspect_ratio} com duração de {calibrated_duration}s usando o modelo {formal_model}: {dispatch_prompt}"
            )
        elif not is_video and not any(k in dispatch_prompt.lower() for k in ["imagem", "image", "foto", "photo"]):
            dispatch_prompt = (
                f"Crie uma imagem conceitual comercial em {aspect_ratio}: {dispatch_prompt}"
            )

        async with async_playwright() as p:
            try:
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

                # 4. Wait for generation to finish
                start_poll = time.time()
                opt1 = None
                last_progress = ""
                while (time.time() - start_poll) < timeout_seconds:
                    try:
                        # 4.1 Check and auto-approve credit permission prompt (flow-permission-message)
                        perm_radio = await page.query_selector(
                            "div[role='radio'][aria-label='Sempre aprovar'], div.option-row[aria-label='Sempre aprovar'], [role='radio']:has-text('Sempre aprovar')"
                        )
                        if not perm_radio:
                            perm_radio = await page.query_selector(
                                "div[role='radio'][aria-label='Aprovar'], div.option-row[aria-label='Aprovar'], [role='radio']:has-text('Aprovar')"
                            )

                        if perm_radio and await perm_radio.is_visible():
                            is_checked = await perm_radio.get_attribute("aria-checked")
                            if is_checked != "true":
                                logger.info("💳 [CREDIT CONFIRMATION] Selecionando 'Sempre aprovar'...")
                                await perm_radio.click()
                                await asyncio.sleep(0.5)

                            confirm_btn = await page.query_selector(
                                "button:has-text('Aprovar'), button:has-text('Confirmar'), button:has-text('Continuar'), flow-permission-message button"
                            )
                            if confirm_btn and await confirm_btn.is_visible() and not await confirm_btn.is_disabled():
                                await confirm_btn.click()
                                logger.info("💳 [CREDIT CONFIRMATION] Diálogo de créditos confirmado.")
                                await asyncio.sleep(2.0)

                        body_text = await page.inner_text("body")
                        lower_body = body_text.lower()

                        for line in body_text.split("\n"):
                            s = line.strip()
                            if "%" in s and len(s) <= 5 and s != last_progress:
                                last_progress = s
                                logger.info(f"Google Flow GPU progress: {s}")
                                break

                        # 4.2 Check if Flow Agent paused with a clarification question in chat
                        if (time.time() - start_poll) > 6.0 and any(
                            q in lower_body
                            for q in [
                                "como gostaria de prosseguir",
                                "modelos de vídeo disponíveis",
                                "sobre as opções de duração",
                                "não está disponível no google flow",
                            ]
                        ):
                            logger.info("🤖 Flow Agent abriu diálogo de desambiguação no chat. Resolvendo autonomamente...")
                            if "veo 3.1" in lower_body:
                                reply_choice = "2" if "2. usar o veo 3.1" in lower_body or "2. usar o veo" in lower_body else "Usar Veo 3.1 com 8 segundos"
                            else:
                                reply_choice = "1"

                            chat_input = await page.query_selector("div[aria-label='O que você quer criar?']")
                            if chat_input:
                                await chat_input.click()
                                await page.keyboard.type(reply_choice, delay=12)
                                await asyncio.sleep(0.5)
                                send_btn = await page.query_selector("button[aria-label='Iniciar geração']")
                                if send_btn and await send_btn.is_enabled():
                                    await send_btn.click()
                                else:
                                    await page.keyboard.press("Enter")
                                logger.info(f"✅ [AUTO-DISAMBIGUATE] Resposta enviada ao Flow Agent: '{reply_choice}'")
                                await asyncio.sleep(4.0)

                        # 4.3 Check for completed media tile (ensure not in busy/generating state)
                        is_busy = await page.query_selector(
                            "flow-grid-tile-container mat-progress-spinner, flow-video-tile mat-progress-bar, [aria-busy='true'], .generating, flow-grid-tile-container .loading"
                        )
                        if not is_busy and (time.time() - start_poll) > 4.0:
                            opt1 = await page.query_selector(
                                "flow-video-tile img.thumbnail, flow-video-tile video, img[alt='Option 1'], [aria-label*='Option 1'], flow-grid-tile-container img[draggable='false'], flow-grid-tile-container img"
                            )
                            if opt1 and await opt1.is_visible():
                                logger.info("🎉 Generation completed on Google Flow!")
                                break
                    except Exception as loop_err:
                        logger.debug(f"Polling loop note: {loop_err}")

                    await asyncio.sleep(2.5)

                if not opt1:
                    raise TimeoutError("Timed out waiting for Google Flow generation variations.")

                # 5. Click media tile to open details dialog
                await opt1.click()
                await asyncio.sleep(2.0)

                # 6. Click Baixar mídia
                download_btn = await page.wait_for_selector(
                    "button[aria-label='Baixar mídia'], button:has-text('Baixar'), [role='button'][aria-label*='Baixar']",
                    timeout=15000,
                )
                await download_btn.click()
                await asyncio.sleep(1.5)

                # 7. Select resolution based on asset type and user request
                res_clean = (target_resolution or "2k").lower().strip()
                target_res_btn = None

                if is_video:
                    # Video menu: 4K Aprimorada, 1080p Aprimorada, 720p Tamanho original, 270p GIF animado
                    if res_clean == "4k":
                        candidate_4k = await page.query_selector("button:has-text('4K Aprimorada'), [role='menuitem']:has-text('4K')")
                        if candidate_4k and not await candidate_4k.is_disabled():
                            target_res_btn = candidate_4k

                    if not target_res_btn and res_clean in ["4k", "2k", "1080p"]:
                        candidate_1080 = await page.query_selector("button:has-text('1080p Aprimorada'), [role='menuitem']:has-text('1080p')")
                        if candidate_1080 and not await candidate_1080.is_disabled():
                            target_res_btn = candidate_1080

                    if not target_res_btn:
                        # 720p original is always ready for instant high-speed download
                        target_res_btn = await page.query_selector("button:has-text('720p'), [role='menuitem']:has-text('720p')")
                else:
                    # Image menu: 4K Aprimorada, 2K Aprimorada, 1K
                    if not auto_upscale or res_clean == "1k":
                        target_res_btn = await page.query_selector("button:has-text('1K'), [role='menuitem']:has-text('1K')")
                    elif res_clean == "4k":
                        candidate_4k = await page.query_selector("button:has-text('4K Aprimorada'), button:has-text('4K'), [role='menuitem']:has-text('4K')")
                        if candidate_4k and not await candidate_4k.is_disabled():
                            target_res_btn = candidate_4k
                    if not target_res_btn:
                        target_res_btn = await page.query_selector("button:has-text('2K Aprimorada'), button:has-text('2K'), [role='menuitem']:has-text('2K')")

                if not target_res_btn:
                    target_res_btn = await page.query_selector(".cdk-overlay-pane button, [role='menuitem']")

                if not target_res_btn:
                    raise RuntimeError("Could not find download resolution option in popup.")

                logger.info(f"Downloading asset ({res_clean.upper()}) from Google Flow...")
                saved_file = None
                try:
                    async with page.expect_download(timeout=15000) as download_info:
                        await target_res_btn.click()
                    download = await download_info.value
                    saved_file = target_dir / download.suggested_filename
                    await download.save_as(str(saved_file))
                except Exception as dl_err:
                    logger.info(f"Direct download trigger note ({dl_err}). Attempting 720p original instant download...")
                    await asyncio.sleep(1.0)
                    re_dl = await page.query_selector("button[aria-label='Baixar mídia']")
                    if re_dl:
                        await re_dl.click()
                        await asyncio.sleep(1.0)
                    btn_720 = await page.wait_for_selector("button:has-text('720p'), [role='menuitem']:has-text('720p')", timeout=10000)
                    async with page.expect_download(timeout=20000) as dl_info2:
                        await btn_720.click()
                    download2 = await dl_info2.value
                    saved_file = target_dir / download2.suggested_filename
                    await download2.save_as(str(saved_file))
                    res_clean = "720p"

                logger.info(f"✅ Real Google Flow asset saved: {saved_file.name} ({saved_file.stat().st_size} bytes)")

                # Optional audio stripping (-an) for stock compliance if video (async to prevent event loop blocking)
                if is_video and strip_audio and saved_file.suffix.lower() in [".mp4", ".webm", ".mov"]:
                    from src.integrations.google_flow.downloader import GoogleFlowDownloader
                    downloader = GoogleFlowDownloader(videos_dir=target_dir)
                    strip_ok = await asyncio.to_thread(downloader._strip_audio_inplace, saved_file)
                    if not strip_ok:
                        logger.warning(f"Audio stripping skipped or failed for {saved_file.name} (ffmpeg may not be present).")

                return {
                    "project_id": project_id,
                    "project_url": project_url,
                    "file_path": str(saved_file),
                    "file_size": saved_file.stat().st_size,
                    "resolution": res_clean,
                    "media_type": "video" if is_video else "image",
                }
            finally:
                await self.close()

    @staticmethod
    async def natural_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
        """Human-like micro-delay to prevent bot pattern detection."""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
