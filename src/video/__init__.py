"""StockCont Video Engine Package."""
from src.video.ffmpeg_processor import (
    VideoProperties,
    create_seamless_loop,
    extract_poster_frame,
    probe_video,
    transcode_to_h264_master,
    transcode_to_prores_master,
)
from src.video.darkfactory_t2v import (
    DarkFactoryT2VDirector,
    T2VScene,
    T2VShot,
    initialize_default_darkfactory_pipeline,
    format_minimax_prompt,
    format_google_veo_prompt,
    NARRATIVE_ARCHETYPES,
)

__all__ = [
    "VideoProperties",
    "create_seamless_loop",
    "extract_poster_frame",
    "probe_video",
    "transcode_to_h264_master",
    "transcode_to_prores_master",
    "DarkFactoryT2VDirector",
    "T2VScene",
    "T2VShot",
    "initialize_default_darkfactory_pipeline",
    "format_minimax_prompt",
    "format_google_veo_prompt",
    "NARRATIVE_ARCHETYPES",
]
