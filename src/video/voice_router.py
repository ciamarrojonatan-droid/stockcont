"""StockCont & DarkFactory — Master Voice Router & Video Narrator Lock.

Enforces the project-wide narration hierarchy:
  1. CosyVoice Neural (Gold Standard Lossless on RunningHub ComfyUI)
  2. Kokoro Neural LOCAL (Fallback 1: Zero-cost local CPU, default 'bm_george')
  3. Deepgram Aura (Fallback 2: High-speed REST API, default 'aura-helios-en')

Mandatory Project Invariant:
  A video project MUST have the exact same narrator from start to finish.
  Never mix different narrators or voice engines across scenes of the same video.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

logger = logging.getLogger("VoiceRouter")

# Narration Engines
ENGINE_COSYVOICE = "cosyvoice"          # Tier 1: Gold Standard Lossless (RunningHub)
ENGINE_KOKORO_LOCAL = "kokoro_local"    # Tier 2: Fallback 1 (Local Neural ONNX)
ENGINE_DEEPGRAM = "deepgram"            # Tier 3: Fallback 2 (Deepgram Aura API)

DEFAULT_KOKORO_VOICE = "bm_george"
DEFAULT_DEEPGRAM_VOICE = "aura-helios-en"


class NarratorConsistencyViolationError(RuntimeError):
    """Raised when an attempt is made to switch narrators midway through a video."""
    pass


@dataclass
class NarratorLock:
    """Locks a single voice and engine for an entire video project."""
    video_id: str
    engine: str
    voice_id: str
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    scenes_completed: List[str] = field(default_factory=list)


@dataclass
class RoutedNarrationResult:
    """Result of a narration synthesis pass."""
    video_id: str
    scene_id: str
    audio_path: Path
    filename: str
    duration_seconds: float
    filesize_bytes: int
    engine_used: str
    voice_used: str
    is_gold_standard: bool
    subtitles_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MasterVoiceRouter:
    """Orchestrates narration across tiers while strictly enforcing single-narrator unity."""

    def __init__(
        self,
        locks_persistence_path: Optional[Path | str] = None,
        output_dir: Optional[Path | str] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.output_dir = Path(output_dir).resolve() if output_dir else base_dir / "data" / "final" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.persistence_path = (
            Path(locks_persistence_path).resolve()
            if locks_persistence_path
            else base_dir / "data" / "processed" / "narrator_locks.json"
        )
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

        self._locks: Dict[str, NarratorLock] = self._load_locks()

    def _load_locks(self) -> Dict[str, NarratorLock]:
        """Load persisted video narrator locks."""
        if not self.persistence_path.exists():
            return {}
        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {vid: NarratorLock(**lock_dict) for vid, lock_dict in data.items()}
        except Exception as e:
            logger.warning(f"Failed to read narrator locks: {e}")
            return {}

    def _save_locks(self) -> None:
        """Atomic write of narrator locks (ADR-02)."""
        tmp_file = self.persistence_path.with_suffix(f".tmp.{os.getpid()}{self.persistence_path.suffix}")
        try:
            serialized = {vid: asdict(lock) for vid, lock in self._locks.items()}
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
            tmp_file.replace(self.persistence_path)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            logger.error(f"Failed to save narrator locks: {e}")

    def get_lock(self, video_id: str) -> Optional[NarratorLock]:
        """Retrieve existing narrator lock for a video project."""
        return self._locks.get(video_id)

    def lock_narrator(self, video_id: str, engine: str, voice_id: str) -> NarratorLock:
        """Lock the narrator for a video project."""
        lock = NarratorLock(video_id=video_id, engine=engine, voice_id=voice_id)
        self._locks[video_id] = lock
        self._save_locks()
        logger.info(f"🔒 Video '{video_id}' locked to Narrator: Engine={engine}, Voice={voice_id}")
        return lock

    def release_lock(self, video_id: str) -> None:
        """Clear narrator lock for a video project (e.g. for complete re-generation)."""
        if video_id in self._locks:
            del self._locks[video_id]
            self._save_locks()
            logger.info(f"🔓 Video '{video_id}' narrator lock released.")

    def synthesize_scene(
        self,
        video_id: str,
        scene_id: str,
        script: str,
        emotion: str = "Speak with controlled urgency and rising dread, deep baritone documentary tone.",
        speed: float = 1.0,
        preferred_engine: Optional[str] = None,
        force_reassign_all: bool = False,
    ) -> RoutedNarrationResult:
        """Synthesize audio for a scene respecting the video's locked narrator.

        Hierarchy:
          1. CosyVoice Neural (Gold Standard Lossless)
          2. Kokoro Neural LOCAL (Fallback 1)
          3. Deepgram Aura (Fallback 2)

        Rules:
          - If video_id already has a lock, MUST use the locked engine & voice.
          - If the locked engine fails, throws NarratorConsistencyViolationError
            unless force_reassign_all is True.
        """
        existing_lock = self.get_lock(video_id)

        # If locked, we must obey the lock
        if existing_lock and not force_reassign_all:
            target_engine = existing_lock.engine
            target_voice = existing_lock.voice_id
            logger.info(
                f"Enforcing Narrator Lock for video '{video_id}' scene '{scene_id}': "
                f"{target_engine} ({target_voice})"
            )
            return self._execute_specific_engine(
                video_id=video_id,
                scene_id=scene_id,
                script=script,
                emotion=emotion,
                speed=speed,
                engine=target_engine,
                voice_id=target_voice,
                lock=existing_lock,
            )

        # No lock yet -> Determine engine according to hierarchy
        candidates = [ENGINE_COSYVOICE, ENGINE_KOKORO_LOCAL, ENGINE_DEEPGRAM]
        if preferred_engine and preferred_engine in candidates:
            # Reorder candidates to test preferred first
            candidates.remove(preferred_engine)
            candidates.insert(0, preferred_engine)

        last_error: Optional[Exception] = None
        for candidate_engine in candidates:
            try:
                result = self._attempt_engine(
                    video_id=video_id,
                    scene_id=scene_id,
                    script=script,
                    emotion=emotion,
                    speed=speed,
                    engine=candidate_engine,
                )
                # Successful synthesis on Scene 1 -> establish lock for this video
                lock = self.lock_narrator(
                    video_id=video_id,
                    engine=result.engine_used,
                    voice_id=result.voice_used,
                )
                lock.scenes_completed.append(scene_id)
                self._save_locks()
                return result
            except Exception as e:
                logger.warning(
                    f"Tier {candidate_engine} failed for video '{video_id}' scene '{scene_id}': {e}. "
                    "Proceeding to next fallback..."
                )
                last_error = e

        raise RuntimeError(
            f"All narration tiers exhausted for video '{video_id}' scene '{scene_id}'. Last error: {last_error}"
        )

    def _execute_specific_engine(
        self,
        video_id: str,
        scene_id: str,
        script: str,
        emotion: str,
        speed: float,
        engine: str,
        voice_id: str,
        lock: NarratorLock,
    ) -> RoutedNarrationResult:
        """Execute the exact locked engine. Fails fast if locked engine is unavailable."""
        try:
            result = self._attempt_engine(
                video_id=video_id,
                scene_id=scene_id,
                script=script,
                emotion=emotion,
                speed=speed,
                engine=engine,
                explicit_voice=voice_id,
            )
            if scene_id not in lock.scenes_completed:
                lock.scenes_completed.append(scene_id)
                self._save_locks()
            return result
        except Exception as e:
            raise NarratorConsistencyViolationError(
                f"LOCKED NARRATOR FAILURE: Scene '{scene_id}' of video '{video_id}' failed with locked engine '{engine}': {e}. "
                "Per project rules, switching narrators midway through a video is forbidden. "
                "To switch narrators, re-synthesize all completed scenes with force_reassign_all=True."
            ) from e

    def _attempt_engine(
        self,
        video_id: str,
        scene_id: str,
        script: str,
        emotion: str,
        speed: float,
        engine: str,
        explicit_voice: Optional[str] = None,
    ) -> RoutedNarrationResult:
        """Synthesize using a single candidate engine."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest_filename = f"{video_id}_{scene_id}_{engine}_{timestamp}"

        if engine == ENGINE_COSYVOICE:
            # Tier 1: CosyVoice on RunningHub ComfyUI
            from src.factory.runninghub_bot import run_narration_bot
            logger.info(f"🎙️ [Tier 1: CosyVoice Gold Standard] Synthesizing {video_id}:{scene_id}...")
            res = run_narration_bot(script=script, emotion=emotion, speed=speed)
            saved_files = res.get("saved_files", [])
            if not saved_files:
                raise RuntimeError("CosyVoice workflow produced no audio output.")
            fn = saved_files[-1]
            out_path = self.output_dir / fn
            duration = 10.0  # approximate fallback if not probed
            sz = out_path.stat().st_size if out_path.exists() else 0

            return RoutedNarrationResult(
                video_id=video_id,
                scene_id=scene_id,
                audio_path=out_path,
                filename=fn,
                duration_seconds=duration,
                filesize_bytes=sz,
                engine_used=ENGINE_COSYVOICE,
                voice_used="cosyvoice_instruct",
                is_gold_standard=True,
                metadata={"workflow_id": "2118531898170486785", "format": "flac"},
            )

        elif engine == ENGINE_KOKORO_LOCAL:
            # Tier 2: Kokoro Neural Local (bm_george)
            voice = explicit_voice or DEFAULT_KOKORO_VOICE
            logger.info(f"🎙️ [Tier 2: Kokoro Neural LOCAL] Synthesizing {video_id}:{scene_id} with {voice}...")
            out_file = self.output_dir / f"{dest_filename}.wav"

            # Execute Kokoro local synthesis
            try:
                base_dir = Path(__file__).resolve().parent.parent.parent
                df_src = base_dir / "darkfactory" / "src"
                if str(df_src) not in sys.path:
                    sys.path.append(str(df_src))
                from kokoro_fallback import KokoroNarrator
                narrator = KokoroNarrator(voice=voice)
                narrator.synthesize(text=script, output_path=out_file, speed=speed)
            except Exception as e:
                raise RuntimeError(f"Kokoro local synthesis failed: {e}") from e

            filesize = out_file.stat().st_size if out_file.exists() else 0
            return RoutedNarrationResult(
                video_id=video_id,
                scene_id=scene_id,
                audio_path=out_file,
                filename=out_file.name,
                duration_seconds=round(len(script.split()) / 2.5, 2),
                filesize_bytes=filesize,
                engine_used=ENGINE_KOKORO_LOCAL,
                voice_used=voice,
                is_gold_standard=False,
                metadata={"format": "wav", "local_cpu": True},
            )

        elif engine == ENGINE_DEEPGRAM:
            # Tier 3: Deepgram Aura REST API
            voice = explicit_voice or DEFAULT_DEEPGRAM_VOICE
            logger.info(f"🎙️ [Tier 3: Deepgram Aura API] Synthesizing {video_id}:{scene_id} with {voice}...")
            from src.video.voice_engine import DeepgramVoiceEngine

            engine_instance = DeepgramVoiceEngine(output_dir=self.output_dir)
            if not engine_instance.is_available:
                raise RuntimeError("DEEPGRAM_API_KEY is not configured.")

            out_file = self.output_dir / f"{dest_filename}.mp3"
            synth = engine_instance.synthesize(
                text=script,
                voice=voice,
                speed=speed,
                destination_path=out_file,
                generate_subtitles=True,
            )

            return RoutedNarrationResult(
                video_id=video_id,
                scene_id=scene_id,
                audio_path=synth.audio_path,
                filename=synth.filename,
                duration_seconds=synth.duration_seconds,
                filesize_bytes=synth.filesize_bytes,
                engine_used=ENGINE_DEEPGRAM,
                voice_used=synth.voice_used,
                is_gold_standard=False,
                subtitles_path=synth.subtitles_path,
                metadata={"cost_usd": synth.estimated_cost_usd, "format": "mp3"},
            )

        else:
            raise ValueError(f"Unknown narration engine: {engine}")
