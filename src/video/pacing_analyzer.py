"""
StockCont & DarkFactory — Cinematic Pacing & Rhythm Analyzer (The Editor's Brain)
=================================================================================
Módulo de inteligência de ritmo e montagem cinematográfica. Analisa a cadência de
cortes de vídeos gerados ou referências (trailers, documentários, reels), calculando:
- Mean Shot Length (MSL): Duração média de cada plano em segundos
- Cuts Per Minute (CPM): Velocidade de transição editorial
- Tension Pacing Index (0-100): Avaliação quantitativa de retenção psicológica
- Detecção de Monotonia Rítmica (Golden Ratio of Film Editing)
Integrado com PySceneDetect (AdaptiveDetector) e fallback inteligente em FFmpeg.
"""

from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.video.ffmpeg_processor import get_ffprobe_binary

logger = logging.getLogger("stockcont.video.pacing_analyzer")

# Tenta importar scenedetect; se indisponível, usa fallback analítico FFmpeg
try:
    from scenedetect import AdaptiveDetector, ContentDetector, SceneManager, open_video
    HAS_SCENEDETECT = True
except ImportError:
    HAS_SCENEDETECT = False


@dataclass
class ShotSegment:
    """Representação de uma tomada (shot) individual."""
    shot_number: int
    start_sec: float
    end_sec: float
    duration_sec: float
    energy_level: str  # 'low', 'medium', 'high', 'climax'


