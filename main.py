#!/usr/bin/env python3
"""StockCont - Master Pipeline CLI Orchestrator

Unified command-line interface for the 4-phase microstock AI pipeline:
  Phase 1: Trend Scout (Adobe Stock Scraper with Niche support)
  Phase 2: Art Director (Prompt Engineering via Gemini Vision)
  Phase 3: The Factory (Mass Generation Bot on Runninghub)
  Phase 4: The Cataloger (Metadata, IPTC/EXIF Injection & CSV Export)
"""

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Root Directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

# Reconfigure stdout/stderr to UTF-8 on Windows consoles to prevent cp1252 UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("StockCont")

# File & Directory Paths
RAW_DIR = BASE_DIR / "data" / "raw"
TRENDS_FILE = RAW_DIR / "trends.json"
RAW_IMAGES_DIR = RAW_DIR / "images"

PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROMPTS_FILE = PROCESSED_DIR / "prompts.json"
CSV_FILE = PROCESSED_DIR / "adobe_stock_upload.csv"

FINAL_DIR = BASE_DIR / "data" / "final"
FINAL_IMAGES_DIR = FINAL_DIR / "images"

def print_banner() -> None:
    """Print the StockCont welcome banner."""
    print("=" * 65)
    print("      📈 StockCont - AI Stock Asset Automation Pipeline")
    print("      Autonomous Microstock Scout, Producer & Cataloger")
    print("=" * 65)

