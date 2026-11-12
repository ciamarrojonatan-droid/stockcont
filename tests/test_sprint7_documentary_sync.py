"""Sprint 7 tests: Word-Timed Voice Alignment, Vector Map Animator & Documentary Composer."""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.dashboard.app import app
from src.video.ffmpeg_processor import (
    decode_audio_pcm_mono,
    get_ffmpeg_binary,
    probe_audio_duration,
    probe_video,
)


def _write_speech_bursts_wav(
    path: Path,
    bursts_sec: list[tuple[float, float]],
    total_sec: float = 5.0,
    sr: int = 16000,
) -> Path:
    """Write a synthetic WAV containing distinct vocal-like bursts separated by silence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(total_sec * sr)
    t = np.linspace(0.0, total_sec, n, endpoint=False)
    signal = np.zeros(n, dtype=np.float32)
    for start_s, end_s in bursts_sec:
        i0 = max(0, int(start_s * sr))
        i1 = min(n, int(end_s * sr))
        if i1 > i0:
            seg_t = t[i0:i1]
            signal[i0:i1] = (
                0.55 * np.sin(2.0 * np.pi * 165.0 * seg_t)
                + 0.25 * np.sin(2.0 * np.pi * 330.0 * seg_t)
            )
    pcm = np.clip(signal * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _make_sample_pd_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (640, 360), (22, 32, 46))
    img.save(path, "JPEG")
    return path


def test_decode_audio_pcm_and_probe_duration_wav_and_mp3(tmp_path):
    wav_path = _write_speech_bursts_wav(tmp_path / "sample.wav", [(0.2, 1.4), (2.2, 3.3)], total_sec=3.6)
    dur_wav = probe_audio_duration(wav_path)
    assert 3.5 <= dur_wav <= 3.7

    samples, sr = decode_audio_pcm_mono(wav_path, target_sr=16000)
    assert sr == 16000
    assert len(samples) >= int(3.5 * 16000)

    mp3_path = tmp_path / "sample.mp3"
    subprocess.run(
        [get_ffmpeg_binary(), "-y", "-i", str(wav_path), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    dur_mp3 = probe_audio_duration(mp3_path)
    assert 3.4 <= dur_mp3 <= 3.8


def test_voice_aligner_segments_by_energy_and_emits_word_triggers(tmp_path):
    from src.video.voice_aligner import VoiceAligner

    # Two distinct speech islands: [0.3, 1.5] and [2.8, 4.4] inside a 4.8s clip
    wav_path = _write_speech_bursts_wav(
        tmp_path / "narration.wav",
        [(0.3, 1.5), (2.8, 4.4)],
        total_sec=4.8,
    )
    transcript = "Classified radar telemetry detected five missiles. 1983 bunker alert triggered."
    aligner = VoiceAligner()
    result = aligner.align_transcript(
        audio_path=wav_path,
        transcript=transcript,
        trigger_keywords=["classified", "radar", "1983", "bunker"],
        save_srt=True,
    )

    assert 4.7 <= result.duration_sec <= 4.9
    assert len(result.word_timings) == len(transcript.split())
    assert result.subtitles_path is not None and Path(result.subtitles_path).is_file()
    assert "-->" in result.srt_content

    # First sentence should land near first burst, final words near second burst (not dumped into silence gap)
    first_word = result.word_timings[0]
    last_word = result.word_timings[-1]
    assert first_word.start_sec >= 0.2
    assert last_word.end_sec >= 3.8

    triggers_by_kw = {t.keyword.lower(): t for t in result.word_triggers}
    assert {"classified", "radar", "1983", "bunker"}.issubset(set(triggers_by_kw.keys()))
    assert triggers_by_kw["1983"].timestamp_sec >= 2.5


def test_voice_router_probes_real_duration_and_aligns_cosyvoice(tmp_path):
    from src.video.voice_router import ENGINE_COSYVOICE, MasterVoiceRouter

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    real_wav = _write_speech_bursts_wav(audio_dir / "cosy_out.wav", [(0.1, 3.2)], total_sec=3.5)

    router = MasterVoiceRouter(
        locks_persistence_path=tmp_path / "locks.json",
        output_dir=audio_dir,
    )
    with patch("src.factory.runninghub_bot.run_narration_bot", return_value={"saved_files": [real_wav.name]}):
        res = router.synthesize_scene(
            video_id="ep_test_01",
            scene_id="scene_01",
            script="Classified 1983 bunker signal confirmed.",
            preferred_engine=ENGINE_COSYVOICE,
        )

    assert 3.4 <= res.duration_seconds <= 3.6
    assert res.subtitles_path is not None and Path(res.subtitles_path).is_file()
    assert len(res.word_timings) == 5
    assert any(t["keyword"] == "classified" for t in res.word_triggers)


def test_map_animator_renders_seekable_svg_html_and_mp4(tmp_path):
    from src.video.map_animator import MapAnimator, MapPin, MapRoute

    animator = MapAnimator(output_dir=tmp_path / "maps")
    res = animator.render_map_animation(
        title="SERPUKHOV MISSILE CORRIDOR",
        subtitle="EARLY WARNING RADAR SECTOR",
        theater="europe_cold_war",
        pins=[
            MapPin(label="SERPUKHOV-15", lat=54.91, lon=37.41, timestamp_sec=0.4),
            MapPin(label="NORAD CHEYENNE", lat=38.74, lon=-104.84, timestamp_sec=1.2),
        ],
        routes=[
            MapRoute(
                origin_lat=54.91,
                origin_lon=37.41,
                dest_lat=52.52,
                dest_lon=13.40,
                label="ALERT VECTOR",
                start_sec=0.6,
                duration_sec=1.4,
            )
        ],
        duration_sec=2.5,
        width=640,
        height=360,
        fps=24,
        editorial_12fps=True,
    )

    assert res.success is True
    assert res.video_path is not None and Path(res.video_path).is_file()
    assert res.svg_path is not None and Path(res.svg_path).is_file()
    assert res.html_path is not None and Path(res.html_path).is_file()

    svg_text = Path(res.svg_path).read_text(encoding="utf-8")
    for group_id in ('id="grid"', 'id="landmass"', 'id="routes"', 'id="pins"', 'id="hud"'):
        assert group_id in svg_text

    html_text = Path(res.html_path).read_text(encoding="utf-8")
    assert "window.__timelines" in html_text
    assert "paused: true" in html_text

    props = probe_video(res.video_path)
    assert props.width == 640
    assert props.height == 360
    assert props.duration_seconds >= 2.2
    assert props.has_audio is False


def test_documentary_composer_golden_slice_end_to_end(tmp_path):
    from src.video.documentary_composer import DocumentaryComposer
    from src.video.research_engine import DossierFactPack, FactCitation, MediaAssetRef

    wav_path = _write_speech_bursts_wav(
        tmp_path / "voice.wav",
        [(0.2, 1.4), (1.7, 3.0)],
        total_sec=3.2,
    )
    pd_img = _make_sample_pd_image(tmp_path / "pd_archive.jpg")

    fake_pack = DossierFactPack(
        topic="1983 Serpukhov Radar",
        slug="1983-serpukhov-radar",
        facts=[
            FactCitation(
                statement="On September 26 1983, classified radar telemetry detected five ballistic missiles.",
                source="local_dossier",
                url=pd_img.as_posix(),
            )
        ],
        media_assets=[
            MediaAssetRef(
                title="Serpukhov Archive Photo",
                source="wikimedia",
                url=pd_img.as_posix(),
                license_name="Public Domain",
                local_path=pd_img.as_posix(),
            )
        ],
        output_file=(tmp_path / "dossier.json").as_posix(),
    )

    composer = DocumentaryComposer(output_dir=tmp_path / "episodes")
    with patch.object(composer.research_engine, "build_dossier", return_value=fake_pack):
        result = composer.compose_episode(
            topic="1983 Serpukhov Radar",
            script="Classified 1983 radar telemetry detected five missiles over Serpukhov bunker.",
            narration_audio_path=wav_path,
            theater="europe_cold_war",
            width=640,
            height=360,
            fps=24,
        )

    assert result.success is True
    assert Path(result.master_video_path).is_file()
    assert Path(result.otio_path).is_file()
    assert Path(result.subtitles_path).is_file()
    assert Path(result.manifest_path).is_file()
    assert len(result.word_triggers) >= 2

    otio_data = json.loads(Path(result.otio_path).read_text(encoding="utf-8"))
    track_names = [t["name"] for t in otio_data["tracks"]["children"]]
    assert "V1_Master_Shots" in track_names
    assert "V2_Tactical_Overlays" in track_names
    assert "A1_Voiceover_EBUR128" in track_names
    assert len(otio_data["markers"]) >= 1

    props = probe_video(result.master_video_path)
    assert props.has_audio is True
    assert props.duration_seconds >= 2.8


def test_sprint7_endpoints_and_path_containment(tmp_path, monkeypatch):
    monkeypatch.delenv("DASHBOARD_ACCESS_TOKEN", raising=False)
    client = TestClient(app)

    res_map = client.post(
        "/api/v1/video/map-animate",
        json={
            "title": "NORTH ATLANTIC CORRIDOR",
            "subtitle": "NAVAL TELEMETRY",
            "theater": "north_atlantic",
            "duration_sec": 2.0,
            "width": 640,
            "height": 360,
            "fps": 24,
        },
    )
    assert res_map.status_code == 200
    body_map = res_map.json()
    assert body_map["success"] is True
    assert Path(body_map["video_path"]).is_file()

    # Path traversal blocked on narration_audio_path
    res_bad = client.post(
        "/api/v1/video/compose-dossier",
        json={
            "topic": "Traversal Guard",
            "script": "Classified radar test.",
            "narration_audio_path": "../../Windows/System32/drivers/etc/hosts",
        },
    )
    assert res_bad.status_code == 400
