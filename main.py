#!/usr/bin/env python3
"""StockCont - Master Pipeline CLI Orchestrator

Unified command-line interface for the 5-phase microstock AI pipeline:
  Phase 1: Trend Scout (Adobe Stock Scraper with Niche support)
  Phase 2: Art Director (Prompt Engineering via Gemini Vision)
  Phase 3: The Factory (Mass Generation Bot on Runninghub)
  Phase 4: The Cataloger (Metadata, IPTC/EXIF Injection & CSV Export)
  Phase 5: The Distributor (Multi-Platform SFTP/FTP Mass Upload)
"""

import argparse
import csv
import json
import logging
import os
import sys
import subprocess
from pathlib import Path

# Root Directory
BASE_DIR = Path(__file__).resolve().parent

from dotenv import load_dotenv
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
    print("      StockCont Studio - AI Stock Asset Automation Pipeline")
    print("      Autonomous Microstock Scout, Producer & Cataloger")
    print("=" * 65)

def check_status() -> None:
    """Check and display the current status of all pipeline stages."""
    print_banner()
    print("\n=== PIPELINE STATUS REPORT ===\n")

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
    missing_raw_str = ""
    if trends_count > 0 and raw_images_count < trends_count:
        missing_raw_str = f" [AVISO] ({trends_count - raw_images_count} ausentes - rode `python main.py --sync-raw`)"
    print(f"  [1] Phase 1 (Scout):     {trends_count} trends recorded | {raw_images_count} raw reference images{missing_raw_str}")

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

    # Phase 3: Final Images & Queue Progress
    from src.factory.prompt_queue import PromptQueueManager
    queue_mgr = PromptQueueManager()
    q_stats = queue_mgr.get_stats()
    final_images = list(FINAL_IMAGES_DIR.glob("*.jpg")) + list(FINAL_IMAGES_DIR.glob("*.jpeg")) + list(FINAL_IMAGES_DIR.glob("*.png")) if FINAL_IMAGES_DIR.exists() else []
    print(f"  [3] Phase 3 (Factory):   {q_stats['generated']}/{q_stats['total']} prompts gerados ({q_stats['pending']} pendentes - {q_stats['progress_percent']}%) | {len(final_images)} assets em data/final/images/")

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

    # Phase 5: Distributed Uploads
    upload_history_file = PROCESSED_DIR / "upload_history.json"
    uploaded_files_count = 0
    if upload_history_file.exists():
        try:
            with open(upload_history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                uploaded_files_count = len(history_data)
        except Exception:
            uploaded_files_count = -1
            
    from src.uploader.ftp_distributor import get_available_agencies
    agencies = get_available_agencies()
    cfg_count = sum(1 for a in agencies.values() if a.is_configured)
    print(f"  [5] Phase 5 (Distributor): {cfg_count}/{len(agencies)} agencies configured | {uploaded_files_count} assets logged in upload_history.json")

    # Video Pipeline Status
    from src.factory.prompt_queue import FINAL_VIDEOS_DIR
    final_videos = list(FINAL_VIDEOS_DIR.glob("*.mp4")) + list(FINAL_VIDEOS_DIR.glob("*.mov")) if FINAL_VIDEOS_DIR.exists() else []
    video_prompts_file = PROCESSED_DIR / "video_prompts.json"
    v_prompts_count = 0
    if video_prompts_file.exists():
        try:
            with open(video_prompts_file, "r", encoding="utf-8") as f:
                v_data = json.load(f)
                v_prompts_count = sum(len(p.get("derivative_prompts", [])) for p in v_data)
        except Exception:
            pass
    print(f"  [V] Video Pipeline:      {v_prompts_count} video prompts prontos | {len(final_videos)} vídeos em data/final/videos/")

    # Cloud Backup: Google Drive
    from src.backup.gdrive_backup import GoogleDriveBackup
    gdrive = GoogleDriveBackup()
    gdrive_status = f"Configured ({gdrive.mode})" if gdrive.is_configured else "Not Configured (Optional in .env)"
    gdrive_history_count = len(gdrive._history)
    print(f"  [CLOUD] Google Drive Backup:  {gdrive_status} | {gdrive_history_count} assets backed up in history")

    # 24/7 Production Daemon Status & Quotas
    daemon_state_file = PROCESSED_DIR / "daemon_state.json"
    if daemon_state_file.exists():
        try:
            with open(daemon_state_file, "r", encoding="utf-8") as df:
                d_data = json.load(df)
                status_icon = "[ACTIVE]" if d_data.get("status") == "running" else ("[PAUSED]" if d_data.get("status") == "paused" else "[STOPPED]")
                print(f"  [DAEMON] Production 24/7:        {status_icon} {d_data.get('status', 'unknown').upper()} | Ciclos: {d_data.get('cycles_completed', 0)} | Ação: {d_data.get('current_action', 'N/A')}")
        except Exception:
            pass

    try:
        from src.uploader.quota_manager import QuotaManager
        qm = QuotaManager()
        q_reports = qm.get_all_reports()
        exhausted = [p.upper() for p, r in q_reports.items() if r.is_quota_exhausted and r.weekly_limit > 0]
        active_slots = sum(r.slots_available for r in q_reports.values() if r.weekly_limit > 0)
        ex_str = f" | Esgotados: {', '.join(exhausted)}" if exhausted else " | 100% livre"
        print(f"  [QUOTAS] Weekly Rolling (7D):  {active_slots} slots livres disponíveis{ex_str}")
    except Exception:
        pass

    print("\n" + "-" * 65)
    uncataloged = max(0, len(final_images) - cataloged_count)
    # Quick action recommendation
    if uncataloged > 0:
        print(f"  [NEXT ACTION]: Run Phase 4 (`python main.py --phase 4`)")
        print(f"     to embed IPTC metadata and update CSV for {uncataloged} uncataloged images.")
        if q_stats['pending'] > 0:
            print(f"     Or continue Phase 3: `python main.py --phase 3 --all-batches` ({q_stats['pending']} prompts pendentes).")
    elif q_stats['pending'] > 0:
        print(f"  [NEXT ACTION]: Run Phase 3 (`python main.py --phase 3 --all-batches`)")
        print(f"     to process the remaining {q_stats['pending']} pending prompts without repeating generated ones.")
    elif len(final_images) > 0 and uncataloged == 0:
        if cfg_count > 0:
            print(f"  [NEXT ACTION]: Run Phase 5 (`python main.py --phase 5 --dry-run`)")
            print(f"     to distribute {len(final_images)} cataloged assets to {cfg_count} configured agencies.")
        else:
            print(f"  All {len(final_images)} images are fully cataloged and embedded with IPTC/EXIF!")
            print(f"     Configure agency credentials in .env to enable Phase 5 automated SFTP/FTP distribution.")
    elif generated_prompts_total > 0:
        print(f"  [NEXT ACTION]: Run Phase 3 (`python main.py --phase 3`)")
        print(f"     to generate images using the {generated_prompts_total} available prompts.")
    else:
        print(f"  [NEXT ACTION]: Run Phase 1 & 2 (`python main.py --phase 1 -q 'minimalist interior'`)")
    print("=" * 65 + "\n")

def run_sync_raw(force: bool = False, workers: int = 8) -> None:
    """Execute concurrent hydration of missing raw reference images."""
    logger.info(f"--- Starting Raw Reference Hydration (Force: {force}, Workers: {workers}) ---")
    from src.scraper.hydrator import hydrate_raw_references
    stats = hydrate_raw_references(max_workers=workers, force=force)
    logger.info(f"Hydration finished: {stats['downloaded']} downloaded, {stats['already_present']} present, {stats['failed']} failed.")

def run_phase_1(
    mode: str = "insights",
    query: str = "trending",
    order: str = "relevance",
    content_type: str = "photo",
    max_items: int = 15,
    min_downloads: int = 0,
    deep_profile: bool = False,
    headless: bool = False
) -> None:
    """Execute Phase 1: Adobe Stock Trend & Contributor Insights Scraper."""
    from src.scraper.adobe_stock import scrape_contributor_insights, scrape_adobe_stock_trends
    if mode == "insights":
        logger.info(f"--- Iniciando Fase 1: Olheiro (Contributor Insights, Tipo: '{content_type}', Max: {max_items}, Deep: {deep_profile}) ---")
        scraped = scrape_contributor_insights(
            content_type=content_type,
            max_items=max_items,
            min_downloads=min_downloads,
            deep_profile=deep_profile,
            headless=headless
        )
    else:
        logger.info(f"--- Iniciando Fase 1: Olheiro (Busca Pública por Termo: '{query}', Ordem: '{order}', Max: {max_items}) ---")
        scraped = scrape_adobe_stock_trends(
            query=query,
            order=order,
            content_type=content_type,
            max_items=max_items,
            headless=headless
        )
    logger.info(f"Fase 1 finalizada. Minerados {len(scraped)} assets.")

def run_phase_2() -> None:
    """Execute Phase 2: Art Director Prompt Generator."""
    logger.info("--- Starting Phase 2: Art Director (Gemini Vision Prompt Generation) ---")
    from src.analyzer.director import main as director_main
    director_main()
    logger.info("Phase 2 finished.")

def run_phase_3(account: int = 1, node: int | None = None, batches: int = 1, all_batches: bool = False, batch_size: int = 210) -> None:
    """Execute Phase 3: The Factory RPA Bot (Conta 1 - Raw Producer ou Conta 2 - SeedVR 8K)."""
    logger.info(f"--- Starting Phase 3: The Factory (Conta {account}, Output Node: {node or 'default'}, Batch Size: {batch_size}, Batches: {batches}) ---")
    from src.factory.runninghub_bot import run_factory_bot
    run_factory_bot(account=account, output_node_id=node, batch_size=batch_size, max_batches=batches, all_batches=all_batches)
    logger.info("Phase 3 finished.")

def run_phase_4(images_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """Execute Phase 4: The Cataloger with IPTC/EXIF Embedding."""
    target_str = f" from '{images_dir}'" if images_dir else ""
    logger.info(f"--- Starting Phase 4: The Cataloger (SEO + IPTC/EXIF Injection + CSV){target_str} ---")
    from src.cataloger.adobe_csv_maker import run_cataloger
    results = run_cataloger(images_dir=images_dir, output_dir=output_dir)
    logger.info(f"Phase 4 finished. Processed {len(results)} assets.")

    # Automated Google Drive Backup
    from src.backup.gdrive_backup import GoogleDriveBackup
    gdrive = GoogleDriveBackup()
    if gdrive.is_configured:
        logger.info("[CLOUD] Google Drive configurado! Sincronizando backup automático dos assets...")
        gdrive.backup_assets()
    else:
        logger.info("[INFO] Dica: Configure o Google Drive no .env para backup automático dos assets em nuvem.")

def run_backup(dry_run: bool = False, force: bool = False) -> None:
    """Execute Google Drive asset backup."""
    logger.info(f"--- Starting Google Drive Backup (DryRun: {dry_run}, Force: {force}) ---")
    from src.backup.gdrive_backup import run_gdrive_backup
    run_gdrive_backup(dry_run=dry_run, force=force)
    logger.info("Google Drive Backup finished.")

def run_video_phase_2(max_items: int | None = None) -> None:
    """Execute Video Phase 2: Video Director of Photography."""
    logger.info("--- Starting Video Phase 2: Video Director (Gemini Vision 4D Temporal Prompts) ---")
    from src.analyzer.video_director import run_video_director
    run_video_director(max_items=max_items)
    logger.info("Video Phase 2 finished.")

def run_video_phase_4(videos_dir: Path | None = None, max_items: int | None = None, generate_prores: bool = False) -> None:
    """Execute Video Phase 4: Video Cataloger with Audio Strip & MP4/MOV Metadata."""
    logger.info("--- Starting Video Phase 4: Video Cataloger (Audio Strip + MP4/QuickTime Metadata + CSV) ---")
    from src.cataloger.video_cataloger import run_video_cataloger
    from src.factory.prompt_queue import FINAL_VIDEOS_DIR
    target_dir = videos_dir or FINAL_VIDEOS_DIR
    run_video_cataloger(videos_dir=target_dir, max_items=max_items, generate_prores=generate_prores)
    logger.info("Video Phase 4 finished.")

def run_phase_5(platform: str = "all", dry_run: bool = False, force: bool = False, images_dir: Path | None = None, asset_type: str = "image") -> None:
    """Execute Phase 5: The Distributor (Multi-Platform SFTP/FTP Mass Upload)."""
    dir_str = f" from '{images_dir}'" if images_dir else ""
    logger.info(f"--- Starting Phase 5: The Distributor (Target: {platform}, DryRun: {dry_run}, Force: {force}, Type: {asset_type}){dir_str} ---")
    from src.uploader.ftp_distributor import run_distributor
    run_distributor(target_platform=platform, dry_run=dry_run, force=force, images_dir=images_dir, asset_type=asset_type)
    logger.info("Phase 5 finished.")

def run_all_pipeline(query: str, max_items: int, node: int = 192, batches: int = 1, all_batches: bool = False) -> None:
    """Run all phases sequentially."""
    print_banner()
    logger.info("Starting Full End-to-End StockCont Pipeline...")
    run_phase_1(max_items=max_items)
    run_phase_2()
    run_phase_3(node=node, batches=batches, all_batches=all_batches)
    run_phase_4()
    run_backup()
    run_phase_5()
    logger.info("Full pipeline execution completed!")


def run_qc(mode: str | None = None) -> None:
    """Execute Quality Control visual auditing (Automated via Gemini Vision or Manual scan)."""
    logger.info(f"--- Starting Quality Control & Curation (Mode: {mode or 'default'}) ---")
    from src.analyzer.qc_inspector import QCInspector
    inspector = QCInspector()
    if mode in ("auto", "manual"):
        inspector.set_config(mode=mode)
    results = inspector.run_batch_qc()
    stats = inspector.get_stats()
    print("\n=== QUALITY CONTROL & CURATION SUMMARY:")
    print(f"  • Modo Atual:       {stats['mode'].upper()} (Padrão: Auto)")
    print(f"  • Total em Staging: {stats['total_staging']}")
    print(f"  • Aprovadas:        {stats['approved']}")
    print(f"  • Rejeitadas:       {stats['rejected']}")
    print(f"  • Pendentes:        {stats['pending']}")
    print(f"  • Prontas em 8K:    {stats['upscaled']}")
    logger.info("Quality Control execution finished.")

def run_upscale() -> None:
    """Upscale approved staging images to 8K via RunningHub Conta 2 (SeedVR) in packs of 10."""
    logger.info("--- Starting 8K Upscale via RunningHub Conta 2 (SeedVR 8K) in packs of 10 ---")
    run_phase_3(account=2, batch_size=10)


def show_seasonal_radar() -> None:
    """Display the predictive seasonal calendar report and high-converting micro-niches."""
    from src.analyzer.seasonal_radar import get_target_procurement_window
    print_banner()
    forecast = get_target_procurement_window()
    print("\n=== SEASONAL DEMAND FORECAST & BLUE OCEAN RADAR ===\n")
    print(f"  Current Date:           {forecast['current_date']}")
    print(f"  Target Procurement Window: {forecast['target_procurement_date']} (Lead time: D+{forecast['lead_time_days']} days)")
    print(f"  Target Quarter:         {forecast['target_quarter']} (Month {forecast['target_month']})")
    print(f"  Macro Buying Theme:     {forecast['macro_theme']}\n")
    print("  RECOMMENDED HIGH-CONVERTING MICRO-NICHES FOR PRODUCTION:")
    for idx, n in enumerate(forecast['recommended_niches'], 1):
        print(f"\n  [{idx}] {n['name']}")
        print(f"      • Command:           python main.py --phase 1 --mode search -q \"{n['query']}\"")
        print(f"      • Target Buyers:     {', '.join(n['target_buyers'])}")
        print(f"      • Suggested Layout:  {n['suggested_layout']}")
        print(f"      • Commercial Reason: {n['rationale']}")
    print("\n" + "=" * 65 + "\n")
def main() -> None:
    parser = argparse.ArgumentParser(
        description="StockCont - Unified Microstock Automation Pipeline",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--sync-raw", "--hydrate", dest="sync_raw", action="store_true", help="Download missing raw reference images listed in trends.json concurrently")
    parser.add_argument("--status", "-s", action="store_true", help="Display the current pipeline dashboard status")
    parser.add_argument("--phase", "-p", type=int, choices=[1, 2, 3, 4, 5], help="Execute a specific phase (1, 2, 3, 4, or 5)")
    parser.add_argument("--backup", "-b", action="store_true", help="Execute Google Drive backup for all cataloged assets")
    parser.add_argument("--restore", "--pull-backup", dest="restore", action="store_true", help="Pull all images, CSV, and upload history from Google Drive backup")
    parser.add_argument("--all", "-a", action="store_true", help="Run all pipeline phases sequentially")
    parser.add_argument("--qc", action="store_true", help="Run Quality Control & Curation auditing on staging images")
    parser.add_argument("--qc-mode", choices=["auto", "manual"], default=None, help="QC mode: 'auto' (Gemini Vision default) or 'manual' (Dashboard triage)")
    parser.add_argument("--upscale", action="store_true", help="Upscale all approved staging images to 8K")
    parser.add_argument("--seasonal", action="store_true", help="Display predictive seasonal demand forecast and Blue Ocean niches")
    parser.add_argument("--dashboard", action="store_true", help="Launch the StockCont web dashboard (http://localhost:8501)")
    parser.add_argument("--port", type=int, default=8501, help="Port for the dashboard server (default: 8501)")
    parser.add_argument("--no-browser", action="store_true", help="Start dashboard without auto-opening browser")

    # Options for Phase 1
    p1_group = parser.add_argument_group("Phase 1 Options")
    p1_group.add_argument("--mode", default="insights", choices=["insights", "search"], help="Phase 1 mode: 'insights' (Contributor Top Sellers) or 'search' (Public keyword)")
    p1_group.add_argument("--query", "-q", default="trending", help="Niche or search keyword for Phase 1 search mode (e.g., 'minimalist office')")
    p1_group.add_argument("--order", "-o", default="relevance", choices=["relevance", "nb_downloads", "creation"], help="Sorting method (search mode)")
    p1_group.add_argument("--type", "-t", default="photo", choices=["all", "photo", "illustration", "vector", "video"], help="Asset type")
    p1_group.add_argument("--max-items", "-m", type=int, default=15, help="Max items to scrape in Phase 1")
    p1_group.add_argument("--min-downloads", type=int, default=0, help="Minimum contributor lifetime downloads threshold")
    p1_group.add_argument("--deep-profile", action="store_true", help="Mine deeper into top contributors' full portfolios")
    p1_group.add_argument("--headless", action="store_true", help="Run scraper browser in headless mode")

    # Options for Phase 3
    p3_group = parser.add_argument_group("Phase 3 Options")
    p3_group.add_argument("--account", type=int, default=1, choices=[1, 2], help="RunningHub Account: 1 (Raw Producer) or 2 (SeedVR 8K Upscaler)")
    p3_group.add_argument("--node", type=int, default=None, help="Output Node ID (default: 121 for Conta 1, 55 for Conta 2)")
    p3_group.add_argument("--batch-size", type=int, default=210, help="Number of prompts per batch (default: 210)")
    p3_group.add_argument("--batches", type=int, default=1, help="Number of consecutive batches to process in Phase 3 (default: 1)")
    p3_group.add_argument("--all-batches", action="store_true", help="Process all remaining pending batches until the prompt queue is exhausted")

    # Options for Phase 4
    p4_group = parser.add_argument_group("Phase 4 Options")
    p4_group.add_argument("--images-dir", type=Path, default=None, help="Custom directory containing images to catalog")
    p4_group.add_argument("--output-dir", type=Path, default=None, help="Custom directory to store final cataloged JPGs")

    # Options for Phase 5 & Backup
    p5_group = parser.add_argument_group("Phase 5 & Backup Options")
    p5_group.add_argument("--platform", default="all", help="Target agency: all, adobe, freepik, dreamstime, pond5, alamy, vecteezy, 123rf")
    p5_group.add_argument("--dry-run", action="store_true", help="Test credentials and simulate upload/backup without transferring files")
    p5_group.add_argument("--force", action="store_true", help="Re-upload or re-backup files even if already recorded in history")

    # Options for 24/7 Production Daemon & Quotas
    daemon_group = parser.add_argument_group("24/7 Production Daemon & Quota Options")
    daemon_group.add_argument("--daemon", action="store_true", help="Launch the 24/7 autonomous production pipeline daemon")
    daemon_group.add_argument("--daemon-interval", type=int, default=300, help="Pacing interval in seconds between daemon cycles (default: 300)")
    daemon_group.add_argument("--min-buffer", type=int, default=50, help="Minimum prompt buffer threshold for daemon (default: 50)")
    daemon_group.add_argument("--quotas", action="store_true", help="Display rolling 7-day weekly quota reports for all platforms")

    # Video Pipeline Specific Options
    video_group = parser.add_argument_group("Video Pipeline Options")
    video_group.add_argument("--video", action="store_true", help="Execute video-specific pipeline phase")
    video_group.add_argument("--asset-type", choices=["image", "video", "all"], default="image", help="Asset type for pipeline processing (default: image)")
    video_group.add_argument("--prores", action="store_true", help="Generate Apple ProRes 422 HQ MOV for Pond5 in Phase 4")
    video_group.add_argument("--videos-dir", type=Path, default=None, help="Custom directory containing videos to catalog")

    args = parser.parse_args()

    # Dashboard mode - launch web UI server
    if args.dashboard:
        # Check if dashboard server is already alive on port
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/status", timeout=1.0) as resp:
                if resp.status == 200:
                    logger.info("[INFO] StockCont Dashboard já está ativo em http://localhost:%d!", args.port)
                    if not args.no_browser:
                        import webbrowser
                        webbrowser.open(f"http://localhost:{args.port}")
                    return
        except Exception:
            pass
        from src.dashboard.app import start_dashboard
        start_dashboard(port=args.port, open_browser=not args.no_browser)
        return

    if args.restore:
        from src.backup.gdrive_backup import run_gdrive_restore
        run_gdrive_restore()
        return

    # If no arguments provided, display status and help
    if len(sys.argv) == 1 or args.status:
        check_status()
        if len(sys.argv) == 1:
            parser.print_help()
        return

    if args.qc:
        run_qc(mode=args.qc_mode)
        return

    if args.upscale:
        run_upscale()
        return

    if args.sync_raw:
        run_sync_raw(force=args.force)
        return

    if args.seasonal:
        show_seasonal_radar()
        return

    if args.backup:
        run_backup(dry_run=args.dry_run, force=args.force)
        return

    if args.quotas:
        from src.uploader.quota_manager import print_quotas_summary
        print_quotas_summary()
        return

    if args.daemon:
        from src.orchestrator.daemon import start_daemon
        start_daemon(interval=args.daemon_interval, min_buffer=args.min_buffer, dry_run=args.dry_run)
        return

    if args.all:
        run_all_pipeline(query=args.query, max_items=args.max_items, node=args.node, batches=args.batches, all_batches=args.all_batches)
        return

    if args.phase == 1:
        c_type = "video" if (args.video or args.asset_type == "video") else args.type
        run_phase_1(
            mode=args.mode,
            query=args.query,
            order=args.order,
            content_type=c_type,
            max_items=args.max_items,
            min_downloads=args.min_downloads,
            deep_profile=args.deep_profile,
            headless=args.headless
        )
    elif args.phase == 2:
        if args.video or args.asset_type == "video":
            run_video_phase_2(max_items=args.max_items)
        else:
            run_phase_2()
    elif args.phase == 3:
        run_phase_3(account=args.account, node=args.node, batches=args.batches, all_batches=args.all_batches, batch_size=args.batch_size)
    elif args.phase == 4:
        if args.video or args.asset_type == "video":
            run_video_phase_4(videos_dir=args.videos_dir, max_items=args.max_items, generate_prores=args.prores)
        else:
            run_phase_4(images_dir=args.images_dir, output_dir=args.output_dir)
    elif args.phase == 5:
        asset_t = "video" if args.video else args.asset_type
        target_dir = args.videos_dir if (args.video or args.asset_type == "video") else args.images_dir
        run_phase_5(platform=args.platform, dry_run=args.dry_run, force=args.force, images_dir=target_dir, asset_type=asset_t)

if __name__ == "__main__":
    # Auto-bootstrap Virtual Environment if running under global/system Python
    venv_python = BASE_DIR / "venv" / "Scripts" / "python.exe"
    if venv_python.exists() and sys.executable.lower() != str(venv_python).lower():
        if sys.prefix == sys.base_prefix or not os.environ.get("VIRTUAL_ENV"):
            sys.exit(subprocess.call([str(venv_python)] + sys.argv))
    main()
