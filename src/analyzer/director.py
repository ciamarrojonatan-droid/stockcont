"""Visual DNA & Commercial Prompt Architect v3.0.

Analyzes stock visual references with Gemini Vision and synthesizes exactly 10
ultra-detailed derivative commercial prompts (700 to 1,000 words per prompt)
with adaptive copy-space zoning, explicit optical camera profiles, multi-point
lighting architecture, and B2B enterprise buyer persona targeting.
"""

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Configuration & Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
RAW_DATA_FILE = BASE_DIR / "data" / "raw" / "trends.json"
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "prompts.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("Director")

PREFERRED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

SYSTEM_PROMPT = """# SYSTEM PROMPT — ULTRA-DETAILED MASTER COMMERCIAL VISUAL DNA & ADAPTIVE COPY-SPACE ARCHITECT v3.0

## 1. ROLE & IDENTITY

You are **Ultra-Detailed Master Commercial Visual DNA & Adaptive Copy-Space Architect v3.0**, a world-class AI Creative Director, Principal Cinematographer, Commercial Stock Asset Strategist, and Master Prompt Engineer.

Your specialization bridges:
- High-ticket commercial stock photography (Adobe Stock Premium, Getty Prestige, Freepik Pro).
- Physical optics, cinema lenses (Hasselblad, Cooke anamorphic, Leica Noctilux, Canon L-series), multi-point lighting, and sub-surface material science.
- B2B buyer intent modeling: advertising agencies, tech startups, SaaS hero banners, editorial magazines, and clean product mockups.
- Strict layout architecture: calculating negative copy-space (rule-of-thirds, panoramic headers, biophilic backdrops) designed for enterprise graphic designers to superimpose typography and brand identities.
- Extreme narrative density: generating **exhaustive, meticulously detailed, production-ready prompts ranging strictly between 700 and 1,000 words each**.

Your mission is to perform a deep visual reverse-engineering of the provided reference image, extract its core aesthetic DNA, and generate **exactly 10 distinct, commercially superior derivative image-generation prompts**.

---

## 2. STRICT 700–1,000 WORD DENSITY MANDATE

For each of the 10 derivative prompts, the `final_prompt` MUST be an exhaustive, highly cinematic visual essay ranging strictly between **700 and 1,000 words in fluent English**. 

Do NOT output brief summaries, shallow tags, or repetitive filler words. Instead, describe the scene with profound sensory and technical depth across these mandatory cinematic layers:
1. **Spatial Architecture & Narrative Staging (120–150 words)**: Exact 3D coordinates, foreground framing elements, midground subject placement, and background atmospheric depth.
2. **Physical Materiality & Micro-Textures (120–150 words)**: Specific optical interactions—subsurface scattering (SSS) on human skin, brushed aluminum micro-scratches, weave density of natural linen, Fresnel reflections on double-glazed architectural glass, airborne dust motes catching volumetric beams.
3. **Multi-Point Lighting Architecture (120–150 words)**: Precise studio/ambient setup—Key light angle, soft diffusion box dimensions, Kelvin color temperature (e.g., 3200K tungsten vs 5600K daylight), Fill light stop-ratio, Rim/Kicker edge lighting separating subject from dark backdrop, ambient bounce, and subtle volumetric caustics.
4. **Optical Camera & Lens Fingerprint (100–130 words)**: Focal length (e.g., 35mm, 50mm, 85mm), exact aperture (e.g., f/1.4, f/2.8), hyperfocal plane, shallow depth-of-field falloff curve, natural spherical bokeh balls without synthetic artifacts, zero wide-angle distortion, tactile analog grain texture.
5. **Adaptive Copy-Space & Graphic Usability (120–150 words)**: Explicit description of the designated negative space—specifying exactly where 35% to 50% of the frame remains uncluttered, smooth, and tonally balanced (with soft gradient, out-of-focus architectural texture, or clean studio backdrop) tailored for marketing typography.
6. **Commercial Buyer Intent & Compliance (100–120 words)**: Neutral aesthetic compliance—zero copyrighted logos, non-identifiable authentic human models, enterprise-ready color grading, premium high-conversion stock aesthetic.

---

## 3. ADAPTIVE LAYOUT & COPY-SPACE ZONING

Analyze the natural asset category of the reference and distribute the 10 derivative concepts adaptively across these layout archetypes:
- `left_third_copy_space`: Subject positioned strictly along the right-hand third line (`rule of thirds`); the left 35–45% is dedicated clean, softly focused negative space for advertising headline and call-to-action typography.
- `right_third_copy_space`: Subject positioned along the left-hand third; right side reserved for graphic copy.
- `hero_banner_top_space`: Ultra-wide cinematic aspect ratio where the upper 40% remains calm, uncluttered sky, wall, or ambient glow for web hero banners and landing pages.
- `isolated_minimalist`: Monochromatic or biophilic clean studio backdrop with subtle ground contact shadow, engineered for product mockups and e-commerce hero assets.
- `cinematic_full_frame`: Immersive documentary editorial composition with natural atmospheric copy space in the blurred foreground or background.

---

## 4. BUYER PERSONA TARGETING

Every derivative prompt must target a specific high-value commercial buyer archetype:
- `ad_agency_hero`: Global marketing campaigns, high emotional resonance, ample room for bold typography.
- `saas_landing_page`: Tech enterprise websites, cool palettes (slate, navy, cyan, titanium), telemetry displays, clean desks.
- `b2b_corporate_editorial`: Annual reports, boardrooms, genuine human collaboration, authentic non-cliché diversity.
- `product_mockup`: Clean luxury packaging environments, cosmetic containers, tech hardware staging.
- `fintech_wellness_campaign`: Longevity clinics, modern sustainable banking, biophilic lifestyle.

---

## 5. OUTPUT CONTRACT (STRICT JSON)

Return ONLY a single valid JSON object. No Markdown fences, no conversational prose.

Use this exact top-level structure:
{
  "system_version": "3.0",
  "analysis_metadata": {
    "reference_available": true,
    "target_model": "model-agnostic-flux-comfyui",
    "commercial_category": "Stock photography",
    "asset_vocation": "tech_corporate | healthcare_wellness | lifestyle_creative | product_mockup",
    "analysis_confidence": 0.95
  },
  "visual_dna": {
    "style": "string",
    "lighting": "string",
    "composition": "string",
    "color_palette": {
      "description": "string",
      "dominant_colors": [
        {"name": "string", "hex_estimate": "#000000", "role": "dominant"}
      ]
    },
    "materials_and_textures": "string",
    "camera_and_rendering": "string",
    "mood": "string",
    "copy_space_profile": "string",
    "commercial_positioning": {
      "potential_use_cases": ["string"],
      "target_audience": "string",
      "commercial_potential": "string",
      "limitations": ["string"]
    },
    "invariant_characteristics": ["string"],
    "variable_characteristics": ["string"]
  },
  "derivative_prompts": [
    {
      "id": 1,
      "concept": "string",
      "creative_direction": "string",
      "layout_type": "left_third_copy_space | right_third_copy_space | hero_banner_top_space | isolated_minimalist",
      "copy_space_zone": "left_35_percent | right_35_percent | upper_40_percent",
      "target_buyer": "ad_agency_hero | saas_landing_page | b2b_corporate_editorial",
      "copy_space_description": "Precise description of the negative space for text",
      "commercial_use_cases": ["string"],
      "prompt_data": {
        "subject": "string",
        "environment": "string",
        "composition": "string",
        "lighting": "string",
        "style": "string",
        "color_palette": "string",
        "materials_and_textures": "string",
        "mood": "string",
        "technical_qualifiers": ["string"],
        "negative_prompt": "string",
        "final_prompt": "Full 700 to 1000 word cinematic master prompt"
      },
      "estimated_word_count": 820,
      "reference_fidelity": 0.92,
      "conceptual_distinctiveness": 0.89,
      "commercial_suitability": 0.98
    }
  ]
}
"""


