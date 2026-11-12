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
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


@dataclass
class AudioTransientAnalysis:
    """Extracted beat/onset transient telemetry for beat-locked cutting."""

    audio_path: str
    duration_sec: float
    sample_rate: int
    estimated_bpm: float
    beat_timestamps: List[float] = field(default_factory=list)
    peak_timestamps: List[float] = field(default_factory=list)
    mean_rms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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

        is_mp3 = out_path.suffix.lower() == ".mp3"
        cmd = [
            get_ffmpeg_binary(),
            "-y",
            "-i", str(v_path),
            "-stream_loop", "-1",
            "-i", str(m_path),
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame" if is_mp3 else "pcm_s16le",
        ]
        if is_mp3:
            cmd.extend(["-b:a", "320k"])
        cmd.append(str(temp_out))

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

    def mix_multitrack_documentary(
        self,
        voice_path: Path | str,
        soundtrack_path: Optional[Path | str],
        foley_path: Optional[Path | str],
        output_path: Path | str,
        music_volume: float = 0.15,
        foley_volume: float = 0.35,
        ducking: bool = True,
        foley_sidechain_ducking: bool = False,
    ) -> Path:
        """3-Stem documentary audio mixer (Voiceover + Music + Foley SFX) via FFmpeg.

        Stem 1: Narration (0 dB reference, leads the mix).
        Stem 2: Soundtrack (-16 to -18 dBFS, dynamically sidechain-ducked by voice and optionally SFX).
        Stem 3: Foley / SFX (-10 to -12 dBFS, positioned alongside speech).
        Master: Formatted to 320kbps MP3 or 24-bit PCM WAV.
        """
        import shutil
        import subprocess
        from src.video.ffmpeg_processor import get_ffmpeg_binary

        v_path = Path(voice_path).resolve()
        if not v_path.exists():
            raise FileNotFoundError(f"Voice audio file not found: {v_path}")

        m_path = Path(soundtrack_path).resolve() if soundtrack_path else None
        f_path = Path(foley_path).resolve() if foley_path else None

        # Fallbacks when stems are missing
        if not m_path and not f_path:
            out_p = Path(output_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(v_path, out_p)
            return out_p
        if not f_path and m_path:
            return self.mix_voice_and_soundtrack(v_path, m_path, output_path, music_volume=music_volume, ducking=ducking)
        if not m_path and f_path:
            return self.mix_voice_and_soundtrack(v_path, f_path, output_path, music_volume=foley_volume, ducking=False)

        # 3-Stem Mixing
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_out = out_path.with_suffix(f".tmp.{os.getpid()}{out_path.suffix}")

        if ducking and foley_sidechain_ducking:
            filter_complex = (
                f"[1:a]volume={music_volume:.2f}[music];"
                f"[2:a]volume={foley_volume:.2f},asplit=2[foley_main][foley_side];"
                f"[0:a]asplit=2[voice_main][voice_side];"
                f"[voice_side][foley_side]amix=inputs=2:duration=first[duck_trigger];"
                f"[music][duck_trigger]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=350[ducked_music];"
                f"[voice_main][ducked_music][foley_main]amix=inputs=3:duration=first:dropout_transition=2[outa]"
            )
        elif ducking:
            filter_complex = (
                f"[1:a]volume={music_volume:.2f}[music];"
                f"[2:a]volume={foley_volume:.2f}[foley];"
                f"[0:a]asplit=2[voice_main][voice_side];"
                f"[music][voice_side]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=350[ducked_music];"
                f"[voice_main][ducked_music][foley]amix=inputs=3:duration=first:dropout_transition=2[outa]"
            )
        else:
            filter_complex = (
                f"[1:a]volume={music_volume:.2f}[music];"
                f"[2:a]volume={foley_volume:.2f}[foley];"
                f"[0:a][music][foley]amix=inputs=3:duration=first:dropout_transition=2[outa]"
            )

        is_mp3 = out_path.suffix.lower() == ".mp3"
        cmd = [
            get_ffmpeg_binary(),
            "-y",
            "-i", str(v_path),
            "-stream_loop", "-1",
            "-i", str(m_path),
            "-stream_loop", "-1",
            "-i", str(f_path),
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame" if is_mp3 else "pcm_s16le",
        ]
        if is_mp3:
            cmd.extend(["-b:a", "320k"])
        cmd.append(str(temp_out))

        logger.info(f"Mixing 3-stem multitrack (voice + music + foley) via FFmpeg...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120.0)

        if res.returncode != 0:
            if temp_out.exists():
                temp_out.unlink()
            err_msg = res.stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg 3-stem audio mixing failed: {err_msg}")
            raise RuntimeError(f"FFmpeg 3-stem audio mixing failed: {err_msg[:300]}")

        if temp_out.exists():
            temp_out.replace(out_path)

        logger.info(f"✅ 3-Stem documentary mix successfully created: {out_path.name}")
        return out_path

    def analyze_audio_transients(
        self,
        audio_path: Path | str,
        frame_ms: int = 25,
        hop_ms: int = 10,
        peak_z_threshold: float = 1.45,
        min_peak_interval_sec: float = 0.25,
    ) -> AudioTransientAnalysis:
        """Extract energy envelope, dominant BPM, and beat transient timestamps."""
        import subprocess
        from src.video.ffmpeg_processor import get_ffmpeg_binary

        src = Path(audio_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Audio file not found for transient analysis: {src}")

        target_sr = 16000
        samples: Optional[np.ndarray] = None
        if src.suffix.lower() == ".wav":
            try:
                with wave.open(str(src), "rb") as wf:
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    if sampwidth not in (1, 2, 4):
                        raise ValueError(f"Unsupported WAV sample width for native decode: {sampwidth}")
                    target_sr = wf.getframerate()
                    raw = wf.readframes(wf.getnframes())
                dtype = np.int16 if sampwidth == 2 else (np.int32 if sampwidth == 4 else np.uint8)
                arr = np.frombuffer(raw, dtype=dtype).astype(np.float32)
                if sampwidth == 2:
                    arr /= 32768.0
                elif sampwidth == 4:
                    arr /= 2147483648.0
                else:
                    arr = (arr - 128.0) / 128.0
                if channels > 1:
                    arr = arr.reshape(-1, channels).mean(axis=1)
                samples = arr
            except (wave.Error, EOFError, ValueError, RuntimeError):
                target_sr = 16000
                samples = None

        if samples is None:
            cmd = [
                get_ffmpeg_binary(),
                "-v",
                "error",
                "-i",
                str(src),
                "-ac",
                "1",
                "-ar",
                str(target_sr),
                "-f",
                "s16le",
                "-",
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60.0)
            if res.returncode != 0 or not res.stdout:
                err_msg = res.stderr.decode("utf-8", errors="replace")[:300]
                raise RuntimeError(f"FFmpeg PCM decode failed for {src.name}: {err_msg}")
            samples = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0

        duration_sec = round(len(samples) / max(1, target_sr), 3)
        if len(samples) == 0:
            return AudioTransientAnalysis(
                audio_path=src.as_posix(),
                duration_sec=0.0,
                sample_rate=target_sr,
                estimated_bpm=0.0,
            )

        frame_len = max(64, int(target_sr * frame_ms / 1000.0))
        hop_len = max(32, int(target_sr * hop_ms / 1000.0))
        rms_values: List[float] = []
        times: List[float] = []
        for start in range(0, max(1, len(samples) - frame_len + 1), hop_len):
            chunk = samples[start : start + frame_len]
            rms_values.append(float(np.sqrt(np.mean(chunk * chunk))))
            times.append(start / target_sr)

        rms_arr = np.asarray(rms_values, dtype=np.float32)
        mean_rms = float(np.mean(rms_arr)) if len(rms_arr) else 0.0
        std_rms = float(np.std(rms_arr)) if len(rms_arr) else 0.0

        # Spectral/energy onset flux emphasizes sudden drum/clock transients over sustained drones
        flux = np.maximum(0.0, np.diff(rms_arr, prepend=rms_arr[0]))
        flux_mean = float(np.mean(flux))
        flux_std = float(np.std(flux))
        thresh = max(1e-4, flux_mean + peak_z_threshold * flux_std)

        peaks: List[float] = []
        last_peak_t = -min_peak_interval_sec
        for i in range(1, len(flux) - 1):
            if flux[i] >= thresh and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
                t_sec = round(float(times[i]), 3)
                if t_sec - last_peak_t >= min_peak_interval_sec:
                    peaks.append(t_sec)
                    last_peak_t = t_sec

        # Estimate dominant BPM from inter-onset intervals
        estimated_bpm = 0.0
        if len(peaks) >= 2:
            ibis = np.diff(np.asarray(peaks, dtype=np.float32))
            valid_ibis = ibis[(ibis >= 0.25) & (ibis <= 1.5)]
            if len(valid_ibis) > 0:
                med_ibi = float(np.median(valid_ibis))
                bpm = 60.0 / med_ibi
                while bpm < 55.0:
                    bpm *= 2.0
                while bpm > 180.0:
                    bpm /= 2.0
                estimated_bpm = round(bpm, 1)

        return AudioTransientAnalysis(
            audio_path=src.as_posix(),
            duration_sec=duration_sec,
            sample_rate=target_sr,
            estimated_bpm=estimated_bpm,
            beat_timestamps=peaks,
            peak_timestamps=peaks,
            mean_rms=round(mean_rms, 5),
        )

    @staticmethod
    def snap_cut_times_to_beats(
        cut_times: List[float],
        beat_timestamps: List[float],
        tolerance_sec: float = 0.18,
        min_spacing_sec: float = 0.60,
    ) -> List[float]:
        """Align scene cut times to nearby audio beats without crushing natural pacing."""
        if not cut_times or not beat_timestamps:
            return list(cut_times)

        sorted_beats = sorted(float(b) for b in beat_timestamps)
        snapped: List[float] = []
        for idx, t in enumerate(cut_times):
            t_val = float(t)
            if idx == 0 and t_val <= 0.05:
                snapped.append(0.0)
                continue
            nearest = min(sorted_beats, key=lambda b: abs(b - t_val))
            candidate = nearest if abs(nearest - t_val) <= tolerance_sec else t_val
            if snapped and (candidate - snapped[-1]) < min_spacing_sec:
                candidate = max(t_val, snapped[-1] + min_spacing_sec)
            snapped.append(round(candidate, 3))
        return snapped
