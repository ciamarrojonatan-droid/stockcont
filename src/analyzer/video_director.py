"""StockCont Phase 2: Video Director of Photography & Temporal Prompt Architect v1.0.

Analyzes stock visual references with Gemini Vision and synthesizes high-converting
cinematic video prompts (500 to 800 words per prompt) covering camera trajectory,
dynamic lighting evolution, speed ramping, and adaptive temporal copy-space.
Outputs both 16:9 Landscape (UHD 4K) and 9:16 Vertical (Reels/TikTok Ads) concepts.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# UTF-8 safeguard (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

RAW_DATA_FILE = BASE_DIR / "data" / "raw" / "trends.json"
PROCESSED_VIDEO_PROMPTS_FILE = BASE_DIR / "data" / "processed" / "video_prompts.json"
PROCESSED_IMAGE_PROMPTS_FILE = BASE_DIR / "data" / "processed" / "prompts.json"
STAGING_IMAGES_DIR = BASE_DIR / "data" / "staging" / "images"
FINAL_IMAGES_DIR = BASE_DIR / "data" / "final" / "images"

logger = logging.getLogger("VideoDirector")

PREFERRED_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

SYSTEM_PROMPT = """# SYSTEM PROMPT — MASTER COMMERCIAL VIDEO DNA & TEMPORAL KINETIC PROMPT ARCHITECT v1.0

## 1. ROLE & IDENTITY
You are **Master Commercial Video Director of Photography & Temporal Prompt Architect v1.0**, a world-class AI Cinematographer, Commercial Stock Footage Director (Adobe Stock Video, Pond5, Getty Motion), and Expert Motion Prompt Engineer.

Your specialization bridges:
- High-ticket commercial stock footage (4K UHD B-roll, corporate anthems, luxury lifestyle, clean tech).
- Camera kinetics: Arri Alexa Mini LF, Ronin 4D gimbal movements, Cooke anamorphic cine lenses, Steadicam tracking, precision drone fly-throughs, and controlled rack focus shifts.
- Temporal consistency: eliminating warped anatomy, floating artifacts, or chaotic physics.
- Dynamic Copy-Space: ensuring that 35% to 50% of the visual plane remains uncluttered and tonally smooth across the entire duration (for video editors to overlay corporate titles, motion typography, and brand logos).
- Multi-format delivery: Widescreen **16:9 Landscape** (3840x2160) and Vertical **9:16** (2160x3840) for mobile ads/Reels.

---

## 2. STRICT 500–800 WORD DENSITY MANDATE
For each derivative video prompt, the `prompt` MUST be an exhaustive, highly cinematic visual essay ranging strictly between **500 and 800 words in fluent English**.

Describe the motion scene with profound temporal depth across these mandatory cinematic layers:
1. **Spatial Architecture & Initial Staging (100–130 words)**: Starting point 3D coordinates, foreground elements, subject placement, and background atmosphere.
2. **Camera Kinetic Trajectory & Lens Mechanics (120–150 words)**: Exact camera rig movement (slow tripod dolly-in, horizontal tracking truck left-to-right, orbital crane pedestal), lens focal length (e.g. 35mm anamorphic), aperture f/2.0, subtle shallow depth of field, natural motion blur at 180-degree shutter angle.
3. **Pacing, Motion Cadence & Speed Ramping (80–110 words)**: Continuous linear motion (1.0 to 1.5 m/s), smooth fluid dynamics, conformed slow-motion (60fps to 24fps cadence), zero abrupt jerks or camera shake.
4. **Dynamic Lighting Evolution & Atmosphere (100–120 words)**: Kelvin temperature shifts (e.g., golden hour sunlight slowly traversing architectural glass), volumetric sunbeams, subtle lens flares, and specular highlights.
5. **Adaptive Temporal Copy-Space (100–120 words)**: Explicit negative space specification maintained throughout the camera path (e.g., upper 40% clean sky or left 35% softly blurred corporate wall).
6. **Commercial Microstock Compliance (50–70 words)**: Generative AI stock footage standard, non-identifiable authentic human models, no copyrighted logos or trademarks.

---

