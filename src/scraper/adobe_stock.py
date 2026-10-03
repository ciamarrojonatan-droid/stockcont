import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import httpx
import time
import random

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
IMAGES_DIR = DATA_DIR / "images"
TRENDS_FILE = DATA_DIR / "trends.json"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def setup_directories() -> None:
    """Ensure data directories exist."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Directories verified: {IMAGES_DIR}")

def download_image(url: str, item_id: str) -> str | None:
    """Download an image and save it locally."""
    # Sanitize item_id to prevent path traversal
    safe_item_id = re.sub(r'[^a-zA-Z0-9_-]', '', item_id)
    if not safe_item_id:
        safe_item_id = f"unknown_{int(time.time())}"
        
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        
        # Extract extension robustly
        parsed_url = urlparse(url)
        ext = Path(parsed_url.path).suffix or ".jpg"
                
        filename = f"{safe_item_id}{ext}"
        filepath = IMAGES_DIR / filename
        
        with open(filepath, "wb") as f:
            f.write(response.content)
            
        return str(filepath.relative_to(BASE_DIR)).replace("\\", "/")
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error(f"Network error downloading {url}: {e}")
    except OSError as e:
        logger.error(f"File system error saving {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
        
    return None

def scrape_adobe_stock_trends(max_items: int = 50) -> list[dict[str, Any]]:
    """Scrape top trending images from Adobe Stock."""
    scraped_data = []
    
    with sync_playwright() as p:
        # Launching in headed mode helps prevent immediate bot detection
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Example URL: searching for popular/trending general assets
        url = "https://stock.adobe.com/search?order=relevance&safe_search=1&k=trending"
        
        logger.info(f"Navigating to {url}")
        
        try:
            page.goto(url, wait_until="networkidle")
            time.sleep(random.uniform(2.0, 4.0))
            
            # Scroll down to load lazy images
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(random.uniform(1.0, 2.0))
                
            # Extract elements
            items = page.locator("article.search-result-cell, div.search-result-cell")
            all_items = items.all()
            logger.info(f"Found {len(all_items)} items on the page.")
            
            for item in all_items[:max_items]:
                try:
                    item_id = item.get_attribute("data-content-id") or f"unknown_{random.randint(1000, 9999)}"
                    
                    img_locator = item.locator("img").first
                    title = img_locator.get_attribute("alt") or "Untitled"
                    img_url = img_locator.get_attribute("src") or img_locator.get_attribute("data-lazy")
                    
                    if not img_url:
                        continue
                        
                    logger.info(f"Scraping item {item_id}: {title[:30]}...")
                    
                    # Download image
                    local_path = download_image(img_url, item_id)
                    
                    if local_path:
                        scraped_data.append({
                            "id": item_id,
                            "title": title,
                            "original_url": img_url,
                            "local_path": local_path,
                            "scraped_at": time.time()
                        })
                        
                except Exception as e:
                    # Generic catch per item to ensure the loop continues
                    # Note: Playwright sync_api errors are usually subclasses of Exception
                    logger.warning(f"Error processing item: {e}")
                    
                time.sleep(random.uniform(0.5, 1.5))
                
        except PlaywrightTimeoutError:
            logger.error("Timeout while trying to load the page.")
        except Exception as e:
            logger.error(f"Unexpected Playwright error during navigation: {e}")
        finally:
            browser.close()
            
    return scraped_data

def save_data(data: list[dict[str, Any]]) -> None:
    """Save scraped metadata to JSON."""
    if not data:
        logger.warning("No data to save.")
        return
        
    existing_data = []
    if TRENDS_FILE.exists():
        try:
            with open(TRENDS_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Existing trends.json is corrupt. Starting fresh.")
            
    existing_ids = {item["id"] for item in existing_data if "id" in item}
    new_items = [item for item in data if item["id"] not in existing_ids]
    
    combined_data = existing_data + new_items
    
    with open(TRENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(new_items)} new items. Total items: {len(combined_data)}.")

if __name__ == "__main__":
    setup_directories()
    logger.info("Starting Trend Scraper...")
    data = scrape_adobe_stock_trends(max_items=5) # 5 for quick MVP test
    save_data(data)
    logger.info("Done.")