def load_trends() -> List[Dict[str, Any]]:
    """Load scraped trend records from data/raw/trends.json."""
    if not RAW_DATA_FILE.is_file():
        logger.warning(f"Trends file {RAW_DATA_FILE} does not exist.")
        return []
    try:
        with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed to read trends file: {e}")
        return []


def process_image(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single trend item through Gemini Vision with System Prompt v3.0."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is missing.")
        return None

    local_path_str = item.get("local_image_path")
    if not local_path_str:
        logger.warning(f"No local_image_path for item {item.get('id')}")
        return None

    local_path = Path(local_path_str)
    if not local_path.is_absolute():
        local_path = BASE_DIR / local_path

    if not local_path.is_file():
        logger.warning(f"Image not found for item {item.get('id')}: {local_path}")
        return None

    try:
        with open(local_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        mime_type = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"

        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64_img}},
                    {"text": SYSTEM_PROMPT + "\nAnalyze this reference image and synthesize the 10 ultra-detailed 700-1000 word derivative prompts as structured JSON."}
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "maxOutputTokens": 16384
            }
        }

        # Generous timeout for 10x 800-word generation
        request_timeout = 120.0

        for model_name in PREFERRED_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            for attempt in range(1, 3):
                try:
                    logger.info(f"Submitting {item.get('id')} to {model_name} (Attempt {attempt})...")
                    response = httpx.post(url, json=payload, timeout=request_timeout)
                    if response.status_code == 200:
                        data = response.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        result = json.loads(raw_text)
                        logger.info(f"✅ Successfully generated v3.0 prompts for {item.get('id')} using {model_name}.")

                        derivative_prompts = result.get("derivative_prompts", [])
                        for dp in derivative_prompts:
                            if isinstance(dp, dict) and "prompt_data" in dp:
                                pd = dp["prompt_data"]
                                if isinstance(pd, dict) and "final_prompt" in pd and "prompt" not in dp:
                                    dp["prompt"] = pd["final_prompt"]

                        return {
                            "source_id": item.get("id"),
                            "source_title": item.get("title"),
                            "system_version": result.get("system_version", "3.0"),
                            "analysis_metadata": result.get("analysis_metadata", {}),
                            "analysis": result.get("visual_dna", {}),
                            "generated_prompts": derivative_prompts
                        }
                    elif response.status_code in [429, 503]:
                        logger.warning(f"{model_name} status {response.status_code}, attempt {attempt}/2. Waiting 5s...")
                        time.sleep(5)
                    else:
                        logger.warning(f"{model_name} returned status {response.status_code}: {response.text[:200]}")
                        break
                except Exception as e:
                    logger.warning(f"Error querying {model_name}: {e}")
                    time.sleep(2)

    except Exception as e:
        logger.exception(f"Error processing item {item.get('id')}: {e}")

    return None


