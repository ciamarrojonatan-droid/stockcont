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

# Auto-detect and re-exec into local virtualenv if invoked via global Python
venv_python = BASE_DIR / "venv" / "Scripts" / "python.exe"
if not os.environ.get("_STOCKCONT_VENV_ACTIVE") and venv_python.exists():
    try:
        if Path(sys.executable).resolve() != venv_python.resolve():
            os.environ["_STOCKCONT_VENV_ACTIVE"] = "1"
            res = subprocess.run([str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:])
            sys.exit(res.returncode)
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except ImportError:
    pass

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
    print(f"  [V] Video Pipeline (4K):  Workflow: 2115926169974812674 (Load Image #164 -> Prompt #17 -> Video Combine #157)")
    print(f"                            {v_prompts_count} video prompts prontos | {len(final_videos)} vídeos em data/final/videos/")

    # DarkFactory Cinema Engine (T2V) Status
    try:
        from src.video.darkfactory_t2v import DarkFactoryT2VDirector
        df_director = DarkFactoryT2VDirector()
        df_stats = df_director.get_stats()
        print(f"  [DF-T2V] DarkFactory Cinema:  {df_stats['total_scenes']} scenes ({df_stats['total_shots']} dual-shots) | Targets: MiniMax H3 & Google Veo 2")
    except Exception:
        pass

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

def run_phase_2(director_mode: str = "auto") -> None:
    """Execute Phase 2: Art Director Prompt Generator."""
    logger.info(f"--- Starting Phase 2: Art Director (Gemini Vision Prompt Generation, mode={director_mode}) ---")
    from src.analyzer.director import main as director_main
    director_main(mode=director_mode)
    logger.info("Phase 2 finished.")

def run_phase_3(
    account: int = 1,
    node: int | None = None,
    batches: int = 1,
    all_batches: bool = False,
    batch_size: int = 210,
    is_video: bool = False,
    input_image: Path | None = None,
    prompt_text: str | None = None,
    upload_wait_sec: int = 30,
    execute_mode: str | None = None,
) -> None:
    """Execute Phase 3: The Factory RPA Bot (Conta 1 - Raw Producer, Conta 2 - SeedVR 8K, ou Conta 3/Vídeo - 4K Video Generator)."""
    if is_video or account == 3:
        account = 3
        logger.info("--- Starting Phase 3: The Factory Video Pipeline (Workflow 4K: Load Image #164, Prompt #17, Video Combine #157) ---")
    else:
        logger.info(f"--- Starting Phase 3: The Factory (Conta {account}, Output Node: {node or 'default'}, Batch Size: {batch_size}, Batches: {batches}) ---")
    from src.factory.runninghub_bot import run_factory_bot
    if execute_mode and execute_mode.lower() == "standard":
        logger.warning("⚠️ Opção --execute-mode standard foi redirecionada para 'lite_plus' (Lite/Plus é mandatório em todos os workflows).")
        execute_mode = "lite_plus"
    run_factory_bot(
        account=account,
        output_node_id=node,
        batch_size=batch_size,
        max_batches=batches,
        all_batches=all_batches,
        input_image_path=input_image,
        custom_prompt_text=prompt_text,
        upload_wait_sec=upload_wait_sec,
        execute_mode=execute_mode,
    )
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

def run_darkfactory_t2v(
    archetype: str = "all",
    export_only: bool = False,
    custom_title: str | None = None,
    custom_beat: str | None = None
) -> None:
    """Execute DarkFactory T2V Cinema Engine: synthesize high-retention dual-shots."""
    logger.info("--- Starting DarkFactory Cinema Engine (T2V Narrative Architect) ---")
    from src.video.darkfactory_t2v import DarkFactoryT2VDirector, NARRATIVE_ARCHETYPES, initialize_default_darkfactory_pipeline
    director = DarkFactoryT2VDirector()
    if export_only:
        minimax_f, veo_f = director.export_model_queues()
        print(f"\n✅ Filas exportadas com sucesso:")
        print(f"  • MiniMax H3 (Hailuo): {minimax_f}")
        print(f"  • Google Flow (Veo 2): {veo_f}\n")
        return

    if custom_title and custom_beat:
        logger.info(f"Generating custom dual-shot scene: '{custom_title}'")
        res = director.create_custom_dual_shot(
            scene_title=custom_title,
            narrative_beat=custom_beat,
            shot_a_subject=f"Dramatic medium close-up of protagonist in {custom_title}, {custom_beat}. Tense breathing, subtle light glinting in eyes, authentic emotion.",
            shot_a_camera="Slow forward push-in dolly movement, eye-level, 35mm anamorphic",
            shot_b_subject=f"Visceral macro cutaway detail supporting {custom_title}. Atmospheric environment, dynamic kinetic motion.",
            shot_b_camera="Handheld visceral drift with macro rack-focus, shallow depth of field"
        )
        print(f"\n🎬 Bespoke Scene Created: {res['title']} (Scene #{res['scene_id']})")
        for sh in res['shots']:
            print(f"  • [{sh['shot_type'].upper()}] {sh['focus']}: {sh['camera_movement']}")
        return

    if archetype == "all":
        director = initialize_default_darkfactory_pipeline()
    else:
        if archetype in NARRATIVE_ARCHETYPES:
            arch = NARRATIVE_ARCHETYPES[archetype]
            for idx in range(len(arch.get("scenes", []))):
                director.create_scene_from_archetype(archetype, scene_index=idx)
        else:
            logger.error(f"Archetype '{archetype}' not recognized. Available: {list(NARRATIVE_ARCHETYPES.keys())}")
            return

    stats = director.get_stats()
    print("\n=== DARKFACTORY CINEMA ENGINE (T2V) SUMMARY:")
    print(f"  • Total de Cenas Narrativas: {stats['total_scenes']}")
    print(f"  • Total de Planos Dual-Shot: {stats['total_shots']} (Shot A: Tensão / Shot B: Macro)")
    print(f"  • Modelos Alvo Calibrados:   MiniMax H3 (Hailuo) & Google Flow (Veo 2)")
    print(f"  • Filas Prontas em:          data/processed/minimax_t2v_queue.json")
    print(f"                               data/processed/google_veo_queue.json\n")