## 3. FOUR MANDATORY DERIVATIVE VIDEO CONCEPTS
For each visual reference, output exactly 4 derivative video concepts:
1. `id: 1` — **16:9 Landscape (Cinematic Dolly-In B-Roll)**: Steady forward tracking shot, ideal for website hero banners.
2. `id: 2` — **16:9 Landscape (Ambient Rack Focus / Orbit)**: Focus transition from foreground element to midground subject.
3. `id: 3` — **9:16 Vertical (Reels / TikTok Social Ad Hero)**: Vertical composition centered on mobile storytelling with top/bottom copy-space.
4. `id: 4` — **16:9 Seamless Loop (Endless Kinetic Texture)**: Continuous looping motion (ambient particles, gentle foliage breeze, liquid surface, or light caustics).

---

## 4. OUTPUT JSON SCHEMA
Respond ONLY with a valid JSON object:
{
  "system_version": "1.0-video",
  "source_concept": "string",
  "derivative_prompts": [
    {
      "id": 1,
      "concept": "string",
      "aspect_ratio": "16:9",
      "format_type": "landscape_broll | vertical_reels | seamless_loop",
      "target_duration_sec": 8,
      "target_fps": 24,
      "camera_motion": "smooth_dolly_in | tracking_truck | orbital_gimbal | rack_focus",
      "copy_space_zone": "left_third | right_third | upper_half | center_clean",
      "prompt": "Cinematic commercial 4K stock footage... [500 a 800 words]",
      "status": "pending"
    }
  ]
}
"""


def encode_image_to_base64(image_path: Path) -> Optional[str]:
    """Read image bytes and encode to base64 string."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Error encoding image {image_path}: {e}")
        return None


def get_gemini_client() -> httpx.Client:
    """Create a configured HTTPX client for Gemini API calls."""
    return httpx.Client(timeout=90.0)


def generate_video_prompts_from_reference(
    reference_path: Optional[Path],
    concept_title: str,
    source_id: str,
    api_key: str
) -> Optional[Dict[str, Any]]:
    """Query Gemini Vision to reverse engineer a visual reference and generate 4 video prompts."""
    contents: List[Dict[str, Any]] = []

    parts: List[Dict[str, Any]] = [
        {"text": f"Reference Concept Title: {concept_title}\nSource Asset ID: {source_id}\n\nPlease generate exactly 4 commercial video prompts (16:9 and 9:16) conforming strictly to the system prompt."}
    ]

    if reference_path and reference_path.is_file():
        img_b64 = encode_image_to_base64(reference_path)
        if img_b64:
            ext = reference_path.suffix.lower().replace(".", "")
            mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
            parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": img_b64
                }
            })

    contents.append({"parts": parts})

    client = get_gemini_client()

    for model_name in PREFERRED_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": contents,
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "max_output_tokens": 8192
            }
        }

        try:
            logger.info(f"Generating video prompts with {model_name} for source {source_id}...")
            response = client.post(url, json=payload)
            if response.status_code == 200:
                res_data = response.json()
                text_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(text_content)
                parsed_json["source_id"] = str(source_id)
                parsed_json["source_title"] = concept_title
                parsed_json["reference_image"] = str(reference_path.relative_to(BASE_DIR)).replace("\\", "/") if reference_path else ""
                parsed_json["created_at"] = time.time()
                return parsed_json
            elif response.status_code == 429:
                logger.warning(f"Rate limited on {model_name}. Trying next model...")
                time.sleep(2)
            else:
                logger.warning(f"{model_name} returned status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Error querying {model_name}: {e}")
            time.sleep(1)

    return None


