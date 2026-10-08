import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from dotenv import load_dotenv

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
RAW_DATA_FILE = BASE_DIR / "data" / "raw" / "trends.json"
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "prompts.json"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("Director")

PREFERRED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

SYSTEM_PROMPT = """You are an expert Art Director for a microstock agency.
Analyze the provided top-selling image and extract its visual DNA (style, lighting, composition, color palette).
Then, generate 5 derivative prompts optimized for AI image generation (e.g., Midjourney/ComfyUI) that share this DNA but offer unique, highly commercial concepts.

Return ONLY a valid JSON object with this exact structure:
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

def load_trends() -> list[dict[str, Any]]:
    """Load the scraped trends."""
    if not RAW_DATA_FILE.exists():
        logger.error(f"Trends file not found at {RAW_DATA_FILE}")
        return []

    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def process_image(item: dict[str, Any]) -> dict[str, Any] | None:
    """Send an image to Gemini and return the structured analysis."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set in .env")

    local_path = (BASE_DIR / item.get("local_path", "")).resolve()

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
                    {"text": SYSTEM_PROMPT + "\nAnalyze this image and return the structured JSON."}
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        }

        for model_name in PREFERRED_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            for attempt in range(1, 3):
                try:
                    response = httpx.post(url, json=payload, timeout=40.0)
                    if response.status_code == 200:
                        data = response.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        result = json.loads(raw_text)
                        logger.info(f"Successfully generated prompts for {item.get('id')} using {model_name}.")
                        return {
                            "source_id": item.get("id"),
                            "source_title": item.get("title"),
                            "analysis": result.get("visual_dna", {}),
                            "generated_prompts": result.get("derivative_prompts", [])
                        }
                    elif response.status_code in [429, 503]:
                        logger.warning(f"{model_name} status {response.status_code}, attempt {attempt}/2. Waiting 2s...")
                        time.sleep(2)
                    else:
                        break
                except Exception as e:
                    logger.warning(f"Error querying {model_name}: {e}")
                    time.sleep(1)

    except Exception as e:
        logger.exception(f"Error processing item {item.get('id')}: {e}")

    return None

def main() -> None:
    """Main execution flow for the Art Director phase."""
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

    logger.info(f"Phase 2 complete. Generated prompts for {new_results} new items.")

if __name__ == "__main__":
    main()
