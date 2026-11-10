"""Google Flow Authentication & Session Lifecycle Manager.

Manages the persistent Chromium user data directory ('google_flow_session/'),
interactive 1-click headed authentication (Passkey/2FA), token capture,
and background session heartbeats to prevent token expiration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.integrations.google_flow.config import (
    GOOGLE_FLOW_SESSION_DIR,
    GOOGLE_FLOW_WEB_URL,
    HEARTBEAT_INTERVAL_MINUTES,
)
from src.integrations.google_flow.models import AuthStatusResponse

logger = logging.getLogger("GoogleFlowAuth")

TOKENS_FILE = GOOGLE_FLOW_SESSION_DIR / "session_tokens.json"


class GoogleFlowAuthManager:
    """Manages persistent browser authentication and token extraction for Google Flow."""

    def __init__(self, session_dir: Path = GOOGLE_FLOW_SESSION_DIR):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.tokens_file = self.session_dir / "session_tokens.json"
        self._cached_headers: Optional[Dict[str, str]] = None
        self._last_heartbeat: Optional[float] = None

    def get_persisted_tokens(self) -> Optional[Dict[str, Any]]:
        """Retrieve persisted tokens from disk if valid and uncorrupted."""
        if not self.tokens_file.exists():
            return None
        try:
            with open(self.tokens_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.warning(f"Failed to read session tokens: {e}")
            return None

    def save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Atomically persist session tokens (ADR-02)."""
        tokens["updated_at"] = time.time()
        tmp = self.tokens_file.with_suffix(f".tmp.{os.getpid()}_{int(time.time())}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)
        tmp.replace(self.tokens_file)
        self._cached_headers = tokens.get("headers", {})
        self._last_heartbeat = time.time()
        logger.info(f"💾 Session tokens saved to {self.tokens_file.name}")

    def get_auth_headers(self) -> Dict[str, str]:
        """Return HTTP headers (Authorization, Cookie, x-goog-api-key) for direct RPC calls."""
        if self._cached_headers:
            return self._cached_headers

        data = self.get_persisted_tokens()
        if data and "headers" in data:
            self._cached_headers = data["headers"]
            return self._cached_headers

        return {}

    def get_status(self) -> AuthStatusResponse:
        """Inspect the current session state and validity."""
        tokens = self.get_persisted_tokens()
        if not tokens:
            return AuthStatusResponse(
                authenticated=False,
                session_dir=str(self.session_dir),
                cookies_count=0,
                message="No session tokens found. Interactive login required."
            )

        cookies = tokens.get("cookies", [])
        has_secure_sid = any(
            c.get("name") in ["__Secure-1PSID", "SID", "SAPISID"] for c in cookies
        )
        is_fresh = (time.time() - tokens.get("updated_at", 0)) < (86400 * 14)  # 14 days

        auth_ok = has_secure_sid and is_fresh
        msg = "Session valid and active" if auth_ok else "Session cookies expired or incomplete"

        return AuthStatusResponse(
            authenticated=auth_ok,
            session_dir=str(self.session_dir),
            user_email=tokens.get("user_email"),
            cookies_count=len(cookies),
            last_heartbeat=tokens.get("updated_at"),
            message=msg
        )

    def interactive_login(self, timeout_sec: int = 300) -> bool:
        """Open headed Chromium window allowing user to complete Google 2FA login.

        Captures authentication cookies, Bearer tokens, and request headers on success.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright is not installed. Please install playwright.")
            return False

        print("\n" + "=" * 65)
        print("  GOOGLE FLOW — LOGIN ASSISTIDO (ONE-SHOT 2FA)")
        print("  Uma janela do navegador será aberta.")
        print("  Por favor, faça login com sua conta Google autorizada.")
        print("  A janela permanecerá aberta até a conclusão do login.")
        print("=" * 65 + "\n")

        captured_headers: Dict[str, str] = {}
        captured_cookies: list = []
        user_email: Optional[str] = None

        with sync_playwright() as p:
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=False,
                args=args,
                viewport={"width": 1280, "height": 850},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.6613.138 Safari/537.36"
                ),
            )

            page = context.pages[0] if context.pages else context.new_page()

            # Intercept network requests to capture internal Google Labs tokens
            def handle_request(req):
                url = req.url
                if "clients6.google.com" in url or "labs.google" in url or "flow.google" in url:
                    hdrs = req.headers
                    if "authorization" in hdrs:
                        captured_headers["Authorization"] = hdrs["authorization"]
                    if "x-goog-api-key" in hdrs:
                        captured_headers["x-goog-api-key"] = hdrs["x-goog-api-key"]

            page.on("request", handle_request)

            # Navigate directly to Google Login with redirect to Flow
            login_url = "https://accounts.google.com/ServiceLogin?continue=https://flow.google.com/"
            try:
                page.goto(login_url, wait_until="commit", timeout=60000)
            except Exception as e:
                logger.warning(f"Initial navigation notice: {e}")

            print("  ⏳ Janela aberta! Digite seu email/senha e realize o 2FA no navegador...")
            print("  (Aguardando você concluir o login no Google)...\n")

            # Wait for user to complete login
            start_time = time.time()
            logged_in = False

            while (time.time() - start_time) < timeout_sec:
                try:
                    if not context.pages or context.pages[0].is_closed():
                        print("  [INFO] Janela fechada pelo usuário.")
                        break

                    current_url = page.url
                    cookies = context.cookies()
                    has_auth_cookie = any(
                        c.get("name") in ["__Secure-1PSID", "SID", "SAPISID"] for c in cookies
                    )

                    # Only consider logged in if real Google session cookies are present
                    # AND user has returned to Flow / Labs, outside of accounts.google.com
                    if (
                        has_auth_cookie
                        and ("flow.google" in current_url or "labs.google" in current_url)
                        and "accounts.google.com" not in current_url
                    ):
                        print("  [✓] Login detectado com sucesso! Capturando credenciais...")
                        time.sleep(3.0)
                        logged_in = True
                        break
                except Exception:
                    pass

                time.sleep(1.0)

            if logged_in:
                captured_cookies = context.cookies()
                # Try to extract user email or profile text if present
                try:
                    profile_el = page.query_selector("button[aria-label*='Google Account']")
                    if profile_el:
                        aria_label = profile_el.get_attribute("aria-label") or ""
                        if "(" in aria_label and ")" in aria_label:
                            user_email = aria_label.split("(")[-1].split(")")[0]
                except Exception:
                    pass

                # Build cookie header string
                cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in captured_cookies)
                captured_headers["Cookie"] = cookie_str
                captured_headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.6613.138 Safari/537.36"
                )

                self.save_tokens({
                    "user_email": user_email,
                    "headers": captured_headers,
                    "cookies": captured_cookies,
                    "landing_url": page.url,
                })
                print("\n  [✓] Login no Google Flow concluído com sucesso!")
                print(f"  [✓] Capturados {len(captured_cookies)} cookies e credenciais de sessão.\n")
                context.close()
                return True
            else:
                print("\n  [✗] Tempo limite atingido sem confirmação de login no Google Flow.\n")
                context.close()
                return False

    async def heartbeat_refresh(self) -> bool:
        """Run headless background heartbeat to refresh session tokens."""
        status = self.get_status()
        if not status.authenticated:
            logger.info("Heartbeat skipped: Session not authenticated.")
            return False

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                args = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_dir),
                    headless=True,
                    args=args
                )
                page = await context.new_page()

                captured_headers: Dict[str, str] = {}

                def on_req(req):
                    if "clients6.google.com" in req.url or "labs.google" in req.url:
                        for k, v in req.headers.items():
                            if k.lower() in ["authorization", "x-goog-api-key"]:
                                captured_headers[k] = v

                page.on("request", on_req)
                await page.goto(GOOGLE_FLOW_WEB_URL, wait_until="domcontentloaded", timeout=30000)

                cookies = await context.cookies()
                cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                captured_headers["Cookie"] = cookie_str

                existing = self.get_persisted_tokens() or {}
                headers = existing.get("headers", {})
                headers.update(captured_headers)
                existing["headers"] = headers
                existing["cookies"] = cookies
                self.save_tokens(existing)

                await context.close()
                logger.info("💓 Session heartbeat refresh succeeded.")
                return True
        except Exception as e:
            logger.warning(f"Session heartbeat failed: {e}")
            return False
