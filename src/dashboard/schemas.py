"""Pydantic response models for the StockCont Dashboard API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


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
