import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai
from PIL import Image

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DATA_FILE = BASE_DIR / "data" / "raw" / "trends.json"
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "prompts.json"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Art Director for a microstock agency.
Analyze the provided top-selling image and extract its visual DNA (style, lighting, composition, color palette).
Then, generate 5 derivative prompts optimized for AI image generation (e.g., Midjourney/ComfyUI) that share this DNA but offer unique, highly commercial concepts.

Return ONLY a valid JSON object with this exact structure (no markdown backticks around it, just the raw JSON):
{
  "visual_dna": {
    "style": "string",
    "lighting": "string",
    "composition": "string",
    "color_palette": "string"
  },
  "derivative_prompts": [
    {
      "concept": "string (short description)",
      "prompt": "string (the actual generation prompt)"
    }
  ]
}
"""

def setup_gemini() -> genai.GenerativeModel:
    """Initialize the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it before running.")
    
    genai.configure(api_key=api_key)
    
    # Use the latest available gemini-3.8-flash model
    model = genai.GenerativeModel(
        model_name="gemini-3.8-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"}
    )
    return model

def load_trends() -> list[dict[str, Any]]:
    """Load the scraped trends."""
    if not RAW_DATA_FILE.exists():
        logger.error(f"Trends file not found at {RAW_DATA_FILE}")
        return []
        
    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def process_image(model: genai.GenerativeModel, item: dict[str, Any]) -> dict[str, Any] | None:
    """Send an image to Gemini and return the structured analysis."""
    local_path = (BASE_DIR / item.get("local_path", "")).resolve()
    
    if not local_path.is_relative_to(BASE_DIR):
        logger.warning(f"Invalid path detected for item {item.get('id')}")
        return None
        
    if not local_path.is_file():
        logger.warning(f"Image not found for item {item.get('id')}: {local_path}")
        return None

    try:
        # Open image using Pillow
        img = Image.open(local_path)
        
        # Call Gemini API
        logger.info(f"Analyzing image for item {item.get('id')}...")
        response = model.generate_content(
            [img, "Analyze this image and generate the JSON output as requested."]
        )
        
        # Parse JSON response
        result = json.loads(response.text)
        
        # Combine original metadata with new analysis
        return {
            "source_id": item.get("id"),
            "source_title": item.get("title"),
            "analysis": result.get("visual_dna", {}),
            "generated_prompts": result.get("derivative_prompts", [])
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini for {item.get('id')}: {e}")
        logger.debug(f"Raw response: {response.text}")
    except Exception as e:
        logger.exception(f"Error processing item {item.get('id')}: {e}")
        
    return None

def main() -> None:
    """Main execution flow for the Art Director phase."""
    try:
        model = setup_gemini()
    except ValueError as e:
        logger.critical(e)
        return

    trends = load_trends()
    if not trends:
        logger.warning("No trends to process. Run the scraper first.")
        return

    # Load existing processed data to avoid reprocessing
    processed_data = []
    processed_ids = set()
    if PROCESSED_DATA_FILE.is_file():
        try:
            with open(PROCESSED_DATA_FILE, "r", encoding="utf-8") as f:
                processed_data = json.load(f)
                
            if isinstance(processed_data, list):
                processed_ids = {p.get("source_id") for p in processed_data if isinstance(p, dict)}
            else:
                logger.warning("Processed data file does not contain a list. Starting fresh.")
                processed_data = []
        except json.JSONDecodeError:
            logger.warning("Corrupt processed data file, starting fresh.")
            processed_data = []

    PROCESSED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    new_results = 0
    # Process only items that haven't been processed yet
    items_to_process = [t for t in trends if t.get("id") not in processed_ids]
    
    logger.info(f"Found {len(items_to_process)} new items to process out of {len(trends)} total.")

    for item in items_to_process:
        result = process_image(model, item)
        if result:
            processed_data.append(result)
            new_results += 1
            
            # Save incrementally in case of crash/rate limits (safe atomic write)
            temp_file = PROCESSED_DATA_FILE.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(PROCESSED_DATA_FILE)
                
        # Rate limit protection (Gemini has limits on requests per minute)
        time.sleep(3)

    logger.info(f"Phase 2 complete. Generated prompts for {new_results} new items.")

if __name__ == "__main__":
    main()
