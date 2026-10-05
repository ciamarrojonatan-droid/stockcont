import os
import json
import csv
import logging
from pathlib import Path
from typing import List, Dict
import google.genai as genai
from google.genai import types

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FINAL_IMAGES_DIR = BASE_DIR / "data" / "final" / "images"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CSV_FILE = PROCESSED_DIR / "adobe_stock_upload.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def setup_gemini():
    """Initialize the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)

def analyze_image(client: genai.Client, image_path: Path) -> dict:
    """Uses Gemini 1.5 Flash to generate a commercial title and 50 keywords."""
    logger.info(f"Analyzing {image_path.name}...")
    
    prompt = (
        "You are an expert Adobe Stock contributor and SEO specialist. "
        "Analyze this image and provide:\n"
        "1. A highly commercial, descriptive Title in English (up to 200 characters, no special symbols).\n"
        "2. Exactly 50 highly relevant Keywords in English, separated by commas, ordered from most relevant to least relevant.\n"
        "Respond ONLY in valid JSON format with keys 'title' and 'keywords'."
    )

    try:
        # Upload the file using the modern GenAI SDK
        uploaded_file = client.files.upload(file=str(image_path))
        
        # We enforce JSON output schema for 100% reliability
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING"},
                        "keywords": {"type": "STRING"}
                    },
                    "required": ["title", "keywords"]
                },
                temperature=0.7
            )
        )
        
        data = json.loads(response.text)
        return data

    except Exception as e:
        logger.error(f"Error analyzing {image_path.name}: {e}")
        return {}

def run_cataloger():
    """Reads final images, gets metadata from Gemini, and exports to CSV."""
    if not FINAL_IMAGES_DIR.exists():
        logger.warning(f"Images directory not found: {FINAL_IMAGES_DIR}")
        return
        
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get all jpg/png files
    image_files = list(FINAL_IMAGES_DIR.glob("*.jpg")) + list(FINAL_IMAGES_DIR.glob("*.png"))
    if not image_files:
        logger.info("No images found to catalog.")
        return

    client = setup_gemini()
    results = []
    
    for img_path in image_files:
        metadata = analyze_image(client, img_path)
        if metadata:
            results.append({
                "Filename": img_path.name,
                "Title": metadata.get("title", ""),
                "Keywords": metadata.get("keywords", ""),
                "Category": "1", # Default Adobe Stock category (e.g., 1 = Animals, 22 = Technology. Change as needed)
                "Releases": "" # Model/Property release file names if any
            })
            
    if not results:
        logger.error("No metadata generated.")
        return
        
    # Write to CSV
    csv_headers = ["Filename", "Title", "Keywords", "Category", "Releases"]
    file_exists = CSV_FILE.exists()
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)
        
    logger.info(f"Successfully appended {len(results)} items to {CSV_FILE}")

if __name__ == "__main__":
    run_cataloger()
