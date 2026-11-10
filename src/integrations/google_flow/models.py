"""Pydantic schemas and data contracts for the Google Flow API.

Defines input validation, project lifecycles, generation configurations,
media candidates, job polling models, and authentication statuses.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from src.integrations.google_flow.config import (
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_DURATIONS,
    SUPPORTED_IMAGE_MODELS,
    SUPPORTED_MODES,
    SUPPORTED_SELECTION_STRATEGIES,
    SUPPORTED_VARIATIONS,
    SUPPORTED_VIDEO_MODELS,
)


class GenerationMode(str, Enum):
    """Supported generation modes."""
    TEXT_TO_VIDEO = "t2v"
    IMAGE_TO_VIDEO = "i2v"
    FRAMES_TO_VIDEO = "frames2v"
    TEXT_TO_IMAGE = "t2i"


class JobStatus(str, Enum):
    """Lifecycle status of a generation job."""
    QUEUED = "queued"
    CREATING_PROJECT = "creating_project"
    GENERATING = "generating"
    READY_FOR_REVIEW = "ready_for_review"
    UPSCALING = "upscaling"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectCreateRequest(BaseModel):
    """Payload to create a new project on Google Flow."""
    name: str = Field(..., description="Project name", min_length=2, max_length=100)
    description: Optional[str] = Field(None, description="Optional project description")
    default_aspect_ratio: str = Field("16:9", description="Default aspect ratio")

    @field_validator("default_aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        if v not in SUPPORTED_ASPECT_RATIOS:
            raise ValueError(f"Invalid aspect_ratio '{v}'. Supported: {SUPPORTED_ASPECT_RATIOS}")
        return v


class ProjectResponse(BaseModel):
    """Google Flow project metadata."""
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    flow_url: Optional[str] = None


class MediaCandidate(BaseModel):
    """A generated media variation (preview or upscaled asset)."""
    candidate_id: str
    variation_index: int = 0
    preview_url: Optional[str] = None
    upscaled_url: Optional[str] = None
    local_path: Optional[str] = None
    is_winner: bool = False
    qc_score: Optional[float] = None
    media_type: Literal["video", "image"] = "video"
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: Optional[str] = None


class GenerationRequest(BaseModel):
    """Comprehensive generation request payload."""
    prompt: str = Field(..., description="Cinematic text prompt", min_length=5)
    mode: str = Field("t2v", description="Generation mode: t2v, i2v, frames2v, t2i")
    model: str = Field("veo-2.0", description="Target model name")
    aspect_ratio: str = Field("16:9", description="Media framing ratio")
    duration_seconds: int = Field(5, description="Video duration in seconds")
    variations_count: int = Field(1, description="Number of variations (1, 2, or 4)")
    ingredients: List[str] = Field(
        default_factory=list,
        description="List of reference image paths or URLs for consistency"
    )
    start_frame: Optional[str] = Field(None, description="Path or URL to start frame image")
    end_frame: Optional[str] = Field(None, description="Path or URL to end frame image")
    negative_prompt: Optional[str] = Field(None, description="Optional negative prompt")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    auto_upscale: bool = Field(True, description="Automatically trigger upscale on completion")
    target_resolution: str = Field(
        "2k",
        description="Target resolution for download/upscale: 1k (original), 2k (enhanced), or 4k (ultra)"
    )
    selection_strategy: str = Field(
        "best_by_ai",
        description="Selection strategy: best_by_ai, upscale_all, or first"
    )
    strip_audio: bool = Field(
        False,
        description="Strip audio tracks (-an) for stock agency compliance"
    )
    project_name: Optional[str] = Field(
        None,
        description="Optional custom project name; if omitted, an auto-name is generated"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="Optional HTTP callback endpoint when job completes"
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in SUPPORTED_MODES:
            raise ValueError(f"Invalid mode '{v}'. Supported: {SUPPORTED_MODES}")
        return v

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        if v not in SUPPORTED_ASPECT_RATIOS:
            raise ValueError(f"Invalid aspect_ratio '{v}'. Supported: {SUPPORTED_ASPECT_RATIOS}")
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v not in SUPPORTED_DURATIONS:
            raise ValueError(f"Invalid duration '{v}'. Supported: {SUPPORTED_DURATIONS}")
        return v

    @field_validator("variations_count")
    @classmethod
    def validate_variations(cls, v: int) -> int:
        if v not in SUPPORTED_VARIATIONS:
            raise ValueError(f"Invalid variations_count '{v}'. Supported: {SUPPORTED_VARIATIONS}")
        return v

    @field_validator("selection_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in SUPPORTED_SELECTION_STRATEGIES:
            raise ValueError(f"Invalid selection_strategy '{v}'. Supported: {SUPPORTED_SELECTION_STRATEGIES}")
        return v

    @field_validator("target_resolution")
    @classmethod
    def validate_target_resolution(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in ["1k", "2k", "4k"]:
            raise ValueError(f"Invalid target_resolution '{v}'. Supported: ['1k', '2k', '4k']")
        return v_clean


class UpscaleRequest(BaseModel):
    """Payload to request upscale on existing job candidates."""
    candidate_ids: Optional[List[str]] = Field(
        None,
        description="Specific candidates to upscale. If empty, uses job's selection_strategy"
    )
    target_resolution: str = Field("4k", description="Target resolution: 1k, 2k, or 4k")


class JobStatusResponse(BaseModel):
    """Real-time job status response."""
    job_id: str
    project_id: str
    project_name: str
    status: JobStatus
    progress_percent: float = 0.0
    message: str = "Job initialized"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    request: GenerationRequest
    candidates: List[MediaCandidate] = Field(default_factory=list)
    final_output_paths: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class AuthStatusResponse(BaseModel):
    """Authentication status of Google Flow session."""
    authenticated: bool
    session_dir: str
    user_email: Optional[str] = None
    cookies_count: int = 0
    last_heartbeat: Optional[float] = None
    message: str