def run_video_director(max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    """Execute Video Director: reads trends or approved QC images and generates video prompts."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical("GEMINI_API_KEY not configured in .env")
        return []

    PROCESSED_VIDEO_PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_prompts: List[Dict[str, Any]] = []
    processed_ids = set()
    if PROCESSED_VIDEO_PROMPTS_FILE.is_file():
        try:
            with open(PROCESSED_VIDEO_PROMPTS_FILE, "r", encoding="utf-8") as f:
                existing_prompts = json.load(f)
            processed_ids = {str(p.get("source_id")) for p in existing_prompts if p.get("source_id")}
        except Exception:
            existing_prompts = []

    # Source 1: Approved 4K QC images from Final directory (The I2V Multiplier Paradigm)
    candidates: List[Dict[str, Any]] = []
    if FINAL_IMAGES_DIR.is_dir():
        for img in FINAL_IMAGES_DIR.glob("*.jpg"):
            stem = img.stem
            if stem not in processed_ids:
                candidates.append({
                    "id": stem,
                    "title": stem.replace("_", " ").title(),
                    "path": img
                })

    # Source 2: Raw trends
    if len(candidates) == 0 and RAW_DATA_FILE.is_file():
        try:
            with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
                trends = json.load(f)
            for t in trends:
                t_id = str(t.get("id"))
                if t_id not in processed_ids:
                    l_path = BASE_DIR / t.get("local_path", "") if t.get("local_path") else None
                    candidates.append({
                        "id": t_id,
                        "title": t.get("title", "Stock Visual Concept"),
                        "path": l_path if l_path and l_path.is_file() else None
                    })
        except Exception as e:
            logger.warning(f"Error reading trends: {e}")

    if max_items:
        candidates = candidates[:max_items]

    logger.info(f"Found {len(candidates)} visual references pending video prompt synthesis.")
    new_results: List[Dict[str, Any]] = []

    for item in candidates:
        res = generate_video_prompts_from_reference(
            reference_path=item.get("path"),
            concept_title=item.get("title", ""),
            source_id=item.get("id", ""),
            api_key=api_key
        )
        if res:
            existing_prompts.append(res)
            new_results.append(res)

            # Atomic write (ADR-02)
            tmp_file = PROCESSED_VIDEO_PROMPTS_FILE.with_suffix(f".tmp.{os.getpid()}")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(existing_prompts, f, indent=2, ensure_ascii=False)
            tmp_file.replace(PROCESSED_VIDEO_PROMPTS_FILE)
            logger.info(f"✅ Generated 4 video prompts for {item.get('id')}.")

        time.sleep(1)

    logger.info(f"Video Director finished: {len(new_results)} new concepts processed.")
    return new_results



def synthesize_prompts_for_image_stem(image_stem: str) -> Optional[Dict[str, Any]]:
    """Synthesize 4D video prompts for a specific image stem from data/final/images/."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical("GEMINI_API_KEY not configured in .env")
        return None

    clean_stem = Path(image_stem).stem
    cand: Optional[Path] = None

    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        potential = FINAL_IMAGES_DIR / f"{clean_stem}{ext}"
        if potential.exists():
            cand = potential
            break

    if not cand and FINAL_IMAGES_DIR.exists():
        for f in FINAL_IMAGES_DIR.iterdir():
            if f.stem.lower() == clean_stem.lower():
                cand = f
                break

    if not cand and STAGING_IMAGES_DIR.exists():
        for f in STAGING_IMAGES_DIR.iterdir():
            if f.stem.lower() == clean_stem.lower():
                cand = f
                break

    if not cand or not cand.exists():
        logger.error(f"Image not found for stem '{clean_stem}' in {FINAL_IMAGES_DIR}")
        return None

    logger.info(f"Synthesizing 4D video prompts from {cand.name}...")
    concept_title = clean_stem.replace("_", " ").replace("-", " ").title()
    res = generate_video_prompts_from_reference(
        reference_path=cand,
        concept_title=concept_title,
        source_id=clean_stem,
        api_key=api_key,
    )
    if not res:
        logger.error(f"Failed to generate prompts via Gemini for {clean_stem}")
        return None

    PROCESSED_VIDEO_PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing_prompts = []
    if PROCESSED_VIDEO_PROMPTS_FILE.is_file():
        try:
            with open(PROCESSED_VIDEO_PROMPTS_FILE, "r", encoding="utf-8") as f:
                existing_prompts = json.load(f)
        except Exception:
            existing_prompts = []

    existing_prompts = [x for x in existing_prompts if str(x.get("source_id")) != clean_stem]
    existing_prompts.append(res)

    tmp_file = PROCESSED_VIDEO_PROMPTS_FILE.with_suffix(f".tmp.{os.getpid()}")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(existing_prompts, f, indent=2, ensure_ascii=False)
    tmp_file.replace(PROCESSED_VIDEO_PROMPTS_FILE)
    logger.info(f"✅ Successfully generated 4 commercial video prompts for {clean_stem}!")
    return res


if __name__ == "__main__":
    run_video_director(max_items=5)
