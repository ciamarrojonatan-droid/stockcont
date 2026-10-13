#!/usr/bin/env python3
"""StockCont Google Drive Asset Backup Module

Automates continuous backup of generated microstock assets:
  - Final processed images (data/final/images/*.jpg, *.png)
  - Cataloger metadata CSVs (data/processed/adobe_stock_upload.csv)

Supports two complementary backup modes:
  1. Google Drive Cloud API (v3):
     - Service Account JSON (service_account.json or GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON)
     - OAuth 2.0 Credentials (credentials.json / token.json)
     - Automated folder discovery and creation ("StockCont_Backup")
  2. Google Drive Desktop Local Sync:
     - Local filesystem path (e.g., "G:\\Meu Drive\\StockCont" or Google Drive sync folder)

Features:
  - Resumable file uploads for large 4K stock images
  - Atomic ledger (data/processed/gdrive_backup_history.json) preventing duplicate uploads
  - Exponential backoff retry logic on network drops
  - Seamless automatic hook into the pipeline after Phase 4 / Phase 3
"""

import json
import logging
import mimetypes
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# UTF-8 encoding safeguard on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Paths setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

FINAL_IMAGES_DIR = BASE_DIR / "data" / "final" / "images"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CSV_FILE = PROCESSED_DIR / "adobe_stock_upload.csv"
BACKUP_HISTORY_FILE = PROCESSED_DIR / "gdrive_backup_history.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("GDriveBackup")


