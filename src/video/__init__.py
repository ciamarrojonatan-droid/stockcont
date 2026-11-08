"""StockCont Video Engine Package."""
from src.video.ffmpeg_processor import (
    VideoProperties,
    create_seamless_loop,
    extract_poster_frame,
    probe_video,
    transcode_to_h264_master,
    transcode_to_prores_master,
    time_stretch_audio_complex_pro,
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
from src.video.youtube_booster import (
    YouTubeAlgorithmBoosterBridge,
    TriVariantThumbnail,
    run_youtube_booster_cli,
)
from src.video.cinematic_color import (
    FilmLookProfile,
    CinematicColorGrader,
    LookSpecification,
    LOOK_REGISTRY,
)
from src.video.pacing_analyzer import (
    CinematicPacingAnalyzer,
    PacingReport,
    ShotSegment,
)
from src.video.otio_exporter import (
    UniversalTimelineExporter,
    TimelineClipRef,
    TimelineMarker,
)
from src.video.tactical_graphics import (
    TacticalGraphicsEngine,
    LowerThirdData,
)
from src.video.cinematography_dop import (
    LensOpticsType,
    CompositionGeometry,
    LightingRatio,
    LensSpecification,
    LENS_CATALOG,
    CinematographyShotPlan,
    KeyframeCompositionAudit,
    CinematographyEngine,
)
from src.video.color_psychology import (
    ColorHarmonyType,
    ColorPsychologyArchetype,
    ColorSwatch,
    CinematicPalette,
    PALETTE_REGISTRY,
    ColorDistributionAudit,
    ColorPsychologyEngine,
)

__all__ = [
    "VideoProperties",
    "probe_video",
    "extract_poster_frame",
    "transcode_to_h264_master",
    "transcode_to_prores_master",
    "create_seamless_loop",
    "time_stretch_audio_complex_pro",
    "DarkFactoryT2VDirector",
    "T2VScene",
    "T2VShot",
    "initialize_default_darkfactory_pipeline",
    "format_minimax_prompt",
    "format_google_veo_prompt",
    "NARRATIVE_ARCHETYPES",
    "YouTubeAlgorithmBoosterBridge",
    "TriVariantThumbnail",
    "run_youtube_booster_cli",
    "FilmLookProfile",
    "CinematicColorGrader",
    "LookSpecification",
    "LOOK_REGISTRY",
    "CinematicPacingAnalyzer",
    "PacingReport",
    "ShotSegment",
    "UniversalTimelineExporter",
    "TimelineClipRef",
    "TimelineMarker",
    "TacticalGraphicsEngine",
    "LowerThirdData",
    "LensOpticsType",
    "CompositionGeometry",
    "LightingRatio",
    "LensSpecification",
    "LENS_CATALOG",
    "CinematographyShotPlan",
    "KeyframeCompositionAudit",
    "CinematographyEngine",
    "ColorHarmonyType",
    "ColorPsychologyArchetype",
    "ColorSwatch",
    "CinematicPalette",
    "PALETTE_REGISTRY",
    "ColorDistributionAudit",
    "ColorPsychologyEngine",
]
