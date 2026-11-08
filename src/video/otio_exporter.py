"""
StockCont & DarkFactory — Universal NLE Interchange Engine (OpenTimelineIO)
===========================================================================
Gera e exporta linhas do tempo profissionais compatíveis com DaVinci Resolve Studio,
Premiere Pro, Final Cut Pro e Blender através do padrão aberto OpenTimelineIO (ASWF/Pixar).
Estrutura multitrack com:
- Video Track 1: Tomadas Principais (Shot A / Shot B / B-roll)
- Video Track 2: Overlays Táticos, Lower-Thirds e Gráficos de Tensão
- Audio Track 1: Voz Documental / Narração EBU R128
- Audio Track 2: Trilha Sonora Épica / Sub-bass Zimmer / Drones de Tensão
- Audio Track 3: Foley Diegético e Efeitos Sonoros Táticos
- Marcadores de Linha do Tempo: Capítulos do YouTube e Batidas Narrativas
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("stockcont.video.otio_exporter")

try:
    import opentimelineio as otio
    HAS_OTIO_LIB = True
except ImportError:
    HAS_OTIO_LIB = False


@dataclass
class TimelineClipRef:
    """Referência a um clipe dentro da timeline."""
    name: str
    media_path: str
    duration_sec: float
    start_offset_sec: float = 0.0
    track_type: str = "video"  # 'video' ou 'audio'
    track_index: int = 1


@dataclass
class TimelineMarker:
    """Marcador de capítulo ou batida narrativa."""
    name: str
    timecode_sec: float
    color: str = "RED"  # 'RED', 'BLUE', 'GREEN', 'YELLOW', 'PURPLE'
    comment: str = ""


class UniversalTimelineExporter:
    """Exportador de Linha do Tempo OpenTimelineIO para NLEs profissionais."""

    def __init__(self, fps: float = 24.0):
        self.fps = fps

    def build_timeline_json(
        self,
        timeline_name: str,
        video_clips: List[TimelineClipRef],
        audio_narration_clips: Optional[List[TimelineClipRef]] = None,
        audio_music_clips: Optional[List[TimelineClipRef]] = None,
        audio_sfx_clips: Optional[List[TimelineClipRef]] = None,
        markers: Optional[List[TimelineMarker]] = None,
    ) -> Dict[str, Any]:
        """
        Monta o dicionário estruturado estritamente compatível com a especificação OTIO 1.0.
        Garante funcionamento mesmo se a biblioteca C++ não estiver presente.
        """
        tracks_data: List[Dict[str, Any]] = []

        # 1. Trilha de Vídeo Principal (V1)
        v1_children = []
        for clip in video_clips:
            v1_children.append(self._create_otio_clip_dict(clip))
        tracks_data.append({
            "OTIO_SCHEMA": "Track.1",
            "metadata": {"name": "V1_Master_Shots"},
            "name": "V1_Master_Shots",
            "kind": "Video",
            "children": v1_children,
        })

        # 2. Trilha de Áudio 1: Narração (A1)
        if audio_narration_clips:
            a1_children = [self._create_otio_clip_dict(c) for c in audio_narration_clips]
            tracks_data.append({
                "OTIO_SCHEMA": "Track.1",
                "metadata": {"name": "A1_Voiceover_EBUR128"},
                "name": "A1_Voiceover_EBUR128",
                "kind": "Audio",
                "children": a1_children,
            })

        # 3. Trilha de Áudio 2: Trilha Sonora (A2)
        if audio_music_clips:
            a2_children = [self._create_otio_clip_dict(c) for c in audio_music_clips]
            tracks_data.append({
                "OTIO_SCHEMA": "Track.1",
                "metadata": {"name": "A2_Zimmer_Tension_Score"},
                "name": "A2_Zimmer_Tension_Score",
                "kind": "Audio",
                "children": a2_children,
            })

        # 4. Trilha de Áudio 3: Foley / SFX (A3)
        if audio_sfx_clips:
            a3_children = [self._create_otio_clip_dict(c) for c in audio_sfx_clips]
            tracks_data.append({
                "OTIO_SCHEMA": "Track.1",
                "metadata": {"name": "A3_Diegetic_Foley_SFX"},
                "name": "A3_Diegetic_Foley_SFX",
                "kind": "Audio",
                "children": a3_children,
            })

        # 5. Marcadores Globais de Linha do Tempo (Capítulos YouTube / Beats)
        otio_markers = []
        for m in (markers or []):
            frame_pos = int(round(m.timecode_sec * self.fps))
            otio_markers.append({
                "OTIO_SCHEMA": "Marker.2",
                "name": m.name,
                "color": m.color,
                "comment": m.comment,
                "marked_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {
                        "OTIO_SCHEMA": "RationalTime.1",
                        "rate": self.fps,
                        "value": frame_pos,
                    },
                    "duration": {
                        "OTIO_SCHEMA": "RationalTime.1",
                        "rate": self.fps,
                        "value": 1,
                    },
                },
            })

        otio_doc = {
            "OTIO_SCHEMA": "Timeline.1",
            "metadata": {
                "generator": "StockCont DarkFactory Cinema Engine v3.0",
                "nle_target": "DaVinci Resolve Studio / Premiere Pro / Final Cut",
            },
            "name": timeline_name,
            "tracks": {
                "OTIO_SCHEMA": "Stack.1",
                "children": tracks_data,
            },
            "markers": otio_markers,
        }
        return otio_doc

    def _create_otio_clip_dict(self, clip: TimelineClipRef) -> Dict[str, Any]:
        """Cria a representação de um clipe no schema OTIO."""
        duration_frames = int(round(clip.duration_sec * self.fps))
        start_frame = int(round(clip.start_offset_sec * self.fps))

        media_url = Path(clip.media_path).as_uri() if Path(clip.media_path).is_absolute() else f"file:///{clip.media_path}"

        return {
            "OTIO_SCHEMA": "Clip.2",
            "name": clip.name,
            "media_reference": {
                "OTIO_SCHEMA": "ExternalReference.1",
                "target_url": media_url,
                "available_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": self.fps, "value": 0},
                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": self.fps, "value": duration_frames},
                },
            },
            "source_range": {
                "OTIO_SCHEMA": "TimeRange.1",
                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": self.fps, "value": start_frame},
                "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": self.fps, "value": duration_frames},
            },
        }

    def export_to_file(
        self,
        output_path: str | Path,
        timeline_name: str,
        video_clips: List[TimelineClipRef],
        audio_narration_clips: Optional[List[TimelineClipRef]] = None,
        audio_music_clips: Optional[List[TimelineClipRef]] = None,
        audio_sfx_clips: Optional[List[TimelineClipRef]] = None,
        markers: Optional[List[TimelineMarker]] = None,
    ) -> Path:
        """
        Exporta a linha do tempo para arquivo .otio pronto para o DaVinci Resolve.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Se tiver a biblioteca nativa opentimelineio, valida e escreve via lib
        if HAS_OTIO_LIB:
            try:
                timeline = otio.schema.Timeline(name=timeline_name)
                # Video Track
                v_track = otio.schema.Track(name="V1_Master_Shots", kind=otio.schema.TrackKind.Video)
                for c in video_clips:
                    media_ref = otio.schema.ExternalReference(target_url=Path(c.media_path).as_uri())
                    clip_dur = otio.opentime.RationalTime(int(round(c.duration_sec * self.fps)), self.fps)
                    clip_obj = otio.schema.Clip(
                        name=c.name,
                        media_reference=media_ref,
                        source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, self.fps), clip_dur),
                    )
                    v_track.append(clip_obj)
                timeline.tracks.append(v_track)

                # Audio Tracks
                if audio_narration_clips:
                    a1_track = otio.schema.Track(name="A1_Voiceover", kind=otio.schema.TrackKind.Audio)
                    for c in audio_narration_clips:
                        clip_dur = otio.opentime.RationalTime(int(round(c.duration_sec * self.fps)), self.fps)
                        a1_track.append(otio.schema.Clip(
                            name=c.name,
                            media_reference=otio.schema.ExternalReference(target_url=Path(c.media_path).as_uri()),
                            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, self.fps), clip_dur),
                        ))
                    timeline.tracks.append(a1_track)

                # Markers
                for m in (markers or []):
                    m_time = otio.opentime.RationalTime(int(round(m.timecode_sec * self.fps)), self.fps)
                    marker_obj = otio.schema.Marker(
                        name=m.name,
                        color=getattr(otio.schema.MarkerColor, m.color.upper(), otio.schema.MarkerColor.RED),
                        marked_range=otio.opentime.TimeRange(m_time, otio.opentime.RationalTime(1, self.fps)),
                    )
                    marker_obj.comment = m.comment
                    timeline.markers.append(marker_obj)

                otio.adapters.write_to_file(timeline, str(out_file))
                logger.info(f"Timeline OTIO exportada com sucesso via opentimelineio: {out_file.name}")
                return out_file
            except Exception as e:
                logger.warning(f"Export via lib otio falhou ({e}), utilizando gerador de schema padrão.")

        # Fallback JSON padrão OTIO Schema 1.0 (compatibilidade total e universal)
        doc = self.build_timeline_json(
            timeline_name=timeline_name,
            video_clips=video_clips,
            audio_narration_clips=audio_narration_clips,
            audio_music_clips=audio_music_clips,
            audio_sfx_clips=audio_sfx_clips,
            markers=markers,
        )
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        logger.info(f"Timeline OTIO gravada com sucesso: {out_file.name}")
        return out_file
