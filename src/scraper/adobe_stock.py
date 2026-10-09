import argparse
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

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
    safe_item_id = re.sub(r"[^a-zA-Z0-9_-]", "", item_id)
    if not safe_item_id:
        safe_item_id = f"unknown_{int(time.time())}"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()

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

def build_adobe_stock_url(
    query: str = "trending",
    order: str = "relevance",
    content_type: str = "all"
) -> str:
    """Construct a clean, valid search URL for Adobe Stock with niche parameters."""
    base_url = "https://stock.adobe.com/search"
    params: dict[str, Any] = {
        "k": query,
        "order": order,
        "safe_search": "1",
    }

    if content_type == "photo":
        params["filters[content_type:photo]"] = "1"
    elif content_type == "illustration":
        params["filters[content_type:illustration]"] = "1"

    return f"{base_url}?{urlencode(params)}"

def scrape_adobe_stock_trends(
    query: str = "trending",
    order: str = "relevance",
    content_type: str = "all",
    max_items: int = 20,
    headless: bool = False
) -> list[dict[str, Any]]:
    """Scrape trending images from Adobe Stock matching a niche or topic."""
    setup_directories()
    scraped_data: list[dict[str, Any]] = []

    search_url = build_adobe_stock_url(query=query, order=order, content_type=content_type)
    logger.info(f"Navigating to Adobe Stock: {search_url} (target items: {max_items})")

    session_dir = BASE_DIR / "chrome_session"
    session_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Launch using installed Chrome or default chromium with stealth options
        launch_kwargs = {
            "user_data_dir": session_dir,
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        }
        try:
            browser = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
        except Exception:
            browser = p.chromium.launch_persistent_context(**launch_kwargs)

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            
            # Wait for content or search cells to appear
            try:
                page.wait_for_selector("article.search-result-cell, div.search-result-cell, [data-content-id]", timeout=15000)
            except Exception:
                time.sleep(3)

            # Scroll down smoothly to load lazy images
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(random.uniform(1.0, 1.8))

            items = page.locator("article.search-result-cell, div.search-result-cell, [data-content-id]")
            all_items = items.all()
            logger.info(f"Found {len(all_items)} potential items on search page.")

            seen_ids = set()
            for item in all_items:
                if len(scraped_data) >= max_items:
                    break

                try:
                    item_id = item.get_attribute("data-content-id")
                    if not item_id:
                        continue
                    if item_id in seen_ids:
                        continue

                    img_locator = item.locator("img").first
                    if img_locator.count() == 0:
                        continue

                    title = img_locator.get_attribute("alt") or "Untitled"
                    img_url = img_locator.get_attribute("src") or img_locator.get_attribute("data-lazy")

                    if not img_url or not img_url.startswith("http"):
                        continue

                    seen_ids.add(item_id)
                    logger.info(f"Scraping asset [{item_id}]: {title[:40]}...")
                    local_path = download_image(img_url, item_id)

                    if local_path:
                        scraped_data.append({
                            "id": item_id,
                            "title": title,
                            "niche": query,
                            "original_url": img_url,
                            "local_path": local_path,
                            "scraped_at": time.time()
                        })

                except Exception as e:
                    logger.warning(f"Error extracting item: {e}")

                time.sleep(random.uniform(0.2, 0.5))

        except PlaywrightTimeoutError:
            logger.error("Timeout waiting for Adobe Stock search results.")
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
        finally:
            browser.close()

    save_data(scraped_data)
    return scraped_data

def save_data(data: list[dict[str, Any]]) -> None:
    """Save scraped metadata to JSON without duplicating existing entries."""
    if not data:
        logger.warning("No new data to save.")
        return

    existing_data: list[dict[str, Any]] = []
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

    logger.info(f"Saved {len(new_items)} new items. Total items in trends.json: {len(combined_data)}.")

def main() -> None:
    parser = argparse.ArgumentParser(description="StockCont - Adobe Stock Niche Trend Scraper")
    parser.add_argument("--query", "-q", default="trending", help="Search keyword or niche (e.g. 'cyberpunk', 'business finance')")
    parser.add_argument("--order", "-o", default="relevance", choices=["relevance", "nb_downloads", "creation"], help="Sorting order")
    parser.add_argument("--type", "-t", default="all", choices=["all", "photo", "illustration"], help="Content type")
    parser.add_argument("--max-items", "-m", type=int, default=10, help="Maximum items to scrape")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    logger.info(f"Starting Scraper with niche='{args.query}', order='{args.order}', type='{args.type}', max={args.max_items}")
    scrape_adobe_stock_trends(
        query=args.query,
        order=args.order,
        content_type=args.type,
        max_items=args.max_items,
        headless=args.headless
    )
    logger.info("Scraper execution finished.")

if __name__ == "__main__":
    main()
