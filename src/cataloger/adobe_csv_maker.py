import base64
import csv
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, List, Dict

import httpx
import iptcinfo3
import piexif
from PIL import Image
from dotenv import load_dotenv

# Suppress verbose debug logs from iptcinfo3
logging.getLogger("iptcinfo").setLevel(logging.ERROR)

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
FINAL_IMAGES_DIR = BASE_DIR / "data" / "final" / "images"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CSV_FILE = PROCESSED_DIR / "adobe_stock_upload.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("Cataloger")

# Priority model list for microstock vision analysis
PREFERRED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

import re

def sanitize_filename(title: str, max_length: int = 60) -> str:
    """Creates a safe, SEO-friendly filename from the title."""
    name = re.sub(r'[^a-z0-9\s-]', '', title.lower())
    name = re.sub(r'[\s-]+', '-', name).strip('-')
    if len(name) > max_length:
        name = name[:max_length].rsplit('-', 1)[0]
        if not name:
            name = name[:max_length]
    return name

def embed_metadata(source_path: Path, target_path: Path, title: str, keywords: list[str]) -> Path:
    """Embed IPTC and EXIF metadata directly into the image file.
    
    If the image is a PNG, it will be automatically converted to high-quality JPEG and renamed.
    If it's already a JPG, it will just be renamed.
    """
    clean_kws = [k.strip() for k in keywords if k.strip()]
    keywords_str = ", ".join(clean_kws)

    # 1. Convert PNG to JPG or just rename if it's already JPG
    if source_path.suffix.lower() == ".png":
        try:
            with Image.open(source_path) as img:
                rgb_img = img.convert("RGB")
                rgb_img.save(target_path, "JPEG", quality=98)
            logger.info(f"Converted & Renamed {source_path.name} to {target_path.name}")
            source_path.unlink() # Excluir o PNG original para economizar espaço
        except Exception as e:
            logger.error(f"Failed to convert PNG to JPG for {source_path.name}: {e}")
            return source_path
    else:
        if source_path != target_path:
            try:
                source_path.rename(target_path)
                logger.info(f"Renamed {source_path.name} to {target_path.name}")
            except Exception as e:
                logger.error(f"Failed to rename {source_path.name} to {target_path.name}: {e}")
                target_path = source_path

    # 2. Embed IPTC metadata (Adobe Stock native indexing: 2:05 Title, 2:25 Keywords, 2:120 Caption)
    try:
        iptc = iptcinfo3.IPTCInfo(str(target_path), force=True)
        iptc["object name"] = title.encode("utf-8")
        iptc["caption/abstract"] = title.encode("utf-8")
        iptc["keywords"] = [k.encode("utf-8") for k in clean_kws]
        iptc.save()

        # Remove the backup file created by iptcinfo3 (filename.jpg~)
        backup_file = Path(str(target_path) + "~")
        if backup_file.exists():
            backup_file.unlink()
        logger.info(f"IPTC metadata embedded in {target_path.name}")
    except Exception as e:
        logger.warning(f"Could not write IPTC to {target_path.name}: {e}")

    # 3. Embed EXIF metadata (ImageDescription, XPTitle, XPKeywords)
    try:
        try:
            exif_dict = piexif.load(str(target_path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

        if "0th" not in exif_dict:
            exif_dict["0th"] = {}

        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = title.encode("utf-8")
        exif_dict["0th"][0x9C9B] = title.encode("utf-16le")  # XPTitle
        exif_dict["0th"][0x9C9E] = keywords_str.encode("utf-16le")  # XPKeywords

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(target_path))
        logger.info(f"EXIF metadata embedded in {target_path.name}")
    except Exception as e:
        logger.warning(f"Could not write EXIF to {target_path.name}: {e}")

    return target_path

def analyze_image(image_path: Path) -> dict:
    """Uses Gemini Vision (REST) to generate commercial title, 50 keywords, and category."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set in .env")

    logger.info(f"Analyzing {image_path.name} with Gemini Vision...")

    with open(image_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode("utf-8")

    mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    prompt = (
        "You are an expert Adobe Stock QA Reviewer and microstock SEO specialist.\n"
        "Analyze this AI-generated image. First, evaluate its quality based on these strict rules:\n"
        "1. No anatomical issues (no extra fingers, fused limbs, distorted faces or bodies).\n"
        "2. No illegible text, gibberish, watermarks, or recognizable brand logos.\n"
        "3. High commercial aesthetic value (good lighting, useful for advertising).\n"
        "If the image FAILS these rules, respond ONLY with JSON: {\"approved\": false, \"reason\": \"short explanation of what is wrong\"}.\n"
        "If it PASSES, provide:\n"
        "1. \"approved\": true\n"
        "2. \"title\": A highly commercial, descriptive Title in English (under 200 characters, no symbols).\n"
        "3. \"keywords\": Exactly 50 highly relevant Keywords in English, ordered by relevance.\n"
        "4. \"category\": The best Adobe Stock Category number (1=Animals, 2=Buildings, 3=Business, 4=Drinks, 5=Environment, "
        "6=States of Mind, 7=Food, 8=Graphic Resources, 9=Hobbies, 10=Industry, 11=Landscapes, 12=Lifestyle, "
        "13=People, 14=Plants, 15=Culture, 16=Science, 17=Social Issues, 18=Sports, 19=Technology, 20=Transport, 21=Travel).\n"
        "Respond ONLY in valid JSON."
    )

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": b64_img}},
                {"text": prompt}
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
                response = httpx.post(url, json=payload, timeout=45.0)
                if response.status_code == 200:
                    data = response.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    logger.info(f"Successfully analyzed {image_path.name} using {model_name}.")
                    return parsed
                elif response.status_code in [429, 503]:
                    logger.warning(f"{model_name} busy (Status {response.status_code}), attempt {attempt}/2. Retrying in 2s...")
                    time.sleep(2)
                else:
                    logger.warning(f"{model_name} returned status {response.status_code}: {response.text[:150]}")
                    break
            except Exception as e:
                logger.warning(f"Error connecting to {model_name}: {e}")
                time.sleep(1)

    logger.error(f"Failed to analyze {image_path.name} across all available models.")
    return {}

def run_cataloger(images_dir: Path | None = None) -> list[dict[str, Any]]:
    """Reads final images, extracts metadata with Gemini, embeds IPTC/EXIF, and exports to CSV."""
    target_dir = images_dir or FINAL_IMAGES_DIR

    if not target_dir.exists():
        logger.warning(f"Images directory not found: {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        return []

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Get all jpg/jpeg/png files
    image_files = [
        f for f in target_dir.iterdir()
        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ]

    if not image_files:
        logger.info(f"No images found to catalog in {target_dir}.")
        return []

    results = []

    # Read already processed filenames in CSV to prevent duplicate entries
    processed_filenames = set()
    if CSV_FILE.exists():
        try:
            with open(CSV_FILE, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "Filename" in row:
                        processed_filenames.add(row["Filename"])
        except Exception:
            pass

    for img_path in image_files:
        check_name = img_path.with_suffix(".jpg").name if img_path.suffix.lower() == ".png" else img_path.name
        if check_name in processed_filenames:
            logger.info(f"Skipping already cataloged file: {check_name}")
            continue

        metadata = analyze_image(img_path)
        if not metadata:
            continue

        if not metadata.get("approved", True):
            reason = metadata.get("reason", "Failed QA criteria.")
            logger.warning(f"❌ REJECTED {check_name}: {reason}")
            # Mover para a pasta de rejeitados
            rejected_dir = FINAL_IMAGES_DIR.parent / "rejected"
            rejected_dir.mkdir(parents=True, exist_ok=True)
            try:
                img_path.rename(rejected_dir / img_path.name)
            except Exception as e:
                logger.error(f"Could not move rejected file {img_path.name}: {e}")
            continue

        raw_keywords = metadata.get("keywords", [])
        if isinstance(raw_keywords, list):
            keywords_list = [str(k).strip() for k in raw_keywords if str(k).strip()]
            keywords_str = ", ".join(keywords_list)
        else:
            keywords_str = str(raw_keywords).strip()
            keywords_list = [k.strip() for k in keywords_str.split(",") if k.strip()]

        title = str(metadata.get("title", "")).strip()
        category = str(metadata.get("category", "3")).strip()

        # Build target filename for SEO
        base_new_name = sanitize_filename(title)
        if not base_new_name:
            base_new_name = "stock-image"
            
        target_path = img_path.with_name(f"{base_new_name}.jpg")
        counter = 1
        while target_path.exists() and target_path != img_path and target_path != img_path.with_suffix(".jpg"):
            target_path = img_path.with_name(f"{base_new_name}-{counter}.jpg")
            counter += 1

        # Injetar metadados diretamente no arquivo da imagem (IPTC + EXIF) e Renomear
        final_image_path = embed_metadata(img_path, target_path, title, keywords_list)

        results.append({
            "Filename": final_image_path.name,
            "Title": title,
            "Keywords": keywords_str,
            "Category": category,
            "Releases": ""
        })

    if not results:
        logger.info("No new items were cataloged.")
        return []

    # Write/Append to CSV
    csv_headers = ["Filename", "Title", "Keywords", "Category", "Releases"]
    file_exists = CSV_FILE.exists()

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

    logger.info(f"Successfully processed and appended {len(results)} items to {CSV_FILE}")
    return results

if __name__ == "__main__":
    run_cataloger()
