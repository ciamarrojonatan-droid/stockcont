"""Pydantic response models for the StockCont Dashboard API."""

from typing import Any, Dict, List, Optional

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
