"""Unit tests for Master Voice Router & Single-Narrator Lock."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.video.voice_router import (
    ENGINE_COSYVOICE,
    ENGINE_DEEPGRAM,
    ENGINE_KOKORO_LOCAL,
    MasterVoiceRouter,
    NarratorConsistencyViolationError,
    NarratorLock,
    RoutedNarrationResult,
)


@pytest.fixture
def router(tmp_path):
    locks_file = tmp_path / "test_narrator_locks.json"
    audio_dir = tmp_path / "audio"
    return MasterVoiceRouter(locks_persistence_path=locks_file, output_dir=audio_dir)


def test_lock_and_retrieve(router):
    """Verify narrator lock creation, retrieval and persistence."""
    lock = router.lock_narrator("doc_1983", ENGINE_KOKORO_LOCAL, "bm_george")
    assert lock.video_id == "doc_1983"
    assert lock.engine == ENGINE_KOKORO_LOCAL
    assert lock.voice_id == "bm_george"

    retrieved = router.get_lock("doc_1983")
    assert retrieved is not None
    assert retrieved.engine == ENGINE_KOKORO_LOCAL
    assert retrieved.voice_id == "bm_george"


def test_release_lock(router):
    """Verify lock release clears the lock."""
    router.lock_narrator("doc_1983", ENGINE_DEEPGRAM, "aura-helios-en")
    assert router.get_lock("doc_1983") is not None

    router.release_lock("doc_1983")
    assert router.get_lock("doc_1983") is None


def test_narrator_lock_enforcement_across_scenes(router):
    """Verify that Scene 2 is forced to use the same narrator locked in Scene 1."""
    # Mock Kokoro synthesis for Scene 1
    mock_res_scene1 = RoutedNarrationResult(
        video_id="doc_coldwar",
        scene_id="scene_01",
        audio_path=router.output_dir / "scene1.wav",
        filename="scene1.wav",
        duration_seconds=5.0,
        filesize_bytes=1000,
        engine_used=ENGINE_KOKORO_LOCAL,
        voice_used="bm_george",
        is_gold_standard=False,
    )

    with patch.object(router, "_attempt_engine", return_value=mock_res_scene1):
        res1 = router.synthesize_scene(
            video_id="doc_coldwar",
            scene_id="scene_01",
            script="First scene text.",
            preferred_engine=ENGINE_KOKORO_LOCAL,
        )
        assert res1.engine_used == ENGINE_KOKORO_LOCAL
        assert res1.voice_used == "bm_george"

    # Verify lock was established
    lock = router.get_lock("doc_coldwar")
    assert lock is not None
    assert lock.engine == ENGINE_KOKORO_LOCAL
    assert lock.voice_id == "bm_george"
    assert "scene_01" in lock.scenes_completed

    # Now attempt Scene 2: Router MUST invoke Kokoro bm_george, ignoring preferred_engine
    mock_res_scene2 = RoutedNarrationResult(
        video_id="doc_coldwar",
        scene_id="scene_02",
        audio_path=router.output_dir / "scene2.wav",
        filename="scene2.wav",
        duration_seconds=6.0,
        filesize_bytes=1200,
        engine_used=ENGINE_KOKORO_LOCAL,
        voice_used="bm_george",
        is_gold_standard=False,
    )

    with patch.object(router, "_attempt_engine", return_value=mock_res_scene2) as mock_attempt:
        res2 = router.synthesize_scene(
            video_id="doc_coldwar",
            scene_id="scene_02",
            script="Second scene text.",
            preferred_engine=ENGINE_DEEPGRAM,  # Requesting Deepgram, but locked to Kokoro!
        )
        # It must call Kokoro with bm_george
        mock_attempt.assert_called_once()
        assert mock_attempt.call_args[1]["engine"] == ENGINE_KOKORO_LOCAL
        assert mock_attempt.call_args[1]["explicit_voice"] == "bm_george"
        assert res2.engine_used == ENGINE_KOKORO_LOCAL


def test_narrator_consistency_violation_on_locked_engine_failure(router):
    """Verify that if locked engine fails midway, NarratorConsistencyViolationError is raised."""
    router.lock_narrator("doc_chernobyl", ENGINE_KOKORO_LOCAL, "bm_george")

    with patch.object(router, "_attempt_engine", side_effect=RuntimeError("Engine crashed")):
        with pytest.raises(NarratorConsistencyViolationError, match="LOCKED NARRATOR FAILURE"):
            router.synthesize_scene(
                video_id="doc_chernobyl",
                scene_id="scene_03",
                script="Tragedy occurred at 01:23.",
            )


def test_hierarchy_fallback_sequence(router):
    """Verify fallback sequence from CosyVoice -> Kokoro -> Deepgram."""
    # When CosyVoice fails and Kokoro fails, it should reach Deepgram
    def mock_attempt_impl(video_id, scene_id, script, emotion, speed, engine, explicit_voice=None):
        if engine == ENGINE_COSYVOICE:
            raise RuntimeError("CosyVoice unavailable")
        elif engine == ENGINE_KOKORO_LOCAL:
            raise RuntimeError("Kokoro local unavailable")
        elif engine == ENGINE_DEEPGRAM:
            return RoutedNarrationResult(
                video_id=video_id,
                scene_id=scene_id,
                audio_path=router.output_dir / "dg.mp3",
                filename="dg.mp3",
                duration_seconds=4.0,
                filesize_bytes=800,
                engine_used=ENGINE_DEEPGRAM,
                voice_used="aura-helios-en",
                is_gold_standard=False,
            )
        raise ValueError(f"Unknown engine {engine}")

    with patch.object(router, "_attempt_engine", side_effect=mock_attempt_impl):
        res = router.synthesize_scene(
            video_id="doc_fallbacks",
            scene_id="scene_01",
            script="Fallback test text.",
        )
        assert res.engine_used == ENGINE_DEEPGRAM
        assert res.voice_used == "aura-helios-en"
        # The lock must now be set to Deepgram for the rest of doc_fallbacks
        lock = router.get_lock("doc_fallbacks")
        assert lock.engine == ENGINE_DEEPGRAM
