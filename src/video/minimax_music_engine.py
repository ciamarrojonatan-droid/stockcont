"""StockCont & DarkFactory — MiniMax Music 3 Cinematic Soundtrack Engine.

Connects to RunningHub ComfyUI RPA (Workflow 2120003151633174529) or procedural fallback
to generate 4-part symphonic tension soundtracks (Hans Zimmer / Ludwig Göransson)
for dark documentary films and microstock assets.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Windows UTF-8 enforcement (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("MiniMaxMusicEngine")

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
FINAL_AUDIO_DIR: Path = BASE_DIR / "data" / "final" / "audio"
FINAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Cinematic Soundtrack Archetypes
MUSIC_PRESETS: Dict[str, Dict[str, str]] = {
    "hans_zimmer_tension": {
        "style": (
            "Hans Zimmer style acoustic architecture, dark cinematic tension soundtrack, "
            "60 BPM mechanical clockwork pulse, analog modular synth bass drones, swelling cello ostinatos, "
            "resonant Taiko impacts, wall of sound crescendo, Christopher Nolan Oppenheimer thriller soundscape."
        ),
        "structure": (
            "[Intro: Ominous low-frequency sub-bass drone and eerie metallic bowed textures]\n"
            "[Tension: 60 BPM mechanical ticking with rising cello ostinato and swelling brass pads]\n"
            "[Climax: Massive Hans Zimmer wall of sound, resonant Taiko percussion, full dark string section]\n"
            "[Outro: Slow decrescendo into lingering low-frequency sub-bass vibration and dying clock ticks]"
        ),
    },
    "ludwig_goransson_action": {
        "style": (
            "Ludwig Göransson modern thriller score, distorted 808 sub-bass, rapid acoustic staccato strings, "
            "metallic industrial percussion, intense suspense pacing, Tenet acoustic reverse motifs, high energy."
        ),
        "structure": (
            "[Intro: Glitched electronic pulses and reverse string swells]\n"
            "[Tension: Accelerating 120 BPM percussive drive, syncopated industrial rhythms]\n"
            "[Climax: Explosive distorted bass hits, chaotic strings, visceral acoustic power]\n"
            "[Outro: Abrupt tape stop effect dissolving into atmospheric low drone]"
        ),
    },
    "cold_war_espionage": {
        "style": (
            "Cold War espionage suspense soundtrack, 55 Hz low frequency drone, ominous BBC documentary tone, "
            "subtle analog radar ticks, mysterious cello harmonies, quiet rising dread, historical solemnity."
        ),
        "structure": (
            "[Intro: Low sub drone with quiet analog tape hiss]\n"
            "[Tension: Subtle 60 BPM clockwork second-hand ticking, mournful cello melodies]\n"
            "[Climax: Intense harmonic dissonance, urgent brass swells, acute historical suspense]\n"
            "[Outro: Fading radar bleeps and long dark ambient chord decay]"
        ),
    },
    "cyber_warfare": {
        "style": (
            "Cyber warfare grid collapse score, dark ambient synthwave bassline, high tension countdown, "
            "glitching electronic textures, atmospheric sub-bass, sterile cold acoustic design."
        ),
        "structure": (
            "[Intro: Digital hum and distant data transmission noises]\n"
            "[Tension: Pulse of cyber alarm, tight synthesizer sequences, rising panic]\n"
            "[Climax: Overwhelming sub-bass drop, distorted warning frequencies]\n"
            "[Outro: System failure shutdown soundbed fading into silent abyss]"
        ),
    },
}


@dataclass
class MusicTrackResult:
    """Result container for generated soundtrack track."""
    audio_path: Path
    filename: str
    duration_seconds: float
    style: str
    structure: str
    engine: str
    filesize_bytes: int


class MiniMaxMusicEngine:
    """Orchestrates MiniMax Music 3 generation on RunningHub with procedural fallback."""

    def __init__(self, output_dir: Optional[Union[Path, str]] = None) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else FINAL_AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_prompts(
        self,
        preset_name: str = "hans_zimmer_tension",
        custom_style: Optional[str] = None,
        custom_structure: Optional[str] = None,
    ) -> tuple[str, str]:
        """Returns (style_prompt, structure_prompt) according to requested style."""
        preset = MUSIC_PRESETS.get(preset_name, MUSIC_PRESETS["hans_zimmer_tension"])
        style = custom_style or preset["style"]
        structure = custom_structure or preset["structure"]
        return style, structure

    def generate_soundtrack(
        self,
        preset_name: str = "hans_zimmer_tension",
        custom_style: Optional[str] = None,
        custom_structure: Optional[str] = None,
        duration_sec: float = 180.0,
        destination_path: Optional[Union[Path, str]] = None,
        force_procedural: bool = False,
    ) -> MusicTrackResult:
        """Generates a soundtrack using MiniMax Music 3 on RunningHub or procedural fallback.

        Args:
            preset_name: One of 'hans_zimmer_tension', 'ludwig_goransson_action', 'cold_war_espionage', 'cyber_warfare'.
            custom_style: Optional override for style description (Node #15).
            custom_structure: Optional override for structure prompt (Node #16).
            duration_sec: Duration in seconds (Node #14, default 180.0).
            destination_path: Optional exact output file destination.
            force_procedural: If True, bypasses RunningHub and uses local procedural synthesis.
        """
        style, structure = self.build_prompts(preset_name, custom_style, custom_structure)

        if not force_procedural:
            try:
                from src.factory.runninghub_bot import run_minimax_music_bot
                logger.info(f"Triggering MiniMax Music 3 on RunningHub ({preset_name}, {duration_sec}s)...")
                res = run_minimax_music_bot(
                    style=style,
                    structure=structure,
                    duration_sec=duration_sec,
                    destination_dir=self.output_dir,
                )
                saved_files = res.get("saved_files", [])
                if saved_files:
                    primary_file = saved_files[0]
                    p = self.output_dir / primary_file
                    if p.exists() and p.stat().st_size > 1000:
                        if destination_path:
                            dest = Path(destination_path).resolve()
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            p.replace(dest)
                            p = dest
                        logger.info(f"✅ MiniMax Music 3 generated via RunningHub: {p.name}")
                        return MusicTrackResult(
                            audio_path=p,
                            filename=p.name,
                            duration_seconds=duration_sec,
                            style=style,
                            structure=structure,
                            engine="minimax_music_3",
                            filesize_bytes=p.stat().st_size,
                        )
            except Exception as e:
                logger.warning(f"RunningHub MiniMax Music RPA unavailable or failed ({e}). Falling back to DarkFactoryAudioEngine procedural synthesis.")

        # Procedural fallback synthesis (48kHz 16-bit Hans Zimmer soundbed)
        from src.video.audio_engine import DarkFactoryAudioEngine
        audio_engine = DarkFactoryAudioEngine(output_dir=self.output_dir)
        profile_map = {
            "hans_zimmer_tension": "cold_war_espionage",
            "cold_war_espionage": "cold_war_espionage",
            "ludwig_goransson_action": "cyber_warfare",
            "cyber_warfare": "cyber_warfare",
        }
        chosen_profile = profile_map.get(preset_name, "cold_war_espionage")
        soundbed = audio_engine.generate_procedural_soundbed(
            duration_seconds=min(duration_sec, 60.0),
            profile_name=chosen_profile,
            destination_path=destination_path,
        )
        logger.info(f"✅ Soundtrack generated via procedural fallback: {soundbed.filename}")
        return MusicTrackResult(
            audio_path=soundbed.audio_path,
            filename=soundbed.filename,
            duration_seconds=soundbed.duration_seconds,
            style=style,
            structure=structure,
            engine="procedural_fallback",
            filesize_bytes=soundbed.filesize_bytes,
        )
