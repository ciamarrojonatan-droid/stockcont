"""StockCont & DarkFactory — Cinematic Soundtrack & Tension Audio Engine.

Provides procedural soundbed synthesis (Hans Zimmer / Ludwig Göransson acoustic architecture),
low-frequency drone beds, 60 BPM suspense clock ticks, and FFmpeg ducking audio mixing.
"""

from __future__ import annotations

import logging
import math
import os
import struct
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("AudioEngine")

# Pre-configured acoustic tensions for DarkFactory thrillers
ACOUSTIC_PROFILES = {
    "cold_war_espionage": {
        "base_freq_hz": 55.0,  # A1 sub-bass
        "overtone_freq_hz": 110.0,
        "lfo_rate_hz": 0.25,  # 4-second breathing cycle
        "tick_bpm": 60,  # Heartbeat / second-hand tension
        "dissonance_factor": 0.08,
        "description": "Cold War espionage tension: low sub drone with 60 BPM analog radar tick.",
    },
    "deep_space_scifi": {
        "base_freq_hz": 43.65,  # F1 deep rumble
        "overtone_freq_hz": 87.3,
        "lfo_rate_hz": 0.15,
        "tick_bpm": 0,  # Ambient floating
        "dissonance_factor": 0.03,
        "description": "Deep space cosmic isolation: 43Hz resonant void drone with slow pulsing.",
    },
    "cyber_warfare": {
        "base_freq_hz": 65.4,  # C2
        "overtone_freq_hz": 130.8,
        "lfo_rate_hz": 0.5,
        "tick_bpm": 120,  # Accelerated technical countdown
        "dissonance_factor": 0.12,
        "description": "Cyber warfare grid collapse: sharp electronic pulse with industrial low drone.",
    },
    "historical_tragedy": {
        "base_freq_hz": 48.99,  # G1
        "overtone_freq_hz": 73.4,  # D2 perfect fifth
        "lfo_rate_hz": 0.1,
        "tick_bpm": 48,  # Funeral cadence
        "dissonance_factor": 0.05,
        "description": "Historical disaster / Chernobyl solemnity: dark cello resonance and slow descent.",
    },
}


@dataclass
class SoundtrackResult:
    """Result container for generated soundtrack."""
    audio_path: Path
    filename: str
    duration_seconds: float
    sample_rate: int
    profile_used: str
    filesize_bytes: int


