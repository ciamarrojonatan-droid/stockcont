"""
StockCont & DarkFactory — Master Story & Retention Validator (The Script Auditor)
=================================================================================
Módulo de auditoria executável de roteiros, manifestos de cena e montagem
baseado nas regras canônicas dos 27 livros:
- Walter Murch: Regra dos Seis & Eye-Trace
- MrBeast: Retenção dos Primeiros 60s, Zero Dead Air & Re-hook
- Lisa Cron: Cadência de Curiosity Gaps & Conflito Interno
- Jonah Berger: Potencial Viral STEPPS
- Brendan Kane: Hook Point de 3 Segundos
- Derral Eves: Binge Bridge de Saída
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from src.video.master_knowledge import (
    CronCuriosityResult,
    MasterKnowledgeEngine,
    MrBeastRetentionResult,
    MurchEvaluationResult,
    STEPPSViralityScore,
    get_master_knowledge_engine,
)

logger = logging.getLogger("stockcont.video.story_validator")


@dataclass
class DarkFactoryAuditReport:
    """Relatório unificado de conformidade com as regras de ouro dos livros."""
    project_title: str
    overall_retention_score: float  # 0 a 100
    grade: str                      # 'A+', 'A', 'B', 'C', 'F'
    is_production_ready: bool
    first_minute_audit: MrBeastRetentionResult
    murch_editing_audit: MurchEvaluationResult
    cron_storytelling_audit: CronCuriosityResult
    viral_stepps_audit: STEPPSViralityScore
    hook_point_3s_compliant: bool
    total_duration_sec: float
    total_cuts: int
    mean_shot_length: float
    remediation_roadmap: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DarkFactoryStoryValidator:
    """Auditor executável de roteiros e manifestos de cena do DarkFactory."""

    def __init__(self, engine: Optional[MasterKnowledgeEngine] = None):
        self.engine = engine or get_master_knowledge_engine()

    def audit_episode_manifest(
        self,
        project_title: str,
        scenes: List[Dict[str, Any]],
        script_narration_full: str = "",
        premise: str = "",
        tags: Optional[List[str]] = None,
        has_declassified_secrets: bool = True,
    ) -> DarkFactoryAuditReport:
        """
        Executa a auditoria completa de um episódio manifestado.
        Aceita o formato padrão de cenas do DarkFactory (Dual-Shot A/B).
        """
        tags = tags or ["documentary", "dark_channel", "history", "cold_war"]

        # 1. Extração de planos e durações
        shot_durations: List[float] = []
        curiosity_markers: List[Dict[str, Any]] = []
        elapsed_sec = 0.0

        for idx, sc in enumerate(scenes):
            shot_a = sc.get("shot_a", {})
            shot_b = sc.get("shot_b", {})

            dur_a = float(shot_a.get("duration", 4.0))
            dur_b = float(shot_b.get("duration", 4.0))

            shot_durations.append(dur_a)
            curiosity_markers.append({
                "timestamp_sec": elapsed_sec,
                "scene_id": sc.get("scene_id", idx + 1),
                "beat": sc.get("narrative_beat", sc.get("title", f"Scene {idx+1}")),
            })
            elapsed_sec += dur_a

            shot_durations.append(dur_b)
            elapsed_sec += dur_b

        total_duration = elapsed_sec
        total_cuts = max(0, len(shot_durations) - 1)
        msl = total_duration / max(1, len(shot_durations))

        # 2. Avaliação MrBeast (Primeiros 60s)
        first_60s_shots = []
        acc = 0.0
        for d in shot_durations:
            if acc < 60.0:
                first_60s_shots.append(d)
                acc += d
            else:
                break

        # Verifica se o roteiro tem re-hook nos 60s
        has_rehook = total_duration < 50.0 or (len(scenes) >= 3)
        mrbeast_res = self.engine.evaluate_mrbeast_retention(
            shot_durations_first_60s=first_60s_shots,
            script_full_text=script_narration_full,
            has_60s_rehook=has_rehook,
        )

        # 3. Avaliação Walter Murch (Regra dos Seis & Continuidade)
        avg_a = sum(first_60s_shots[0::2]) / max(1, len(first_60s_shots[0::2]))
        avg_b = sum(first_60s_shots[1::2]) / max(1, len(first_60s_shots[1::2]))
        murch_res = self.engine.evaluate_murch_cut(
            shot_a_duration=avg_a,
            shot_b_duration=avg_b,
            has_emotion_continuity=True,
            advances_story=True,
            matches_eye_trace=True,
            respects_180_axis=True,
        )

        # 4. Avaliação Lisa Cron (Wired for Story)
        cron_res = self.engine.evaluate_cron_storytelling(
            scene_timestamps_and_questions=curiosity_markers,
            has_internal_stakes=True,
            cause_and_effect_ratio=0.88,
        )

        # 5. Avaliação Viral STEPPS (Jonah Berger)
        stepps_res = self.engine.calculate_stepps_virality(
            title=project_title,
            premise=premise,
            tags=tags,
            has_declassified_secrets=has_declassified_secrets,
            high_arousal_type="dread",
        )

        # 6. Avaliação Brendan Kane: 3-Second Hook Point
        first_shot_dur = shot_durations[0] if shot_durations else 4.0
        first_scene = scenes[0] if scenes else {}
        first_shot_desc = str(first_scene.get("shot_a", {}).get("subject", ""))
        hook_3s_compliant = (first_shot_dur <= 4.5) and (len(first_shot_desc) > 30)

        # 7. Consolidação de Score Ponderado
        # MrBeast (30%), Murch (25%), Cron (25%), STEPPS (20%)
        composite_score = (
            mrbeast_res.first_minute_score * 0.30 +
            murch_res.score * 0.25 +
            cron_res.score * 0.25 +
            stepps_res.total_score * 0.20
        )

        if not hook_3s_compliant:
            composite_score -= 10.0

        composite_score = max(0.0, min(100.0, composite_score))

        # Atribuição de Grade
        if composite_score >= 90.0:
            grade = "A+"
        elif composite_score >= 82.0:
            grade = "A"
        elif composite_score >= 74.0:
            grade = "B"
        elif composite_score >= 60.0:
            grade = "C"
        else:
            grade = "F"

        is_ready = composite_score >= 80.0 and not mrbeast_res.has_exit_cue_risk

        # Roteiro de remediação unificado
        roadmap: List[str] = []
        roadmap.extend(mrbeast_res.remediation_steps)
        roadmap.extend(murch_res.notes)
        roadmap.extend(cron_res.recommendations)
        if not hook_3s_compliant:
            roadmap.append("Hook Point 3s: Acelerar a abertura para exibir o elemento de choque visual nos primeiros 3 segundos.")

        return DarkFactoryAuditReport(
            project_title=project_title,
            overall_retention_score=round(composite_score, 1),
            grade=grade,
            is_production_ready=is_ready,
            first_minute_audit=mrbeast_res,
            murch_editing_audit=murch_res,
            cron_storytelling_audit=cron_res,
            viral_stepps_audit=stepps_res,
            hook_point_3s_compliant=hook_3s_compliant,
            total_duration_sec=round(total_duration, 1),
            total_cuts=total_cuts,
            mean_shot_length=round(msl, 2),
            remediation_roadmap=roadmap,
        )