def run_nolan_director(topic: str = "1983 Soviet nuclear false alarm incident") -> None:
    """Execute Christopher Nolan Showrunner Engine to direct a dark historical documentary episode."""
    logger.info(f"--- Starting Christopher Nolan Dark History Director on '{topic}' ---")
    df_root = Path(__file__).resolve().parent.parent / "darkfactory"
    nolan_script = df_root / "src" / "nolan_director.py"
    if nolan_script.exists():
        import subprocess
        python_exe = sys.executable
        subprocess.run([python_exe, str(nolan_script), "--topic", topic])
    else:
        logger.error(f"Nolan Director script not found at {nolan_script}")


def run_video_phase_2(max_items: int | None = None, image_stem: str | None = None) -> None:
    """Execute Video Phase 2: Video Director of Photography."""
    logger.info("--- Starting Video Phase 2: Video Director (Gemini Vision 4D Temporal Prompts) ---")
    from src.analyzer.video_director import run_video_director, synthesize_prompts_for_image_stem
    if image_stem:
        synthesize_prompts_for_image_stem(image_stem)
    else:
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
    parser.add_argument("--narration", action="store_true", help="Generate AI voice narration via CosyVoice on RunningHub")
    parser.add_argument("--script", type=str, default=None, help="Script text for CosyVoice narration")
    parser.add_argument("--emotion", type=str, default=None, help="Emotion and tone instruction for CosyVoice")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed for CosyVoice (default: 1.0)")
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

    # Options for Phase 2
    p2_group = parser.add_argument_group("Phase 2 Options")
    p2_group.add_argument(
        "--director-mode",
        default=os.getenv("DIRECTOR_DEFAULT_MODE", "auto"),
        choices=["commercial", "technical", "auto"],
        help="Art Director prompt mode: commercial (B2B lifestyle), technical (7 Image Codes), or auto",
    )

    # Options for Phase 3
    p3_group = parser.add_argument_group("Phase 3 Options")
    p3_group.add_argument("--account", type=int, default=1, choices=[1, 2, 3], help="RunningHub Account: 1 (Raw Producer), 2 (SeedVR 8K Upscaler), or 3 (Video 4K Generator & Upscaler)")
    p3_group.add_argument("--node", type=int, default=None, help="Output Node ID (default: 121 for Conta 1, 55 for Conta 2)")
    p3_group.add_argument("--batch-size", type=int, default=210, help="Number of prompts per batch (default: 210)")
    p3_group.add_argument("--batches", type=int, default=1, help="Number of consecutive batches to process in Phase 3 (default: 1)")
    p3_group.add_argument("--all-batches", action="store_true", help="Process all remaining pending batches until the prompt queue is exhausted")
    p3_group.add_argument("--upload-wait-sec", type=int, default=int(os.getenv("RUNNINGHUB_IMAGE_UPLOAD_WAIT_SEC", "30")), help="Seconds to wait after uploading image to Load Image node before clicking execute (default: 30)")
    p3_group.add_argument("--execute-mode", default=None, choices=["lite_plus", "ultra", "standard"], help="Execution tier button: lite_plus (middle - default for all workflows) or ultra (right). Note: standard is prohibited and automatically redirected to lite_plus.")

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
    video_group.add_argument("--input-image", type=Path, default=None, help="Reference image path for video generation (Node #164)")
    video_group.add_argument("--video-prompt", type=str, default=None, help="Custom prompt text for video generation (Node #17)")
    video_group.add_argument("--image-stem", type=str, default=None, help="Specific image stem for I2V prompt synthesis")
    video_group.add_argument("--t2v", action="store_true", help="Execute DarkFactory Text-to-Video (T2V) Cinema Engine for YouTube Dark channels")
    video_group.add_argument("--t2v-archetype", choices=["cold_war_espionage", "cyber_warfare", "deep_space_scifi", "all"], default="all", help="Narrative archetype for T2V synthesis (default: all)")
    video_group.add_argument("--t2v-export", action="store_true", help="Export formatted queues for MiniMax H3 and Google Veo 2")
    video_group.add_argument("--t2v-title", type=str, default=None, help="Title for custom dual-shot scene")
    video_group.add_argument("--t2v-beat", type=str, default=None, help="Narrative story beat for custom dual-shot scene")
    video_group.add_argument("--nolan-direct", action="store_true", help="Execute Christopher Nolan Showrunner Engine to direct a dark historical documentary episode")
    video_group.add_argument("--nolan-topic", type=str, default="1983 Soviet nuclear false alarm incident", help="Historical topic to direct with Nolan non-linear methodology")
    video_group.add_argument("--youtube-boost", action="store_true", help="Execute YouTube Algorithm Booster (MLA, chapters, tri-variant thumbnails, series playlist)")
    video_group.add_argument("--youtube-compliance", action="store_true", help="Execute YouTube Compliance QC and Self-Certification Pre-Rater for Green Dollar Sign")
    video_group.add_argument("--youtube-title", type=str, default="The 1983 Soviet Glitch: 20 Minutes to Armageddon", help="Title for YouTube master optimization package")
    video_group.add_argument("--youtube-desc", type=str, default="A detailed historical Cold War documentary investigating Serpukhov-15 declassified telemetry.", help="Description for YouTube package")
    video_group.add_argument("--youtube-duration", type=float, default=600.0, help="Video duration in seconds for YouTube package calculation")
    video_group.add_argument("--cinematic-profiles", action="store_true", help="List all Hollywood/35mm film emulation look profiles available")
    video_group.add_argument("--cinematic-grade", type=str, default=None, choices=["kodak_2383", "fuji_eterna", "bleach_bypass", "oppenheimer_mono", "cold_war_noir", "cyber_tactical"], help="Apply Hollywood cinematic color grade and film grain")
    video_group.add_argument("--cinematic-grain", type=float, default=None, help="Custom film grain strength (0.0 to 1.0)")
    video_group.add_argument("--cinematic-letterbox", action="store_true", help="Apply 2.39:1 CinemaScope anamorphic matte")
    video_group.add_argument("--video-in", type=str, default=None, help="Input video file path for cinematic processing or pacing analysis")
    video_group.add_argument("--video-out", type=str, default=None, help="Output video file path for cinematic processing")
    video_group.add_argument("--analyze-pacing", type=str, default=None, help="Analyze video pacing (MSL, Cuts Per Minute, Tension Score) for a video file")
    video_group.add_argument("--export-otio", action="store_true", help="Export universal OpenTimelineIO (.otio) project for DaVinci Resolve Studio")
    video_group.add_argument("--otio-title", type=str, default="DarkFactory_Master_Cut", help="Title for OTIO project")
    video_group.add_argument("--tactical-hud", action="store_true", help="Generate tactical military radar HUD overlay PNG")
    video_group.add_argument("--tactical-stamp", action="store_true", help="Generate declassified TOP SECRET stamp overlay PNG")
    video_group.add_argument("--dop-plan", action="store_true", help="Synthesize Hollywood Director of Photography (DoP) & Composition Plan")
    video_group.add_argument("--dop-title", type=str, default="Nuclear Bunker False Alarm", help="Title for DoP shot plan")
    video_group.add_argument("--dop-lens", type=str, default="cooke_anamorphic_i", choices=["panavision_c_series", "cooke_anamorphic_i", "arri_master_anamorphic", "zeiss_supreme_prime", "leica_summilux_c", "arri_signature_75mm", "laowa_probe_24mm"], help="Optical cinema lens family")
    video_group.add_argument("--dop-comp", type=str, default="rule_of_thirds", choices=["rule_of_thirds", "golden_spiral", "kubrick_one_point", "dutch_angle", "dirty_single", "low_angle_oppression", "high_angle_vuln"], help="Compositional framing geometry")
    video_group.add_argument("--dop-lighting", type=str, default="8_to_1", choices=["16:1", "8_to_1", "4_to_1", "2_to_1"], help="Key-to-Fill chiaroscuro lighting ratio")
    video_group.add_argument("--audit-keyframe", type=str, default=None, help="Audit keyframe composition, rule of thirds adherence, and render visual guides")
    video_group.add_argument("--extract-keyframes", type=str, default=None, help="Extract strategic cinematic keyframes (Opening, Golden Ratio, Climax) from a video")
    video_group.add_argument("--list-palettes", action="store_true", help="List all calibrated 60-30-10 cinematic color psychology palettes")
    video_group.add_argument("--color-palette", type=str, default=None, choices=["cold_war_paranoia", "nuclear_dread_siren", "cyber_espionage", "deep_space_void", "bio_pathogen_hazard", "gordon_willis_noir", "fincher_muted_sage"], help="Synthesize 60-30-10 color psychology prompt clause")
    video_group.add_argument("--audit-palette", type=str, default=None, help="Audit keyframe 60-30-10 color distribution via K-Means clustering and render swatch card")
    video_group.add_argument("--render-motion-hud", action="store_true", help="Render deterministic HyperFrames/Anatomy motion overlay or B2B 4K loop")
    video_group.add_argument("--motion-template", type=str, default="tactical_hud", help="Motion template name (e.g. tactical_hud, anatomy_mechanical, saas_fintech_telemetry_ui)")
    video_group.add_argument("--motion-title", type=str, default="CLASSIFIED TELEMETRY UNIT", help="Primary headline for HyperFrames overlay")
    video_group.add_argument("--motion-subtitle", type=str, default="SIGNAL ARCHIVE 1961", help="Secondary subtitle for HyperFrames overlay")
    video_group.add_argument("--preview-20s", action="store_true", help="Enforce deterministic <=20s preview gate during motion render")
    video_group.add_argument("--yt-lint", action="store_true", help="Run YouTube title/thumbnail/chapters/retention closed-loop linter")
    video_group.add_argument("--yt-title", type=str, default="Why The Secret 1961 Archive Stayed Buried", help="YouTube title to audit with --yt-lint")
    video_group.add_argument("--yt-thumb", type=str, default="LEAKED BLUEPRINT", help="YouTube thumbnail overlay text to audit with --yt-lint")
    video_group.add_argument("--yt-retention-csv", type=str, default=None, help="Optional YouTube retention CSV file or inline data")
    video_group.add_argument("--unit-economics", action="store_true", help="Print B2B niche unit economics, break-even, and ROI rankings")
    video_group.add_argument("--research-topic", type=str, default=None, help="Fetch public-domain dossier facts & PD media assets (Wikipedia/Wikimedia/IA/NASA)")

    # Google Flow Industrial API Options
    flow_group = parser.add_argument_group("Google Flow Industrial API Options")
    flow_group.add_argument("--flow", action="store_true", help="Execute Google Flow Industrial API commands")
    flow_group.add_argument("--flow-login", action="store_true", help="Launch interactive 1-click Google login for Flow")
    flow_group.add_argument("--flow-status", action="store_true", help="Check Google Flow session status")
    flow_group.add_argument("--flow-serve", action="store_true", help="Start Google Flow FastAPI REST server")
    flow_group.add_argument("--flow-port", type=int, default=8000, help="Port for Google Flow API server (default: 8000)")
    flow_group.add_argument("--flow-generate", type=str, default=None, help="Cinematic prompt to generate via Google Flow")
    flow_group.add_argument("--flow-mode", type=str, default=None, choices=["t2v", "t2i", "i2v"], help="Google Flow mode: t2v, t2i, i2v")
    flow_group.add_argument("--flow-model", type=str, default="veo-3.1-quality", help="Google Flow model: veo-3.1-quality, veo-3.1-fast, veo-3.1-lite, omni-1.2-flash, imagen-3.0")
    flow_group.add_argument("--flow-ratio", type=str, default="16:9", help="Google Flow aspect ratio: 16:9, 9:16, 1:1, 4:3, 2.39:1")
    flow_group.add_argument("--flow-duration", type=int, default=8, help="Google Flow video duration (8s for Veo 3.1, 5s for Omni)")
    flow_group.add_argument("--flow-variations", type=int, default=1, help="Google Flow variations count (1, 2, or 4)")
    flow_group.add_argument("--flow-upscale", type=str, default="2k", choices=["1k", "2k", "4k"], help="Target upscale resolution: 1k, 2k, or 4k (default: 2k)")
    flow_group.add_argument("--flow-no-upscale", action="store_true", help="Skip Google Flow automatic upscale")
    flow_group.add_argument("--flow-strip-audio", action="store_true", help="Strip audio track (-an) for stock upload")
    flow_group.add_argument("--flow-project-name", type=str, default=None, help="Custom project title for Google Flow")
    flow_group.add_argument("--flow-process-queue", action="store_true", help="Process pending prompts from google_veo_queue.json via Google Flow")

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

    # Google Flow Industrial API Command Dispatch
    if (
        getattr(args, "flow", False)
        or getattr(args, "flow_serve", False)
        or getattr(args, "flow_login", False)
        or getattr(args, "flow_status", False)
        or getattr(args, "flow_generate", None)
        or getattr(args, "flow_process_queue", False)
    ):
        from src.integrations.google_flow.cli import main_cli
        cli_args = []
        if getattr(args, "flow_login", False):
            cli_args.append("--login")
        elif getattr(args, "flow_status", False):
            cli_args.append("--status")
        elif getattr(args, "flow_serve", False):
            cli_args.extend(["--serve", "--port", str(getattr(args, "flow_port", 8000))])
        elif getattr(args, "flow_generate", None):
            cli_args.extend([
                "--generate", args.flow_generate,
                "--model", getattr(args, "flow_model", "veo-2.0"),
                "--ratio", getattr(args, "flow_ratio", "16:9"),
                "--duration", str(getattr(args, "flow_duration", 5)),
                "--variations", str(getattr(args, "flow_variations", 1)),
                "--upscale", getattr(args, "flow_upscale", "2k"),
            ])
            if getattr(args, "flow_mode", None):
                cli_args.extend(["--mode", args.flow_mode])
            if getattr(args, "flow_project_name", None):
                cli_args.extend(["--project-name", args.flow_project_name])
            if getattr(args, "flow_no_upscale", False):
                cli_args.append("--no-upscale")
            if getattr(args, "flow_strip_audio", False):
                cli_args.append("--strip-audio")
        elif getattr(args, "flow_process_queue", False):
            cli_args.append("--process-queue")
        else:
            cli_args.append("--status")
        main_cli(cli_args)
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

    if getattr(args, "narration", False):
        from src.factory.runninghub_bot import run_narration_bot
        script = getattr(args, "script", None) or "At 12:15 AM on September 26, 1983, a red siren illuminated a top-secret Soviet bunker outside Moscow..."
        emotion = getattr(args, "emotion", None)
        speed = getattr(args, "speed", 1.0)
        logger.info("🎙️ Disparando CosyVoice Narration Bot via RunningHub...")
        res = run_narration_bot(script=script, emotion=emotion, speed=speed)
        logger.info(f"🏁 Benchmark Narração: {res}")
        return

    if getattr(args, "t2v", False):
        run_darkfactory_t2v(
            archetype=getattr(args, "t2v_archetype", "all"),
            export_only=getattr(args, "t2v_export", False),
            custom_title=getattr(args, "t2v_title", None),
            custom_beat=getattr(args, "t2v_beat", None),
        )
        return

    if getattr(args, "nolan_direct", False):
        run_nolan_director(topic=getattr(args, "nolan_topic", "1983 Soviet nuclear false alarm incident"))
        return

    if getattr(args, "youtube_boost", False):
        from src.video.youtube_booster import run_youtube_booster_cli
        run_youtube_booster_cli(
            title=getattr(args, "youtube_title", "The 1983 Soviet Glitch: 20 Minutes to Armageddon"),
            description=getattr(args, "youtube_desc", "A detailed historical Cold War documentary."),
            duration=getattr(args, "youtube_duration", 600.0),
        )
        return

    if getattr(args, "youtube_compliance", False):
        from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge
        bridge = YouTubeAlgorithmBoosterBridge()
        cert = bridge.generate_self_certification_manifest(
            project_id="cli_audit",
            title=getattr(args, "youtube_title", "The 1983 Soviet Glitch"),
            description=getattr(args, "youtube_desc", "Historical documentary."),
        )
        edsa = bridge.evaluate_edsa_framing(
            title=getattr(args, "youtube_title", "The 1983 Soviet Glitch"),
            description=getattr(args, "youtube_desc", "Historical documentary."),
        )
        print("\n==================================================================")
        print("🛡️ YOUTUBE COMPLIANCE & EDSA SELF-CERTIFICATION REPORT")
        print("==================================================================")
        print(f"  • Projected Monetization: {cert.get('projected_monetization_status')}")
        print(f"  • Rating Accuracy Tier:   {cert.get('rating_accuracy_tier')}")
        print(f"  • EDSA Protection:        {edsa.get('status')} (Score: {edsa.get('edsa_score')}/100)")
        anchors = edsa.get('anchors_detected', [])
        print(f"  • Anchors Detected:       {', '.join(anchors)}\n")
        return

    if getattr(args, "cinematic_profiles", False):
        from src.video.cinematic_color import CinematicColorGrader
        grader = CinematicColorGrader()
        profiles = grader.list_profiles()
        print("\n==================================================================")
        print("🎬 DARKFACTORY CINEMATIC COLOR SCIENCE (35MM FILM PROFILES)")
        print("==================================================================")
        for p in profiles:
            print(f"  • [{p['id'].upper()}] {p['name']}")
            print(f"    - Diretor / Vibe: {p['director_vibe']}")
            print(f"    - Descrição:      {p['description']}")
            print(f"    - Grão Padrão:    {int(p['recommended_grain'] * 100)}% film grain\n")
        return

    if getattr(args, "cinematic_grade", None):
        profile = getattr(args, "cinematic_grade")
        in_file = getattr(args, "video_in", None)
        out_file = getattr(args, "video_out", None) or f"data/final/videos/{profile}_graded.mp4"
        if not in_file:
            print("[ERRO] Informe o arquivo de entrada via --video-in <caminho.mp4>")
            return
        from src.video.cinematic_color import CinematicColorGrader
        grader = CinematicColorGrader()
        ok = grader.apply_grade(
            input_path=in_file,
            output_path=out_file,
            profile=profile,
            film_grain=True,
            grain_strength=getattr(args, "cinematic_grain", None),
            letterbox_239=getattr(args, "cinematic_letterbox", False),
        )
        if ok:
            print(f"\n✅ Color grading '{profile}' aplicado com sucesso: {out_file}")
        else:
            print(f"\n❌ Falha ao aplicar color grading em: {in_file}")
        return

    if getattr(args, "analyze_pacing", None):
        video_to_analyze = getattr(args, "analyze_pacing")
        from src.video.pacing_analyzer import CinematicPacingAnalyzer
        analyzer = CinematicPacingAnalyzer()
        report = analyzer.analyze_pacing(video_to_analyze)
        print("\n==================================================================")
        print("⏱️ CINEMATIC PACING & MONTAGE RHYTHM REPORT (THE EDITOR'S BRAIN)")
        print("==================================================================")
        print(f"  • Vídeo Analisado:       {report.video_path}")
        print(f"  • Duração Total:         {report.total_duration_sec:.2f}s ({report.total_shots} planos)")
        print(f"  • Mean Shot Length (MSL): {report.mean_shot_length:.2f}s por plano")
        print(f"  • Cuts Per Minute (CPM): {report.cuts_per_minute:.1f} cortes/min")
        print(f"  • Arquétipo de Pacing:   {report.pacing_archetype.upper()}")
        print(f"  • Tension Pacing Score:  {report.tension_score}/100")
        print(f"  • Penalidade Monotonia:  -{report.monotony_penalty:.1f} pts\n")
        return

    if getattr(args, "export_otio", False):
        from src.video.otio_exporter import UniversalTimelineExporter, TimelineClipRef, TimelineMarker
        exporter = UniversalTimelineExporter(fps=24.0)
        # Monta timeline com as tomadas da fila T2V
        clips = [
            TimelineClipRef(name="Shot_A_Tension_Lead", media_path="data/final/videos/shot_a_tension.mp4", duration_sec=5.0),
            TimelineClipRef(name="Shot_B_Tactical_Macro", media_path="data/final/videos/shot_b_macro.mp4", duration_sec=4.5),
        ]
        markers = [
            TimelineMarker(name="00:00 - The Serpukhov Glitch", timecode_sec=0.0, color="RED"),
            TimelineMarker(name="00:05 - The False Alarm Climax", timecode_sec=5.0, color="YELLOW"),
        ]
        out_otio = exporter.export_to_file(
            output_path="data/processed/davinci_resolve_timeline.otio",
            timeline_name=getattr(args, "otio_title", "DarkFactory_Master_Cut"),
            video_clips=clips,
            markers=markers,
        )
        print(f"\n✅ Linha do tempo OpenTimelineIO (.otio) exportada com sucesso: {out_otio}")
        print("   -> Importe diretamente no DaVinci Resolve Studio (File > Import > Timeline...)")
        return

    if getattr(args, "tactical_hud", False):
        from src.video.tactical_graphics import TacticalGraphicsEngine
        t_engine = TacticalGraphicsEngine()
        hud_path = t_engine.create_tactical_hud_overlay("data/processed/tactical_hud_overlay.png")
        print(f"\n✅ HUD tático de radar militar gerado em: {hud_path}")
        return

    if getattr(args, "tactical_stamp", False):
        from src.video.tactical_graphics import TacticalGraphicsEngine
        t_engine = TacticalGraphicsEngine()
        stamp_path = t_engine.create_declassified_stamp_overlay("data/processed/declassified_stamp.png")
        print(f"\n✅ Carimbo de documento desclassificado gerado em: {stamp_path}")
        return

    if getattr(args, "dop_plan", False):
        from src.video.cinematography_dop import (
            CinematographyEngine,
            LensOpticsType,
            CompositionGeometry,
            LightingRatio,
        )
        engine = CinematographyEngine()
        plan = engine.build_shot_plan(
            shot_name=getattr(args, "dop_title", "Nuclear Bunker False Alarm"),
            lens_type=LensOpticsType(getattr(args, "dop_lens", "cooke_anamorphic_i")),
            composition=CompositionGeometry(getattr(args, "dop_comp", "rule_of_thirds")),
            lighting_ratio=LightingRatio(getattr(args, "dop_lighting", "8_to_1")),
        )
        print("\n==================================================================")
        print("🎬 DIRECTOR OF PHOTOGRAPHY (DoP) & COMPOSITION BLUEPRINT")
        print("==================================================================")
        print(f"  • Tomada / Cena:        {plan.shot_name}")
        print(f"  • Câmera:               {plan.camera_body}")
        print(f"  • Lente Óptica:         {plan.lens.model_name} ({plan.lens.focal_length_mm}mm T{plan.lens.t_stop})")
        print(f"  • Anamórfica / Squeeze: {'SIM (2.39:1 CinemaScope)' if plan.lens.anamorphic else 'NÃO (Esférica Prime)'}")
        print(f"  • Bokeh & Flares:       {plan.lens.bokeh_shape} | {plan.lens.flare_character}")
        print(f"  • Geometria de Quadro:  {plan.composition.value.upper()}")
        print(f"  • Razão Chiaroscuro:    {plan.lighting_ratio.value} (Key {plan.kelvin_key}K vs Fill {plan.kelvin_fill}K)")
        print(f"  • Shutter & Movimento:  {plan.shutter_angle} | {plan.camera_movement}")
        print("\n  [DoP Prompt Injector]:")
        print(f"  \"{plan.to_dop_prompt()}\"\n")
        return

    if getattr(args, "audit_keyframe", None):
        img_path = getattr(args, "audit_keyframe")
        from src.video.cinematography_dop import CinematographyEngine
        engine = CinematographyEngine()
        audit = engine.audit_keyframe_composition(img_path, generate_annotated_grid=True)
        print("\n==================================================================")
        print("📐 KEYFRAME COMPOSITION & DoP COMPUTER VISION AUDIT")
        print("==================================================================")
        print(f"  • Imagem Auditada:           {audit.image_path}")
        print(f"  • Resolução:                 {audit.width} x {audit.height}")
        print(f"  • Rule of Thirds Score:      {audit.rule_of_thirds_score:.1f}% de alinhamento")
        print(f"  • Contraste Chiaroscuro:     {audit.chiaroscuro_contrast_ratio}:1")
        print(f"  • Balanço Quente/Frio:       {audit.warm_cold_kelvin_bias.upper()}")
        print(f"  • Equilíbrio Horizontal:     {audit.visual_balance_horizontal:+.3f}")
        if audit.annotated_guide_path:
            print(f"  • Guia Visual Anotada:       {audit.annotated_guide_path}")
        print("==================================================================\n")
        return

    if getattr(args, "extract_keyframes", None):
        video_path = getattr(args, "extract_keyframes")
        from src.video.cinematography_dop import CinematographyEngine
        engine = CinematographyEngine()
        out_dir = Path("data/processed/keyframes")
        kfs = engine.extract_cinematic_keyframes(video_path, out_dir)
        print(f"\n✅ {len(kfs)} keyframes cinematográficos extraídos em: {out_dir}")
        for k in kfs:
            audit = engine.audit_keyframe_composition(k, generate_annotated_grid=True)
            print(f"  • [{k.name}] Thirds: {audit.rule_of_thirds_score:.1f}% | Contrast: {audit.chiaroscuro_contrast_ratio}:1 | Guide: {audit.annotated_guide_path}")
        return

    if getattr(args, "list_palettes", False):
        from src.video.color_psychology import ColorPsychologyEngine
        engine = ColorPsychologyEngine()
        palettes = engine.list_palettes()
        print("\n==================================================================")
        print("🎨 CINEMATIC COLOR PSYCHOLOGY & 60-30-10 PALETTE REGISTRY")
        print("==================================================================")
        for p in palettes:
            print(f"  • [{p['id'].upper()}] {p['name']} ({p['harmony'].upper()})")
            print(f"    - Tese Semiótica: {p['psychological_thesis']}")
            print(f"    - 60% Dominante:  {p['dominant_60']['name']} ({p['dominant_60']['hex']})")
            print(f"    - 30% Secundária: {p['secondary_30']['name']} ({p['secondary_30']['hex']})")
            print(f"    - 10% Acento:     {p['accent_10']['name']} ({p['accent_10']['hex']})")
            print(f"    - Referências:    {p['director_references']}\n")
        return

    if getattr(args, "color_palette", None):
        pal_id = getattr(args, "color_palette")
        from src.video.color_psychology import ColorPsychologyEngine
        engine = ColorPsychologyEngine()
        pal = engine.get_palette(pal_id)
        print("\n==================================================================")
        print(f"🎨 60-30-10 COLOR PROMPT CLAUSE: {pal.name.upper()}")
        print("==================================================================")
        print(f"  • Harmonia:      {pal.harmony.value.upper()}")
        print(f"  • 60% Base:      {pal.dominant_60.name} ({pal.dominant_60.hex_code})")
        print(f"  • 30% Estrutura: {pal.secondary_30.name} ({pal.secondary_30.hex_code})")
        print(f"  • 10% Acento:    {pal.accent_10.name} ({pal.accent_10.hex_code})")
        print("\n  [Color Psychology Prompt Injector]:")
        print(f"  \"{pal.to_color_prompt()}\"\n")
        return

    if getattr(args, "audit_palette", None):
        img_to_audit = getattr(args, "audit_palette")
        from src.video.color_psychology import ColorPsychologyEngine
        engine = ColorPsychologyEngine()
        audit = engine.audit_keyframe_palette(img_to_audit, render_swatch_card=True)
        print("\n==================================================================")
        print("🎨 60-30-10 K-MEANS COLOR AUDIT & PSYCHOLOGICAL MAPPING")
        print("==================================================================")
        print(f"  • Imagem Auditada:           {audit.image_path}")
        print(f"  • 60% Base Dominante Real:   {audit.dominant_pct:.1f}% (Hex: {audit.dominant_color_hex})")
        print(f"  • 30% Secundária Real:       {audit.secondary_pct:.1f}% (Hex: {audit.secondary_color_hex})")
        print(f"  • 10% Acento Punctum Real:   {audit.accent_pct:.1f}% (Hex: {audit.accent_color_hex})")
        print(f"  • Score de Aderência 60-30-10: {audit.rule_60_30_10_adherence_score:.1f}/100")
        print(f"  • Arquétipo Mais Próximo:    {audit.closest_archetype.upper()}")
        if audit.annotated_palette_card_path:
            print(f"  • Cartela Visual Anotada:    {audit.annotated_palette_card_path}")
        print("==================================================================\n")
        return

    if args.seasonal:
        show_seasonal_radar()
        return

    if getattr(args, "render_motion_hud", False):
        from src.video.hyperframes_engine import HyperFramesMotionEngine
        engine = HyperFramesMotionEngine()
        if getattr(args, "preview_20s", False):
            res = engine.render_preview_gate(
                template=args.motion_template,
                title=args.motion_title,
                subtitle=args.motion_subtitle,
                force_procedural=True,
            )
        else:
            res = engine.render_motion_clip(
                template=args.motion_template,
                title=args.motion_title,
                subtitle=args.motion_subtitle,
                force_procedural=True,
            )
        print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
        return

    if getattr(args, "yt_lint", False):
        from src.video.youtube_booster import YouTubeAlgorithmBoosterBridge
        bridge = YouTubeAlgorithmBoosterBridge()
        lint_out = bridge.lint_title_thumbnail_pair(title=args.yt_title, thumbnail_text=args.yt_thumb)
        retention_out = bridge.parse_retention_csv(args.yt_retention_csv) if args.yt_retention_csv else None
        print(json.dumps({"title_thumbnail_lint": lint_out, "retention_audit": retention_out}, indent=2, ensure_ascii=False))
        return

    if getattr(args, "unit_economics", False):
        from src.analyzer.unit_economics import UnitEconomicsCalculator
        calc = UnitEconomicsCalculator()
        print(json.dumps(calc.recommend_priority_niches(), indent=2, ensure_ascii=False))
        return

    if getattr(args, "research_topic", None):
        from src.video.research_engine import PublicDomainResearchEngine
        engine = PublicDomainResearchEngine()
        pack = engine.build_dossier(args.research_topic)
        print(json.dumps(pack.to_dict(), indent=2, ensure_ascii=False))
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
            run_video_phase_2(max_items=args.max_items, image_stem=getattr(args, "image_stem", None))
        else:
            run_phase_2(director_mode=getattr(args, "director_mode", "auto"))
    elif args.phase == 3:
        is_vid = bool(args.video or args.asset_type == "video" or args.account == 3)
        run_phase_3(
            account=3 if is_vid else args.account,
            node=args.node,
            batches=args.batches,
            all_batches=args.all_batches,
            batch_size=args.batch_size,
            is_video=is_vid,
            input_image=getattr(args, "input_image", None),
            prompt_text=getattr(args, "video_prompt", None),
            upload_wait_sec=getattr(args, "upload_wait_sec", 30),
            execute_mode=getattr(args, "execute_mode", None),
        )
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
