"""CLI Management Interface for Google Flow API Engine.

Enables standalone operation, interactive login, batch queue execution,
and server startup directly from the command line.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Optional

from src.integrations.google_flow.api_server import start_server
from src.integrations.google_flow.auth_manager import GoogleFlowAuthManager
from src.integrations.google_flow.config import (
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    GOOGLE_VEO_QUEUE_FILE,
)
from src.integrations.google_flow.models import GenerationRequest, JobStatus
from src.integrations.google_flow.service import GoogleFlowService

logger = logging.getLogger("GoogleFlowCLI")


def main_cli(args: Optional[list] = None) -> int:
    """Main CLI entry point for Google Flow."""
    parser = argparse.ArgumentParser(
        description="Google Flow Industrial REST API & Automation Engine"
    )
    parser.add_argument("--login", action="store_true", help="Launch interactive 1-click Google login")
    parser.add_argument("--status", action="store_true", help="Check Google Flow session status")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI REST server with Swagger docs")
    parser.add_argument("--host", default=DEFAULT_API_HOST, help="API server bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT, help="API server port")

    # Direct generation flags
    parser.add_argument("--generate", type=str, help="Cinematic text prompt to generate")
    parser.add_argument("--mode", default=None, choices=["t2v", "t2i", "i2v"], help="Generation mode: t2v, t2i, i2v")
    parser.add_argument("--model", default="veo-3.1-quality", help="Model: veo-3.1-quality, veo-3.1-fast, veo-3.1-lite, omni-1.2-flash, imagen-3.0")
    parser.add_argument("--ratio", default="16:9", help="Aspect ratio: 16:9, 9:16, 1:1, 4:3, 2.39:1")
    parser.add_argument("--duration", type=int, default=8, help="Duration in seconds (8s for Veo 3.1, 5s for Omni)")
    parser.add_argument("--variations", type=int, default=1, help="Variations count (1, 2, 4)")
    parser.add_argument("--upscale", default="2k", choices=["1k", "2k", "4k"], help="Target upscale resolution (1k, 2k, 4k)")
    parser.add_argument("--no-upscale", action="store_true", help="Disable automatic upscale")
    parser.add_argument("--strip-audio", action="store_true", help="Strip audio track (-an) for stock upload")
    parser.add_argument("--project-name", default=None, help="Custom project title for Google Flow")

    # Queue processing
    parser.add_argument("--process-queue", action="store_true", help="Process pending prompts in google_veo_queue.json")

    parsed = parser.parse_args(args)

    auth = GoogleFlowAuthManager()

    if parsed.login:
        success = auth.interactive_login()
        return 0 if success else 1

    if parsed.status:
        st = auth.get_status()
        print("\n=== GOOGLE FLOW SESSION STATUS ===")
        print(f"  Authenticated: {st.authenticated}")
        print(f"  User Email:    {st.user_email or 'Not detected'}")
        print(f"  Cookies Count: {st.cookies_count}")
        print(f"  Message:       {st.message}")
        print("==================================\n")
        return 0

    if parsed.serve:
        start_server(host=parsed.host, port=parsed.port)
        return 0

    if parsed.generate:
        return asyncio.run(
            _run_single_generation(
                prompt=parsed.generate,
                mode=parsed.mode,
                model=parsed.model,
                aspect_ratio=parsed.ratio,
                duration=parsed.duration,
                variations=parsed.variations,
                auto_upscale=not parsed.no_upscale,
                target_resolution=parsed.upscale,
                strip_audio=parsed.strip_audio,
                project_name=parsed.project_name,
            )
        )

    if parsed.process_queue:
        return asyncio.run(_run_queue_processor())

    parser.print_help()
    return 0


async def _run_single_generation(
    prompt: str,
    mode: Optional[str],
    model: str,
    aspect_ratio: str,
    duration: int,
    variations: int,
    auto_upscale: bool,
    target_resolution: str,
    strip_audio: bool,
    project_name: Optional[str] = None,
) -> int:
    """Run a single generation from CLI and await completion."""
    service = GoogleFlowService()
    auth_status = service.auth_manager.get_status()
    if not auth_status.authenticated:
        print("\n" + "=" * 65)
        print("  ⚠️  AVISO DE AUTENTICAÇÃO — GOOGLE FLOW")
        print("  Sua sessão Google ainda não está autenticada!")
        print("  As requisições à nuvem do Google Flow retornarão HTTP 302 (login).")
        print("  Para gerar vídeos reais via Veo, faça o login de 1 clique:")
        print("    python main.py --flow-login")
        print("=" * 65)

    determined_mode = mode or ("t2v" if "veo" in model.lower() else "t2i")
    req = GenerationRequest(
        prompt=prompt,
        mode=determined_mode,
        model=model,
        aspect_ratio=aspect_ratio,
        duration_seconds=duration,
        variations_count=variations,
        auto_upscale=auto_upscale,
        target_resolution=target_resolution,
        strip_audio=strip_audio,
        project_name=project_name,
    )
    print(f"\n🚀 Enqueuing generation for prompt: {prompt[:60]}...")
    job = await service.enqueue_generation(req)

    # Monitor until finished
    while True:
        await asyncio.sleep(2.0)
        curr = service.get_job(job.job_id)
        if not curr:
            break
        print(f"  [{curr.status.value.upper()}] ({curr.progress_percent:.0f}%) — {curr.message}")
        if curr.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            if curr.status == JobStatus.COMPLETED:
                print(f"\n✨ Assets ready:")
                for p in curr.final_output_paths:
                    print(f"  📁 {p}")
                return 0
            else:
                print(f"\n❌ Error: {curr.error}")
                return 1
    return 0


async def _run_queue_processor() -> int:
    """Consume prompts from google_veo_queue.json."""
    if not GOOGLE_VEO_QUEUE_FILE.exists():
        print(f"Queue file {GOOGLE_VEO_QUEUE_FILE.name} not found.")
        return 1

    with open(GOOGLE_VEO_QUEUE_FILE, "r", encoding="utf-8") as f:
        queue = json.load(f)

    pending = [item for item in queue if item.get("status") == "pending"]
    if not pending:
        print("No pending items in Google Veo queue.")
        return 0

    print(f"\n🎬 Processing {len(pending)} pending prompts from Google Veo queue...")
    service = GoogleFlowService()

    for item in pending:
        prompt_text = item.get("veo_prompt") or item.get("prompt")
        shot_id = item.get("shot_id", "shot")
        duration = int(item.get("duration", 5))

        req = GenerationRequest(
            prompt=prompt_text,
            mode="t2v",
            model="veo-2.0",
            aspect_ratio="16:9",
            duration_seconds=duration,
            variations_count=1,
            auto_upscale=True,
            project_name=f"StockCont_{shot_id}",
        )
        job = await service.enqueue_generation(req)
        while True:
            await asyncio.sleep(2.0)
            curr = service.get_job(job.job_id)
            if not curr:
                break
            if curr.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                if curr.status == JobStatus.COMPLETED:
                    item["status"] = "generated"
                    item["outputs"] = curr.final_output_paths
                break

    # Persist updated queue atomically (ADR-02)
    tmp = GOOGLE_VEO_QUEUE_FILE.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}.json")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        tmp.replace(GOOGLE_VEO_QUEUE_FILE)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    print("✅ Queue processing batch complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
