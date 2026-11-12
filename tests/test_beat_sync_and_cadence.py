"""Sprint 5 unit and integration tests for Audio Beat-Sync, SFX Ducking, Cadence Blueprint & Shot Cards."""

import json
from pathlib import Path
import wave

import numpy as np
import pytest

from src.analyzer.video_director import (
    SHOT_CARD_RECIPES,
    build_shot_card_directive,
    get_shot_card_recipe,
)
from src.video.audio_engine import DarkFactoryAudioEngine
from src.video.otio_exporter import TimelineClipRef, UniversalTimelineExporter
from src.video.pacing_analyzer import CinematicPacingAnalyzer, PacingReport, ShotSegment


def _write_pulsed_wav(path: Path, bpm: float = 120.0, duration_sec: float = 4.0, sr: int = 16000) -> Path:
    """Create a synthetic mono WAV with crisp transient pulses at the exact target BPM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    signal = 0.02 * np.sin(2.0 * np.pi * 60.0 * t)  # low drone floor

    interval_sec = 60.0 / bpm
    pulse_len = int(sr * 0.04)
    pulse_t = np.linspace(0, 0.04, pulse_len, endpoint=False)
    pulse_wave = 0.85 * np.sin(2.0 * np.pi * 880.0 * pulse_t) * np.exp(-pulse_t * 60.0)

    beat_time = 0.5
    while beat_time < duration_sec - 0.1:
        idx = int(beat_time * sr)
        end = min(idx + pulse_len, total_samples)
        signal[idx:end] += pulse_wave[: end - idx]
        beat_time += interval_sec

    pcm = np.clip(signal * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _write_tone_wav(path: Path, freq_hz: float, duration_sec: float = 1.5, amp: float = 0.4, sr: int = 16000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, duration_sec, int(duration_sec * sr), endpoint=False)
    pcm = np.clip(amp * np.sin(2.0 * np.pi * freq_hz * t) * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def test_analyze_audio_transients_detects_known_bpm_wav(tmp_path):
    wav_path = _write_pulsed_wav(tmp_path / "pulse_120bpm.wav", bpm=120.0, duration_sec=4.0)
    engine = DarkFactoryAudioEngine(output_dir=tmp_path)
    analysis = engine.analyze_audio_transients(wav_path)

    assert analysis.duration_sec >= 3.9
    assert len(analysis.beat_timestamps) >= 5
    assert 112.0 <= analysis.estimated_bpm <= 128.0
    assert any(abs(b - 1.0) < 0.08 for b in analysis.beat_timestamps)
    assert any(abs(b - 2.0) < 0.08 for b in analysis.beat_timestamps)


def test_snap_cut_times_to_beats_respects_tolerance_and_min_spacing():
    beats = [0.5, 1.0, 1.5, 2.0, 2.5, 5.0]
    raw_cuts = [0.0, 0.92, 1.44, 3.80, 5.08]
    snapped = DarkFactoryAudioEngine.snap_cut_times_to_beats(
        raw_cuts,
        beat_timestamps=beats,
        tolerance_sec=0.18,
        min_spacing_sec=0.50,
    )
    assert snapped[0] == 0.0
    assert snapped[1] == 1.0
    assert snapped[2] == 1.5
    assert snapped[3] == 3.8  # Outside 0.18s tolerance -> left organic
    assert snapped[4] == 5.0


def test_mix_multitrack_documentary_with_foley_sidechain_ducking(tmp_path):
    voice = _write_tone_wav(tmp_path / "voice.wav", 220.0, duration_sec=1.5, amp=0.5)
    music = _write_tone_wav(tmp_path / "music.wav", 55.0, duration_sec=1.5, amp=0.4)
    foley = _write_pulsed_wav(tmp_path / "foley.wav", bpm=120.0, duration_sec=1.5)

    out_mix = tmp_path / "master_3stem_sfx_duck.wav"
    engine = DarkFactoryAudioEngine(output_dir=tmp_path)
    result = engine.mix_multitrack_documentary(
        voice_path=voice,
        soundtrack_path=music,
        foley_path=foley,
        output_path=out_mix,
        ducking=True,
        foley_sidechain_ducking=True,
    )
    assert result.exists()
    assert result.stat().st_size > 1000


def test_pacing_analyzer_export_cadence_blueprint_atomic(tmp_path):
    shots = [
        ShotSegment(1, 0.0, 2.5, 2.5, "high"),
        ShotSegment(2, 2.5, 6.0, 3.5, "medium"),
        ShotSegment(3, 6.0, 56.0, 50.0, "low"),
        ShotSegment(4, 56.0, 60.0, 4.0, "high"),
    ]
    report = PacingReport(
        video_path=str(tmp_path / "ref_doc.mp4"),
        total_duration_sec=60.0,
        total_shots=4,
        mean_shot_length=15.0,
        cuts_per_minute=4.0,
        pacing_velocity_curve=[2.5, 3.5, 50.0, 4.0],
        pacing_archetype="tactical_thriller",
        tension_score=86,
        monotony_penalty=2.0,
        shots=shots,
    )

    analyzer = CinematicPacingAnalyzer()
    out_json = tmp_path / "cadence_blueprint.json"
    bp = analyzer.export_cadence_blueprint(
        report=report,
        output_json_path=out_json,
        beat_timestamps=[0.0, 2.45, 6.10],
    )
    assert bp.total_duration_sec == 60.0
    assert bp.rehook_timestamps_sec == [56.0]
    assert len(bp.normalized_beats) == 4
    assert bp.normalized_beats[0]["beat_locked"] is True
    assert bp.normalized_beats[1]["beat_locked"] is True
    assert bp.normalized_beats[2]["beat_locked"] is True
    assert abs(sum(b["duration_ratio"] for b in bp.normalized_beats) - 1.0) < 0.01

    assert out_json.exists()
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["pacing_archetype"] == "tactical_thriller"


def test_otio_exporter_injects_beat_markers_and_aligns_overlays(tmp_path):
    v1 = tmp_path / "v1.mp4"
    v2 = tmp_path / "hud.mp4"
    v1.write_bytes(b"v1")
    v2.write_bytes(b"v2")

    exporter = UniversalTimelineExporter(fps=24)
    doc = exporter.build_timeline_json(
        timeline_name="BeatSync_Timeline",
        video_clips=[TimelineClipRef("Master_Shot", str(v1), 6.0)],
        overlay_clips=[TimelineClipRef("HUD_Overlay", str(v2), 2.0, start_offset_sec=1.92)],
        beat_timestamps=[1.0, 2.0, 3.0],
        align_overlays_to_beats=True,
    )
    marker_names = [m["name"] for m in doc["markers"]]
    assert "BEAT_001" in marker_names
    assert "BEAT_002" in marker_names

    v2_track = next(t for t in doc["tracks"]["children"] if t["name"] == "V2_Tactical_Overlays")
    aligned_start_frames = v2_track["children"][0]["source_range"]["start_time"]["value"]
    assert aligned_start_frames == 48  # Snapped 1.92s -> 2.0s * 24fps

    otio_path = tmp_path / "beatsync.otio"
    exporter.export_to_file(
        output_path=otio_path,
        timeline_name="BeatSync_Timeline",
        video_clips=[TimelineClipRef("Master_Shot", str(v1), 6.0)],
        overlay_clips=[TimelineClipRef("HUD_Overlay", str(v2), 2.0, start_offset_sec=1.92)],
        beat_timestamps=[1.0, 2.0, 3.0],
        align_overlays_to_beats=True,
    )
    assert otio_path.exists()
    assert "BEAT_001" in otio_path.read_text(encoding="utf-8")


def test_video_director_shot_card_recipes():
    assert {"dolly_in_tension", "macro_archival_reveal", "hud_telemetry_cut", "blueprint_wipe_transition"}.issubset(
        set(SHOT_CARD_RECIPES.keys())
    )
    card = get_shot_card_recipe("macro_archival_reveal")
    assert card["recommended_overlay"] == "risograph_declassified"
    directive = build_shot_card_directive("dolly_in_tension")
    assert "Dolly-In Archival Tension" in directive
    assert "tactical_hud" in directive
    with pytest.raises(ValueError):
        get_shot_card_recipe("unknown_card")
