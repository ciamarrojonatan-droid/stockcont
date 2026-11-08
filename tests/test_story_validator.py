"""Unit tests for DarkFactory Story & Retention Validator."""

import pytest
from src.video.story_validator import DarkFactoryStoryValidator, DarkFactoryAuditReport


def test_story_validator_with_cold_war_manifest():
    validator = DarkFactoryStoryValidator()

    # Exemplary high-retention DarkFactory scene manifest
    scenes = [
        {
            "scene_id": 1,
            "title": "False Alarm Beacon",
            "narrative_beat": "Serpukhov-15 bunker sirens ignite under emergency red strobes.",
            "shot_a": {"duration": 3.8, "subject": "Soviet duty officer Lieutenant Colonel Petrov staring in sheer disbelief at the flashing klaxon."},
            "shot_b": {"duration": 4.0, "subject": "Macro probe lens drifting across glowing green phosphor CRT screen showing ballistic trajectories."},
        },
        {
            "scene_id": 2,
            "title": "Defying Protocol",
            "narrative_beat": "Petrov grasps the bakelite phone, refusing to confirm automated retaliatory strike.",
            "shot_a": {"duration": 3.5, "subject": "Petrov with beads of cold sweat on his forehead, speaking with hushed intensity into the receiver."},
            "shot_b": {"duration": 3.8, "subject": "Mechanical analog timer ticking down towards zero with relentless precision."},
        },
        {
            "scene_id": 3,
            "title": "The Sixty Second Rehook",
            "narrative_beat": "The computer repeats confirmation. Petrov has 30 seconds left.",
            "shot_a": {"duration": 3.5, "subject": "Wide tracking shot of the bunker control room frozen in stunned dread."},
            "shot_b": {"duration": 4.0, "subject": "Close-up on the radar satellite glitch telemetry."},
        },
    ]

    clean_narration = "At 12:15 AM, the Serpukhov-15 early warning satellite confirmed what every officer dreaded. Five nuclear warheads were already in flight."
    report = validator.audit_episode_manifest(
        project_title="The 1983 Soviet Glitch: 20 Minutes to Armageddon",
        scenes=scenes,
        script_narration_full=clean_narration,
        premise="Declassified KGB military archives reveal how Stanislav Petrov disobeyed orders during an AI radar anomaly.",
        tags=["declassified", "nuclear", "war", "kgb", "survival"],
    )

    assert isinstance(report, DarkFactoryAuditReport)
    assert report.overall_retention_score >= 80.0
    assert report.grade in ["A+", "A"]
    assert report.is_production_ready is True
    assert report.hook_point_3s_compliant is True
    assert report.total_cuts == 5  # 6 shots -> 5 cuts
    assert report.mean_shot_length <= 4.2
    assert report.first_minute_audit.has_exit_cue_risk is False

    d = report.to_dict()
    assert "overall_retention_score" in d
    assert "remediation_roadmap" in d


def test_story_validator_catches_bad_retention():
    validator = DarkFactoryStoryValidator()

    # Manifest with extreme dead air, exit cues and no curiosity progression
    bad_scenes = [
        {
            "scene_id": 1,
            "title": "Boring Intro",
            "narrative_beat": "A generic introduction to the cold war.",
            "shot_a": {"duration": 9.0, "subject": "Static map on wall"},
            "shot_b": {"duration": 8.0, "subject": "Empty hallway"},
        }
    ]
    bad_narration = "In conclusion, thank you for watching, and see you next time!"

    report = validator.audit_episode_manifest(
        project_title="Cold War Overview",
        scenes=bad_scenes,
        script_narration_full=bad_narration,
        premise="A historical lecture about missiles.",
        tags=["lecture", "history"],
        has_declassified_secrets=False,
    )

    assert report.is_production_ready is False
    assert report.first_minute_audit.has_dead_air is True
    assert report.first_minute_audit.has_exit_cue_risk is True
    assert len(report.remediation_roadmap) > 0
