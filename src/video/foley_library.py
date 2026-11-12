"""StockCont & DarkFactory — Curated CC0 Foley SFX Library & Procedural Mixer.

Provides deterministic, offline CC0-1.0 foley sound effects and timed
multi-event audio stem generation ready for 3-stem documentary mixing.
"""

from __future__ import annotations

import logging
import math
import os
import re
import sys
import uuid
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from src.video.ffmpeg_processor import decode_audio_pcm_mono

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.foley_library")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_FOLEY_DIR = BASE_DIR / "data" / "final" / "audio" / "foley_stems"
DEFAULT_CUSTOM_SFX_DIR = BASE_DIR / "data" / "raw" / "sfx_cc0"

CC0_SFX_CATALOG: Dict[str, Dict[str, Any]] = {
    "whoosh_subtle": {
        "category": "transition",
        "license": "CC0-1.0",
        "default_duration_sec": 0.45,
        "description": "Filtered air sweep transition between documentary scenes.",
    },
    "stamp_slam": {
        "category": "hud_impact",
        "license": "CC0-1.0",
        "default_duration_sec": 0.35,
        "description": "Weighted archival rubber-stamp slam + paper thud for DECLASSIFIED badges.",
    },
    "radar_ping": {
        "category": "telemetry",
        "license": "CC0-1.0",
        "default_duration_sec": 0.70,
        "description": "Clean resonant Cold War submarine/radar oscilloscope ping.",
    },
    "teletype_burst": {
        "category": "telemetry",
        "license": "CC0-1.0",
        "default_duration_sec": 0.60,
        "description": "Rapid mechanical teletype cipher print burst for date/coordinate reveals.",
    },
    "sub_riser": {
        "category": "tension",
        "license": "CC0-1.0",
        "default_duration_sec": 1.20,
        "description": "Low-frequency Zimmer/Goransson sub-bass tension swell leading into cuts.",
    },
}


@dataclass
class FoleyCue:
    """Single foley placement cue on the timeline."""

    sfx_name: str
    timestamp_sec: float
    gain_db: float = -8.0
    pan: float = 0.0  # -1.0 (L) to +1.0 (R)
    duration_sec: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FoleyTrackResult:
    """Output contract for a generated multi-cue CC0 foley stem."""

    success: bool
    sfx_track_path: Optional[str] = None
    duration_sec: float = 0.0
    cues_applied: int = 0
    catalog_used: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", (value or "foley").strip().lower()).strip("_")[:50] or "foley"


