"""
StockCont Video & Motion Engine.

Includes FFmpeg transcoding/probing, Phase 4 QuickTime/MP4 metadata injection,
HyperFrames Stock B2B Motion Engine, Motion QA Inspector, and Promo Motion Director.
"""

from src.video.ffmpeg_processor import (
    VideoProperties,
    create_seamless_loop,
    extract_poster_frame,
    get_ffmpeg_binary,
    get_ffprobe_binary,
    probe_video,
    transcode_to_h264_master,
    transcode_to_prores_master,
)
from src.video.hyperframes_engine import (
    ANATOMY_FOUR_TONE_PALETTE,
    DEFAULT_MOTION_OUTPUT_DIR,
    DEFAULT_STOCK_VIDEOS_DIR,
    MOTION_PERSONALITIES,
    MOTION_TEMPLATES,
    HyperFramesMotionEngine,
    MotionCompositionResult,
)
from src.video.motion_qa import (
    PERSONALITY_MIN_MOTION_DELTAS,
    PLATFORM_SAFE_ZONES,
    MotionQAFinding,
    MotionQAInspector,
    MotionQAReport,
    OverlapAuditResult,
    OverlapFinding,
    OverlayPlacement,
)
from src.video.promo_motion_director import (
    BANNED_TRADEMARK_TERMS,
    DEFAULT_PROMO_DIR,
    PROMO_PRESETS,
    PROMO_TONE_MATRIX,
    PromoBatchResult,
    PromoMotionAsset,
    PromoMotionDirector,
    VarietyAuditResult,
)
from src.video.video_metadata import (
    MANDATORY_AI_VIDEO_KEYWORDS,
    embed_video_metadata,
    format_video_caption,
    format_video_keywords,
    get_exiftool_path,
    inject_video_metadata_exiftool,
    inject_video_metadata_ffmpeg,
    sanitize_video_title,
)

__all__ = [
    "ANATOMY_FOUR_TONE_PALETTE",
    "BANNED_TRADEMARK_TERMS",
    "DEFAULT_MOTION_OUTPUT_DIR",
    "DEFAULT_PROMO_DIR",
    "DEFAULT_STOCK_VIDEOS_DIR",
    "HyperFramesMotionEngine",
    "MANDATORY_AI_VIDEO_KEYWORDS",
    "MOTION_PERSONALITIES",
    "MOTION_TEMPLATES",
    "MotionCompositionResult",
    "MotionQAFinding",
    "MotionQAInspector",
    "MotionQAReport",
    "OverlapAuditResult",
    "OverlapFinding",
    "OverlayPlacement",
    "PERSONALITY_MIN_MOTION_DELTAS",
    "PLATFORM_SAFE_ZONES",
    "PROMO_PRESETS",
    "PROMO_TONE_MATRIX",
    "PromoBatchResult",
    "PromoMotionAsset",
    "PromoMotionDirector",
    "VarietyAuditResult",
    "VideoProperties",
    "create_seamless_loop",
    "embed_video_metadata",
    "extract_poster_frame",
    "format_video_caption",
    "format_video_keywords",
    "get_exiftool_path",
    "get_ffmpeg_binary",
    "get_ffprobe_binary",
    "inject_video_metadata_exiftool",
    "inject_video_metadata_ffmpeg",
    "probe_video",
    "sanitize_video_title",
    "transcode_to_h264_master",
    "transcode_to_prores_master",
]