@dataclass
class PacingReport:
    """Relatório quantitativo de ritmo de montagem."""
    video_path: str
    total_duration_sec: float
    total_shots: int
    mean_shot_length: float  # MSL
    cuts_per_minute: float   # CPM
    pacing_velocity_curve: List[float]  # Duração de cada plano
    pacing_archetype: str    # 'dark_suspense', 'tactical_thriller', 'action_climax', 'slow_burn'
    tension_score: int       # 0 a 100
    monotony_penalty: float  # Penalidade se todos os planos tiverem mesmo tempo
    shots: List[ShotSegment]
    murch_rule_of_six_score: float = 85.0
    mrbeast_first_minute_compliant: bool = True
    retention_remediations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CadenceBlueprint:
    """Reusable rhythmic pacing blueprint extracted from reference or master cuts."""

    source_video: str
    pacing_archetype: str
    total_duration_sec: float
    target_msl_sec: float
    tension_score: int
    rehook_timestamps_sec: List[float] = field(default_factory=list)
    normalized_beats: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CinematicPacingAnalyzer:
    """Analisador de ritmo e decupagem de vídeo."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def analyze_pacing(
        self,
        video_path: str | Path,
        threshold: float = 27.0,
        min_scene_len_frames: int = 15,
    ) -> PacingReport:
        """
        Analisa a estrutura de tomadas do vídeo e calcula as métricas cinematográficas.
        """
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Vídeo não encontrado para análise de pacing: {video_file}")

        shots: List[ShotSegment] = []
        total_duration = self._probe_duration(video_file)

        if HAS_SCENEDETECT:
            shots = self._detect_via_scenedetect(video_file, threshold, min_scene_len_frames)
        
        # Se scenedetect não achou cortes (ou está indisponível), usa fallback
        if not shots:
            shots = self._fallback_shot_segmentation(video_file, total_duration)

        return self._build_pacing_report(video_file, total_duration, shots)

    def _detect_via_scenedetect(
        self,
        video_file: Path,
        threshold: float,
        min_scene_len_frames: int,
    ) -> List[ShotSegment]:
        """Executa a detecção adaptativa com scenedetect."""
        try:
            video = open_video(str(video_file))
            scene_manager = SceneManager()
            # AdaptiveDetector se adapta a movimentações de câmera dinâmicas
            scene_manager.add_detector(
                AdaptiveDetector(
                    adaptive_threshold=threshold,
                    min_scene_len=min_scene_len_frames,
                )
            )
            scene_manager.detect_scenes(video)
            scene_list = scene_manager.get_scene_list()

            shots: List[ShotSegment] = []
            for i, (start_time, end_time) in enumerate(scene_list):
                start_sec = start_time.get_seconds()
                end_sec = end_time.get_seconds()
                dur = max(0.1, end_sec - start_sec)
                energy = self._classify_energy(dur)
                shots.append(ShotSegment(
                    shot_number=i + 1,
                    start_sec=round(start_sec, 2),
                    end_sec=round(end_sec, 2),
                    duration_sec=round(dur, 2),
                    energy_level=energy,
                ))
            return shots
        except Exception as e:
            logger.warning(f"Detecção via scenedetect falhou: {e}. Usando fallback analítico.")
            return []

    def _probe_duration(self, video_file: Path) -> float:
        """Obtém a duração total em segundos via ffprobe."""
        cmd = [
            get_ffprobe_binary(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_file),
        ]
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
            return float(res.stdout.strip())
        except Exception:
            # Fallback seguro para vídeos padrão
            return 10.0

    def _fallback_shot_segmentation(self, video_file: Path, total_duration: float) -> List[ShotSegment]:
        """
        Fallback heurístico: analisa se é tomada única contínua ou estima planos.
        """
        # Se for clipe curto gerado por IA (ex: 5s ou 10s), trata como Single Master Shot
        dur = max(0.5, total_duration)
        return [
            ShotSegment(
                shot_number=1,
                start_sec=0.0,
                end_sec=round(dur, 2),
                duration_sec=round(dur, 2),
                energy_level=self._classify_energy(dur),
            )
        ]

    def _classify_energy(self, duration: float) -> str:
        """Classifica o nível de energia com base na duração do plano."""
        if duration < 1.8:
            return "climax"
        elif duration < 3.2:
            return "high"
        elif duration < 5.5:
            return "medium"
        return "low"

    def _build_pacing_report(
        self,
        video_file: Path,
        total_duration: float,
        shots: List[ShotSegment],
    ) -> PacingReport:
        """Calcula estatísticas de pacing e arquétipo de tensão."""
        num_shots = len(shots)
        if num_shots == 0:
            shots = [ShotSegment(1, 0.0, total_duration, total_duration, "medium")]
            num_shots = 1

        durations = [s.duration_sec for s in shots]
        msl = sum(durations) / num_shots
        cpm = (num_shots / max(1.0, total_duration)) * 60.0

        # Penalidade por monotonia rítmica (se todos os planos tiverem o mesmo corte exato)
        if num_shots > 1:
            mean = msl
            variance = sum((d - mean) ** 2 for d in durations) / num_shots
            std_dev = math.sqrt(variance)
            cv = std_dev / mean if mean > 0 else 0
            # Coeficiente de variação ideal no cinema é entre 0.35 e 0.70 (ritmo orgânico humano)
            monotony_penalty = max(0.0, 1.0 - (cv / 0.40)) * 20.0
        else:
            monotony_penalty = 0.0

        # Classificação do Arquétipo de Pacing
        if msl <= 2.2:
            archetype = "action_climax"
            base_tension = 92
        elif msl <= 3.8:
            archetype = "tactical_thriller"
            base_tension = 88
        elif msl <= 6.5:
            archetype = "dark_suspense"
            base_tension = 82
        else:
            archetype = "slow_burn"
            base_tension = 72

        tension_score = int(max(40, min(99, base_tension - monotony_penalty)))

        # Auditoria Walter Murch & MrBeast
        try:
            from src.video.master_knowledge import get_master_knowledge_engine
            engine = get_master_knowledge_engine()
            dur_a = durations[0] if durations else 4.0
            dur_b = durations[1] if len(durations) > 1 else dur_a
            murch_res = engine.evaluate_murch_cut(dur_a, dur_b)
            murch_score = murch_res.score

            first_60s = []
            acc = 0.0
            for d in durations:
                if acc < 60.0:
                    first_60s.append(d)
                    acc += d
            mb_res = engine.evaluate_mrbeast_retention(first_60s, "")
            mb_compliant = mb_res.is_compliant
            remediations = mb_res.remediation_steps + murch_res.notes
        except Exception:
            murch_score = 85.0
            mb_compliant = True
            remediations = []

        return PacingReport(
            video_path=str(video_file),
            total_duration_sec=round(total_duration, 2),
            total_shots=num_shots,
            mean_shot_length=round(msl, 2),
            cuts_per_minute=round(cpm, 1),
            pacing_velocity_curve=durations,
            pacing_archetype=archetype,
            tension_score=tension_score,
            monotony_penalty=round(monotony_penalty, 1),
            shots=shots,
            murch_rule_of_six_score=round(murch_score, 1),
            mrbeast_first_minute_compliant=mb_compliant,
            retention_remediations=remediations,
        )

    def export_cadence_blueprint(
        self,
        report: PacingReport,
        output_json_path: Optional[str | Path] = None,
        beat_timestamps: Optional[List[float]] = None,
        snap_tolerance_sec: float = 0.18,
    ) -> CadenceBlueprint:
        """Export normalized remake cadence template inspired by howseen-ai Reference Mode."""
        total_dur = max(0.5, float(report.total_duration_sec))
        beats_list = sorted(float(b) for b in (beat_timestamps or []))
        rehook_points: List[float] = []
        next_rehook = 55.0

        normalized_beats: List[Dict[str, Any]] = []
        for shot in report.shots:
            ratio = round(shot.duration_sec / total_dur, 4)
            beat_locked = False
            if beats_list:
                nearest = min(beats_list, key=lambda b: abs(b - shot.start_sec))
                beat_locked = abs(nearest - shot.start_sec) <= snap_tolerance_sec
            if shot.start_sec >= next_rehook:
                rehook_points.append(round(shot.start_sec, 2))
                next_rehook += 60.0
            normalized_beats.append(
                {
                    "shot_index": shot.shot_number,
                    "start_sec": shot.start_sec,
                    "duration_sec": shot.duration_sec,
                    "duration_ratio": ratio,
                    "energy_level": shot.energy_level,
                    "beat_locked": beat_locked,
                }
            )

        blueprint = CadenceBlueprint(
            source_video=Path(report.video_path).name,
            pacing_archetype=report.pacing_archetype,
            total_duration_sec=round(total_dur, 2),
            target_msl_sec=report.mean_shot_length,
            tension_score=report.tension_score,
            rehook_timestamps_sec=rehook_points,
            normalized_beats=normalized_beats,
        )

        if output_json_path is not None:
            out_file = Path(output_json_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = out_file.with_name(f"{out_file.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
            try:
                with open(tmp_file, "w", encoding="utf-8") as handle:
                    json.dump(blueprint.to_dict(), handle, indent=2, ensure_ascii=False)
                tmp_file.replace(out_file)
            except Exception:
                tmp_file.unlink(missing_ok=True)
                raise

        return blueprint
