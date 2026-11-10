"""StockCont & DarkFactory — Sony Woosh Foley & SFX Engine.

Connects to RunningHub ComfyUI RPA (Workflow 2119999521484034049) to generate
automatic audio foley effects (V2A / T2A) and extract clean watermark-free video
via Node #94 (FeiHouVideoPreview).
"""

from __future__ import annotations

import logging
import math
import os
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

# Windows UTF-8 enforcement (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("SonyWooshFoleyEngine")

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
FINAL_AUDIO_DIR: Path = BASE_DIR / "data" / "final" / "audio"
FINAL_VIDEOS_DIR: Path = BASE_DIR / "data" / "final" / "videos"
FINAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
FINAL_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# Curated Foley Sound Design Presets
FOLEY_PRESETS: Dict[str, str] = {
    "espionage_bunker": "classified typewriter keystrokes, magnetic tape spooling, bunker alarm klaxon, muffled radio distortion, heavy steel blast door latching",
    "cyber_warfare": "server room hum, mechanical keyboard typing, digital glitch bursts, fiber optic server rack cooling fans, data beep alerts",
    "deep_space": "pressurized airlock hiss, metallic hull groaning, deep cosmic sub-bass rumble, spacesuit breath respirator, magnetic tether click",
    "cinematic_impact": "sub-bass boom, metallic shiver, slow motion glass shatter, distant explosion, ominous brass drone",
}


@dataclass
class FoleyResult:
    """Result container for generated Foley SFX."""
    audio_path: Path
    video_path: Optional[Path]
    mode: str  # 'v2a' or 't2a'
    prompt_used: str
    engine: str
    filesize_bytes: int


class SonyWooshFoleyEngine:
    """Orchestrates Sony Woosh Foley generation on RunningHub with watermark-free video extraction."""

    def __init__(
        self,
        audio_output_dir: Optional[Union[Path, str]] = None,
        video_output_dir: Optional[Union[Path, str]] = None,
    ) -> None:
        self.audio_output_dir = Path(audio_output_dir).resolve() if audio_output_dir else FINAL_AUDIO_DIR
        self.video_output_dir = Path(video_output_dir).resolve() if video_output_dir else FINAL_VIDEOS_DIR
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)
        self.video_output_dir.mkdir(parents=True, exist_ok=True)

    def generate_foley(
        self,
        mode: str = "t2a",
        video_path: Optional[Union[Path, str]] = None,
        sfx_prompt: Optional[str] = None,
        preset_name: Optional[str] = None,
        force_procedural: bool = False,
    ) -> FoleyResult:
        """Generates Foley effects via RunningHub (V2A or T2A) or local procedural fallback.

        Args:
            mode: 'v2a' (video-to-audio) or 't2a' (text-to-audio).
            video_path: Input video path for V2A mode (injected into Node #34).
            sfx_prompt: Custom sound effects prompt (injected into Node #46).
            preset_name: Key from FOLEY_PRESETS if sfx_prompt not provided.
            force_procedural: If True, uses local procedural synthesis without RunningHub.
        """
        # Determine prompt
        effective_prompt = sfx_prompt or FOLEY_PRESETS.get(preset_name or "espionage_bunker", FOLEY_PRESETS["espionage_bunker"])

        if not force_procedural:
            try:
                from src.factory.runninghub_bot import run_woosh_foley_bot
                logger.info(f"Triggering Sony Woosh Foley on RunningHub (mode={mode}, prompt='{effective_prompt[:40]}...')...")
                res = run_woosh_foley_bot(
                    video_path=video_path,
                    prompt=effective_prompt,
                    mode=mode,
                    destination_dir=self.audio_output_dir,
                )
                saved_files = res.get("saved_files", [])
                found_audio: Optional[Path] = None
                found_video: Optional[Path] = None

                for fn in saved_files:
                    p = self.audio_output_dir / fn
                    pv = self.video_output_dir / fn
                    if p.exists() and p.suffix.lower() in (".wav", ".mp3", ".flac"):
                        found_audio = p
                    elif pv.exists() and pv.suffix.lower() in (".mp4", ".mov", ".webm"):
                        found_video = pv

                if found_audio:
                    logger.info(f"✅ Sony Woosh Foley audio generated via RunningHub: {found_audio.name}")
                    return FoleyResult(
                        audio_path=found_audio,
                        video_path=found_video,
                        mode=mode,
                        prompt_used=effective_prompt,
                        engine="sony_woosh_vflow",
                        filesize_bytes=found_audio.stat().st_size,
                    )
            except Exception as e:
                logger.warning(f"RunningHub Woosh Foley RPA unavailable ({e}). Falling back to local procedural Foley synthesis.")

        # Local procedural synthesis fallback (generates cinematic impact/whoosh 48kHz WAV)
        out_audio = self._generate_procedural_foley(effective_prompt)
        logger.info(f"✅ Foley SFX generated via procedural fallback: {out_audio.name}")
        return FoleyResult(
            audio_path=out_audio,
            video_path=Path(video_path) if video_path and Path(video_path).exists() else None,
            mode=mode,
            prompt_used=effective_prompt,
            engine="procedural_fallback",
            filesize_bytes=out_audio.stat().st_size,
        )

    def _generate_procedural_foley(self, prompt: str, duration_sec: float = 6.0) -> Path:
        """Synthesizes high-fidelity 48kHz Foley/Whoosh audio bed for offline operation."""
        sample_rate = 48000
        total_samples = int(sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)

        # Base atmospheric whoosh (lowpass shaped white noise + sub impact)
        noise = np.random.normal(0, 0.25, total_samples)
        envelope = np.exp(-1.5 * t) * (1.0 - np.exp(-10.0 * t))

        # Resonant sub boom (80Hz down-sweep to 30Hz)
        sweep_freq = 80.0 * np.exp(-1.2 * t) + 30.0
        phase = 2 * np.pi * np.cumsum(sweep_freq) / sample_rate
        sub_boom = 0.5 * np.sin(phase) * np.exp(-1.8 * t)

        # High frequency metallic transient
        transient = 0.3 * np.sin(2 * np.pi * 2400 * t) * np.exp(-25.0 * t)

        combined = (noise * envelope) + sub_boom + transient
        peak = np.max(np.abs(combined))
        if peak > 0:
            combined = (combined / peak) * 0.85

        int16_samples = (combined * 32767.0).astype(np.int16)
        out_file = self.audio_output_dir / f"woosh_foley_procedural_{int(time.time())}.wav"
        with wave.open(str(out_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(int16_samples.tobytes())

        return out_file
