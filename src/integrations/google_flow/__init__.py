"""Google Flow Industrial REST API & Automation Engine package.

Exposes high-level clients, FastAPI server, auth manager, models, and service.
"""

from src.integrations.google_flow.api_server import create_app, start_server
from src.integrations.google_flow.auth_manager import GoogleFlowAuthManager
from src.integrations.google_flow.config import (
    GOOGLE_FLOW_HISTORY_FILE,
    GOOGLE_FLOW_SESSION_DIR,
    GOOGLE_VEO_QUEUE_FILE,
)
from src.integrations.google_flow.downloader import GoogleFlowDownloader
from src.integrations.google_flow.models import (
    AuthStatusResponse,
    GenerationMode,
    GenerationRequest,
    JobStatus,
    JobStatusResponse,
    MediaCandidate,
    ProjectCreateRequest,
    ProjectResponse,
    UpscaleRequest,
)
from src.integrations.google_flow.qc_curator import GoogleFlowQCCurator
from src.integrations.google_flow.rpc_client import GoogleFlowRPCClient
from src.integrations.google_flow.service import GoogleFlowService

__all__ = [
    "create_app",
    "start_server",
    "GoogleFlowAuthManager",
    "GoogleFlowRPCClient",
    "GoogleFlowQCCurator",
    "GoogleFlowDownloader",
    "GoogleFlowService",
    "GenerationRequest",
    "GenerationMode",
    "JobStatus",
    "JobStatusResponse",
    "MediaCandidate",
    "ProjectCreateRequest",
    "ProjectResponse",
    "UpscaleRequest",
    "AuthStatusResponse",
    "GOOGLE_FLOW_SESSION_DIR",
    "GOOGLE_FLOW_HISTORY_FILE",
    "GOOGLE_VEO_QUEUE_FILE",
]