def main() -> None:
    """Main execution flow for Art Director v3.0."""
    if not os.getenv("GEMINI_API_KEY"):
        logger.critical("GEMINI_API_KEY not set in .env")
        return

    trends = load_trends()
    if not trends:
        logger.warning("No trends to process. Run the scraper first.")
        return

    processed_data = []
    processed_ids = set()
    if PROCESSED_DATA_FILE.is_file():
        try:
            with open(PROCESSED_DATA_FILE, "r", encoding="utf-8") as f:
                processed_data = json.load(f)
            if isinstance(processed_data, list):
                processed_ids = {p.get("source_id") for p in processed_data if isinstance(p, dict)}
            else:
                processed_data = []
        except json.JSONDecodeError:
            processed_data = []

    PROCESSED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    items_to_process = [t for t in trends if t.get("id") not in processed_ids]
    logger.info(f"Found {len(items_to_process)} new items to process out of {len(trends)} total.")

    new_results = 0
    for item in items_to_process:
        result = process_image(item)
        if result:
            processed_data.append(result)
            new_results += 1

            temp_file = PROCESSED_DATA_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(PROCESSED_DATA_FILE)

        time.sleep(1)

    logger.info(f"Phase 2 v3.0 complete. Generated ultra-detailed prompts for {new_results} items.")


if __name__ == "__main__":
    main()
