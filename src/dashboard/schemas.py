"""Pydantic response models for the StockCont Dashboard API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class KPIData(BaseModel):
    trends: int = 0
    raw_images: int = 0
    prompts_analyzed: int = 0
    prompts_total: int = 0
    queue_generated: int = 0
    queue_total: int = 0
    queue_pending: int = 0
    queue_percent: float = 0.0
    final_images: int = 0
    cataloged: int = 0
    distributed: int = 0
    gemini_configured: bool = False


class PipelinePhaseStatus(BaseModel):
    phase: int
    name: str
    icon: str
    count: int
    total: Optional[int] = None
    status: str  # "ok", "warning", "error", "idle"
    detail: str = ""


class AgencyStatus(BaseModel):
    name: str
    key: str
    configured: bool
    uploads: int = 0
    last_upload: Optional[str] = None
    protocol: str = "FTP"


class BackupStatus(BaseModel):
    configured: bool
    mode: str = ""
    synced_count: int = 0
    last_sync: Optional[str] = None


class PipelineStatus(BaseModel):
    kpis: KPIData
    phases: List[PipelinePhaseStatus]
    agencies: List[AgencyStatus]
    backup: BackupStatus
    timestamp: str


class PromptItemResponse(BaseModel):
    prompt_text: str
    prompt_hash: str
    full_hash: Optional[str] = None
    source_id: str = ""
    prompt_id: Optional[Any] = None
    concept: str = ""
    status: str = "pending"
    generated_at: Optional[str] = None
    image_file: Optional[str] = None


class ImageItem(BaseModel):
    filename: str
    path: str
    size_bytes: int
    created_at: str
    is_cataloged: bool = False
    title: Optional[str] = None
    keywords: Optional[str] = None
    category: Optional[str] = None


class TimelineEvent(BaseModel):
    timestamp: str
    phase: Optional[int] = None
    icon: str
    message: str
    type: str = "info"


class RunPhaseResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None


class MarkGeneratedRequest(BaseModel):
    hashes: Optional[List[str]] = None
    all_pending: Optional[bool] = False


class MarkPendingRequest(BaseModel):
    hashes: Optional[List[str]] = None
    all_generated: Optional[bool] = False


class MatrixToggleRequest(BaseModel):
    filename: str
    agency: str
    uploaded: bool


class MatrixBatchRequest(BaseModel):
    agency: str
    action: Literal["mark_all", "unmark_all"]
    filenames: Optional[List[str]] = None


# ── Quality Control (QC) & Curation ──────────────────

class QCConfigRequest(BaseModel):
    mode: Optional[Literal["auto", "manual"]] = None
    min_score: Optional[float] = None
    auto_upscale: Optional[bool] = None


class QCSetStatusRequest(BaseModel):
    filename: str
    status: Literal["approved", "rejected", "pending"]
    notes: Optional[str] = ""


class QCBatchStatusRequest(BaseModel):
    filenames: List[str]
    status: Literal["approved", "rejected", "pending"]


class QCEvaluateRequest(BaseModel):
    filenames: Optional[List[str]] = None
    force: Optional[bool] = False


class QCUpscaleRequest(BaseModel):
    filenames: Optional[List[str]] = None


class QCPackageZipRequest(BaseModel):
    pack_size: Optional[int] = 10
    only_unprocessed: Optional[bool] = True
    auto_run: Optional[bool] = False


class QCRunConta2Request(BaseModel):
    batch_size: Optional[int] = 10
    mode: Optional[Literal['window', 'background']] = 'window'


# ── Video Models ─────────────────────────────────────

class VideoPromptMarkRequest(BaseModel):
    hashes: Optional[List[str]] = None
    all_pending: Optional[bool] = False
    all_generated: Optional[bool] = False


class VideoI2VRequest(BaseModel):
    image_stem: str


class VideoMatrixToggleRequest(BaseModel):
    filename: str
    agency: str
    uploaded: bool


class VideoMatrixBatchRequest(BaseModel):
    agency: str
    action: Literal["mark_all", "unmark_all"]
    filenames: Optional[List[str]] = None


# ── HyperFrames Stock Motion Models ────────────────

class MotionOverlayRequest(BaseModel):
    template: str = "saas_fintech_telemetry_ui"
    title: str
    subtitle: Optional[str] = ""
    duration_sec: float = Field(default=5.0, ge=0.5, le=60.0)
    width: int = Field(default=1280, ge=320, le=3840)
    height: int = Field(default=720, ge=240, le=2160)
    fps: int = Field(default=30, ge=1, le=60)
    preview_gate_20s: bool = False
    force_procedural: bool = True
    use_hyperframes_cli: bool = False
    muted: bool = True
    components: Optional[List[str]] = None
    seed: Optional[int] = None
    personality: Optional[str] = None
    run_qa_gate: bool = False
    image_path: Optional[str] = None


class MotionOverlayResponse(BaseModel):
    success: bool
    template: str
    category: str
    output_video_path: Optional[str] = None
    html_path: Optional[str] = None
    svg_path: Optional[str] = None
    duration_sec: float
    width: int
    height: int
    fps: int
    render_backend: str
    is_preview_gate: bool = False
    has_audio: bool = False
    error: Optional[str] = None
    seed: Optional[int] = None
    personality: Optional[str] = None
    contact_sheet_path: Optional[str] = None
    qa_report: Optional[Dict[str, Any]] = None


class MotionQARequest(BaseModel):
    video_path: str
    bg_hex: str = "#070D17"
    fg_hex: str = "#F1F5F9"
    accent_hex: Optional[str] = "#38BDF8"
    personality: str = "cold_war_noir"
    generate_sheet: bool = True
    vision_critique: bool = False


class MotionQAResponse(BaseModel):
    passed: bool
    score: float
    video_path: str
    contact_sheet_path: Optional[str] = None
    contrast_ratio: float
    min_motion_delta: float
    max_motion_delta: float
    frozen_frame_pairs: int
    safe_margin_ok: bool
    sampled_frame_count: int
    findings: List[Dict[str, Any]] = []
    vision_critique: Optional[str] = None


class UnitEconomicsResponse(BaseModel):
    asset_type: str
    batch_size: int
    expected_downloads_per_asset: float
    unit_cost_breakdown: Dict[str, Any]
    niches: List[Dict[str, Any]]


class PromoMotionBatchRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    subtitle: str = Field(default="SYNTHETIC TELEMETRY OVERVIEW", max_length=160)
    niche_id: str = Field(default="finance", max_length=80)
    count: int = Field(default=3, ge=1, le=8)
    preset: str = Field(default="AUTO", max_length=64)
    width: int = Field(default=1920, ge=640, le=3840)
    height: int = Field(default=1080, ge=360, le=2160)
    duration_sec: float = Field(default=3.0, ge=1.0, le=15.0)
    fps: int = Field(default=24, ge=12, le=60)
    strict_trademark: bool = True
    min_variety_distance: float = Field(default=0.20, ge=0.0, le=1.5)


class PromoMotionBatchResponse(BaseModel):
    success: bool
    niche_id: str
    assets: List[Dict[str, Any]] = Field(default_factory=list)
    variety_audit: Dict[str, Any] = Field(default_factory=dict)
    estimated_unit_royalty_usd: float = 0.0
    alamy_blocked: bool = True
    eligible_agencies: List[str] = Field(default_factory=list)
    manifest_path: Optional[str] = None
    error: Optional[str] = None
