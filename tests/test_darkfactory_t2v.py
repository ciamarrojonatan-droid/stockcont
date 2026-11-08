"""Tests for DarkFactory Cinema Engine — Text-to-Video (T2V) Narrative Architect."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.video.darkfactory_t2v import (
    DarkFactoryT2VDirector,
    NARRATIVE_ARCHETYPES,
    T2VScene,
    T2VShot,
    format_google_veo_prompt,
    format_minimax_prompt,
    initialize_default_darkfactory_pipeline,
)


def test_format_minimax_prompt():
    """Verify MiniMax prompt formatting includes camera movement, lighting, and negative anchors."""
    prompt = format_minimax_prompt(
        subject="Officer looking at radar screen with tension",
        camera="Slow push-in dolly track",
        lighting_palette="Deep amber warning lights, CRT green",
        duration=5.0
    )
    assert "[Camera Movement: Slow push-in dolly track]" in prompt
    assert "Officer looking at radar screen with tension" in prompt
    assert "Deep amber warning lights, CRT green" in prompt
    assert "24fps motion cadence" in prompt
    assert "no digital warping" in prompt


def test_format_google_veo_prompt():
    """Verify Google Veo prompt formatting specifies anamorphic lens, aspect ratio, and 35mm film."""
    prompt = format_google_veo_prompt(
        subject="Nuclear bunker blast doors shutting tight",
        camera="Low-angle upward crane pan",
        optics="Cooke Anamorphic 35mm f/2.0",
        lighting_palette="Emergency red strobes"
    )
    assert "2.39:1 letterbox" in prompt
    assert "Nuclear bunker blast doors shutting tight" in prompt
    assert "Camera trajectory: Low-angle upward crane pan" in prompt
    assert "Cooke Anamorphic 35mm f/2.0" in prompt
    assert "35mm motion picture film" in prompt


def test_t2v_director_create_archetype_scene(tmp_path: Path):
    """Verify creating a dual-shot scene from an archetype creates Shot A and Shot B."""
    test_json = tmp_path / "test_t2v.json"
    director = DarkFactoryT2VDirector(persistence_file=test_json)
    
    scene = director.create_scene_from_archetype("cold_war_espionage", scene_index=0)
    assert scene is not None
    assert scene["archetype"] == "cold_war_espionage"
    assert len(scene["shots"]) == 2

    shot_a = scene["shots"][0]
    shot_b = scene["shots"][1]

    assert shot_a["shot_type"] == "shot_a"
    assert shot_a["focus"] == "character_tension"
    assert "Petrov" in shot_a["subject_description"]
    assert "[Camera Movement:" in shot_a["minimax_prompt"]
    assert "2.39:1 letterbox" in shot_a["google_veo_prompt"]

    assert shot_b["shot_type"] == "shot_b"
    assert shot_b["focus"] == "tactical_macro"
    assert "CRT screen" in shot_b["subject_description"]

    # Verify atomic file persistence
    assert test_json.exists()
    with open(test_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["title"] == scene["title"]


def test_t2v_director_custom_dual_shot(tmp_path: Path):
    """Verify bespoke custom dual-shot generation."""
    test_json = tmp_path / "test_custom_t2v.json"
    director = DarkFactoryT2VDirector(persistence_file=test_json)

    res = director.create_custom_dual_shot(
        scene_title="Berlin Wall Trenchcoat Exchange",
        narrative_beat="Agent handing over microfiche under flickering streetlight",
        shot_a_subject="Spy in wet trenchcoat whispering into rain collar",
        shot_a_camera="Steadicam tracking shot moving alongside footsteps",
        shot_b_subject="Macro of gloved hands exchanging steel cigarette case",
        shot_b_camera="Macro rack focus from wet cobblestone to metal clasp"
    )

    assert res["title"] == "Berlin Wall Trenchcoat Exchange"
    assert len(res["shots"]) == 2
    assert res["shots"][0]["shot_type"] == "shot_a"
    assert res["shots"][1]["shot_type"] == "shot_b"
    assert "Spy in wet trenchcoat" in res["shots"][0]["minimax_prompt"]
    assert "gloved hands exchanging" in res["shots"][1]["google_veo_prompt"]


def test_t2v_director_export_queues(tmp_path: Path, monkeypatch):
    """Verify model export queues for MiniMax and Google Veo are created."""
    test_json = tmp_path / "t2v_prompts.json"
    minimax_q = tmp_path / "minimax_q.json"
    veo_q = tmp_path / "veo_q.json"

    monkeypatch.setattr("src.video.darkfactory_t2v.MINIMAX_QUEUE_FILE", minimax_q)
    monkeypatch.setattr("src.video.darkfactory_t2v.GOOGLE_VEO_QUEUE_FILE", veo_q)

    director = DarkFactoryT2VDirector(persistence_file=test_json)
    director.create_scene_from_archetype("cyber_warfare", scene_index=0)

    f1, f2 = director.export_model_queues()
    assert f1.exists()
    assert f2.exists()

    with open(f1, "r", encoding="utf-8") as f:
        mm_data = json.load(f)
    assert len(mm_data) == 2
    assert "minimax_prompt" in mm_data[0]

    with open(f2, "r", encoding="utf-8") as f:
        veo_data = json.load(f)
    assert len(veo_data) == 2
    assert "veo_prompt" in veo_data[0]


def test_t2v_director_stats(tmp_path: Path):
    """Verify statistics counters."""
    test_json = tmp_path / "test_stats_t2v.json"
    director = DarkFactoryT2VDirector(persistence_file=test_json)
    director.create_scene_from_archetype("cold_war_espionage", scene_index=0)
    director.create_scene_from_archetype("deep_space_scifi", scene_index=0)

    stats = director.get_stats()
    assert stats["total_scenes"] == 2
    assert stats["total_shots"] == 4
    assert stats["pending_shots"] == 4
    assert "cold_war_espionage" in stats["archetypes_available"]
