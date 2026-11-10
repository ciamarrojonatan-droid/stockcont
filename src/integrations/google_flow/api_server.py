"""FastAPI REST Server for Google Flow Industrial API.

Exposes RESTful endpoints with interactive Swagger documentation (/docs)
for project creation, media generation, polling, upscaling, downloading,
and authentication management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from src.integrations.google_flow.config import (
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    SUPPORTED_IMAGE_MODELS,
    SUPPORTED_MODES,
    SUPPORTED_VIDEO_MODELS,
)
from src.integrations.google_flow.models import (
    AuthStatusResponse,
    GenerationRequest,
    JobStatus,
    JobStatusResponse,
    ProjectCreateRequest,
    ProjectResponse,
    UpscaleRequest,
)
from src.integrations.google_flow.service import GoogleFlowService

logger = logging.getLogger("GoogleFlowAPI")


def create_app(service: Optional[GoogleFlowService] = None) -> FastAPI:
    """Application factory for the Google Flow FastAPI service."""
    app = FastAPI(
        title="Google Flow Industrial REST API",
        description=(
            "Unified REST API converting Google Flow (Veo 2/3 & Imagen 3) "
            "into an autonomous video & image generation pipeline with dedicated projects, "
            "AI curation, native upscale, and StockCont ingestion."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Enable CORS for external/local dashboard clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    flow_service = service or GoogleFlowService()

    # ══════════════════════════════════════════════════════
    # Health & System Status Endpoints
    # ══════════════════════════════════════════════════════

    @app.get("/api/v1/health", tags=["System"])
    async def get_health() -> Dict[str, Any]:
        """System healthcheck, uptime, and engine capabilities."""
        auth_status = flow_service.auth_manager.get_status()
        return {
            "status": "online",
            "service": "Google Flow Industrial API",
            "timestamp": time.time(),
            "authenticated": auth_status.authenticated,
            "user_email": auth_status.user_email,
            "supported_modes": SUPPORTED_MODES,
            "supported_video_models": SUPPORTED_VIDEO_MODELS,
            "supported_image_models": SUPPORTED_IMAGE_MODELS,
            "active_jobs_count": len(flow_service.list_jobs()),
        }

    # ══════════════════════════════════════════════════════
    # Authentication Management Endpoints
    # ══════════════════════════════════════════════════════

    @app.get("/api/v1/auth/status", response_model=AuthStatusResponse, tags=["Authentication"])
    async def get_auth_status() -> AuthStatusResponse:
        """Check the status and validity of persistent Google Flow session cookies."""
        return flow_service.auth_manager.get_status()

    @app.post("/api/v1/auth/login", tags=["Authentication"])
    async def trigger_interactive_login(
        background_tasks: BackgroundTasks,
        timeout_sec: int = Query(180, description="Timeout for manual login in seconds"),
    ) -> Dict[str, Any]:
        """Launch headed Chromium browser to perform one-click Google 2FA login."""
        # Run in threadpool so it does not block the async event loop
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, flow_service.auth_manager.interactive_login, timeout_sec
        )
        if success:
            return {
                "success": True,
                "message": "Login completed and session credentials captured.",
                "status": flow_service.auth_manager.get_status().model_dump(),
            }
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Interactive login timed out or was cancelled by user.",
        )

    # ══════════════════════════════════════════════════════
    # Project Management Endpoints
    # ══════════════════════════════════════════════════════

    @app.post("/api/v1/projects", response_model=ProjectResponse, tags=["Projects"])
    async def create_project(req: ProjectCreateRequest) -> ProjectResponse:
        """Create a dedicated workspace project on Google Flow."""
        return await flow_service.rpc_client.create_project(
            name=req.name,
            description=req.description,
            default_aspect_ratio=req.default_aspect_ratio,
        )

    # ══════════════════════════════════════════════════════
    # Generation & Job Lifecycles
    # ══════════════════════════════════════════════════════

    @app.post(
        "/api/v1/generate",
        response_model=JobStatusResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Generation"],
    )
    async def enqueue_generation(req: GenerationRequest) -> JobStatusResponse:
        """Enqueue text-to-video, image-to-video, or image generation.

        Automatically creates a dedicated project on Google Flow, dispatches the prompt,
        polls for variations, executes AI candidate curation, triggers native upscale,
        and saves finalized assets directly to disk.
        """
        job = await flow_service.enqueue_generation(req)
        return job

    @app.get("/api/v1/jobs", response_model=List[JobStatusResponse], tags=["Jobs"])
    async def list_jobs() -> List[JobStatusResponse]:
        """List all tracked jobs and their current statuses."""
        return flow_service.list_jobs()

    @app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
    async def get_job_status(job_id: str) -> JobStatusResponse:
        """Query real-time progress, previews, and download links for a specific job."""
        job = flow_service.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )
        return job

    @app.post(
        "/api/v1/jobs/{job_id}/upscale",
        response_model=JobStatusResponse,
        tags=["Jobs"],
    )
    async def trigger_manual_upscale(
        job_id: str, req: UpscaleRequest
    ) -> JobStatusResponse:
        """Trigger native Google Flow upscale on demand for candidate variations."""
        try:
            return await flow_service.trigger_manual_upscale(job_id, req)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.get("/api/v1/jobs/{job_id}/download", tags=["Jobs"])
    async def download_job_asset(
        job_id: str,
        asset_index: int = Query(0, description="Index of output asset to retrieve"),
    ):
        """Direct file download of generated and upscaled MP4 or JPG asset."""
        job = flow_service.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )
        if not job.final_output_paths or asset_index >= len(job.final_output_paths):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No downloaded assets ready for job '{job_id}' at index {asset_index}.",
            )
        file_path = job.final_output_paths[asset_index]
        media_type = "video/mp4" if file_path.endswith(".mp4") else "image/jpeg"
        return FileResponse(path=file_path, media_type=media_type, filename=file_path.split("\\")[-1])

    return app


# Module-level app instance for uvicorn runner
app = create_app()


def start_server(host: str = DEFAULT_API_HOST, port: int = DEFAULT_API_PORT) -> None:
    """Run server synchronously via uvicorn."""
    import uvicorn
    print("\n" + "=" * 65)
    print(f"  GOOGLE FLOW INDUSTRIAL REST API — SWAGGER DOCS AT:")
    print(f"  http://{host}:{port}/docs")
    print("=" * 65 + "\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
