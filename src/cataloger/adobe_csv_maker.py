import base64
import csv
import io
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

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
PREFERRED_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

DANGLING_WORDS = {'a', 'an', 'the', 'on', 'in', 'of', 'to', 'for', 'with', 'at', 'by', 'from', 'and', 'or', 'is', 'as'}
MANDATORY_AI_KEYWORDS = ["ai generated", "generative ai", "digital art", "illustration"]


def sanitize_filename(title: str, max_length: int = 75) -> str:
    """Creates a safe, SEO-friendly filename from the title without dangling prepositions or AI prefixes."""
    clean_title = re.sub(
        r'^(generative\s+ai|ai\s+generated)(\s+(illustration|image|photo|art))?(\s+of)?\s*[:.-]?\s*',
        '',
        title,
        flags=re.IGNORECASE,
    )
    name = re.sub(r'[^a-z0-9\s-]', '', clean_title.lower())
    name = re.sub(r'[\s-]+', '-', name).strip('-')
    if len(name) > max_length:
        name = name[:max_length].rsplit('-', 1)[0]

    parts = name.split('-')
    # Strip leading articles (e.g. avoiding a-futuristic-robot -> futuristic-robot)
    while parts and parts[0] in {'a', 'an', 'the'}:
        parts.pop(0)
    # Strip dangling trailing prepositions/stopwords (e.g. avoiding -on-a)
    while parts and parts[-1] in DANGLING_WORDS:
        parts.pop()
    name = '-'.join(parts)
    return name or "stock-image"


def normalize_keywords(keywords: list[str], max_keywords: int = 50) -> tuple[list[str], str]:
    """Ensures mandatory AI tags are present, deduplicates, and caps strictly at max_keywords (agency limit)."""
    clean_kws: list[str] = []
    seen = set()
    for k in keywords:
        k_clean = k.strip()
        if k_clean and k_clean.lower() not in seen:
            seen.add(k_clean.lower())
            clean_kws.append(k_clean)

    # Append missing mandatory keywords
    for mkw in MANDATORY_AI_KEYWORDS:
        if mkw not in seen:
            clean_kws.append(mkw)
            seen.add(mkw)

    # Enforce strict agency ceiling (default 50) without discarding mandatory tags
    if len(clean_kws) > max_keywords:
        mandatory_set = set(MANDATORY_AI_KEYWORDS)
        preserved_mandatory = [k for k in clean_kws if k.lower() in mandatory_set]
        other_kws = [k for k in clean_kws if k.lower() not in mandatory_set]
        clean_kws = other_kws[: max_keywords - len(preserved_mandatory)] + preserved_mandatory

    return clean_kws, ", ".join(clean_kws)


def format_description(title: str, description: str | None = None) -> str:
    """Formats a clean, non-duplicated commercial description with mandatory AI disclosure."""
    desc_raw = (description or title).strip()
    desc_body = re.sub(
        r'^(generative\s+ai|ai\s+generated)(\s+(illustration|image|photo|art))?(\s+of)?\s*[:.-]?\s*',
        '',
        desc_raw,
        flags=re.IGNORECASE,
    ).strip()

    if not desc_body:
        desc_body = title.strip()

    # Capitalize the first letter of desc_body for clean sentence case
    if desc_body:
        desc_body = desc_body[0].upper() + desc_body[1:]

    return f"Generative AI illustration. {desc_body.rstrip('.')}."


