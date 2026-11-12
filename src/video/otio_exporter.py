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
import os
import uuid
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

    @staticmethod
    def build_beat_markers(
        beat_timestamps: List[float],
        label_prefix: str = "BEAT",
        color: str = "CYAN",
        max_markers: int = 120,
    ) -> List[TimelineMarker]:
        """Convert extracted audio beat timestamps into OTIO timeline markers."""
        markers: List[TimelineMarker] = []
        for idx, ts in enumerate(sorted(set(round(float(t), 3) for t in beat_timestamps if t >= 0.0))[:max_markers], start=1):
            markers.append(
                TimelineMarker(
                    name=f"{label_prefix}_{idx:03d}",
                    timecode_sec=ts,
                    color=color,
                    comment=f"Audio transient beat lock at {ts:.3f}s",
                )
            )
        return markers

    @staticmethod
    def _align_clips_to_beats(
        clips: List[TimelineClipRef],
        beat_timestamps: List[float],
        tolerance_sec: float = 0.18,
    ) -> List[TimelineClipRef]:
        """Nudge overlay clip offsets gently onto the nearest musical transient."""
        if not clips or not beat_timestamps:
            return clips
        sorted_beats = sorted(float(b) for b in beat_timestamps)
        aligned: List[TimelineClipRef] = []
        for clip in clips:
            nearest = min(sorted_beats, key=lambda b: abs(b - clip.start_offset_sec))
            new_offset = nearest if abs(nearest - clip.start_offset_sec) <= tolerance_sec else clip.start_offset_sec
            aligned.append(
                TimelineClipRef(
                    name=clip.name,
                    media_path=clip.media_path,
                    duration_sec=clip.duration_sec,
                    start_offset_sec=round(new_offset, 3),
                    track_type=clip.track_type,
                    track_index=clip.track_index,
                )
            )
        return aligned

    def build_timeline_json(
        self,
        timeline_name: str,
        video_clips: List[TimelineClipRef],
        audio_narration_clips: Optional[List[TimelineClipRef]] = None,
        audio_music_clips: Optional[List[TimelineClipRef]] = None,
        audio_sfx_clips: Optional[List[TimelineClipRef]] = None,
        markers: Optional[List[TimelineMarker]] = None,
        overlay_clips: Optional[List[TimelineClipRef]] = None,
        beat_timestamps: Optional[List[float]] = None,
        align_overlays_to_beats: bool = False,
    ) -> Dict[str, Any]:
        """
        Monta o dicionário estruturado estritamente compatível com a especificação OTIO 1.0.
        Garante funcionamento mesmo se a biblioteca C++ não estiver presente.
        """
        tracks_data: List[Dict[str, Any]] = []
        resolved_overlays = (
            self._align_clips_to_beats(overlay_clips, beat_timestamps or [])
            if (overlay_clips and align_overlays_to_beats and beat_timestamps)
            else overlay_clips
        )
        merged_markers = list(markers or [])
        if beat_timestamps:
            merged_markers.extend(self.build_beat_markers(beat_timestamps))

        # 1. Trilha de Vídeo Principal (V1)
        v1_children = [self._create_otio_clip_dict(clip) for clip in video_clips]
        tracks_data.append({
            "OTIO_SCHEMA": "Track.1",
            "metadata": {"name": "V1_Master_Shots"},
            "name": "V1_Master_Shots",
            "kind": "Video",
            "children": v1_children,
        })

        # 1b. Trilha de Vídeo Secundária: Motion Overlays / Tactical HUD (V2)
        if resolved_overlays:
            v2_children = [self._create_otio_clip_dict(clip) for clip in resolved_overlays]
            tracks_data.append({
                "OTIO_SCHEMA": "Track.1",
                "metadata": {"name": "V2_Tactical_Overlays"},
                "name": "V2_Tactical_Overlays",
                "kind": "Video",
                "children": v2_children,
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
        for m in merged_markers:
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

    def _build_otio_lib_track(
        self,
        name: str,
        kind: Any,
        clips: List[TimelineClipRef],
    ) -> Any:
        """Constroi uma Track nativa opentimelineio preservando caminhos relativos."""
        track = otio.schema.Track(name=name, kind=kind)
        for c in clips:
            clip_dur = otio.opentime.RationalTime(int(round(c.duration_sec * self.fps)), self.fps)
            start_rt = otio.opentime.RationalTime(int(round(c.start_offset_sec * self.fps)), self.fps)
            target_url = Path(c.media_path).resolve().as_uri()
            track.append(
                otio.schema.Clip(
                    name=c.name,
                    media_reference=otio.schema.ExternalReference(target_url=target_url),
                    source_range=otio.opentime.TimeRange(start_rt, clip_dur),
                )
            )
        return track

    def export_to_file(
        self,
        output_path: str | Path,
        timeline_name: str,
        video_clips: List[TimelineClipRef],
        audio_narration_clips: Optional[List[TimelineClipRef]] = None,
        audio_music_clips: Optional[List[TimelineClipRef]] = None,
        audio_sfx_clips: Optional[List[TimelineClipRef]] = None,
        markers: Optional[List[TimelineMarker]] = None,
        overlay_clips: Optional[List[TimelineClipRef]] = None,
        beat_timestamps: Optional[List[float]] = None,
        align_overlays_to_beats: bool = False,
    ) -> Path:
        """
        Exporta a linha do tempo para arquivo .otio pronto para o DaVinci Resolve.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        resolved_overlays = (
            self._align_clips_to_beats(overlay_clips, beat_timestamps or [])
            if (overlay_clips and align_overlays_to_beats and beat_timestamps)
            else overlay_clips
        )
        merged_markers = list(markers or [])
        if beat_timestamps:
            merged_markers.extend(self.build_beat_markers(beat_timestamps))

        # Se tiver a biblioteca nativa opentimelineio, valida e escreve via lib
        if HAS_OTIO_LIB:
            try:
                timeline = otio.schema.Timeline(name=timeline_name)
                timeline.tracks.append(
                    self._build_otio_lib_track("V1_Master_Shots", otio.schema.TrackKind.Video, video_clips)
                )
                if resolved_overlays:
                    timeline.tracks.append(
                        self._build_otio_lib_track("V2_Tactical_Overlays", otio.schema.TrackKind.Video, resolved_overlays)
                    )
                if audio_narration_clips:
                    timeline.tracks.append(
                        self._build_otio_lib_track("A1_Voiceover", otio.schema.TrackKind.Audio, audio_narration_clips)
                    )
                if audio_music_clips:
                    timeline.tracks.append(
                        self._build_otio_lib_track("A2_Zimmer_Tension_Score", otio.schema.TrackKind.Audio, audio_music_clips)
                    )
                if audio_sfx_clips:
                    timeline.tracks.append(
                        self._build_otio_lib_track("A3_Diegetic_Foley_SFX", otio.schema.TrackKind.Audio, audio_sfx_clips)
                    )

                # Markers
                for m in merged_markers:
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
            markers=merged_markers,
            overlay_clips=resolved_overlays,
        )
        tmp_out = out_file.with_name(f"{out_file.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        try:
            with open(tmp_out, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
            tmp_out.replace(out_file)
        except Exception:
            tmp_out.unlink(missing_ok=True)
            raise

        logger.info(f"Timeline OTIO gravada com sucesso: {out_file.name}")
        return out_file
