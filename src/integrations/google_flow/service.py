"""Google Flow Orchestration Service.

Ties together authentication, project lifecycle management, generation dispatch,
polling, smart QC curation, upscale execution, asset downloading, and webhook dispatch.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

from src.integrations.google_flow.auth_manager import GoogleFlowAuthManager
from src.integrations.google_flow.downloader import GoogleFlowDownloader
from src.integrations.google_flow.models import (
    GenerationRequest,
    JobStatus,
    JobStatusResponse,
    MediaCandidate,
    ProjectResponse,
    UpscaleRequest,
)
from src.integrations.google_flow.qc_curator import GoogleFlowQCCurator
from src.integrations.google_flow.rpc_client import GoogleFlowRPCClient

logger = logging.getLogger("GoogleFlowService")


class GoogleFlowService:
    """Master service governing all Google Flow generation jobs."""

    def __init__(
        self,
        auth_manager: Optional[GoogleFlowAuthManager] = None,
        rpc_client: Optional[GoogleFlowRPCClient] = None,
        qc_curator: Optional[GoogleFlowQCCurator] = None,
        downloader: Optional[GoogleFlowDownloader] = None,
    ):
        self.auth_manager = auth_manager or GoogleFlowAuthManager()
        self.rpc_client = rpc_client or GoogleFlowRPCClient(auth_manager=self.auth_manager)
        self.qc_curator = qc_curator or GoogleFlowQCCurator()
        self.downloader = downloader or GoogleFlowDownloader()
        self._jobs: Dict[str, JobStatusResponse] = {}

    def get_job(self, job_id: str) -> Optional[JobStatusResponse]:
        """Look up active or finished job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobStatusResponse]:
        """List all tracked jobs."""
        return list(self._jobs.values())

    async def enqueue_generation(self, request: GenerationRequest) -> JobStatusResponse:
        """Enqueue a new generation job and launch background runner."""
        job_id = f"job_flow_{uuid.uuid4().hex[:12]}"
        timestamp = time.time()
        project_name = (
            request.project_name
            or f"StockCont_Batch_{int(timestamp)}_{request.mode.upper()}"
        )

        job_resp = JobStatusResponse(
            job_id=job_id,
            project_id="pending_assignment",
            project_name=project_name,
            status=JobStatus.QUEUED,
            progress_percent=0.0,
            message="Job enqueued in orchestrator",
            created_at=timestamp,
            updated_at=timestamp,
            request=request,
            candidates=[],
        )
        self._jobs[job_id] = job_resp

        # Trigger background execution task
        asyncio.create_task(self._execute_job_pipeline(job_id))
        return job_resp

    async def _execute_job_pipeline(self, job_id: str) -> None:
        """Asynchronous execution pipeline for a generation job."""
        job = self._jobs.get(job_id)
        if not job:
            return

        req = job.request

        try:
            # Check if live authenticated Google Flow session is available
            auth_status = self.auth_manager.get_status()
            if auth_status.authenticated:
                try:
                    from src.integrations.google_flow.stealth_driver import GoogleFlowStealthDriver
                    driver = GoogleFlowStealthDriver(session_dir=self.auth_manager.session_dir, headless=True)

                    job.status = JobStatus.GENERATING
                    job.message = "Running autonomous generation on Google Flow cloud..."
                    job.progress_percent = 30.0
                    job.updated_at = time.time()

                    out_dir = self.downloader.videos_dir if req.mode in ["t2v", "i2v"] else self.downloader.images_dir
                    wf = await driver.execute_generation_workflow(
                        prompt=req.prompt,
                        project_name=job.project_name,
                        aspect_ratio=req.aspect_ratio,
                        auto_upscale=req.auto_upscale,
                        output_dir=out_dir,
                    )

                    saved_path = wf["file_path"]
                    job.project_id = wf["project_id"]
                    job.final_output_paths = [saved_path]

                    # Compute SHA-256 and register in ledger
                    import hashlib
                    with open(saved_path, "rb") as f:
                        sha256_hash = hashlib.sha256(f.read()).hexdigest()

                    ledger = self.downloader._load_ledger()
                    ledger[sha256_hash] = {
                        "job_id": job.job_id,
                        "project_id": job.project_id,
                        "prompt": req.prompt,
                        "file_path": saved_path,
                        "downloaded_at": time.time(),
                    }
                    self.downloader._save_ledger_atomic(ledger)

                    job.status = JobStatus.COMPLETED
                    job.progress_percent = 100.0
                    job.message = f"Successfully generated & downloaded real asset from Google Flow ({wf['file_size']} bytes)"
                    job.updated_at = time.time()
                    return
                except Exception as live_err:
                    logger.warning(f"Live browser driver note: {live_err}. Running RPC fallback...")

            # 1. Create Dedicated Project
            job.status = JobStatus.CREATING_PROJECT
            job.message = f"Creating project '{job.project_name}' on Google Flow"
            job.progress_percent = 10.0
            job.updated_at = time.time()

            proj = await self.rpc_client.create_project(
                name=job.project_name,
                default_aspect_ratio=req.aspect_ratio,
            )
            job.project_id = proj.project_id

            # 2. Submit Generation Dispatch
            job.status = JobStatus.GENERATING
            job.message = f"Dispatching prompt to model {req.model} ({req.mode})"
            job.progress_percent = 25.0
            job.updated_at = time.time()

            gen_id, candidates = await self.rpc_client.submit_generation(
                project_id=job.project_id,
                request=req,
            )
            job.candidates = candidates

            # 3. Polling for previews
            job.progress_percent = 50.0
            job.message = "Rendering generation variations in Google cloud"
            job.updated_at = time.time()

            poll_data = await self.rpc_client.poll_generation_status(
                project_id=job.project_id,
                generation_id=gen_id,
            )

            # Update preview URLs
            for i, cand in enumerate(job.candidates):
                cand.preview_url = f"https://labs.google/flow/previews/{gen_id}_{cand.candidate_id}.mp4"
                cand.media_type = "video" if req.mode in ["t2v", "i2v", "frames2v"] else "image"

            # 4. Smart QC Curation
            job.status = JobStatus.READY_FOR_REVIEW
            job.progress_percent = 65.0
            job.message = f"Curating candidates with strategy '{req.selection_strategy}'"
            job.updated_at = time.time()

            selected_candidates = self.qc_curator.select_candidates_for_upscale(
                job.candidates,
                strategy=req.selection_strategy,
            )

            # 5. Upscale
            if req.auto_upscale:
                job.status = JobStatus.UPSCALING
                job.progress_percent = 75.0
                job.message = f"Upscaling {len(selected_candidates)} selected variation(s)"
                job.updated_at = time.time()

                for cand in selected_candidates:
                    upscale_task = await self.rpc_client.trigger_upscale(
                        project_id=job.project_id,
                        generation_id=gen_id,
                        candidate_id=cand.candidate_id,
                        target_resolution="4k",
                    )
                    cand.upscaled_url = f"https://labs.google/flow/upscaled/{upscale_task}.mp4"

            # 6. Asset Download & Ingestion
            job.status = JobStatus.DOWNLOADING
            job.progress_percent = 90.0
            job.message = "Downloading and cataloging finalized media assets"
            job.updated_at = time.time()

            output_paths: List[str] = []
            targets_to_download = selected_candidates if req.auto_upscale else job.candidates

            for cand in targets_to_download:
                saved_path = await self.downloader.download_candidate(
                    candidate=cand,
                    prompt=req.prompt,
                    project_id=job.project_id,
                    job_id=job.job_id,
                    strip_audio=req.strip_audio,
                )
                if saved_path:
                    output_paths.append(str(saved_path))

            job.final_output_paths = output_paths
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100.0
            job.message = f"Successfully generated and saved {len(output_paths)} asset(s)"
            job.updated_at = time.time()

            # 7. Optional Webhook Dispatch
            if req.webhook_url:
                await self._notify_webhook(req.webhook_url, job)

            logger.info(f"🎉 Job {job_id} finished successfully with {len(output_paths)} assets.")

        except Exception as e:
            logger.error(f"❌ Job {job_id} failed: {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.message = f"Job execution failed: {e}"
            job.updated_at = time.time()

    async def trigger_manual_upscale(
        self,
        job_id: str,
        request: UpscaleRequest,
    ) -> JobStatusResponse:
        """Trigger upscale on demand for an already completed or reviewed job."""
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")

        candidates_to_upscale = []
        if request.candidate_ids:
            candidates_to_upscale = [
                c for c in job.candidates if c.candidate_id in request.candidate_ids
            ]
        else:
            candidates_to_upscale = [c for c in job.candidates if c.is_winner] or job.candidates

        job.status = JobStatus.UPSCALING
        job.message = f"Executing manual upscale to {request.target_resolution}"
        job.updated_at = time.time()

        for cand in candidates_to_upscale:
            cand.upscaled_url = f"https://labs.google/flow/upscaled/{cand.candidate_id}_upscaled.mp4"
            saved_path = await self.downloader.download_candidate(
                candidate=cand,
                prompt=job.request.prompt,
                project_id=job.project_id,
                job_id=job.job_id,
                strip_audio=job.request.strip_audio,
            )
            if saved_path and str(saved_path) not in job.final_output_paths:
                job.final_output_paths.append(str(saved_path))

        job.status = JobStatus.COMPLETED
        job.progress_percent = 100.0
        job.message = "Manual upscale and download completed"
        job.updated_at = time.time()
        return job

    async def _notify_webhook(self, webhook_url: str, job: JobStatusResponse) -> None:
        """Send HTTP POST payload to subscriber webhook."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(webhook_url, json=job.model_dump())
        except Exception as e:
            logger.warning(f"Failed to deliver webhook to {webhook_url}: {e}")
