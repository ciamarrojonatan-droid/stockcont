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


# ── Sprint 7-9: Documentary Map Sync, Foley & Storyboard Schemas ──


class MapPinInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=64)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    timestamp_sec: float = Field(0.3, ge=0.0, le=120.0)
    color_hex: str = Field("#EF4444", pattern=r"^#[0-9a-fA-F]{6}$")


class MapRouteInput(BaseModel):
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lon: float = Field(..., ge=-180.0, le=180.0)
    dest_lat: float = Field(..., ge=-90.0, le=90.0)
    dest_lon: float = Field(..., ge=-180.0, le=180.0)
    label: str = Field("", max_length=64)
    start_sec: float = Field(0.5, ge=0.0, le=120.0)
    duration_sec: float = Field(1.5, ge=0.1, le=120.0)
    color_hex: str = Field("#38BDF8", pattern=r"^#[0-9a-fA-F]{6}$")


class MapAnimateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    subtitle: str = Field("", max_length=140)
    theater: str = Field("europe_cold_war", min_length=1, max_length=60)
    pins: List[MapPinInput] = Field(default_factory=list)
    routes: List[MapRouteInput] = Field(default_factory=list)
    duration_sec: float = Field(4.0, ge=0.5, le=60.0)
    width: int = Field(1280, ge=320, le=3840)
    height: int = Field(720, ge=240, le=2160)
    fps: int = Field(24, ge=12, le=60)
    editorial_12fps: bool = True


class MapAnimateResponse(BaseModel):
    success: bool
    theater: str
    title: str
    video_path: Optional[str] = None
    svg_path: Optional[str] = None
    html_path: Optional[str] = None
    duration_sec: float = 0.0
    width: int = 1280
    height: int = 720
    fps: int = 24
    editorial_12fps: bool = True
    error: Optional[str] = None


class ComposeDossierRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=160)
    script: str = Field(..., min_length=1, max_length=20000)
    narration_audio_path: str = Field(..., min_length=1, max_length=512)
    theater: str = Field("europe_cold_war", min_length=1, max_length=60)
    trigger_keywords: Optional[List[str]] = None
    width: int = Field(1280, ge=320, le=3840)
    height: int = Field(720, ge=240, le=2160)
    fps: int = Field(24, ge=12, le=60)


class ComposeDossierResponse(BaseModel):
    success: bool
    topic: str
    slug: str
    duration_sec: float = 0.0
    master_video_path: Optional[str] = None
    map_video_path: Optional[str] = None
    otio_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    manifest_path: Optional[str] = None
    word_triggers: List[Dict[str, Any]] = Field(default_factory=list)
    facts_count: int = 0
    pd_assets_count: int = 0
    error: Optional[str] = None


class FoleyCueInput(BaseModel):
    sfx_name: str = Field(..., min_length=1, max_length=64)
    timestamp_sec: float = Field(..., ge=0.0, le=3600.0)
    gain_db: float = Field(-8.0, ge=-48.0, le=6.0)
    pan: float = Field(0.0, ge=-1.0, le=1.0)
    duration_sec: Optional[float] = Field(None, ge=0.05, le=30.0)


class FoleyTrackRequest(BaseModel):
    total_duration_sec: float = Field(..., ge=0.5, le=3600.0)
    cues: List[FoleyCueInput] = Field(default_factory=list)
    sample_rate: int = Field(44100, ge=16000, le=96000)


class FoleyTrackResponse(BaseModel):
    success: bool
    sfx_track_path: Optional[str] = None
    duration_sec: float = 0.0
    cues_applied: int = 0
    catalog_used: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class VideoReverseRequest(BaseModel):
    video_path: str = Field(..., min_length=1, max_length=512)
    topic: Optional[str] = Field(None, max_length=160)
    mode: str = Field("AUTO", max_length=16)
    use_vision: bool = False


class VideoReverseResponse(BaseModel):
    success: bool
    video_path: str
    topic: str
    mode: str
    total_duration_sec: float
    mean_shot_length: float
    shots: List[Dict[str, Any]] = Field(default_factory=list)
    story_audit: Dict[str, Any] = Field(default_factory=dict)
    manifest_path: Optional[str] = None
    error: Optional[str] = None


class StoryboardCompileRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    script: str = Field(..., min_length=1, max_length=30000)
    target_niche: str = Field("industrial_automation", min_length=1, max_length=80)
    target_duration_sec: float = Field(20.0, ge=4.0, le=3600.0)
    theater: str = Field("europe_cold_war", min_length=1, max_length=60)


class StoryboardCompileResponse(BaseModel):
    success: bool
    title: str
    slug: str
    target_niche: str
    total_duration_sec: float
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    hook_audit: Dict[str, Any] = Field(default_factory=dict)
    story_audit: Dict[str, Any] = Field(default_factory=dict)
    overlap_audit: Dict[str, Any] = Field(default_factory=dict)
    budget_estimate: Dict[str, Any] = Field(default_factory=dict)
    manifest_path: Optional[str] = None
    error: Optional[str] = None


class MonetizationPackRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=80)
    title: str = Field(..., min_length=1, max_length=140)
    subtitle: str = Field("DECLASSIFIED ARCHIVE", max_length=100)
    backdrop_path: Optional[str] = Field(None, max_length=512)
    master_video_path: Optional[str] = Field(None, max_length=512)
    broll_count: int = Field(3, ge=3, le=12)
    target_width: int = Field(3840, ge=640, le=3840)
    target_height: int = Field(2160, ge=360, le=2160)


class MonetizationPackResponse(BaseModel):
    success: bool
    project_id: str
    thumbnails: List[Dict[str, Any]] = Field(default_factory=list)
    stock_broll_pack: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ShortsRepurposeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    script: str = Field(default="", max_length=5000)
    source_video_path: Optional[str] = Field(default=None, max_length=320)
    audio_path: Optional[str] = Field(default=None, max_length=320)
    style: str = Field(default="editorial_karaoke", max_length=40)
    safe_zone_profile: str = Field(default="youtube_shorts", max_length=40)
    target_duration_sec: float = Field(default=15.0, ge=3.0, le=60.0)
    width: int = Field(default=1080, ge=360, le=2160)
    height: int = Field(default=1920, ge=640, le=3840)
    fps: int = Field(default=24, ge=12, le=60)
    export_microstock_broll: bool = True


class ShortsRepurposeResponse(BaseModel):
    success: bool
    title: str
    style: str
    safe_zone_profile: str
    short_video_path: Optional[str] = None
    ass_path: Optional[str] = None
    stock_broll_path: Optional[str] = None
    stock_broll_muted: bool = True
    manifest_path: Optional[str] = None
    width: int = 1080
    height: int = 1920
    duration_sec: float = 0.0
    window_start_sec: float = 0.0
    window_end_sec: float = 0.0
    salient_center_x: float = 0.5
    safe_zone_passed: bool = False
    alamy_blocked: bool = True
    eligible_agencies: List[str] = Field(default_factory=list)
    overlap_audit: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


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