def _atomic_write_stereo_wav(path: Path, stereo_samples: np.ndarray, sample_rate: int) -> Path:
    """Write float32 [-1, 1] stereo (2, N) array atomically as 16-bit PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(stereo_samples, -0.95, 0.95)
    interleaved = np.empty(clipped.shape[1] * 2, dtype=np.int16)
    interleaved[0::2] = (clipped[0] * 32767.0).astype(np.int16)
    interleaved[1::2] = (clipped[1] * 32767.0).astype(np.int16)

    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(interleaved.tobytes())
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return path


class FoleyLibrary:
    """Offline CC0-1.0 foley SFX catalog and timeline stem synthesizer."""

    def __init__(
        self,
        output_dir: Optional[Path | str] = None,
        custom_sfx_dir: Optional[Path | str] = None,
    ) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_FOLEY_DIR.resolve()
        self.custom_sfx_dir = (
            Path(custom_sfx_dir).resolve() if custom_sfx_dir else DEFAULT_CUSTOM_SFX_DIR.resolve()
        )

    def list_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Return merged catalog of built-in CC0 effects and optional local CC0 WAVs."""
        catalog = {k: dict(v) for k, v in CC0_SFX_CATALOG.items()}
        if self.custom_sfx_dir.is_dir():
            for wav_file in sorted(self.custom_sfx_dir.glob("*.wav")):
                stem = wav_file.stem.lower()
                if stem not in catalog:
                    catalog[stem] = {
                        "category": "custom_local",
                        "license": "CC0-1.0",
                        "default_duration_sec": 0.5,
                        "description": f"Local CC0 asset: {wav_file.name}",
                        "local_path": wav_file.as_posix(),
                    }
        return catalog

    def synthesize_sfx(
        self,
        sfx_name: str,
        sample_rate: int = 44100,
        duration_sec: Optional[float] = None,
    ) -> np.ndarray:
        """Synthesize or load mono float32 waveform for a cataloged foley sound."""
        key = (sfx_name or "whoosh_subtle").strip().lower()
        custom_file = self.custom_sfx_dir / f"{key}.wav"
        if custom_file.is_file():
            pcm, _sr = decode_audio_pcm_mono(custom_file, target_sr=sample_rate)
            if len(pcm) > 0:
                return pcm

        if key not in CC0_SFX_CATALOG:
            raise ValueError(f"Unknown CC0 SFX '{sfx_name}'. Available: {sorted(CC0_SFX_CATALOG)}")

        dur = max(0.1, float(duration_sec or CC0_SFX_CATALOG[key]["default_duration_sec"]))
        n = int(round(dur * sample_rate))
        t = np.linspace(0.0, dur, n, endpoint=False, dtype=np.float32)
        rng = np.random.default_rng(42)
        noise = rng.normal(0.0, 1.0, size=n).astype(np.float32)

        if key == "stamp_slam":
            # Low percussive impact + paper slap decay
            env = np.exp(-t * 18.0)
            freq_sweep = 145.0 * np.exp(-t * 22.0) + 52.0
            phase = np.cumsum(2.0 * math.pi * freq_sweep / sample_rate)
            body = np.sin(phase) * env
            transient = noise * np.exp(-t * 55.0) * 0.45
            sig = 0.85 * body + transient
        elif key == "radar_ping":
            # High resonant sonar ping with dual harmonic tail
            env = np.minimum(1.0, t / 0.008) * np.exp(-t * 5.2)
            sig = (0.75 * np.sin(2.0 * math.pi * 1320.0 * t) + 0.25 * np.sin(2.0 * math.pi * 2640.0 * t)) * env
        elif key == "teletype_burst":
            # Rhythmic crisp mechanical impulses every ~48ms
            sig = np.zeros(n, dtype=np.float32)
            step = max(1, int(0.048 * sample_rate))
            click_len = max(16, int(0.012 * sample_rate))
            for pos in range(0, n - click_len, step):
                decay = np.exp(-np.linspace(0, 1, click_len, dtype=np.float32) * 8.0)
                tone = np.sin(2.0 * math.pi * 1850.0 * np.arange(click_len) / sample_rate)
                sig[pos : pos + click_len] += (0.55 * tone + 0.45 * noise[pos : pos + click_len]) * decay
        elif key == "sub_riser":
            # Smooth sub-bass riser swell + airy breath
            env = np.power(np.clip(t / dur, 0.0, 1.0), 1.8) * np.exp(-np.maximum(0.0, t - dur * 0.92) * 30.0)
            freq = 38.0 + (88.0 - 38.0) * (t / dur) ** 1.5
            phase = np.cumsum(2.0 * math.pi * freq / sample_rate)
            sig = (0.85 * np.sin(phase) + 0.20 * noise) * env
        else:
            # whoosh_subtle: smooth bell-envelope filtered air sweep
            win = np.sin(math.pi * t / dur) ** 2
            # Simple rolling average low-pass on noise
            kernel = np.ones(11, dtype=np.float32) / 11.0
            filtered = np.convolve(noise, kernel, mode="same")
            sig = filtered * win * 1.4

        peak = float(np.max(np.abs(sig))) if len(sig) else 0.0
        if peak > 1e-5:
            sig = (sig / peak) * 0.85
        return sig.astype(np.float32)

    @staticmethod
    def build_cues_from_triggers(
        trigger_events: Sequence[Dict[str, Any]],
        default_sfx: str = "stamp_slam",
    ) -> List[FoleyCue]:
        """Convert spoken keyword triggers or markers into appropriate CC0 foley cues."""
        cues: List[FoleyCue] = []
        for idx, ev in enumerate(trigger_events):
            kw = str(ev.get("keyword") or ev.get("sfx_name") or "").lower()
            ts = float(ev.get("timestamp_sec") or 0.0)
            sfx = default_sfx
            if any(tok in kw for tok in ("radar", "missile", "sonar", "ping", "orbit", "satellit")):
                sfx = "radar_ping"
            elif any(tok in kw for tok in ("declassified", "classified", "secret", "top secret", "stamp")):
                sfx = "stamp_slam"
            elif any(tok in kw for tok in ("date", "1983", "teletype", "intercept", "cipher", "file")):
                sfx = "teletype_burst"
            elif any(tok in kw for tok in ("tension", "countdown", "alert", "riser")):
                sfx = "sub_riser"
            elif any(tok in kw for tok in ("transition", "whoosh", "cut")):
                sfx = "whoosh_subtle"
            pan = -0.15 if idx % 2 == 0 else 0.15
            cues.append(FoleyCue(sfx_name=sfx, timestamp_sec=max(0.0, ts), gain_db=-6.0, pan=pan))
        return cues

    def build_foley_stem(
        self,
        cues: Sequence[FoleyCue],
        total_duration_sec: float,
        output_wav_path: Optional[Path | str] = None,
        sample_rate: int = 44100,
    ) -> FoleyTrackResult:
        """Render and mix all foley cues onto a synchronized stereo WAV stem."""
        dur = max(0.5, float(total_duration_sec))
        total_samples = max(1, int(round(dur * sample_rate)))
        stereo = np.zeros((2, total_samples), dtype=np.float32)
        used: List[str] = []
        applied = 0

        for cue in cues:
            if cue.timestamp_sec < 0.0 or cue.timestamp_sec >= dur:
                continue
            mono = self.synthesize_sfx(
                cue.sfx_name,
                sample_rate=sample_rate,
                duration_sec=cue.duration_sec,
            )
            gain = float(10.0 ** (float(cue.gain_db) / 20.0))
            pan = max(-1.0, min(1.0, float(cue.pan)))
            left_gain = gain * math.sqrt((1.0 - pan) * 0.5)
            right_gain = gain * math.sqrt((1.0 + pan) * 0.5)

            start_idx = int(round(cue.timestamp_sec * sample_rate))
            avail = min(len(mono), total_samples - start_idx)
            if avail <= 0:
                continue
            stereo[0, start_idx : start_idx + avail] += mono[:avail] * left_gain
            stereo[1, start_idx : start_idx + avail] += mono[:avail] * right_gain
            applied += 1
            if cue.sfx_name not in used:
                used.append(cue.sfx_name)

        # Peak safety limiter
        max_peak = float(np.max(np.abs(stereo))) if stereo.size else 0.0
        if max_peak > 0.92:
            stereo *= 0.92 / max_peak

        out_path = (
            Path(output_wav_path).resolve()
            if output_wav_path
            else (self.output_dir / f"foley_{_slugify('_'.join(used) or 'stem')}_{uuid.uuid4().hex[:6]}.wav").resolve()
        )
        _atomic_write_stereo_wav(out_path, stereo, sample_rate=sample_rate)

        return FoleyTrackResult(
            success=True,
            sfx_track_path=out_path.as_posix(),
            duration_sec=round(dur, 3),
            cues_applied=applied,
            catalog_used=used,
        )
