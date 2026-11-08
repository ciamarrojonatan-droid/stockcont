"""Unit tests for DarkFactory Master Knowledge Engine and Distiller."""

import json
from pathlib import Path
import pytest

from src.video.master_knowledge import (
    MasterKnowledgeEngine,
    get_master_knowledge_engine,
    MurchEvaluationResult,
    MrBeastRetentionResult,
    CronCuriosityResult,
    STEPPSViralityScore,
)
from src.video.knowledge_distiller import MasterKnowledgeDistiller


def test_master_knowledge_distiller_scan_and_manifest(tmp_path):
    distiller = MasterKnowledgeDistiller(output_dir=tmp_path)
    books = distiller.scan_available_books()
    # If the books folder exists on this machine, it should list PDFs
    assert isinstance(books, list)

    outputs = distiller.distill_all_and_save()
    assert "walter_murch" in outputs
    assert "mrbeast" in outputs
    assert "lisa_cron" in outputs
    assert "virality" in outputs
    assert "growth" in outputs
    assert "index" in outputs

    for key, p in outputs.items():
        assert p.exists()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)


def test_murch_rule_of_six_evaluation():
    engine = get_master_knowledge_engine()
    # Good cut: 3.5s to 3.5s, emotional continuity, advances story, matches eye-trace
    res = engine.evaluate_murch_cut(
        shot_a_duration=3.5,
        shot_b_duration=3.5,
        has_emotion_continuity=True,
        advances_story=True,
        matches_eye_trace=True,
        respects_180_axis=True,
    )
    assert res.is_compliant is True
    assert res.score >= 80.0
    assert res.emotion_preservation == 51.0
    assert res.story_advancement == 23.0

    # Bad cut: breaks eye trace, doesn't advance story
    bad_res = engine.evaluate_murch_cut(
        shot_a_duration=8.0,
        shot_b_duration=3.5,
        has_emotion_continuity=True,
        advances_story=False,
        matches_eye_trace=False,
    )
    assert bad_res.is_compliant is False
    assert bad_res.score < 80.0
    assert any("Eye-Trace" in n for n in bad_res.notes)


def test_mrbeast_first_minute_retention_evaluation():
    engine = get_master_knowledge_engine()

    # Good: shots average 3.5s, no dead air, has rehook, clean script
    good_shots = [3.5, 3.0, 4.0, 3.5, 3.8, 3.2, 4.0, 3.5]
    clean_script = "Serpukhov-15. Five missiles in flight. Stanislav Petrov has 180 seconds to decide the fate of 300 million lives."
    res = engine.evaluate_mrbeast_retention(
        shot_durations_first_60s=good_shots,
        script_full_text=clean_script,
        has_60s_rehook=True,
    )
    assert res.is_compliant is True
    assert res.first_minute_score >= 80.0
    assert res.has_dead_air is False
    assert res.has_exit_cue_risk is False

    # Bad: dead air (> 5.5s), exit cues present, missing rehook
    bad_shots = [7.0, 6.0, 8.0]
    bad_script = "In conclusion, thank you for watching, and see you next time!"
    bad_res = engine.evaluate_mrbeast_retention(
        shot_durations_first_60s=bad_shots,
        script_full_text=bad_script,
        has_60s_rehook=False,
    )
    assert bad_res.is_compliant is False
    assert bad_res.has_dead_air is True
    assert bad_res.has_exit_cue_risk is True
    assert len(bad_res.identified_issues) >= 3


def test_lisa_cron_curiosity_gaps():
    engine = get_master_knowledge_engine()
    # Good pacing of narrative curiosity: questions every 10-15s
    markers = [
        {"timestamp_sec": 0.0, "beat": "Siren blares"},
        {"timestamp_sec": 12.0, "beat": "Petrov questions satellite data"},
        {"timestamp_sec": 24.0, "beat": "Command phone rings"},
        {"timestamp_sec": 38.0, "beat": "Radar confirms 5 targets"},
    ]
    res = engine.evaluate_cron_storytelling(
        scene_timestamps_and_questions=markers,
        has_internal_stakes=True,
        cause_and_effect_ratio=0.90,
    )
    assert res.is_compliant is True
    assert res.score >= 80.0
    assert res.total_gaps_opened == 4

    # Bad: huge gap of 40 seconds without new questions
    stale_markers = [
        {"timestamp_sec": 0.0, "beat": "Intro"},
        {"timestamp_sec": 45.0, "beat": "Long silent wait"},
    ]
    bad_res = engine.evaluate_cron_storytelling(
        scene_timestamps_and_questions=stale_markers,
        has_internal_stakes=False,
    )
    assert bad_res.is_compliant is False
    assert len(bad_res.critical_drop_timestamps) > 0


def test_jonah_berger_stepps_virality():
    engine = get_master_knowledge_engine()
    res = engine.calculate_stepps_virality(
        title="The Declassified Soviet Nuclear Glitch That Almost Ended the World",
        premise="Secret KGB records reveal how Stanislav Petrov disobeyed orders during an AI radar anomaly.",
        tags=["secret", "declassified", "nuclear", "war", "survival", "kgb"],
        has_declassified_secrets=True,
        high_arousal_type="dread",
    )
    assert res.total_score >= 85.0
    assert res.virality_tier in ["blockbuster", "high"]
    assert res.high_arousal_emotion >= 9.0
    assert res.primary_arousal_emotion == "dread"