def load_backup_history() -> Dict[str, Dict[str, Any]]:
    """Load Google Drive backup ledger to avoid re-uploading existing files."""
    if not BACKUP_HISTORY_FILE.exists():
        return {}
    try:
        with open(BACKUP_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Não foi possível ler {BACKUP_HISTORY_FILE.name} ({e}). Criando novo registro.")
        return {}


def save_backup_history(history: Dict[str, Dict[str, Any]]) -> None:
    """Atomically save backup history ledger."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = BACKUP_HISTORY_FILE.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        tmp_file.replace(BACKUP_HISTORY_FILE)
    except Exception as e:
        logger.error(f"Erro ao salvar histórico de backup: {e}")


class GoogleDriveBackup:
    """Handles Google Drive cloud uploads and local sync backups."""

    def __init__(self) -> None:
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        self.service_account_file = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "").strip()
        self.service_account_json = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "").strip()
        self.oauth_creds_file = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "").strip()
        self.oauth_token_file = os.getenv("GOOGLE_DRIVE_TOKEN_FILE", "").strip()
        self.local_sync_path = os.getenv("GOOGLE_DRIVE_LOCAL_PATH", "").strip()

        self._service: Optional[Any] = None
        self._history: Dict[str, Dict[str, Any]] = load_backup_history()

    @property
    def is_configured(self) -> bool:
        """Return True if either Google Drive Cloud API or Local Sync path is configured."""
        has_sa = bool(self.service_account_json or (self.service_account_file and Path(self.service_account_file).exists()))
        has_oauth = bool(self.oauth_creds_file and Path(self.oauth_creds_file).exists())
        has_local = bool(self.local_sync_path and Path(self.local_sync_path).exists())
        return has_sa or has_oauth or has_local

    @property
    def mode(self) -> str:
        """Return human-readable active mode."""
        if self.service_account_json or (self.service_account_file and Path(self.service_account_file).exists()):
            return "api_service_account"
        if self.oauth_creds_file and Path(self.oauth_creds_file).exists():
            return "api_oauth"
        if self.local_sync_path and Path(self.local_sync_path).exists():
            return "local_sync"
        return "unconfigured"

    def get_service(self) -> Optional[Any]:
        """Initialize and return Google Drive API service client."""
        if self._service is not None:
            return self._service

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account, credentials

            creds = None

            # 1. Service Account (Raw JSON string)
            if self.service_account_json:
                try:
                    sa_info = json.loads(self.service_account_json)
                    creds = service_account.Credentials.from_service_account_info(
                        sa_info, scopes=SCOPES
                    )
                    logger.info("🔑 Autenticado com Google Drive via Service Account (JSON no .env).")
                except Exception as e:
                    logger.error(f"Erro ao parsear GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON: {e}")

            # 2. Service Account (File path)
            elif self.service_account_file and Path(self.service_account_file).exists():
                creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=SCOPES
                )
                logger.info(f"🔑 Autenticado com Google Drive via Service Account ({self.service_account_file}).")

            # 3. OAuth 2.0 Credentials / Token
            elif self.oauth_creds_file and Path(self.oauth_creds_file).exists():
                from google_auth_oauthlib.flow import InstalledAppFlow
                token_path = Path(self.oauth_token_file or "token.json")

                if token_path.exists():
                    try:
                        creds = credentials.Credentials.from_authorized_user_file(
                            str(token_path), SCOPES
                        )
                    except Exception:
                        creds = None

                if not creds or not creds.valid:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.oauth_creds_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    with open(token_path, "w", encoding="utf-8") as token_f:
                        token_f.write(creds.to_json())
                    logger.info(f"🔑 Token OAuth salvo em {token_path}.")

            if creds:
                self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
                return self._service

        except ImportError as e:
            logger.error(f"Bibliotecas da Google API ausentes: {e}")
        except Exception as e:
            logger.error(f"Falha na autenticação do Google Drive: {e}")

        return None

    def get_or_create_remote_folder(self, folder_name: str = "StockCont_Backup") -> Optional[str]:
        """Find or create remote Google Drive folder for StockCont backups."""
        if self.folder_id:
            return self.folder_id

        service = self.get_service()
        if not service:
            return None

        try:
            # Query if folder already exists
            query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
            results = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1
            ).execute()
            files = results.get("files", [])

            if files:
                found_id = files[0]["id"]
                logger.info(f"📁 Pasta remota '{folder_name}' encontrada no Google Drive (ID: {found_id}).")
                self.folder_id = found_id
                return found_id

            # Create folder if not found
            metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            created = service.files().create(body=metadata, fields="id").execute()
            new_id = created.get("id")
            logger.info(f"📁 Pasta remota '{folder_name}' criada com sucesso no Google Drive (ID: {new_id})!")
            self.folder_id = new_id
            return new_id

        except Exception as e:
            logger.error(f"Erro ao buscar/criar pasta remota no Google Drive: {e}")
            return None

    def upload_file_cloud(self, file_path: Path, max_retries: int = 3) -> Tuple[bool, Optional[str]]:
        """Upload a single file to Google Drive using the Drive API with resumable upload."""
        service = self.get_service()
        if not service:
            return False, None

        folder_id = self.get_or_create_remote_folder()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        file_metadata: Dict[str, Any] = {"name": file_path.name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True
        )

        for attempt in range(1, max_retries + 1):
            try:
                request = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, size"
                )
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.debug(f"  ⬆️ Upload {file_path.name}: {progress}% concluído...")

                remote_id = response.get("id")
                return True, remote_id

            except Exception as e:
                logger.warning(f"  ⚠️ Falha ao subir {file_path.name} para o Google Drive [Tentativa {attempt}/{max_retries}]: {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        return False, None

    def sync_file_local(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Sync a file to a local Google Drive Desktop folder."""
        dest_dir = Path(self.local_sync_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / file_path.name

        try:
            shutil.copy2(file_path, dest_file)
            return True, str(dest_file)
        except Exception as e:
            logger.error(f"Erro ao copiar {file_path.name} para {dest_dir}: {e}")
            return False, None

    def backup_assets(
        self,
        dry_run: bool = False,
        force: bool = False,
        include_csv: bool = True
    ) -> Dict[str, Any]:
        """Execute full backup of all final assets to Google Drive."""
        logger.info("=" * 65)
        logger.info("☁️ INICIANDO BACKUP DE ASSETS PARA O GOOGLE DRIVE")
        logger.info("=" * 65)

        if not self.is_configured:
            logger.warning("⚠️ GOOGLE DRIVE NÃO CONFIGURADO NO ARQUIVO .ENV!")
            logger.info("Você pode configurar o backup de duas formas simples:")
            logger.info("  1. Google Drive API (Recomendado para automação contínua):")
            logger.info('     GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE="service_account.json"')
            logger.info("     (ou GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON com o conteúdo da chave)")
            logger.info('     GOOGLE_DRIVE_FOLDER_ID="id_da_pasta_no_drive" (Opcional)')
            logger.info("  2. Sincronização Local (Google Drive Desktop instalado):")
            logger.info('     GOOGLE_DRIVE_LOCAL_PATH="G:\\Meu Drive\\StockCont"')
            logger.info("\nVeja mais detalhes em state.md e .env.example.")
            return {"status": "unconfigured", "uploaded": 0, "skipped": 0, "failed": 0}

        # Collect candidate assets
        assets: List[Path] = []
        if FINAL_IMAGES_DIR.exists():
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                assets.extend(sorted(FINAL_IMAGES_DIR.glob(ext)))

        if include_csv and CSV_FILE.exists():
            assets.append(CSV_FILE)

        logger.info(f"📊 Modo Ativo: {self.mode.upper()}")
        logger.info(f"📁 Total de assets locais identificados: {len(assets)}")

        if not assets:
            logger.info("Nenhum asset encontrado para backup no momento.")
            return {"status": "empty", "uploaded": 0, "skipped": 0, "failed": 0}

        pending: List[Path] = []
        skipped = 0

        for asset in assets:
            entry = self._history.get(asset.name)
            if force or not entry or entry.get("status") != "success":
                pending.append(asset)
            else:
                skipped += 1

        logger.info(f"  - Pendentes para backup: {len(pending)}")
        logger.info(f"  - Já salvos anteriormente: {skipped}")

        if dry_run:
            logger.info("\n🧪 MODO DRY-RUN: Nenhuma transferência realizada.")
            for p in pending:
                size_mb = p.stat().st_size / (1024 * 1024)
                logger.info(f"  [Simulação] Faria backup de: {p.name} ({size_mb:.2f} MB)")
            return {
                "status": "dry_run",
                "pending": len(pending),
                "skipped": skipped,
                "uploaded": 0,
                "failed": 0
            }

        uploaded = 0
        failed = 0

        for idx, asset in enumerate(pending, 1):
            size_mb = asset.stat().st_size / (1024 * 1024)
            logger.info(f"[{idx}/{len(pending)}] Fazendo backup de {asset.name} ({size_mb:.2f} MB)...")

            success = False
            remote_ref = None

            if self.mode in ("api_service_account", "api_oauth"):
                success, remote_ref = self.upload_file_cloud(asset)
            elif self.mode == "local_sync":
                success, remote_ref = self.sync_file_local(asset)

            if success:
                uploaded += 1
                logger.info(f"  ✅ Backup concluído: {asset.name} (Ref: {remote_ref})")
                self._history[asset.name] = {
                    "status": "success",
                    "mode": self.mode,
                    "ref": remote_ref,
                    "size_bytes": asset.stat().st_size,
                    "backup_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                save_backup_history(self._history)
            else:
                failed += 1
                logger.error(f"  ❌ Falha no backup de {asset.name}.")

        logger.info("\n" + "=" * 65)
        logger.info(f"🎉 RELATÓRIO DE BACKUP NO GOOGLE DRIVE:")
        logger.info(f"  - Enviados com sucesso: {uploaded}")
        logger.info(f"  - Já sincronizados: {skipped}")
        logger.info(f"  - Falhas: {failed}")
        logger.info(f"Histórico registrado em: {BACKUP_HISTORY_FILE}")
        logger.info("=" * 65 + "\n")

        return {
            "status": "completed",
            "uploaded": uploaded,
            "skipped": skipped,
            "failed": failed,
        }


def run_gdrive_backup(
    dry_run: bool = False,
    force: bool = False,
    include_csv: bool = True
) -> Dict[str, Any]:
    """Helper entry point for pipeline and CLI invocation."""
    backup = GoogleDriveBackup()
    return backup.backup_assets(dry_run=dry_run, force=force, include_csv=include_csv)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StockCont: Google Drive Asset Backup")
    parser.add_argument("--dry-run", action="store_true", help="Simulate backup without transferring files")
    parser.add_argument("--force", action="store_true", help="Re-backup files even if already marked as completed")
    args = parser.parse_args()

    run_gdrive_backup(dry_run=args.dry_run, force=args.force)
