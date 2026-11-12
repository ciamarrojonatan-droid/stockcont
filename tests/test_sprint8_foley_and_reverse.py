"""Sprint 8 TDD Suite: CC0 Foley Library, Dead-Air Trim, J/L-Cuts & Video Reverse-Engineer."""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_audio_duration


def _write_tone_with_dead_air(
    path: Path,
    sample_rate: int = 24000,
) -> Path:
    """Create WAV with burst (0.0-0.8s), 1.3s dead air (0.8-2.1s), burst (2.1-2.9s)."""
    t_b1 = np.linspace(0, 0.8, int(sample_rate * 0.8), endpoint=False, dtype=np.float32)
    b1 = (0.45 * np.sin(2.0 * np.pi * 310.0 * t_b1)).astype(np.float32)
    silence = np.zeros(int(sample_rate * 1.3), dtype=np.float32)
    t_b2 = np.linspace(0, 0.8, int(sample_rate * 0.8), endpoint=False, dtype=np.float32)
    b2 = (0.45 * np.sin(2.0 * np.pi * 440.0 * t_b2)).astype(np.float32)
    pcm = (np.clip(np.concatenate([b1, silence, b2]), -0.95, 0.95) * 32767.0).astype(np.int16)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return path


def _make_multishot_mp4(path: Path, width: int = 320, height: int = 180, fps: int = 12) -> Path:
    """Generate a 3-shot synthetic MP4 (blue dark -> red bright -> green grid)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        get_ffmpeg_binary(),
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        path.as_posix(),
    ]
    raw_frames = bytearray()
    for idx in range(fps * 3):
        if idx < fps:
            frame = np.full((height, width, 3), (95, 25, 15), dtype=np.uint8)
            cv2.circle(frame, (50 + idx * 6, 90), 18, (220, 220, 220), -1)
        elif idx < fps * 2:
            frame = np.full((height, width, 3), (30, 35, 185), dtype=np.uint8)
            cv2.rectangle(frame, (40, 35), (260, 145), (240, 210, 40), 4)
        else:
            frame = np.full((height, width, 3), (35, 130, 50), dtype=np.uint8)
            cv2.line(frame, (20, 20), (300, 160), (255, 255, 255), 3)
        raw_frames.extend(frame.tobytes())
    res = subprocess.run(cmd, input=bytes(raw_frames), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    assert res.returncode == 0, res.stderr.decode("utf-8", errors="replace")[:300]
    return path


def test_foley_library_builds_cc0_cued_wav_stem(tmp_path):
    from src.video.foley_library import FoleyCue, FoleyLibrary

    lib = FoleyLibrary()
    catalog = lib.list_catalog()
    for required in ("whoosh_subtle", "stamp_slam", "radar_ping", "teletype_burst", "sub_riser"):
        assert required in catalog
        assert catalog[required]["license"] == "CC0-1.0"

    cues = [
        FoleyCue(sfx_name="stamp_slam", timestamp_sec=0.5, gain_db=-4.0),
        FoleyCue(sfx_name="radar_ping", timestamp_sec=1.6, gain_db=-6.0),
        FoleyCue(sfx_name="whoosh_subtle", timestamp_sec=2.3, gain_db=-8.0),
    ]
    out_wav = tmp_path / "foley_stem.wav"
    res = lib.build_foley_stem(cues=cues, total_duration_sec=3.0, output_wav_path=out_wav)

    assert res.success is True
    assert out_wav.is_file()
    assert res.cues_applied == 3
    dur = probe_audio_duration(out_wav)
    assert 2.85 <= dur <= 3.15

    with wave.open(str(out_wav), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        # Energy near stamp_slam (0.5-0.75s) must clearly exceed idle silence (0.0-0.25s)
        sr = wf.getframerate() * wf.getnchannels()
        idle_rms = float(np.sqrt(np.mean(samples[: int(0.25 * sr)] ** 2)))
        cue_rms = float(np.sqrt(np.mean(samples[int(0.5 * sr) : int(0.8 * sr)] ** 2)))
        assert cue_rms > idle_rms * 4.0
        assert float(np.max(np.abs(samples))) <= 0.96


def test_audio_engine_trims_dead_air_and_mixes_auto_foley(tmp_path):
    from src.video.audio_engine import DarkFactoryAudioEngine

    speech = _write_tone_with_dead_air(tmp_path / "speech_gaps.wav")
    orig_dur = probe_audio_duration(speech)
    assert 2.8 <= orig_dur <= 3.05

    engine = DarkFactoryAudioEngine()
    trim_res = engine.trim_dead_air(
        audio_path=speech,
        output_path=tmp_path / "speech_trimmed.wav",
        silence_thresh_db=-38.0,
        min_silence_sec=0.35,
        keep_pause_sec=0.12,
    )

    assert trim_res.trimmed_duration_sec < orig_dur - 0.8
    assert trim_res.silence_spans_removed >= 1
    assert Path(trim_res.trimmed_audio_path).is_file()

    # Auto foley pre-mix pipeline (voice + music + generated CC0 foley stem)
    music = _write_tone_with_dead_air(tmp_path / "music.wav")
    mixed = engine.mix_with_auto_foley(
        voice_path=trim_res.trimmed_audio_path,
        output_path=tmp_path / "master_audio.wav",
        trigger_events=[
            {"keyword": "declassified", "timestamp_sec": 0.4},
            {"keyword": "radar", "timestamp_sec": 1.2},
        ],
        soundtrack_path=music,
    )
    assert Path(mixed.mixed_audio_path).is_file()
    assert Path(mixed.foley_stem_path).is_file()
    assert mixed.foley_cues_count == 2


def test_otio_exporter_applies_jl_cut_split_edits(tmp_path):
    from src.video.otio_exporter import TimelineClipRef, UniversalTimelineExporter

    exporter = UniversalTimelineExporter(fps=24)
    video_clips = [
        TimelineClipRef(
            name="Shot_01",
            media_path=str(tmp_path / "s1.mp4"),
            duration_sec=4.0,
            start_offset_sec=0.0,
            audio_tail_sec=0.4,   # L-cut: Shot_01 audio trails 0.4s over Shot_02
        ),
        TimelineClipRef(
            name="Shot_02",
            media_path=str(tmp_path / "s2.mp4"),
            duration_sec=5.0,
            start_offset_sec=4.0,
            audio_lead_sec=0.6,   # J-cut: next audio leads picture cut by 0.6s
            audio_tail_sec=0.4,   # L-cut: trails 0.4s
        ),
    ]
    narration_clips = [
        TimelineClipRef(name="VO_01", media_path=str(tmp_path / "vo1.wav"), duration_sec=4.0, start_offset_sec=0.0),
        TimelineClipRef(name="VO_02", media_path=str(tmp_path / "vo2.wav"), duration_sec=5.0, start_offset_sec=4.0),
    ]

    adj_video, adj_audio = exporter.apply_jl_cut_offsets(video_clips, narration_clips)
    assert adj_audio[0].duration_sec == pytest.approx(4.4, abs=0.05)  # extended or bridged on L-cut/J-cut
    assert adj_audio[1].start_offset_sec == pytest.approx(3.4, abs=0.05)  # J-cut 4.0 - 0.6 = 3.4s
    assert adj_audio[1].duration_sec == pytest.approx(6.0, abs=0.05)  # +0.6 lead +0.4 tail

    otio_path = tmp_path / "jl_cut_timeline.otio"
    exporter.export_to_file(
        output_path=otio_path,
        timeline_name="JL_Cut_Documentary",
        video_clips=adj_video,
        audio_narration_clips=adj_audio,
    )
    doc = json.loads(otio_path.read_text(encoding="utf-8"))
    tracks = {t["name"]: t for t in doc["tracks"]["children"]}
    vo2_clip = tracks["A1_Voiceover_EBUR128"]["children"][1]
    assert vo2_clip["source_range"]["start_time"]["value"] == round(3.4 * 24)


def test_video_reverse_engineer_extracts_shots_and_prompts(tmp_path):
    from src.video.video_reverse_engineer import VideoReverseEngineer

    clip = _make_multishot_mp4(tmp_path / "reference_doc.mp4")

    def fake_vision(sheet_path: Path, scene_idx: int, duration_sec: float):
        assert sheet_path.is_file()
        return {
            "subject": f"Cold War bunker radar console glow during shot {scene_idx}",
            "camera": "Slow tactile push-in dolly across brass dials",
            "lighting": "Tungsten desk lamp cutting through deep slate shadow",
            "recommended_mode": "I2V" if scene_idx % 2 == 0 else "T2VA",
        }

    engine = VideoReverseEngineer(output_dir=tmp_path / "reverse_out")
    res = engine.reverse_engineer_video(
        video_path=clip,
        topic="Cold War Reference Breakdown",
        mode="AUTO",
        vision_callback=fake_vision,
    )

    assert res.success is True
    assert len(res.shots) >= 2
    assert Path(res.manifest_path).is_file()
    for shot in res.shots:
        assert Path(shot["contact_sheet_path"]).is_file()
        assert shot["generation_mode"] in ("T2VA", "I2V", "DUAL")
        assert shot["minimax_prompt"]
        assert shot["google_veo_prompt"]
    assert res.story_audit["overall_retention_score"] > 0


def test_sprint8_endpoints_and_path_containment():
    client = TestClient(app)

    res_foley = client.post(
        "/api/v1/audio/foley-track",
        json={
            "total_duration_sec": 2.5,
            "cues": [
                {"sfx_name": "stamp_slam", "timestamp_sec": 0.4, "gain_db": -5.0},
                {"sfx_name": "radar_ping", "timestamp_sec": 1.5, "gain_db": -7.0},
            ],
        },
    )
    assert res_foley.status_code == 200
    body_foley = res_foley.json()
    assert body_foley["success"] is True
    assert Path(body_foley["sfx_track_path"]).is_file()

    # Path traversal blocked on /api/v1/video/reverse-engineer
    res_bad = client.post(
        "/api/v1/video/reverse-engineer",
        json={
            "video_path": "../../Windows/System32/cmd.exe",
            "mode": "AUTO",
        },
    )
    assert res_bad.status_code == 400