def check_status() -> None:
    """Check and display the current status of all pipeline stages."""
    print_banner()
    print("\n🔍 PIPELINE STATUS REPORT:\n")

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "Present"
        print(f"  [✓] Gemini API Key: Configured ({masked_key})")
    else:
        print("  [✗] Gemini API Key: NOT FOUND (Check .env file)")

    # Phase 1: Raw Trends
    trends_count = 0
    if TRENDS_FILE.exists():
        try:
            with open(TRENDS_FILE, "r", encoding="utf-8") as f:
                trends_data = json.load(f)
                trends_count = len(trends_data)
        except Exception:
            trends_count = -1
    raw_images_count = len(list(RAW_IMAGES_DIR.glob("*.*"))) if RAW_IMAGES_DIR.exists() else 0
    print(f"  [1] Phase 1 (Scout):     {trends_count} trends recorded | {raw_images_count} raw reference images")

    # Phase 2: Prompts
    prompts_count = 0
    generated_prompts_total = 0
    if PROMPTS_FILE.exists():
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)
                prompts_count = len(prompts_data)
                for item in prompts_data:
                    generated_prompts_total += len(item.get("generated_prompts", []))
        except Exception:
            prompts_count = -1
    print(f"  [2] Phase 2 (Director):  {prompts_count} analyzed items | {generated_prompts_total} ready prompts")

    # Phase 3: Final Images Generated
    final_images = list(FINAL_IMAGES_DIR.glob("*.jpg")) + list(FINAL_IMAGES_DIR.glob("*.jpeg")) + list(FINAL_IMAGES_DIR.glob("*.png")) if FINAL_IMAGES_DIR.exists() else []
    print(f"  [3] Phase 3 (Factory):   {len(final_images)} assets waiting in data/final/images/")

    # Phase 4: Cataloged CSV
    cataloged_count = 0
    if CSV_FILE.exists():
        try:
            with open(CSV_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                cataloged_count = sum(1 for _ in reader)
        except Exception:
            cataloged_count = -1
    print(f"  [4] Phase 4 (Cataloger): {cataloged_count} assets cataloged in adobe_stock_upload.csv")

    print("\n" + "-" * 65)
    uncataloged = max(0, len(final_images) - cataloged_count)
    # Quick action recommendation
    if uncataloged > 0:
        print(f"  💡 Next Recommended Action: Run Phase 4 (`python main.py --phase 4`)")
        print(f"     to embed IPTC metadata and update CSV for {uncataloged} uncataloged images.")
    elif len(final_images) > 0 and uncataloged == 0:
        print(f"  🎉 All {len(final_images)} images are fully cataloged and embedded with IPTC/EXIF!")
        print(f"     Assets in data/final/images/ and data/processed/adobe_stock_upload.csv are ready for upload.")
    elif generated_prompts_total > 0:
        print(f"  💡 Next Recommended Action: Run Phase 3 (`python main.py --phase 3`)")
        print(f"     to generate images using the {generated_prompts_total} available prompts.")
    else:
        print(f"  💡 Next Recommended Action: Run Phase 1 & 2 (`python main.py --phase 1 -q 'minimalist interior'`)")
    print("=" * 65 + "\n")

def run_phase_1(query: str = "trending", order: str = "relevance", content_type: str = "all", max_items: int = 10, headless: bool = False) -> None:
    """Execute Phase 1: Adobe Stock Trend Scraper."""
    logger.info(f"--- Starting Phase 1: Scout (Query: '{query}', Order: '{order}', Max: {max_items}) ---")
    from src.scraper.adobe_stock import scrape_adobe_stock_trends
    scraped = scrape_adobe_stock_trends(
        query=query,
        order=order,
        content_type=content_type,
        max_items=max_items,
        headless=headless
    )
    logger.info(f"Phase 1 finished. Scraped {len(scraped)} assets.")

def run_phase_2() -> None:
    """Execute Phase 2: Art Director Prompt Generator."""
    logger.info("--- Starting Phase 2: Art Director (Gemini Vision Prompt Generation) ---")
    from src.analyzer.director import main as director_main
    director_main()
    logger.info("Phase 2 finished.")

def run_phase_3() -> None:
    """Execute Phase 3: The Factory RPA Bot."""
    logger.info("--- Starting Phase 3: The Factory (Runninghub Automation Bot) ---")
    from src.factory.runninghub_bot import run_factory_bot
    run_factory_bot()
    logger.info("Phase 3 finished.")

def run_phase_4() -> None:
    """Execute Phase 4: The Cataloger with IPTC/EXIF Embedding."""
    logger.info("--- Starting Phase 4: The Cataloger (SEO + IPTC/EXIF Injection + CSV) ---")
    from src.cataloger.adobe_csv_maker import run_cataloger
    results = run_cataloger()
    logger.info(f"Phase 4 finished. Processed {len(results)} assets.")

def run_all_pipeline(query: str, max_items: int) -> None:
    """Run all phases sequentially."""
    print_banner()
    logger.info("Starting Full End-to-End StockCont Pipeline...")
    run_phase_1(query=query, max_items=max_items)
    run_phase_2()
    run_phase_3()
    run_phase_4()
    logger.info("Full pipeline execution completed!")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="StockCont - Unified Microstock Automation Pipeline",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--status", "-s", action="store_true", help="Display the current pipeline dashboard status")
    parser.add_argument("--phase", "-p", type=int, choices=[1, 2, 3, 4], help="Execute a specific phase (1, 2, 3, or 4)")
    parser.add_argument("--all", "-a", action="store_true", help="Run all 4 phases sequentially")

    # Options for Phase 1
    p1_group = parser.add_argument_group("Phase 1 Options")
    p1_group.add_argument("--query", "-q", default="trending", help="Niche or search keyword for Phase 1 (e.g., 'minimalist office')")
    p1_group.add_argument("--order", "-o", default="relevance", choices=["relevance", "nb_downloads", "creation"], help="Sorting method")
    p1_group.add_argument("--type", "-t", default="all", choices=["all", "photo", "illustration"], help="Asset type")
    p1_group.add_argument("--max-items", "-m", type=int, default=10, help="Max items to scrape in Phase 1")
    p1_group.add_argument("--headless", action="store_true", help="Run scraper browser in headless mode")

    args = parser.parse_args()

    # If no arguments provided, display status and help
    if len(sys.argv) == 1 or args.status:
        check_status()
        if len(sys.argv) == 1:
            parser.print_help()
        return

    if args.all:
        run_all_pipeline(query=args.query, max_items=args.max_items)
        return

    if args.phase == 1:
        run_phase_1(
            query=args.query,
            order=args.order,
            content_type=args.type,
            max_items=args.max_items,
            headless=args.headless
        )
    elif args.phase == 2:
        run_phase_2()
    elif args.phase == 3:
        run_phase_3()
    elif args.phase == 4:
        run_phase_4()

if __name__ == "__main__":
    main()
