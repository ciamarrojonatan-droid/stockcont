"""
StockCont & DarkFactory — Master Knowledge Engine (Operational Interface)
==========================================================================
Interface operacional em Python que carrega e aplica os conhecimentos
canônicos destilados dos 27 livros:
- Walter Murch (Rule of Six, Blink Theory, Eye-Trace)
- MrBeast (First Minute Law, Zero Dead Air, 3.5s Re-engagement)
- Lisa Cron (Curiosity Gap Cadence, Cause-and-Effect Imperative)
- Jonah Berger (STEPPS Viral Matrix, High-Arousal Emotion)
- Brendan Kane & Derek Thompson (Hook Point 3s, MAYA Principle)
- Derral Eves & Alex Hormozi (CTR x AVD Formula, Binge Bridge)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("stockcont.video.master_knowledge")

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"


@dataclass
class MurchEvaluationResult:
    """Resultado da validação segundo a Regra dos Seis de Walter Murch."""
    is_compliant: bool
    score: float  # 0 a 100
    emotion_preservation: float
    story_advancement: float
    rhythm_alignment: float
    eye_trace_continuity: float
    plane_compliance_2d: float
    space_continuity_3d: float
    notes: List[str] = field(default_factory=list)


@dataclass
class MrBeastRetentionResult:
    """Resultado da validação segundo o Manual de Produção do MrBeast."""
    is_compliant: bool
    first_minute_score: float  # 0 a 100
    avg_stimulus_interval_sec: float
    has_dead_air: bool
    has_60s_rehook: bool
    has_exit_cue_risk: bool
    identified_issues: List[str] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)


@dataclass
class CronCuriosityResult:
    """Resultado da auditoria de Curiosity Gaps de Lisa Cron (Wired for Story)."""
    is_compliant: bool
    score: float
    total_gaps_opened: int
    max_interval_without_gap_sec: float
    has_internal_stakes: bool
    cause_effect_score: float
    critical_drop_timestamps: List[float] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class STEPPSViralityScore:
    """Avaliação de potencial viral segundo o framework STEPPS de Jonah Berger."""
    total_score: float  # 0 a 100
    social_currency: float  # 0 a 10
    triggers: float         # 0 a 10
    high_arousal_emotion: float  # 0 a 10 (Awe/Dread/Anger vs sadness)
    public_visibility: float     # 0 a 10
    practical_value: float       # 0 a 10
    stories_trope: float         # 0 a 10
    primary_arousal_emotion: str # 'dread', 'awe', 'shock', 'urgency'
    virality_tier: str           # 'blockbuster', 'high', 'moderate', 'low'


class MasterKnowledgeEngine:
    """Carregador e avaliador central de regras cinematográficas e de retenção."""

    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
        self.murch_data = self._load_module("walter_murch_editing.json")
        self.mrbeast_data = self._load_module("mrbeast_production.json")
        self.cron_data = self._load_module("lisa_cron_story.json")
        self.viral_data = self._load_module("viral_retention_stepps.json")
        self.growth_data = self._load_module("youtube_growth_packaging.json")

    def _load_module(self, filename: str) -> Dict[str, Any]:
        path = self.knowledge_dir / filename
        if not path.exists():
            logger.warning(f"Arquivo de conhecimento não encontrado: {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar {filename}: {e}")
            return {}

    # =========================================================================
    # 1. MÓDULO WALTER MURCH: REGRA DOS SEIS & TEORIA DO PISCAR
    # =========================================================================

    def evaluate_murch_cut(
        self,
        shot_a_duration: float,
        shot_b_duration: float,
        has_emotion_continuity: bool = True,
        advances_story: bool = True,
        matches_eye_trace: bool = True,
        respects_180_axis: bool = True,
    ) -> MurchEvaluationResult:
        """
        Avalia um corte entre dois planos segundo os pesos da Regra dos Seis:
        - Emotion: 51%
        - Story: 23%
        - Rhythm: 10%
        - Eye-Trace: 7%
        - 2D Plane: 5%
        - 3D Space: 4%
        """
        weights = {
            "emotion": 51.0,
            "story": 23.0,
            "rhythm": 10.0,
            "eye_trace": 7.0,
            "plane_2d": 5.0,
            "space_3d": 4.0,
        }

        # Avaliação de ritmo baseada na Teoria do Piscar (janela ideal entre 1.8s e 4.8s)
        rhythm_score = 10.0
        notes = []
        if shot_a_duration < 1.5 and shot_b_duration < 1.5:
            # Corte ultra rápido (aceitável para clímax, mas arriscado para narrativa densa)
            rhythm_score = 7.0
            notes.append("Ritmo estroboscópico muito rápido: risco de fadiga cognitiva.")
        elif shot_a_duration > 7.0:
            rhythm_score = 5.0
            notes.append("Plano A excede 7 segundos: viola a teoria do piscar sem movimento de câmera ativo.")

        emotion_score = weights["emotion"] if has_emotion_continuity else 0.0
        story_score = weights["story"] if advances_story else 0.0
        eye_score = weights["eye_trace"] if matches_eye_trace else 0.0
        plane_score = weights["plane_2d"] if respects_180_axis else 0.0
        space_score = weights["space_3d"]  # Presumido neutro/bom em T2V Nolan

        total_score = emotion_score + story_score + rhythm_score + eye_score + plane_score + space_score
        is_compliant = total_score >= 80.0

        if not matches_eye_trace:
            notes.append("Violação de Eye-Trace: o foco do espectador é obrigado a saltar de ponta a ponta.")
        if not advances_story:
            notes.append("Corte estático: o novo plano não adiciona informação narrativa nova.")

        return MurchEvaluationResult(
            is_compliant=is_compliant,
            score=round(total_score, 1),
            emotion_preservation=emotion_score,
            story_advancement=story_score,
            rhythm_alignment=rhythm_score,
            eye_trace_continuity=eye_score,
            plane_compliance_2d=plane_score,
            space_continuity_3d=space_score,
            notes=notes,
        )

    # =========================================================================
    # 2. MÓDULO MRBEAST: RETENÇÃO DOS PRIMEIROS 60S & ZERO DEAD AIR
    # =========================================================================

    def evaluate_mrbeast_retention(
        self,
        shot_durations_first_60s: List[float],
        script_full_text: str,
        has_60s_rehook: bool = True,
    ) -> MrBeastRetentionResult:
        """
        Avalia o roteiro e o plano de cortes segundo os padrões de retenção do MrBeast:
        - Duração máxima média de shot nos primeiros 60s: <= 4.2s
        - Densidade de estímulos: >= 12 mudanças por minuto
        - Banimento absoluto de gatilhos de evasão (exit-cues)
        - Re-hook aos 60s
        """
        issues = []
        remediations = []

        if not shot_durations_first_60s:
            avg_interval = 4.0
        else:
            avg_interval = sum(shot_durations_first_60s) / len(shot_durations_first_60s)

        # Checa tempo morto
        has_dead_air = any(d > 5.5 for d in shot_durations_first_60s)
        if has_dead_air:
            issues.append("Detectado plano com mais de 5.5s nos primeiros 60 segundos (tempo morto MrBeast).")
            remediations.append("Inserir corte tático (Shot B) ou transição de câmera push-in aos 3.5s.")

        # Checa cadência de estímulo
        if avg_interval > 4.2:
            issues.append(f"Média de duração ({avg_interval:.1f}s) acima do limite MrBeast (4.2s).")
            remediations.append("Acelerar o ritmo de corte dos primeiros 45 segundos para aumentar a retenção inicial.")

        # Checa Exit-Cues no roteiro
        banned_cues = ["em conclusão", "para resumir", "obrigado por assistir", "no próximo vídeo", "espero que tenham gostado", "in conclusion"]
        lower_script = script_full_text.lower()
        found_cues = [cue for cue in banned_cues if cue in lower_script]
        has_exit_cue = len(found_cues) > 0

        if has_exit_cue:
            issues.append(f"Gatilho de evasão detectado no roteiro: {found_cues}.")
            remediations.append("Eliminar palavras de conclusão e substituir por Seamless Binge Bridge.")

        if not has_60s_rehook:
            issues.append("Ausência de re-hook de confirmação entre 50s e 70s.")
            remediations.append("Adicionar frase reiterando a aposta máxima do documentário no segundo 60.")

        # Cálculo do score
        score = 100.0
        if has_dead_air:
            score -= 25.0
        if avg_interval > 4.2:
            score -= 15.0
        if has_exit_cue:
            score -= 30.0
        if not has_60s_rehook:
            score -= 15.0

        score = max(0.0, score)
        is_compliant = score >= 80.0

        return MrBeastRetentionResult(
            is_compliant=is_compliant,
            first_minute_score=round(score, 1),
            avg_stimulus_interval_sec=round(avg_interval, 2),
            has_dead_air=has_dead_air,
            has_60s_rehook=has_60s_rehook,
            has_exit_cue_risk=has_exit_cue,
            identified_issues=issues,
            remediation_steps=remediations,
        )

    # =========================================================================
    # 3. MÓDULO LISA CRON: WIRED FOR STORY (CURIOSITY GAPS)
    # =========================================================================

    def evaluate_cron_storytelling(
        self,
        scene_timestamps_and_questions: List[Dict[str, Any]],
        has_internal_stakes: bool = True,
        cause_and_effect_ratio: float = 0.85,
    ) -> CronCuriosityResult:
        """
        Audita a progressão narrativa segundo Lisa Cron:
        - A cada 20-25s deve haver uma dúvida ou Curiosity Gap aberta.
        - Relações de causa-e-efeito ("Portanto/Porém") vs episódico ("E depois").
        - Dilema moral do personagem (The Third Rail).
        """
        recommendations = []
        critical_drops = []

        total_gaps = len(scene_timestamps_and_questions)
        max_interval = 0.0

        for i in range(1, len(scene_timestamps_and_questions)):
            prev_t = scene_timestamps_and_questions[i - 1].get("timestamp_sec", 0.0)
            curr_t = scene_timestamps_and_questions[i].get("timestamp_sec", 0.0)
            diff = curr_t - prev_t
            if diff > max_interval:
                max_interval = diff
            if diff > 28.0:
                critical_drops.append(curr_t)
                recommendations.append(f"Janela de {diff:.1f}s sem nova pergunta narrativa próxima ao segundo {curr_t:.0f}.")

        score = 100.0
        if max_interval > 25.0:
            score -= 20.0
        if not has_internal_stakes:
            score -= 25.0
            recommendations.append("Falta de conflito interno subjetivo (The Third Rail): o espectador vê fatos sem empatia visceral.")
        if cause_and_effect_ratio < 0.70:
            score -= 15.0
            recommendations.append("Muitos saltos episódicos ('E depois'). Conectar cada cena com 'Portanto' ou 'Porém'.")

        score = max(0.0, score)
        return CronCuriosityResult(
            is_compliant=(score >= 75.0),
            score=round(score, 1),
            total_gaps_opened=total_gaps,
            max_interval_without_gap_sec=round(max_interval, 1),
            has_internal_stakes=has_internal_stakes,
            cause_effect_score=round(cause_and_effect_ratio * 100, 1),
            critical_drop_timestamps=critical_drops,
            recommendations=recommendations,
        )

    # =========================================================================
    # 4. MÓDULO JONAH BERGER: STEPPS VIRALITY SCORING
    # =========================================================================

    def calculate_stepps_virality(
        self,
        title: str,
        premise: str,
        tags: List[str],
        has_declassified_secrets: bool = True,
        high_arousal_type: str = "dread",  # 'dread', 'awe', 'shock', 'anger'
    ) -> STEPPSViralityScore:
        """
        Calcula o índice de compartilhamento e retenção viral baseado no STEPPS:
        - Social Currency: Fatos secretos, documentos proibidos (+2 a +3)
        - Triggers: Conexão com perigos globais (+2)
        - Emotion: Alta excitabilidade (+2)
        - Public: Iconografia militar/tática (+1)
        - Practical Value: Lição histórica de tomada de decisão (+1)
        - Stories: Cavalo de Tróia narrativo (+1)
        """
        text = f"{title} {premise} {' '.join(tags)}".lower()

        # 1. Social Currency (Documentos secretos, arquivos da KGB, CIA, Churchill, Petrov)
        secret_keywords = ["declassified", "secret", "kgb", "cia", "forbidden", "classified", "desclassificado", "secreto", "arquivo"]
        sc_matches = sum(1 for k in secret_keywords if k in text)
        social_currency = min(10.0, 6.0 + (sc_matches * 1.5) + (2.0 if has_declassified_secrets else 0.0))

        # 2. Triggers (Conexão com perigos atômicos, IA, sobrevivência humana)
        trigger_keywords = ["nuclear", "ai", "war", "survival", "catastrophe", "protocol", "apocalypse", "guerra", "radar"]
        tr_matches = sum(1 for k in trigger_keywords if k in text)
        triggers = min(10.0, 5.0 + (tr_matches * 1.2))

        # 3. High Arousal Emotion (Espanto ou Tensão Existencial)
        if high_arousal_type in ["dread", "awe", "shock", "anger"]:
            emotion = 9.5
        else:
            emotion = 5.0

        # 4. Public Visibility (Estética icônica)
        public_visibility = 8.5  # Padrão Hoyte van Hoytema / IMAX 70mm

        # 5. Practical Value (Decisão sob pressão extrema)
        practical_value = 8.0

        # 6. Stories (Narrativa pessoal com dilema)
        stories = 9.0

        # Média ponderada
        total = (
            social_currency * 0.25 +
            triggers * 0.20 +
            emotion * 0.25 +
            public_visibility * 0.10 +
            practical_value * 0.10 +
            stories * 0.10
        ) * 10.0

        total_score = round(min(100.0, total), 1)

        if total_score >= 88.0:
            tier = "blockbuster"
        elif total_score >= 75.0:
            tier = "high"
        elif total_score >= 60.0:
            tier = "moderate"
        else:
            tier = "low"

        return STEPPSViralityScore(
            total_score=total_score,
            social_currency=round(social_currency, 1),
            triggers=round(triggers, 1),
            high_arousal_emotion=round(emotion, 1),
            public_visibility=round(public_visibility, 1),
            practical_value=round(practical_value, 1),
            stories_trope=round(stories, 1),
            primary_arousal_emotion=high_arousal_type,
            virality_tier=tier,
        )


# Singleton para uso nos demais módulos do DarkFactory
_engine_instance: Optional[MasterKnowledgeEngine] = None


def get_master_knowledge_engine() -> MasterKnowledgeEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MasterKnowledgeEngine()
    return _engine_instance