class DarkFactoryAudioEngine:
    """Cinematic Soundtrack Synthesizer & Audio Mixer."""

    def __init__(self, output_dir: Optional[Path | str] = None, sample_rate: int = 48000) -> None:
        self.sample_rate = sample_rate
        if output_dir:
            self.output_dir = Path(output_dir).resolve()
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.output_dir = base_dir / "data" / "staging" / "soundtracks"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_procedural_soundbed(
        self,
        duration_seconds: float = 30.0,
        profile_name: str = "cold_war_espionage",
        destination_path: Optional[Path | str] = None,
    ) -> SoundtrackResult:
        """Synthesize a pristine 48kHz 24-bit cinematic tension bed without external APIs.

        Generates multi-layer acoustic waves:
        1. Sub-fundamental frequency drone
        2. Harmonic overtone with LFO amplitude breathing
        3. Dissonant frequency beat
        4. Optional 60 BPM acoustic clock tick (Zimmer Dunkirk technique)
        """
        profile = ACOUSTIC_PROFILES.get(profile_name, ACOUSTIC_PROFILES["cold_war_espionage"])
        total_samples = int(self.sample_rate * duration_seconds)
        t = np.linspace(0, duration_seconds, total_samples, endpoint=False)

        # 1. Fundamental sub-bass
        base_f = profile["base_freq_hz"]
        sub_layer = 0.45 * np.sin(2 * np.pi * base_f * t)

        # 2. Overtone with subtle LFO modulation
        lfo_rate = profile["lfo_rate_hz"]
        lfo = 0.5 * (1.0 + np.sin(2 * np.pi * lfo_rate * t))
        overtone_f = profile["overtone_freq_hz"]
        overtone_layer = 0.25 * lfo * np.sin(2 * np.pi * overtone_f * t)

        # 3. Dissonance friction layer (minor second slight offset)
        diss_f = base_f * (1.0 + profile["dissonance_factor"])
        dissonance_layer = 0.15 * np.sin(2 * np.pi * diss_f * t)

        combined = sub_layer + overtone_layer + dissonance_layer

        # 4. Tension clock tick (if profile specifies BPM > 0)
        tick_bpm = profile.get("tick_bpm", 0)
        if tick_bpm > 0:
            tick_interval_sec = 60.0 / tick_bpm
            tick_indices = (np.arange(0, duration_seconds, tick_interval_sec) * self.sample_rate).astype(int)
            tick_samples_len = int(self.sample_rate * 0.035)  # 35ms sharp click
            tick_t = np.linspace(0, 0.035, tick_samples_len, endpoint=False)
            # High frequency metallic click + exponential decay
            click_wave = (
                0.28
                * np.sin(2 * np.pi * 1800 * tick_t)
                * np.exp(-tick_t * 90.0)
            )

            for idx in tick_indices:
                end_idx = min(idx + tick_samples_len, total_samples)
                actual_len = end_idx - idx
                if actual_len > 0:
                    combined[idx:end_idx] += click_wave[:actual_len]

        # 5. Envelope: 1.5s fade-in, 2.0s fade-out
        fade_in_len = min(int(self.sample_rate * 1.5), total_samples // 4)
        fade_out_len = min(int(self.sample_rate * 2.0), total_samples // 4)

        if fade_in_len > 0:
            combined[:fade_in_len] *= np.linspace(0.0, 1.0, fade_in_len)
        if fade_out_len > 0:
            combined[-fade_out_len:] *= np.linspace(1.0, 0.0, fade_out_len)

        # 6. Master Limiter & Normalization (-1 dBFS peak headroom)
        peak = np.max(np.abs(combined))
        if peak > 0:
            combined = (combined / peak) * 0.89  # -1 dBFS headroom

        # Convert to 16-bit PCM for universal compatibility
        int16_samples = (combined * 32767.0).astype(np.int16)

        # Save to file
        if destination_path:
            out_file = Path(destination_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_file = self.output_dir / f"soundtrack_{profile_name}_{int(duration_seconds)}s.wav"

        with wave.open(str(out_file), "wb") as wf:
            wf.setnchannels(1)  # Mono track (standard for background bed before stereo spatialization)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(int16_samples.tobytes())

        filesize = out_file.stat().st_size
        logger.info(
            f"✅ Procedural soundbed generated: {out_file.name} ({duration_seconds}s, {filesize} bytes)"
        )
        return SoundtrackResult(
            audio_path=out_file,
            filename=out_file.name,
            duration_seconds=duration_seconds,
            sample_rate=self.sample_rate,
            profile_used=profile_name,
            filesize_bytes=filesize,
        )

    def mix_voice_and_soundtrack(
        self,
        voice_path: Path | str,
        soundtrack_path: Path | str,
        output_path: Path | str,
        music_volume: float = 0.16,
        ducking: bool = True,
    ) -> Path:
        """Mix voiceover and background music via FFmpeg with intelligent ducking.

        Args:
            voice_path: Path to narration audio.
            soundtrack_path: Path to soundtrack audio.
            output_path: Destination output path (.mp3 or .wav).
            music_volume: Default soundtrack volume multiplier (0.12 - 0.20 recommended).
            ducking: Whether to apply sidechain ducking when narration is active.

        Returns:
            Path to the mastered final mixed audio file.
        """
        import subprocess
        from src.video.ffmpeg_processor import get_ffmpeg_binary

        v_path = Path(voice_path).resolve()
        m_path = Path(soundtrack_path).resolve()
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not v_path.exists():
            raise FileNotFoundError(f"Voice audio file not found: {v_path}")
        if not m_path.exists():
            raise FileNotFoundError(f"Soundtrack audio file not found: {m_path}")

        temp_out = out_path.with_suffix(f".tmp.{os.getpid()}{out_path.suffix}")

        # Intelligent mixing filter:
        # [0:a] is voice, [1:a] is background music.
        # We loop the music infinitely if needed and apply volume scale + amix.
        if ducking:
            # Sidechain compression: voice dynamically suppresses music by ~14dB during speech
            filter_complex = (
                f"[1:a]volume={music_volume:.2f}[music];"
                f"[0:a]asplit=2[voice_main][voice_side];"
                f"[music][voice_side]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=350[ducked_music];"
                f"[voice_main][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            )
        else:
            filter_complex = (
                f"[1:a]volume={music_volume:.2f}[music];"
                f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            )

        cmd = [
            get_ffmpeg_binary(),
            "-y",
            "-i", str(v_path),
            "-stream_loop", "-1",
            "-i", str(m_path),
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame" if out_path.suffix.lower() == ".mp3" else "pcm_s16le",
            "-b:a", "320k" if out_path.suffix.lower() == ".mp3" else None,
            str(temp_out),
        ]
        cmd = [c for c in cmd if c is not None]

        logger.info(f"Mixing narration and soundtrack via FFmpeg (ducking={ducking})...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120.0)

        if res.returncode != 0:
            if temp_out.exists():
                temp_out.unlink()
            err_msg = res.stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg audio mixing failed: {err_msg}")
            raise RuntimeError(f"FFmpeg audio mixing failed: {err_msg[:300]}")

        if temp_out.exists():
            temp_out.replace(out_path)

        logger.info(f"✅ Audio mix successfully created: {out_path.name}")
        return out_path