def embed_metadata(
    source_path: Path,
    target_path: Path,
    title: str,
    keywords: list[str],
    description: str | None = None,
) -> Path:
    """Embed IPTC and EXIF metadata directly into the image file.
    
    If the image is a PNG, it will be automatically converted to high-quality JPEG and renamed.
    If it's already a JPG, it will just be renamed.
    """
    clean_kws, keywords_str = normalize_keywords(keywords, max_keywords=50)
    formatted_description = format_description(title, description)

    # 1. Convert PNG to JPG or just rename if it's already JPG
    if source_path.suffix.lower() == ".png":
        try:
            with Image.open(source_path) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    rgb_img = bg
                else:
                    rgb_img = img.convert("RGB")

                icc = img.info.get("icc_profile")
                if icc:
                    rgb_img.save(target_path, "JPEG", quality=98, dpi=(300, 300), icc_profile=icc)
                else:
                    rgb_img.save(target_path, "JPEG", quality=98, dpi=(300, 300))
            logger.info(f"Converted & Renamed {source_path.name} to {target_path.name}")
            source_path.unlink()  # Excluir o PNG original para economizar espaço
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

    # 2. Embed IPTC metadata (2:05 ObjectName/Title, 2:25 Keywords, 2:120 Caption/Description)
    try:
        iptc = iptcinfo3.IPTCInfo(str(target_path), force=True)
        # IPTC ObjectName (2:05) legacy spec standard limit is 64 octets (bytes)
        iptc_title = title.strip()
        if len(iptc_title.encode("utf-8")) > 64:
            short = iptc_title[:64]
            if " " in short:
                short = short.rsplit(" ", 1)[0]
            encoded_title = short.encode("utf-8")[:64].decode("utf-8", "ignore").encode("utf-8")
        else:
            encoded_title = iptc_title.encode("utf-8")

        iptc["object name"] = encoded_title
        iptc["caption/abstract"] = formatted_description.encode("utf-8")
        iptc["keywords"] = [k.encode("utf-8") for k in clean_kws]
        iptc.save()

        # Remove the backup file created by iptcinfo3 (filename.jpg~)
        backup_file = Path(str(target_path) + "~")
        if backup_file.exists():
            backup_file.unlink()
        logger.info(f"IPTC metadata embedded in {target_path.name}")
    except Exception as e:
        logger.warning(f"Could not write IPTC to {target_path.name}: {e}")

    # 3. Embed EXIF metadata (ImageDescription, XPTitle, XPComment, XPKeywords)
    try:
        try:
            exif_dict = piexif.load(str(target_path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

        if "0th" not in exif_dict:
            exif_dict["0th"] = {}

        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = formatted_description.encode("utf-8")
        # Commercial 300 DPI Resolution Tags
        exif_dict["0th"][piexif.ImageIFD.XResolution] = (300, 1)
        exif_dict["0th"][piexif.ImageIFD.YResolution] = (300, 1)
        exif_dict["0th"][piexif.ImageIFD.ResolutionUnit] = 2  # 2 = Inches (DPI)
        # Windows EXIF XP Tags require null-terminated UTF-16LE byte strings
        exif_dict["0th"][0x9C9B] = f"{title}\0".encode("utf-16le")  # XPTitle
        exif_dict["0th"][0x9C9C] = f"{formatted_description}\0".encode("utf-16le")  # XPComment
        exif_dict["0th"][0x9C9E] = f"{keywords_str}\0".encode("utf-16le")  # XPKeywords

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(target_path))
        logger.info(f"EXIF metadata embedded in {target_path.name}")
    except Exception as e:
        logger.warning(f"Could not write EXIF to {target_path.name}: {e}")

    # 4. Enforce 300 DPI across both JFIF APP0 and EXIF IFD0 headers
    try:
        from src.cataloger.platform_compliance import ensure_image_dpi
        ensure_image_dpi(target_path, target_dpi=300)
    except Exception as e:
        logger.warning(f"Could not enforce 300 DPI on {target_path.name}: {e}")

    return target_path


def analyze_image(image_path: Path) -> dict:
    """Uses Gemini Vision (REST) to generate commercial title, description, 50 keywords, and category."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set in .env")

    logger.info(f"Analyzing {image_path.name} with Gemini Vision...")

    # Downsample image for vision analysis (microstock SEO requires at most 1024px)
    # Reduces payload from ~15-20MB down to ~50-80KB, preventing 503 high demand & timeouts
    try:
        with Image.open(image_path) as im:
            im_copy = im.copy()
            im_copy.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            if im_copy.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im_copy.size, (255, 255, 255))
                if im_copy.mode == "P":
                    im_copy = im_copy.convert("RGBA")
                bg.paste(im_copy, mask=im_copy.split()[-1] if im_copy.mode == "RGBA" else None)
                im_copy = bg
            elif im_copy.mode != "RGB":
                im_copy = im_copy.convert("RGB")

            buf = io.BytesIO()
            im_copy.save(buf, format="JPEG", quality=80)
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
            mime_type = "image/jpeg"
    except Exception as img_err:
        logger.warning(f"Could not downsample {image_path.name}, using raw file: {img_err}")
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
        mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    prompt = """You are an expert microstock reviewer and SEO specialist (Adobe Stock, Dreamstime, Freepik, Shutterstock).
Analyze this AI-generated image. First, evaluate its quality based on these strict rules:
1. No anatomical issues (no extra fingers, fused limbs, distorted faces or bodies).
2. No illegible text, gibberish, watermarks, or recognizable brand logos).
3. High commercial aesthetic value (good lighting, useful for advertising).
If the image FAILS these rules, respond ONLY with JSON: {"approved": false, "reason": "short explanation of what is wrong"}.
If it PASSES, provide:
1. "approved": true
2. "title": A concise, natural commercial Title in English (5 to 12 words, 40 to 80 characters, no symbols, complete phrase without trailing prepositions).
3. "description": A detailed commercial Description in English (1 to 2 complete sentences) MUST explicitly begin with 'Generative AI illustration. ' followed by a vivid description of the scene, subjects, setting, lighting, and mood (required by Dreamstime and microstock AI policies).
4. "keywords": Exactly 50 highly relevant Keywords in English, ordered by relevance. MUST include standard microstock AI tags such as: 'ai generated', 'generative ai', 'digital art', 'concept art', 'illustration'.
5. "category": The best Adobe Stock Category number (1=Animals, 2=Buildings, 3=Business, 4=Drinks, 5=Environment, 6=States of Mind, 7=Food, 8=Graphic Resources, 9=Hobbies, 10=Industry, 11=Landscapes, 12=Lifestyle, 13=People, 14=Plants, 15=Culture, 16=Science, 17=Social Issues, 18=Sports, 19=Technology, 20=Transport, 21=Travel).
Respond ONLY in valid JSON."""

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
                response = httpx.post(url, json=payload, timeout=60.0)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        logger.warning(f"No candidates returned by {model_name} for {image_path.name}")
                        break

                    parts = candidates[0].get("content", {}).get("parts", [])
                    raw_text = ""
                    for part in parts:
                        if "text" in part and not part.get("thought", False):
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

                    parsed = json.loads(clean_json)
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


def run_cataloger(images_dir: Path | None = None, output_dir: Path | None = None) -> list[dict[str, Any]]:
    """Reads final images, extracts metadata with Gemini, embeds IPTC/EXIF, and exports to CSV."""
    target_dir = images_dir or FINAL_IMAGES_DIR
    out_dir = output_dir or target_dir

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
                dest = rejected_dir / img_path.name
                if dest.exists():
                    dest.unlink()
                img_path.rename(dest)
                logger.info(f"Moved rejected asset {img_path.name} to {dest}")
            except Exception as e:
                logger.error(f"Could not move rejected file {img_path.name}: {e}")
            continue

        raw_keywords = metadata.get("keywords", [])
        if isinstance(raw_keywords, list):
            keywords_list = [str(k).strip() for k in raw_keywords if str(k).strip()]
        else:
            keywords_list = [k.strip() for k in str(raw_keywords).split(",") if k.strip()]

        # Synchronize keywords with strict 50 cap and mandatory AI tags for both image and CSV
        clean_kws, keywords_str = normalize_keywords(keywords_list, max_keywords=50)

        title = str(metadata.get("title", "")).strip()
        description = str(metadata.get("description", "")).strip()
        category = str(metadata.get("category", "3")).strip()

        # Build target filename for SEO
        base_new_name = sanitize_filename(title)
        if not base_new_name:
            base_new_name = "stock-image"
            
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = out_dir / f"{base_new_name}.jpg"
        counter = 1
        while target_path.exists() and target_path != img_path and target_path != img_path.with_suffix(".jpg"):
            target_path = out_dir / f"{base_new_name}-{counter}.jpg"
            counter += 1

        # Injetar metadados diretamente no arquivo da imagem (IPTC + EXIF) e Renomear
        final_image_path = embed_metadata(img_path, target_path, title, clean_kws, description=description)

        # Skip recording in CSV if conversion failed (e.g. left as .png)
        if final_image_path.suffix.lower() not in [".jpg", ".jpeg"]:
            logger.error(f"Skipping CSV entry for unconverted image: {final_image_path.name}")
            continue

        # Multi-Platform Compliance Verification
        from src.cataloger.platform_compliance import validate_all_platforms
        comp_map = validate_all_platforms(final_image_path, is_ai_generated=True)
        passed = [plat for plat, c in comp_map.items() if c.is_compliant and not c.blocked]
        blocked = [plat for plat, c in comp_map.items() if c.blocked]
        logger.info(f"  🛡️ Conformidade: {final_image_path.name} apto para {len(passed)} plataformas ({', '.join(passed)}). Bloqueado preventivo: {', '.join(blocked)}.")

        row = {
            "Filename": final_image_path.name,
            "Title": title,
            "Keywords": keywords_str,
            "Category": category,
            "Releases": ""
        }
        results.append(row)
        processed_filenames.add(final_image_path.name)

        # Incremental write to CSV: instantly persist every cataloged asset
        csv_headers = ["Filename", "Title", "Keywords", "Category", "Releases"]
        file_exists = CSV_FILE.exists()
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    if not results:
        logger.info("No new items were cataloged.")
        return []

    logger.info(f"Successfully processed and appended {len(results)} items to {CSV_FILE}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StockCont Cataloger")
    parser.add_argument("--images-dir", type=Path, default=None, help="Input directory of images to catalog")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for cataloged images")
    cli_args = parser.parse_args()
    run_cataloger(images_dir=cli_args.images_dir, output_dir=cli_args.output_dir)
