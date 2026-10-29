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

PREFERRED_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

SYSTEM_PROMPT = """# SYSTEM PROMPT — ULTRA-DETAILED MASTER COMMERCIAL VISUAL DNA & ADAPTIVE COPY-SPACE ARCHITECT v3.0

## 1. ROLE & IDENTITY

You are **Ultra-Detailed Master Commercial Visual DNA & Adaptive Copy-Space Architect v3.0**, a world-class AI Creative Director, Principal Cinematographer, Commercial Stock Asset Strategist, and Master Prompt Engineer.

Your specialization bridges:
- High-ticket commercial stock photography (Adobe Stock Premium, Getty Prestige, Freepik Pro).
- Physical optics, cinema lenses (Hasselblad, Cooke anamorphic, Leica Noctilux, Canon L-series), multi-point lighting, and sub-surface material science.
- B2B buyer intent modeling: advertising agencies, tech startups, SaaS hero banners, editorial magazines, and clean product mockups.
- Strict layout architecture: calculating negative copy-space (rule-of-thirds, panoramic headers, biophilic backdrops) designed for enterprise graphic designers to superimpose typography and brand identities.
- Extreme narrative density: generating **exhaustive, meticulously detailed, production-ready prompts ranging strictly between 700 and 1,000 words each**.

Your mission is to perform a deep visual reverse-engineering of the provided reference image, extract its core aesthetic DNA, and generate **exactly 10 distinct, commercially superior derivative image-generation prompts** (id 1 through 10).

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
You MUST output all 10 derivative prompt items (with id 1 to 10) in the `derivative_prompts` array.

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

    item_id = str(item.get("id") or "").strip()

    # Look for local image path across possible keys (local_path is the standard schema)
    local_path_str = item.get("local_path") or item.get("local_image_path") or item.get("image_path")
    local_path: Optional[Path] = None

    if local_path_str:
        candidate_path = Path(local_path_str)
        if not candidate_path.is_absolute():
            candidate_path = BASE_DIR / candidate_path
        if candidate_path.is_file():
            local_path = candidate_path

    # Fallback to standard convention data/raw/images/{item_id}.ext if path not found
    if local_path is None and item_id:
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            candidate = BASE_DIR / "data" / "raw" / "images" / f"{item_id}{ext}"
            if candidate.is_file():
                local_path = candidate
                break

    # Fallback: attempt to download if URL is present in the record
    if local_path is None and item_id:
        img_url = item.get("original_url") or item.get("thumbnail_url")
        if img_url:
            try:
                logger.info(f"Downloading reference image for item {item_id} from {img_url}...")
                candidate_dir = BASE_DIR / "data" / "raw" / "images"
                candidate_dir.mkdir(parents=True, exist_ok=True)
                candidate = candidate_dir / f"{item_id}.jpg"
                resp = httpx.get(img_url, timeout=15.0)
                if resp.status_code == 200:
                    with open(candidate, "wb") as f:
                        f.write(resp.content)
                    local_path = candidate
                    logger.info(f"Successfully downloaded reference image for item {item_id}")
            except Exception as dl_err:
                logger.warning(f"Failed to auto-download image for item {item_id}: {dl_err}")

    is_textual_fallback = False
    b64_img = ""
    mime_type = "image/jpeg"

    if local_path and local_path.is_file():
        try:
            with open(local_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            mime_type = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"
        except Exception as read_err:
            logger.warning(f"Failed reading image for {item_id}: {read_err}. Activating graceful textual synthesis fallback.")
            is_textual_fallback = True
    else:
        logger.warning(f"Image not found on disk for item {item.get('id')}. Activating graceful textual synthesis fallback.")
        is_textual_fallback = True

    try:
        if not is_textual_fallback and b64_img:
            prompt_instruction = (
                SYSTEM_PROMPT
                + "\n\nCRITICAL MANDATE: Analyze this reference image and synthesize exactly 10 distinct derivative prompts "
                + "numbered 1 through 10 in the 'derivative_prompts' array. Each prompt MUST follow the 700-1000 word density mandate."
            )
            contents_parts = [
                {"inline_data": {"mime_type": mime_type, "data": b64_img}},
                {"text": prompt_instruction}
            ]
        else:
            is_textual_fallback = True
            keywords_val = item.get("keywords")
            if isinstance(keywords_val, list):
                kw_str = ", ".join(keywords_val)
            else:
                kw_str = str(keywords_val or "N/A")

            meta_context = (
                f"Title: {item.get('title', 'Unknown Concept')}\n"
                f"Content Type: {item.get('content_type', 'photo')}\n"
                f"Contributor: {item.get('contributor_name', 'Top Contributor')}\n"
                f"Keywords: {kw_str}\n"
                f"Source Niche: {item.get('source', 'Commercial Microstock')}"
            )
            prompt_instruction = (
                SYSTEM_PROMPT
                + f"\n\nCRITICAL CONTEXT: Physical reference image is temporarily unavailable. Based on the following top-selling stock metadata:\n{meta_context}\n\n"
                + "Perform a conceptual reverse-engineering of the aesthetic DNA and synthesize exactly 10 distinct derivative prompts "
                + "numbered 1 through 10 in the 'derivative_prompts' array. Each prompt MUST strictly follow the 700-1000 word density mandate. "
                + "In 'analysis_metadata', ensure 'reference_available' is set to false."
            )
            contents_parts = [
                {"text": prompt_instruction}
            ]

        payload = {
            "contents": [{
                "parts": contents_parts
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
            for attempt in range(1, 3):
                try:
                    logger.info(f"Submitting {item.get('id')} to {model_name} (Attempt {attempt})...")
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    response = httpx.post(url, json=payload, timeout=request_timeout)
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            logger.warning(f"No candidates returned by {model_name} for {item.get('id')}")
                            continue

                        parts = candidates[0].get("content", {}).get("parts", [])
                        raw_text = ""
                        for part in parts:
                            if "text" in part:
                                if not part.get("thought", False):
                                    raw_text = part["text"]
                                    break
                        if not raw_text and parts and "text" in parts[0]:
                            raw_text = parts[0]["text"]

                        clean_json = raw_text.strip()
                        if clean_json.startswith("```json"):
                            clean_json = clean_json[7:]
                        elif clean_json.startswith("```"):
                            clean_json = clean_json[3:]
                        if clean_json.endswith("```"):
                            clean_json = clean_json[:-3]
                        clean_json = clean_json.strip()

                        result = json.loads(clean_json)
                        logger.info(f"✅ Successfully generated v3.0 prompts for {item.get('id')} using {model_name}.")

                        derivative_prompts = result.get("derivative_prompts") or result.get("generated_prompts", [])
                        for dp in derivative_prompts:
                            if isinstance(dp, dict):
                                if "status" not in dp:
                                    dp["status"] = "pending"
                                if "prompt_data" in dp:
                                    pd = dp["prompt_data"]
                                    if isinstance(pd, dict) and "final_prompt" in pd and "prompt" not in dp:
                                        dp["prompt"] = pd["final_prompt"]

                        analysis_metadata = result.get("analysis_metadata", {})
                        if is_textual_fallback:
                            analysis_metadata["reference_available"] = False

                        return {
                            "source_id": str(item.get("id")),
                            "source_title": item.get("title"),
                            "system_version": result.get("system_version", "3.0"),
                            "analysis_metadata": analysis_metadata,
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


def main(max_items: Optional[int] = None) -> None:
    """Main execution flow for Art Director v3.0."""
    if not os.getenv("GEMINI_API_KEY"):
        logger.critical("GEMINI_API_KEY not set in .env")
        return

    # Pre-flight automatic hydration of raw reference images
    try:
        from src.scraper.hydrator import hydrate_raw_references
        logger.info("Executing pre-flight hydration check for raw reference images...")
        hydrate_raw_references()
    except Exception as h_err:
        logger.warning(f"Pre-flight hydration warning: {h_err}")

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
                processed_ids = {str(p.get("source_id")) for p in processed_data if isinstance(p, dict) and p.get("source_id")}
            else:
                processed_data = []
        except json.JSONDecodeError:
            processed_data = []

    PROCESSED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    items_to_process = [t for t in trends if str(t.get("id")) not in processed_ids]
    if max_items is not None and max_items > 0:
        items_to_process = items_to_process[:max_items]

    logger.info(f"Found {len(items_to_process)} new items to process out of {len(trends)} total.")

    new_results = 0
    for item in items_to_process:
        result = process_image(item)
        if result:
            processed_data.append(result)
            new_results += 1

            temp_file = PROCESSED_DATA_FILE.parent / f"{PROCESSED_DATA_FILE.name}.tmp.{os.getpid()}"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(PROCESSED_DATA_FILE)

        time.sleep(1)

    logger.info(f"Phase 2 v3.0 complete. Generated ultra-detailed prompts for {new_results} items.")


if __name__ == "__main__":
    main()
