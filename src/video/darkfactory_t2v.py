"""DarkFactory Cinema Engine — Text-to-Video (T2V) Narrative Architect v1.0.

Designed specifically for Faceless YouTube Dark Channels, historical documentaries,
and cinematic storytelling. Bypasses the limitations of static Image-to-Video (I2V)
by synthesizing high-retention, kinetic dual-shot scenes targeting MiniMax (Hailuo H3)
and Google Flow (Veo 2).
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

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
T2V_PROMPTS_FILE = PROCESSED_DIR / "darkfactory_t2v_prompts.json"
MINIMAX_QUEUE_FILE = PROCESSED_DIR / "minimax_t2v_queue.json"
GOOGLE_VEO_QUEUE_FILE = PROCESSED_DIR / "google_veo_queue.json"

logger = logging.getLogger("DarkFactoryT2V")

# ══════════════════════════════════════════════════════
# Narrative Archetypes for Faceless Dark Channels
# ══════════════════════════════════════════════════════

NARRATIVE_ARCHETYPES = {
    "cold_war_espionage": {
        "title": "Cold War Nuclear Tension & False Alarm",
        "description": "High-stakes Soviet/US military bunkers, CRT radar telemetry, red emergency sirens, and psychological pressure.",
        "color_palette": "Military olive drab, CRT phosphor green (#00FF66), blood red alarm strobes (#FF1A1A), amber incandescent warning lights.",
        "optics": "Cooke Anamorphic 35mm f/2.0, shallow depth of field, 2.39:1 letterbox, Kodak Vision3 500T 5219 grain emulation.",
        "scenes": [
            {
                "scene_id": 1,
                "title": "The First Nuclear Alarm Beacon",
                "narrative_beat": "Serpukhov-15 secret military bunker, 1983. The early warning satellite system blares false nuclear launch confirmation.",
                "shot_a": {
                    "focus": "character_tension",
                    "camera": "Slow cinematic push-in (dolly track forward) from medium to tight close-up",
                    "subject": "Soviet duty officer Lieutenant Colonel Stanislav Petrov seated at a heavy steel console, under pulsating red emergency alarm beacons. His eyes wide with sudden tension, subtle cold sweat glinting on his brow as red light reflects in his glasses. Authentic human micro-expressions, breathing heavily with palpable psychological dread.",
                    "duration": 5.0,
                },
                "shot_b": {
                    "focus": "tactical_macro",
                    "camera": "Handheld visceral drift with slight mechanical rumble, macro focus pull",
                    "subject": "Extreme macro of the retro Soviet command CRT screen. A glowing phosphor-green ballistic trajectory map showing 5 incoming intercontinental missiles with flashing Cyrillic warning text 'СТАРТ'. The amber mechanical toggle switches vibrate gently on the brushed steel dashboard.",
                    "duration": 5.0,
                }
            },
            {
                "scene_id": 2,
                "title": "The Agonizing Phone Line",
                "narrative_beat": "Petrov grasps the secure bakelite red telephone receiver to report the false alarm, defying automated protocols.",
                "shot_a": {
                    "focus": "character_action",
                    "camera": "Low-angle eye-level tracking shot moving laterally across the command room",
                    "subject": "Petrov lifting the heavy crimson military telephone to his ear, his jaw clenched, veins visible on his neck, speaking into the receiver with intense hushed authority while junior officers behind him freeze in stunned panic.",
                    "duration": 5.0,
                },
                "shot_b": {
                    "focus": "tactical_macro",
                    "camera": "Dutch angle tight zoom settling onto the glowing countdown dials",
                    "subject": "Close-up on the analog ballistic timer ticking down towards zero. The second hand ticks with sharp mechanical precision, illuminated by flickering overhead fluorescent tubes, deep shadows casting dramatic contrast across the rivets.",
                    "duration": 5.0,
                }
            }
        ]
    },
    "cyber_warfare": {
        "title": "Covert Cyber Espionage & Server Infiltration",
        "description": "Subterranean datacenter intrusion, glowing optical racks, terminal code execution, and high-tech corporate sabotage.",
        "color_palette": "Deep cyan (#00D2FF), obsidian glass black, laser indigo (#4B0082), pulsating server LED orange.",
        "optics": "Leica Noctilux 50mm f/0.95, extreme low-light sensitivity, crisp optical chromatic aberrations, anamorphic horizontal streaks.",
        "scenes": [
            {
                "scene_id": 1,
                "title": "Zero-Day Datacenter Breach",
                "narrative_beat": "A shadowy operative in a dark server hall taps into an air-gapped mainframe fiber array.",
                "shot_a": {
                    "focus": "character_tension",
                    "camera": "Smooth Ronin 4D gimbal orbital drift around the operator",
                    "subject": "Silhouetted cybersecurity hacker in tactical black apparel kneeling beside an open enterprise server rack. The cascading teal and amber LEDs cast complex shadows across their face mask as their gloved hands rapidly deploy a hardware bypass module.",
                    "duration": 5.0,
                },
                "shot_b": {
                    "focus": "tactical_macro",
                    "camera": "Macro probe lens tracking across glowing optical fiber glass",
                    "subject": "Macro probe perspective skimming along glowing fiber optic cables with high-speed light pulses flowing inside translucent conduits, culminating at a high-speed data transfer screen displaying rapid hexadecimal packet dumps.",
                    "duration": 5.0,
                }
            }
        ]
    },
    "deep_space_scifi": {
        "title": "Deep Space Station & Isolation Anomaly",
        "description": "Silent monolithic orbital station, vast planetary rings, depressurization alarms, and cosmic existential dread.",
        "color_palette": "Vacuum void black, solar gold reflection (#FFD700), oxygen warning amber, frost cyan.",
        "optics": "Arri Master Anamorphic 40mm, pin-sharp stars, zero atmospheric haze, majestic slow 24fps cinema cadence.",
        "scenes": [
            {
                "scene_id": 1,
                "title": "The Silent Exterior Airlock",
                "narrative_beat": "An astronaut floats outside the massive rotating hab-ring overlooking the ice rings of Saturn.",
                "shot_a": {
                    "focus": "character_tension",
                    "camera": "Slow floating cinematic crane descent past the reflective gold visor",
                    "subject": "Astronaut in detailed EVA suit tethered to the titanium hull. The curved gold visor reflects the blinding crescent of Saturn and billions of razor-sharp ice particles. The astronaut's breathing condensates slightly against the thermal glass.",
                    "duration": 6.0,
                },
                "shot_b": {
                    "focus": "tactical_macro",
                    "camera": "Macro tracking along thruster manifold and locking clamps",
                    "subject": "Close-up on the hydraulic airlock docking clamp groaning under pressure, tiny micro-meteorite sparks glinting against cold brushed tungsten as cryogenic vapor vents into the dark vacuum of space.",
                    "duration": 6.0,
                }
            }
        ]
    }
}


@dataclass
class T2VShot:
    """Represents a single cinema camera shot generated for T2V models."""
    shot_id: str                   # e.g., "scene_1_shot_a"
    shot_type: str                 # "shot_a" (character/drama) or "shot_b" (macro/tactical)
    focus: str                     # "character_tension" | "tactical_macro" | "establishing"
    camera_movement: str           # e.g., "Slow push-in dolly track"
    subject_description: str
    target_duration_sec: float
    aspect_ratio: str              # "16:9" default
    minimax_prompt: str            # Tailored for MiniMax H3 (Hailuo)
    google_veo_prompt: str         # Tailored for Google Flow / Veo 2
    status: str = "pending"        # "pending" | "generated" | "cataloged"


@dataclass
class T2VScene:
    """Represents a dual-shot scene (Shot A + Shot B) designed for high YouTube retention."""
    scene_id: int
    title: str
    archetype: str
    narrative_beat: str
    shots: List[T2VShot] = field(default_factory=list)


def format_minimax_prompt(
    subject: str,
    camera: str,
    lighting_palette: str,
    duration: float = 5.0
) -> str:
    """Format prompt adhering strictly to MiniMax H3 / Hailuo Video-01 best practices.

    MiniMax responds exceptionally to explicit camera tags, natural physical momentum,
    and visceral material textures.
    """
    clean_subj = subject.strip().rstrip(".")
    clean_cam = camera.strip().rstrip(".")
    
    return (
        f"[Camera Movement: {clean_cam}]. "
        f"{clean_subj}. "
        f"Cinematic lighting: {lighting_palette}. "
        f"Authentic film grain, natural weight and physics, hyper-realistic human motion, "
        f"atmospheric volumetric shadows, 24fps motion cadence, master cinematography, "
        f"no digital warping, no anatomical glitches."
    )


def format_google_veo_prompt(
    subject: str,
    camera: str,
    optics: str,
    lighting_palette: str
) -> str:
    """Format prompt adhering strictly to Google Flow / Veo 2 cinematography standards.

    Veo 2 requires precise optical lens profiles, film stock emulation, and 3D volumetric staging.
    """
    clean_subj = subject.strip().rstrip(".")
    clean_cam = camera.strip().rstrip(".")
    
    return (
        f"Cinematic 4K UHD widescreen 2.39:1 letterbox footage. "
        f"{clean_subj}. "
        f"Camera trajectory: {clean_cam}. "
        f"Lens & Optics: {optics}. "
        f"Color Palette: {lighting_palette}. "
        f"Shot on 35mm motion picture film, natural organic motion blur, rich micro-contrast, "
        f"zero artificial smoothing, deep shadow detail, broadcast documentary prestige quality."
    )


class DarkFactoryT2VDirector:
    """Orchestrator for Text-to-Video scene generation and prompt dispatch."""

    def __init__(self, persistence_file: Path = T2V_PROMPTS_FILE):
        self.persistence_file = persistence_file
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        self.scenes: List[Dict[str, Any]] = self._load_persisted()

    def _load_persisted(self) -> List[Dict[str, Any]]:
        if self.persistence_file.exists():
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read existing T2V prompts: {e}")
        return []

    def _save_atomic(self) -> None:
        """Atomic write (ADR-02) using temporary file replacement."""
        tmp = self.persistence_file.with_suffix(f".tmp.{os.getpid()}_{int(time.time())}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.scenes, f, indent=2, ensure_ascii=False)
        tmp.replace(self.persistence_file)
        logger.info(f"💾 Persisted {len(self.scenes)} T2V scenes to {self.persistence_file.name}")

    def create_scene_from_archetype(
        self,
        archetype_key: str,
        scene_index: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Instantiate a structured dual-shot scene from the curated archetype library."""
        arch = NARRATIVE_ARCHETYPES.get(archetype_key)
        if not arch:
            logger.error(f"Unknown archetype: '{archetype_key}'. Available: {list(NARRATIVE_ARCHETYPES.keys())}")
            return None

        available_scenes = arch.get("scenes", [])
        if not available_scenes or scene_index >= len(available_scenes):
            logger.warning(f"Scene index {scene_index} out of bounds for archetype {archetype_key}")
            return None

        raw_scene = available_scenes[scene_index]
        s_id = raw_scene["scene_id"]
        palette = arch["color_palette"]
        optics = arch["optics"]

        # Build Shot A (Character / Tension)
        shot_a_raw = raw_scene["shot_a"]
        shot_a = T2VShot(
            shot_id=f"{archetype_key}_scene_{s_id}_shot_a",
            shot_type="shot_a",
            focus=shot_a_raw["focus"],
            camera_movement=shot_a_raw["camera"],
            subject_description=shot_a_raw["subject"],
            target_duration_sec=shot_a_raw.get("duration", 5.0),
            aspect_ratio="16:9",
            minimax_prompt=format_minimax_prompt(
                subject=shot_a_raw["subject"],
                camera=shot_a_raw["camera"],
                lighting_palette=palette,
                duration=shot_a_raw.get("duration", 5.0)
            ),
            google_veo_prompt=format_google_veo_prompt(
                subject=shot_a_raw["subject"],
                camera=shot_a_raw["camera"],
                optics=optics,
                lighting_palette=palette
            )
        )

        # Build Shot B (Tactical Macro / Action)
        shot_b_raw = raw_scene["shot_b"]
        shot_b = T2VShot(
            shot_id=f"{archetype_key}_scene_{s_id}_shot_b",
            shot_type="shot_b",
            focus=shot_b_raw["focus"],
            camera_movement=shot_b_raw["camera"],
            subject_description=shot_b_raw["subject"],
            target_duration_sec=shot_b_raw.get("duration", 5.0),
            aspect_ratio="16:9",
            minimax_prompt=format_minimax_prompt(
                subject=shot_b_raw["subject"],
                camera=shot_b_raw["camera"],
                lighting_palette=palette,
                duration=shot_b_raw.get("duration", 5.0)
            ),
            google_veo_prompt=format_google_veo_prompt(
                subject=shot_b_raw["subject"],
                camera=shot_b_raw["camera"],
                optics=optics,
                lighting_palette=palette
            )
        )

        scene_dict = {
            "scene_id": s_id,
            "title": raw_scene["title"],
            "archetype": archetype_key,
            "narrative_beat": raw_scene["narrative_beat"],
            "created_at": time.time(),
            "shots": [asdict(shot_a), asdict(shot_b)]
        }

        # Update or append
        existing_idx = next((i for i, s in enumerate(self.scenes) if s.get("title") == raw_scene["title"] and s.get("archetype") == archetype_key), None)
        if existing_idx is not None:
            self.scenes[existing_idx] = scene_dict
        else:
            self.scenes.append(scene_dict)

        self._save_atomic()
        self.export_model_queues()
        return scene_dict

    def create_custom_dual_shot(
        self,
        scene_title: str,
        narrative_beat: str,
        shot_a_subject: str,
        shot_a_camera: str,
        shot_b_subject: str,
        shot_b_camera: str,
        archetype: str = "custom",
        color_palette: str = "Cinematic Kodak 2383 Bleach-Bypass, deep contrast shadows, warm amber highlights",
        optics: str = "Cooke Anamorphic 35mm f/2.0 cine lens, 2.39:1 widescreen frame",
        duration: float = 5.0
    ) -> Dict[str, Any]:
        """Synthesize a bespoke custom Dual-Shot scene for any script beat."""
        scene_id = len(self.scenes) + 1
        
        shot_a = T2VShot(
            shot_id=f"custom_scene_{scene_id}_shot_a",
            shot_type="shot_a",
            focus="character_tension",
            camera_movement=shot_a_camera,
            subject_description=shot_a_subject,
            target_duration_sec=duration,
            aspect_ratio="16:9",
            minimax_prompt=format_minimax_prompt(shot_a_subject, shot_a_camera, color_palette, duration),
            google_veo_prompt=format_google_veo_prompt(shot_a_subject, shot_a_camera, optics, color_palette)
        )

        shot_b = T2VShot(
            shot_id=f"custom_scene_{scene_id}_shot_b",
            shot_type="shot_b",
            focus="tactical_macro",
            camera_movement=shot_b_camera,
            subject_description=shot_b_subject,
            target_duration_sec=duration,
            aspect_ratio="16:9",
            minimax_prompt=format_minimax_prompt(shot_b_subject, shot_b_camera, color_palette, duration),
            google_veo_prompt=format_google_veo_prompt(shot_b_subject, shot_b_camera, optics, color_palette)
        )

        scene_dict = {
            "scene_id": scene_id,
            "title": scene_title,
            "archetype": archetype,
            "narrative_beat": narrative_beat,
            "created_at": time.time(),
            "shots": [asdict(shot_a), asdict(shot_b)]
        }

        self.scenes.append(scene_dict)
        self._save_atomic()
        self.export_model_queues()
        return scene_dict

    def export_model_queues(self) -> Tuple[Path, Path]:
        """Export clean, ready-to-run prompt queues for MiniMax and Google Veo 2."""
        minimax_items = []
        veo_items = []

        for sc in self.scenes:
            for sh in sc.get("shots", []):
                minimax_items.append({
                    "shot_id": sh["shot_id"],
                    "scene_title": sc.get("title"),
                    "shot_type": sh["shot_type"],
                    "duration": sh["target_duration_sec"],
                    "minimax_prompt": sh["minimax_prompt"],
                    "status": sh.get("status", "pending")
                })
                veo_items.append({
                    "shot_id": sh["shot_id"],
                    "scene_title": sc.get("title"),
                    "shot_type": sh["shot_type"],
                    "duration": sh["target_duration_sec"],
                    "veo_prompt": sh["google_veo_prompt"],
                    "status": sh.get("status", "pending")
                })

        with open(MINIMAX_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(minimax_items, f, indent=2, ensure_ascii=False)

        with open(GOOGLE_VEO_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(veo_items, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Exported {len(minimax_items)} prompts to {MINIMAX_QUEUE_FILE.name}")
        logger.info(f"✅ Exported {len(veo_items)} prompts to {GOOGLE_VEO_QUEUE_FILE.name}")
        return MINIMAX_QUEUE_FILE, GOOGLE_VEO_QUEUE_FILE

    def get_stats(self) -> Dict[str, Any]:
        """Summary metrics for the DarkFactory T2V pipeline."""
        total_scenes = len(self.scenes)
        total_shots = sum(len(s.get("shots", [])) for s in self.scenes)
        pending_shots = sum(
            1 for s in self.scenes for sh in s.get("shots", []) if sh.get("status") == "pending"
        )
        return {
            "total_scenes": total_scenes,
            "total_shots": total_shots,
            "pending_shots": pending_shots,
            "archetypes_available": list(NARRATIVE_ARCHETYPES.keys()),
        }


def initialize_default_darkfactory_pipeline() -> DarkFactoryT2VDirector:
    """Initialize the DarkFactory with Petrov Cold War scenes and Cyber Warfare scenes."""
    director = DarkFactoryT2VDirector()
    director.create_scene_from_archetype("cold_war_espionage", scene_index=0)
    director.create_scene_from_archetype("cold_war_espionage", scene_index=1)
    director.create_scene_from_archetype("cyber_warfare", scene_index=0)
    return director
