#!/usr/bin/env python3
"""StockCont 24/7 Autonomous Production Daemon

Continuous orchestrator that runs the end-to-end microstock pipeline:
  1. Buffer Management: Replenishes prompts (Phase 1 & 2) when pending buffer is low.
  2. The Factory Conta 1 (Raw Producer): Renders raw 4K batches in RunningHub.
  3. Quality Control (QC): Evaluates images with Gemini Vision and packages in packs of 10.
  4. The Factory Conta 2 (SeedVR 8K Upscaler): Upscales approved packs.
  5. The Cataloger (Phase 4): Embeds IPTC/EXIF 300 DPI metadata and syncs to Google Drive.
  6. The Distributor (Phase 5): Enforces rolling 7-day weekly quotas per agency.
  7. Smart Vault & Auto-Purge: Safely removes local 8K JPGs from SSD only after
     confirmed upload to ALL configured agencies AND backup in Google Drive.
  8. Resilient Watchdog & Heartbeat: Atomic state persistence in data/processed/daemon_state.json.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv

# UTF-8 encoding safeguard on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

PROCESSED_DIR = BASE_DIR / "data" / "processed"
STAGING_IMAGES_DIR = BASE_DIR / "data" / "staging" / "images"
FINAL_IMAGES_DIR = BASE_DIR / "data" / "final" / "images"

DAEMON_STATE_FILE = PROCESSED_DIR / "daemon_state.json"
UPLOAD_HISTORY_FILE = PROCESSED_DIR / "upload_history.json"
BACKUP_HISTORY_FILE = PROCESSED_DIR / "gdrive_backup_history.json"
PURGED_HISTORY_FILE = PROCESSED_DIR / "purged_history.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] [Daemon] - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("StockContDaemon")


class StockContDaemon:
    """Master 24/7 pipeline supervisor with buffer pacing and rolling weekly quota enforcement."""

    def __init__(
        self,
        pacing_interval: int = 300,
        min_prompt_buffer: int = 50,
        dry_run: bool = False,
    ) -> None:
        self.pacing_interval = max(30, pacing_interval)
        self.min_prompt_buffer = max(10, min_prompt_buffer)
        self.dry_run = dry_run

        self.is_running = False
        self.is_paused = False
        self._stop_requested = False
        self.cycles_completed = 0
        self.consecutive_errors = 0
        self.started_at: Optional[datetime] = None

    def update_state(
        self,
        current_phase: str,
        current_action: str,
        last_error: Optional[str] = None,
    ) -> None:
        """Atomically persist daemon state and heartbeat (ADR-02)."""
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        now_iso = datetime.now(timezone.utc).isoformat()

        from src.uploader.ftp_distributor import get_all_quota_status
        quotas_summary = get_all_quota_status()
        vault_summary = self.get_vault_stats()

        status_str = "stopped"
        if self.is_running:
            status_str = "paused" if self.is_paused else "running"

        state_data = {
            "status": status_str,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_heartbeat": now_iso,
            "cycles_completed": self.cycles_completed,
            "current_phase": current_phase,
            "current_action": current_action,
            "pacing_interval_seconds": self.pacing_interval,
            "min_prompt_buffer": self.min_prompt_buffer,
            "dry_run": self.dry_run,
            "consecutive_errors": self.consecutive_errors,
            "last_error": last_error,
            "quotas": quotas_summary,
            "vault": vault_summary,
        }

        tmp_file = DAEMON_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            tmp_file.replace(DAEMON_STATE_FILE)
        except Exception as e:
            logger.warning(f"Erro ao salvar daemon_state.json: {e}")

    def get_vault_stats(self) -> Dict[str, int]:
        """Compute statistics for assets stored in local vault and Google Drive."""
        from src.uploader.ftp_distributor import get_available_agencies, load_upload_history
        from src.backup.gdrive_backup import load_backup_history

        all_agencies = get_available_agencies()
        configured_keys = [k for k, ag in all_agencies.items() if ag.is_configured and k != "alamy"]

        local_files = []
        if FINAL_IMAGES_DIR.exists():
            local_files = list(FINAL_IMAGES_DIR.glob("*.jpg")) + list(FINAL_IMAGES_DIR.glob("*.jpeg"))

        upload_hist = load_upload_history()
        backup_hist = load_backup_history()

        pending_dist = 0
        fully_dist = 0

        for f in local_files:
            history_entry = upload_hist.get(f.name, {})
            # Check if all active agencies have received this asset
            missing_any = any(k not in history_entry for k in configured_keys)
            if missing_any:
                pending_dist += 1
            else:
                fully_dist += 1

        purged_count = 0
        if PURGED_HISTORY_FILE.exists():
            try:
                with open(PURGED_HISTORY_FILE, "r", encoding="utf-8") as pf:
                    purged_data = json.load(pf)
                    purged_count = len(purged_data)
            except Exception:
                pass

        return {
            "total_local_assets": len(local_files),
            "pending_distribution": pending_dist,
            "fully_distributed": fully_dist,
            "gdrive_backed_up": len(backup_hist),
            "purged_from_local_ssd": purged_count,
        }

    def smart_auto_purge(self) -> int:
        """Purge local 8K JPGs only when fully uploaded to all active agencies AND backed up in GDrive."""
        from src.uploader.ftp_distributor import get_available_agencies, load_upload_history
        from src.backup.gdrive_backup import GoogleDriveBackup, load_backup_history

        gdrive = GoogleDriveBackup()
        if not gdrive.is_configured:
            logger.debug("Google Drive não configurado. Auto-purga suspensa para prevenir perda de dados.")
            return 0

        all_agencies = get_available_agencies()
        configured_keys = [k for k, ag in all_agencies.items() if ag.is_configured and k != "alamy"]
        if not configured_keys:
            return 0

        if not FINAL_IMAGES_DIR.exists():
            return 0

        upload_hist = load_upload_history()
        backup_hist = load_backup_history()

        purged_history: Dict[str, Any] = {}
        if PURGED_HISTORY_FILE.exists():
            try:
                with open(PURGED_HISTORY_FILE, "r", encoding="utf-8") as f:
                    purged_history = json.load(f)
            except Exception:
                purged_history = {}

        local_files = list(FINAL_IMAGES_DIR.glob("*.jpg")) + list(FINAL_IMAGES_DIR.glob("*.jpeg"))
        purged_count = 0

        for file_path in local_files:
            fname = file_path.name

            # Condition 1: Must be backed up in Google Drive
            if fname not in backup_hist:
                continue

            # Condition 2: Must be uploaded to all configured agencies
            agency_uploads = upload_hist.get(fname, {})
            all_sent = all(k in agency_uploads for k in configured_keys)
            if not all_sent:
                continue

            # Safe to purge local copy to free SSD space
            try:
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if not self.dry_run:
                    file_path.unlink()
                purged_count += 1
                purged_history[fname] = {
                    "purged_at": datetime.now(timezone.utc).isoformat(),
                    "size_mb": round(file_size_mb, 2),
                    "gdrive_id": backup_hist[fname].get("file_id", ""),
                }
                logger.info(f"  🧹 [AUTO-PURGA] {fname} ({file_size_mb:.1f} MB) liberado do SSD local (100% seguro no Cofre Cloud).")
            except Exception as e:
                logger.warning(f"Erro ao purgar {fname}: {e}")

        if purged_count > 0 and not self.dry_run:
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            tmp_p = PURGED_HISTORY_FILE.with_suffix(".tmp")
            try:
                with open(tmp_p, "w", encoding="utf-8") as f:
                    json.dump(purged_history, f, indent=2, ensure_ascii=False)
                tmp_p.replace(PURGED_HISTORY_FILE)
            except Exception as e:
                logger.error(f"Erro ao salvar histórico de purga: {e}")

        return purged_count

    def execute_single_cycle(self) -> None:
        """Run one end-to-end pipelined iteration of all production phases."""
        logger.info("=" * 68)
        logger.info(f"🔄 INICIANDO CICLO #{self.cycles_completed + 1} DO DAEMON 24/7 (DryRun={self.dry_run})")
        logger.info("=" * 68)

        # -------------------------------------------------------------
        # STEP 1: Buffer Check & Prompt Replenishment (Fases 1 e 2)
        # -------------------------------------------------------------
        self.update_state("Fase 1/2: Buffer Check", "Avaliando estoque de prompts pendentes...")
        from src.factory.prompt_queue import PromptQueueManager
        queue_mgr = PromptQueueManager()
        stats = queue_mgr.get_stats()
        pending_prompts = stats.get("pending", 0)
        staging_count = len(list(STAGING_IMAGES_DIR.glob("*.png"))) if STAGING_IMAGES_DIR.exists() else 0
        approved_zip = BASE_DIR / "data" / "staging" / "approved_batch.zip"
        logger.info(f"📊 Fila de prompts: {pending_prompts} pendentes | Staging: {staging_count} renders brutos (Mínimo buffer: {self.min_prompt_buffer})")

        # Se houver imagens em staging ou pacote pronto para upscale, prioriza avançar a esteira atual
        if staging_count > 0 or approved_zip.exists():
            logger.info(f"⚡ Esteira ativa: {staging_count} renders em staging aguardando QC/Upscale (Conta 2). Processando esteira antes de nova mineração.")
        elif pending_prompts < self.min_prompt_buffer:
            logger.info("⚡ Buffer de prompts baixo e esteira livre! Disparando Fase 1 (Olheiro) e Fase 2 (Diretor de Arte)...")
            try:
                if not self.dry_run:
                    from src.scraper.adobe_stock import scrape_contributor_insights
                    scrape_contributor_insights(content_type="photo", max_items=15, headless=True)
                    from src.analyzer.director import main as director_main
                    director_main()
                else:
                    logger.info("[DryRun] Simulação de Fase 1 e 2 executada.")
            except Exception as e:
                logger.error(f"⚠️ Aviso durante Fase 1/2: {e}")

        # -------------------------------------------------------------
        # STEP 2: The Factory Conta 1 (Raw Producer - Fase 3)
        # -------------------------------------------------------------
        self.update_state("Fase 3: Conta 1", "Verificando geração de renders brutos no RunningHub...")
        stats = queue_mgr.get_stats()
        if stats.get("pending", 0) > 0:
            logger.info(f"🎨 prompts pendentes na fila ({stats['pending']}). Executando Conta 1...")
            try:
                if not self.dry_run:
                    from src.factory.runninghub_bot import run_factory_bot
                    run_factory_bot(account=1, batch_size=min(210, stats["pending"]))
                else:
                    logger.info("[DryRun] Simulação Conta 1 executada.")
            except Exception as e:
                logger.error(f"⚠️ Erro ao executar Conta 1: {e}")
        else:
            logger.info("✓ Conta 1: Nenhum prompt pendente no momento.")

        # -------------------------------------------------------------
        # STEP 3: Quality Control & Packing (QC Automático)
        # -------------------------------------------------------------
        self.update_state("Módulo QC", "Auditando imagens brutas de staging via Gemini Vision...")
        try:
            from src.analyzer.qc_inspector import QCInspector
            inspector = QCInspector()
            inspector.set_config(mode="auto")
            if not self.dry_run:
                inspector.run_batch_qc()
                zip_path, packed = inspector.package_approved_images(max_images=10)
                if zip_path and packed:
                    logger.info(f"📦 Pacote de 10 imagens aprovadas gerado para Conta 2: {zip_path.name}")
            else:
                logger.info("[DryRun] Simulação de QC executada.")
        except Exception as e:
            logger.error(f"⚠️ Erro no Módulo QC: {e}")

        # -------------------------------------------------------------
        # STEP 4: The Factory Conta 2 (SeedVR 8K Upscaler)
        # -------------------------------------------------------------
        self.update_state("Fase 3: Conta 2", "Verificando pacotes aprovados para upscale 8K...")
        approved_zip = BASE_DIR / "data" / "staging" / "approved_batch.zip"
        if approved_zip.exists():
            logger.info("🔍 Pacote approved_batch.zip pronto. Disparando Conta 2 (SeedVR 8K)...")
            try:
                if not self.dry_run:
                    from src.factory.runninghub_bot import run_factory_bot
                    run_factory_bot(account=2, batch_size=10)
                else:
                    logger.info("[DryRun] Simulação Conta 2 executada.")
            except Exception as e:
                logger.error(f"⚠️ Erro ao executar Conta 2: {e}")
        else:
            logger.info("✓ Conta 2: Nenhum pacote zip pendente para upscale no momento.")

        # -------------------------------------------------------------
        # STEP 5: The Cataloger (Fase 4 & Google Drive Backup)
        # -------------------------------------------------------------
        self.update_state("Fase 4: Catalogador", "Injetando metadados IPTC/EXIF e salvando no Cofre Cloud...")
        try:
            if not self.dry_run:
                from src.cataloger.adobe_csv_maker import run_cataloger
                run_cataloger()
                from src.backup.gdrive_backup import GoogleDriveBackup
                gdrive = GoogleDriveBackup()
                if gdrive.is_configured:
                    gdrive.backup_assets()
            else:
                logger.info("[DryRun] Simulação de Fase 4 e Backup executada.")
        except Exception as e:
            logger.error(f"⚠️ Erro no Catalogador / Backup: {e}")

        # -------------------------------------------------------------
        # STEP 6: The Distributor (Fase 5 com Quota Manager)
        # -------------------------------------------------------------
        self.update_state("Fase 5: Distribuidor", "Verificando cotas semanais (Rolling 7D) e despachando...")
        try:
            from src.uploader.quota_manager import QuotaManager
            from src.uploader.ftp_distributor import run_distributor, get_available_agencies

            qm = QuotaManager()
            agencies = get_available_agencies()
            configured = [k for k, ag in agencies.items() if ag.is_configured and k != "alamy"]

            any_quota_available = False
            for k in configured:
                if qm.is_quota_available(k):
                    any_quota_available = True
                    break

            if any_quota_available or self.dry_run:
                run_distributor(target_platform="all", dry_run=self.dry_run, quota_manager=qm)
            else:
                logger.info("⏸️ [COTA ESGOTADA EM TODAS AS PLATAFORMAS] Nenhum slot semanal disponível no momento.")
                logger.info("   Assets preservados no Cofre (Google Drive). A Fase 5 será reativada assim que novas vagas abrirem.")
        except Exception as e:
            logger.error(f"⚠️ Erro na Fase 5: {e}")

        # -------------------------------------------------------------
        # STEP 7: Smart Auto-Purge de SSD
        # -------------------------------------------------------------
        self.update_state("Auto-Purga", "Avaliando liberação de SSD para assets 100% distribuídos...")
        purged = self.smart_auto_purge()
        if purged > 0:
            logger.info(f"✨ Auto-purga concluída: {purged} arquivo(s) liberados do disco local.")

        self.cycles_completed += 1
        self.consecutive_errors = 0
        logger.info(f"🎉 CICLO #{self.cycles_completed} CONCLUÍDO COM SUCESSO!\n")

    def run_forever(self) -> None:
        """Main 24/7 supervisor loop with signal handling and responsive pacing sleep."""
        self.is_running = True
        self.is_paused = False
        self._stop_requested = False
        self.started_at = datetime.now(timezone.utc)

        def handle_signal(sig, frame):
            logger.info(f"\n🛑 Sinal {sig} recebido. Finalizando o daemon com segurança...")
            self._stop_requested = True
            self.is_running = False

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
        except Exception:
            pass

        logger.info("=" * 68)
        logger.info("🚀 STOCKCONT 24/7 AUTONOMOUS PRODUCTION DAEMON INICIADO!")
        logger.info(f"   • Pacing Interval:  {self.pacing_interval} segundos ({self.pacing_interval / 60:.1f} minutos)")
        logger.info(f"   • Buffer de Prompts: Mínimo {self.min_prompt_buffer}")
        logger.info(f"   • Modo Dry-Run:     {self.dry_run}")
        logger.info(f"   • Heartbeat State:  {DAEMON_STATE_FILE}")
        logger.info("=" * 68)

        while not self._stop_requested:
            if self.is_paused:
                self.update_state("Pausado", "Daemon em pausa pelo operador.")
                time.sleep(5)
                continue

            try:
                self.execute_single_cycle()
            except Exception as e:
                self.consecutive_errors += 1
                logger.error(f"❌ Erro crítico no ciclo #{self.cycles_completed + 1}: {e}")
                self.update_state("Erro", f"Erro no ciclo: {e}", last_error=str(e))
                backoff_sleep = min(300, 15 * (2 ** min(self.consecutive_errors, 4)))
                logger.info(f"⏳ Aguardando {backoff_sleep}s antes da auto-recuperação...")
                time.sleep(backoff_sleep)
                continue

            # Pacing sleep with responsive 2-second polling to respond immediately to pause/stop signals
            sleep_start = time.time()
            while (time.time() - sleep_start) < self.pacing_interval and not self._stop_requested and not self.is_paused:
                remaining = int(self.pacing_interval - (time.time() - sleep_start))
                self.update_state("Pacing Sleep", f"Próxima rodada em {remaining}s...")
                time.sleep(2)

        self.is_running = False
        self.update_state("Parado", "Daemon finalizado.")
        logger.info("🏁 Daemon 24/7 finalizado com sucesso.")


def start_daemon(
    interval: int = 300,
    min_buffer: int = 50,
    dry_run: bool = False,
) -> None:
    """Entry point to launch the 24/7 daemon process."""
    daemon = StockContDaemon(
        pacing_interval=interval,
        min_prompt_buffer=min_buffer,
        dry_run=dry_run,
    )
    daemon.run_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StockCont 24/7 Production Daemon")
    parser.add_argument("--interval", type=int, default=300, help="Pacing interval in seconds between cycles (default: 300)")
    parser.add_argument("--min-buffer", type=int, default=50, help="Minimum prompt buffer threshold (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Run in simulation mode without sending actual files or consuming credits")
    args = parser.parse_args()

    start_daemon(interval=args.interval, min_buffer=args.min_buffer, dry_run=args.dry_run)
