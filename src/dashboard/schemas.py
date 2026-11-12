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


# ── Audio & Narration Models ─────────────────────────

class NarrationRequest(BaseModel):
    script: str
    emotion: Optional[str] = "Speak with controlled urgency and rising dread, deep baritone documentary tone, sharp articulation."
    speed: Optional[float] = 1.0
    account: Optional[Any] = 4
    engine: Optional[str] = "auto"  # "auto", "deepgram", "cosyvoice", or "kokoro"
    voice: Optional[str] = "aura-helios-en"


class NarrationResponse(BaseModel):
    success: bool
    message: str
    audio_file: Optional[str] = None
    audio_url: Optional[str] = None
    duration_sec: Optional[float] = None
    size_bytes: Optional[int] = None
    provider: Optional[str] = None
    cost_usd: Optional[float] = None



class NarrationItem(BaseModel):
    filename: str
    path: str
    size_bytes: int
    created_at: str
    audio_url: str


# ── Music & Soundtrack Models ───────────────────────

class MusicRequest(BaseModel):
    preset: Optional[str] = "hans_zimmer_tension"
    style: Optional[str] = None
    structure: Optional[str] = None
    duration_sec: Optional[float] = 180.0
    use_runninghub: Optional[bool] = True


class MusicResponse(BaseModel):
    success: bool
    message: str
    audio_file: Optional[str] = None
    audio_url: Optional[str] = None
    duration_sec: Optional[float] = None
    style_used: Optional[str] = None
    engine: Optional[str] = None
    size_bytes: Optional[int] = None



# ── 3-Stem Multitrack Audio Mix Models ──────────────

class AudioMixRequest(BaseModel):
    voice_file: str
    soundtrack_file: Optional[str] = None
    foley_file: Optional[str] = None
    output_filename: Optional[str] = None
    music_volume: Optional[float] = 0.15
    foley_volume: Optional[float] = 0.35
    ducking: Optional[bool] = True


class AudioMixResponse(BaseModel):
    success: bool
    message: str
    mix_file: Optional[str] = None
    mix_url: Optional[str] = None
    size_bytes: Optional[int] = None


# ── MiniMax H3 Cinematic Video Models ───────────────

class MiniMaxH3VideoRequest(BaseModel):
    prompt: str
    reference_image: Optional[str] = None
    duration_sec: Optional[float] = 10.0
    camera_movement: Optional[str] = "Slow cinematic push-in dolly track forward"
    lighting: Optional[str] = "Volumetric cinematic rim lighting, atmospheric shadows, 2.39:1 letterbox"
    use_runninghub: Optional[bool] = True


class MiniMaxH3VideoResponse(BaseModel):
    success: bool
    message: str
    video_file: Optional[str] = None
    video_url: Optional[str] = None
    duration_sec: Optional[float] = None
    engine: Optional[str] = None
    size_bytes: Optional[int] = None
    has_watermark: bool = False
    has_audio: bool = False
    audio_codec: Optional[str] = None


# ── HyperFrames & YouTube Closed-Loop Models ────────

class MotionOverlayRequest(BaseModel):
    template: str = "tactical_hud"
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


class CadenceBlueprintRequest(BaseModel):
    video_path: str
    audio_path: Optional[str] = None
    snap_tolerance_sec: float = Field(default=0.18, ge=0.02, le=1.0)
    save_json: bool = False


class CadenceBlueprintResponse(BaseModel):
    source_video: str
    pacing_archetype: str
    total_duration_sec: float
    target_msl_sec: float
    tension_score: int
    rehook_timestamps_sec: List[float] = []
    normalized_beats: List[Dict[str, Any]] = []
    estimated_bpm: Optional[float] = None
    audio_beats: List[float] = []
    blueprint_json_path: Optional[str] = None


class SVGDeconstructRequest(BaseModel):
    image_path: str
    title: str = "DECLASSIFIED ARTIFACT"
    subtitle: str = "SEMANTIC VECTOR RECONSTRUCTION"
    max_paths: int = Field(default=48, ge=1, le=200)
    duration_sec: float = Field(default=4.0, ge=0.5, le=30.0)


class SVGDeconstructResponse(BaseModel):
    success: bool
    source_image_path: str
    svg_path: Optional[str] = None
    html_path: Optional[str] = None
    semantic_groups: List[str] = []
    path_count: int = 0
    total_vertices: int = 0
    faithful_landing_iou: float = 0.0
    smoothness_gate_passed: bool = False
    svg_markup: str = ""
    error: Optional[str] = None


class YouTubeLintRequest(BaseModel):
    title: str
    thumbnail_text: str
    chapters: Optional[Any] = None
    total_duration_sec: float = 300.0
    retention_csv: Optional[str] = None
    description: Optional[str] = ""


class YouTubeLintResponse(BaseModel):
    title_thumbnail_lint: Dict[str, Any]
    chapters_audit: Optional[Dict[str, Any]] = None
    retention_audit: Optional[Dict[str, Any]] = None
    shorts_candidates: List[Dict[str, Any]] = []


class UnitEconomicsResponse(BaseModel):
    asset_type: str
    batch_size: int
    expected_downloads_per_asset: float
    unit_cost_breakdown: Dict[str, Any]
    niches: List[Dict[str, Any]]
