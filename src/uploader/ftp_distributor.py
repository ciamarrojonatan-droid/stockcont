#!/usr/bin/env python3
"""StockCont Phase 5: The Distributor (Multi-Platform SFTP & FTP Auto-Uploader)

Automates mass submission of cataloged microstock assets (JPGs with IPTC/EXIF)
to major stock photography agencies and marketplaces:
  - Adobe Stock (SFTP)
  - Freepik (FTP)
  - Dreamstime (FTP)
  - Pond5 (FTP)
  - Alamy (FTP)
  - Vecteezy (FTP)
  - 123RF (FTP)
  - Ingram (FTP)

Features:
  - Supports both SFTP (paramiko) and FTP (ftplib) protocols
  - Smart ledger (data/processed/upload_history.json) preventing duplicate submissions
  - Exponential backoff retries on network drops
  - Dry-run validation of accounts and pending files
  - Automatic directory discovery in data/final/images/
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from ftplib import FTP, FTP_TLS, error_perm, all_errors as ftp_all_errors
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import paramiko
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
UPLOAD_HISTORY_FILE = PROCESSED_DIR / "upload_history.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Distributor")


@dataclass
class AgencyConfig:
    key: str
    name: str
    protocol: str  # "sftp" or "ftp"
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    remote_dir: str = ""
    use_tls: bool = False

    @property
    def is_configured(self) -> bool:
        """Returns True if username and password are provided and non-empty."""
        return bool(self.username and self.password and self.username.strip() and self.password.strip())


def get_available_agencies() -> Dict[str, AgencyConfig]:
    """Load configuration for all supported agencies from environment variables."""
    return {
        "adobe": AgencyConfig(
            key="adobe",
            name="Adobe Stock",
            protocol="sftp",
            host=os.getenv("ADOBE_SFTP_HOST", "sftp.contributor.adobestock.com"),
            port=int(os.getenv("ADOBE_SFTP_PORT", "22")),
            username=os.getenv("ADOBE_SFTP_USER", "").strip(),
            password=os.getenv("ADOBE_SFTP_PASS", "").strip(),
            remote_dir=os.getenv("ADOBE_SFTP_DIR", ""),
        ),
        "freepik": AgencyConfig(
            key="freepik",
            name="Freepik",
            protocol="ftp",
            host=os.getenv("FREEPIK_FTP_HOST", "ftp.freepik.com"),
            port=int(os.getenv("FREEPIK_FTP_PORT", "21")),
            username=os.getenv("FREEPIK_FTP_USER", "").strip(),
            password=os.getenv("FREEPIK_FTP_PASS", "").strip(),
            remote_dir=os.getenv("FREEPIK_FTP_DIR", ""),
        ),
        "dreamstime": AgencyConfig(
            key="dreamstime",
            name="Dreamstime",
            protocol="ftp",
            host=os.getenv("DREAMSTIME_FTP_HOST", "upload.dreamstime.com"),
            port=int(os.getenv("DREAMSTIME_FTP_PORT", "21")),
            username=os.getenv("DREAMSTIME_FTP_USER", "").strip(),
            password=os.getenv("DREAMSTIME_FTP_PASS", "").strip(),
            remote_dir=os.getenv("DREAMSTIME_FTP_DIR", ""),
        ),
        "pond5": AgencyConfig(
            key="pond5",
            name="Pond5",
            protocol="ftp",
            host=os.getenv("POND5_FTP_HOST", "ftp.pond5.com"),
            port=int(os.getenv("POND5_FTP_PORT", "21")),
            username=os.getenv("POND5_FTP_USER", "").strip(),
            password=os.getenv("POND5_FTP_PASS", "").strip(),
            remote_dir=os.getenv("POND5_FTP_DIR", ""),
        ),
        "alamy": AgencyConfig(
            key="alamy",
            name="Alamy",
            protocol="ftp",
            host=os.getenv("ALAMY_FTP_HOST", "upload.alamy.com"),
            port=int(os.getenv("ALAMY_FTP_PORT", "21")),
            username=os.getenv("ALAMY_FTP_USER", "").strip(),
            password=os.getenv("ALAMY_FTP_PASS", "").strip(),
            remote_dir=os.getenv("ALAMY_FTP_DIR", ""),
        ),
        "vecteezy": AgencyConfig(
            key="vecteezy",
            name="Vecteezy",
            protocol="ftp",
            host=os.getenv("VECTEEZY_FTP_HOST", "ftp.vecteezy.com"),
            port=int(os.getenv("VECTEEZY_FTP_PORT", "21")),
            username=os.getenv("VECTEEZY_FTP_USER", "").strip(),
            password=os.getenv("VECTEEZY_FTP_PASS", "").strip(),
            remote_dir=os.getenv("VECTEEZY_FTP_DIR", ""),
        ),
        "123rf": AgencyConfig(
            key="123rf",
            name="123RF",
            protocol="ftp",
            host=os.getenv("ONETWOTHREERF_FTP_HOST", "ftp.123rf.com"),
            port=int(os.getenv("ONETWOTHREERF_FTP_PORT", "21")),
            username=os.getenv("ONETWOTHREERF_FTP_USER", "").strip(),
            password=os.getenv("ONETWOTHREERF_FTP_PASS", "").strip(),
            remote_dir=os.getenv("ONETWOTHREERF_FTP_DIR", ""),
        ),
        "ingram": AgencyConfig(
            key="ingram",
            name="Ingram",
            protocol="ftp",
            host=os.getenv("INGRAM_FTP_HOST", "ftp.ingrampublishing.com"),
            port=int(os.getenv("INGRAM_FTP_PORT", "21")),
            username=os.getenv("INGRAM_FTP_USER", "").strip(),
            password=os.getenv("INGRAM_FTP_PASS", "").strip(),
            remote_dir=os.getenv("INGRAM_FTP_DIR", ""),
        ),
    }


def load_upload_history() -> Dict[str, Dict[str, str]]:
    """Load upload history ledger to avoid duplicate submissions."""
    if not UPLOAD_HISTORY_FILE.exists():
        return {}
    try:
        with open(UPLOAD_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Não foi possível ler upload_history.json ({e}). Criando novo registro.")
        return {}


def save_upload_history(history: Dict[str, Dict[str, str]]) -> None:
    """Atomically persist upload history ledger."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = UPLOAD_HISTORY_FILE.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        tmp_file.replace(UPLOAD_HISTORY_FILE)
    except Exception as e:
        logger.error(f"Erro ao salvar histórico de upload: {e}")


def get_ready_images(images_dir: Optional[Path] = None) -> List[Path]:
    """Find all cataloged JPG images ready for upload."""
    target_dir = images_dir or FINAL_IMAGES_DIR
    if images_dir is None and (not target_dir.exists() or not (list(target_dir.glob("*.jpg")) or list(target_dir.glob("*.jpeg")))):
        # Fallback to Google Drive local path if configured
        gdrive_path = os.getenv("GOOGLE_DRIVE_LOCAL_PATH", "").strip()
        if gdrive_path:
            gd_p = Path(gdrive_path)
            if gd_p.exists() and gd_p.is_dir():
                target_dir = gd_p

    if not target_dir.exists():
        return []

    # Priority: .jpg and .jpeg images containing embedded IPTC metadata
    jpg_images = sorted(list(target_dir.glob("*.jpg")) + list(target_dir.glob("*.jpeg")))
    
    # Check if there are PNGs that need conversion via Phase 4
    png_images = list(target_dir.glob("*.png"))
    if png_images and not jpg_images:
        logger.warning(f"⚠️ Encontradas {len(png_images)} imagens PNG, mas nenhum JPG catalogado.")
        logger.warning("   Recomendação: Execute 'python main.py --phase 4' primeiro para injetar metadados IPTC/EXIF nos JPGs.")
        
    return jpg_images


def upload_via_sftp(
    agency: AgencyConfig,
    file_path: Path,
    max_retries: int = 3,
    timeout: int = 30
) -> bool:
    """Upload a file via SFTP using paramiko with retry backoff."""
    for attempt in range(1, max_retries + 1):
        ssh = None
        sftp = None
        try:
            logger.info(f"  📡 Conectando SFTP {agency.name} ({agency.host}:{agency.port}) [Tentativa {attempt}/{max_retries}]...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=agency.host,
                port=agency.port,
                username=agency.username,
                password=agency.password,
                timeout=timeout,
                banner_timeout=timeout,
                auth_timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )
            sftp = ssh.open_sftp()
            
            if agency.remote_dir:
                try:
                    sftp.chdir(agency.remote_dir)
                except IOError:
                    logger.debug(f"Criando diretório remoto {agency.remote_dir}...")
                    sftp.mkdir(agency.remote_dir)
                    sftp.chdir(agency.remote_dir)
                    
            remote_filename = file_path.name
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"  ⬆️ Enviando {remote_filename} ({file_size_mb:.2f} MB) via SFTP...")
            
            sftp.put(str(file_path), remote_filename)
            
            # Verify file exists on remote server
            remote_stat = sftp.stat(remote_filename)
            if remote_stat.st_size > 0:
                logger.info(f"  ✅ Upload concluído com sucesso para {agency.name}: {remote_filename}")
                return True
            else:
                logger.warning(f"  ⚠️ Arquivo remoto tem tamanho 0 bytes. Tentando novamente...")
                
        except Exception as e:
            logger.warning(f"  ⚠️ Falha no upload SFTP ({agency.name}): {e}")
            if attempt < max_retries:
                sleep_sec = 2 ** attempt
                logger.info(f"  ⏳ Aguardando {sleep_sec}s antes de tentar novamente...")
                time.sleep(sleep_sec)
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass
    return False


def upload_via_ftp(
    agency: AgencyConfig,
    file_path: Path,
    max_retries: int = 3,
    timeout: int = 30
) -> bool:
    """Upload a file via standard FTP (or FTPS) using ftplib with retry backoff."""
    for attempt in range(1, max_retries + 1):
        ftp = None
        try:
            logger.info(f"  📡 Conectando FTP {agency.name} ({agency.host}:{agency.port}) [Tentativa {attempt}/{max_retries}]...")
            
            if agency.use_tls:
                ftp = FTP_TLS(timeout=timeout)
            else:
                ftp = FTP(timeout=timeout)
                
            ftp.connect(agency.host, agency.port)
            ftp.login(agency.username, agency.password)
            
            if agency.use_tls and isinstance(ftp, FTP_TLS):
                ftp.prot_p()  # Switch to secure data channel
                
            ftp.set_pasv(True)
            
            if agency.remote_dir:
                try:
                    ftp.cwd(agency.remote_dir)
                except error_perm:
                    logger.debug(f"Criando diretório remoto {agency.remote_dir}...")
                    ftp.mkd(agency.remote_dir)
                    ftp.cwd(agency.remote_dir)
                    
            remote_filename = file_path.name
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"  ⬆️ Enviando {remote_filename} ({file_size_mb:.2f} MB) via FTP...")
            
            with open(file_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_filename}", f)
                
            logger.info(f"  ✅ Upload concluído com sucesso para {agency.name}: {remote_filename}")
            return True
            
        except Exception as e:
            logger.warning(f"  ⚠️ Falha no upload FTP ({agency.name}): {e}")
            if attempt < max_retries:
                sleep_sec = 2 ** attempt
                logger.info(f"  ⏳ Aguardando {sleep_sec}s antes de tentar novamente...")
                time.sleep(sleep_sec)
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    try:
                        ftp.close()
                    except Exception:
                        pass
    return False


def test_agency_connection(agency: AgencyConfig) -> Tuple[bool, str]:
    """Test connection and authentication to an agency without sending files."""
    if not agency.is_configured:
        return False, "Credenciais ausentes no .env"
        
    if agency.protocol == "sftp":
        ssh = None
        sftp = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=agency.host,
                port=agency.port,
                username=agency.username,
                password=agency.password,
                timeout=15,
                look_for_keys=False,
                allow_agent=False
            )
            sftp = ssh.open_sftp()
            return True, "Conexão e autenticação SFTP bem-sucedidas!"
        except Exception as e:
            return False, f"Falha SFTP: {e}"
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass
    else:
        ftp = None
        try:
            ftp = FTP_TLS(timeout=15) if agency.use_tls else FTP(timeout=15)
            ftp.connect(agency.host, agency.port)
            ftp.login(agency.username, agency.password)
            ftp.set_pasv(True)
            return True, "Conexão e autenticação FTP bem-sucedidas!"
        except Exception as e:
            return False, f"Falha FTP: {e}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    try:
                        ftp.close()
                    except Exception:
                        pass


def run_distributor(
    target_platform: str = "all",
    dry_run: bool = False,
    force: bool = False,
    images_dir: Optional[Path] = None
) -> Dict[str, int]:
    """Execute Phase 5: Mass Multi-Platform Asset Distributor.

    Args:
        target_platform: Target agency key ("all", "adobe", "freepik", etc.)
        dry_run: If True, tests connections and validates files without uploading.
        force: If True, re-uploads files already registered in upload_history.json.
    """
    logger.info("=" * 65)
    logger.info("🚀 INICIANDO FASE 5: O DISTRIBUIDOR (MULTI-PLATFORM AUTO-UPLOADER)")
    logger.info("=" * 65)

    all_agencies = get_available_agencies()
    
    # Filter target agencies
    if target_platform != "all":
        if target_platform not in all_agencies:
            logger.error(f"Plataforma '{target_platform}' desconhecida. Opções: {list(all_agencies.keys())}")
            return {}
        active_agencies = {target_platform: all_agencies[target_platform]}
    else:
        active_agencies = all_agencies

    # Check configuration status
    configured_agencies = {k: v for k, v in active_agencies.items() if v.is_configured}
    unconfigured_agencies = {k: v for k, v in active_agencies.items() if not v.is_configured}

    logger.info(f"📊 Relatório de Agências ({len(active_agencies)} no escopo):")
    for key, ag in configured_agencies.items():
        masked_user = f"{ag.username[:3]}***" if len(ag.username) > 3 else "configurado"
        logger.info(f"  [✓] {ag.name} ({ag.protocol.upper()} -> {ag.host}:{ag.port}) | Usuário: {masked_user}")
    for key, ag in unconfigured_agencies.items():
        logger.info(f"  [-] {ag.name} ({ag.protocol.upper()}): Não configurado no .env (Pular)")

    if not configured_agencies:
        logger.warning("\n⚠️ NENHUMA AGÊNCIA COM CREDENCIAIS VÁLIDAS NO .ENV!")
        logger.info("Para habilitar o envio automático para o Adobe Stock, adicione ao seu arquivo .env:")
        logger.info('  ADOBE_SFTP_USER="seu_id_contributor"')
        logger.info('  ADOBE_SFTP_PASS="sua_senha_sftp_gerada"')
        logger.info("\nVeja mais detalhes em state.md (Seção 3: Credenciais FTP/SFTP).")
        return {}

    # Discover ready files
    images = get_ready_images(images_dir=images_dir)
    dir_str = str(images_dir) if images_dir else "data/final/images/"
    logger.info(f"\n📁 Imagens catalogadas prontas em {dir_str}: {len(images)} arquivos.")

    if not images:
        logger.warning("⚠️ Nenhuma imagem JPG encontrada em data/final/images/ para distribuição.")
        logger.info("Execute primeiro a Fase 3 e a Fase 4 para gerar e catalogar seus assets.")
        return {}

    history = load_upload_history()
    results: Dict[str, int] = {k: 0 for k in configured_agencies}

    if dry_run:
        logger.info("\n🧪 MODO DRY-RUN ATIVADO: Testando credenciais e simulando despachos...")
        for key, ag in configured_agencies.items():
            success, msg = test_agency_connection(ag)
            status_icon = "✅" if success else "❌"
            logger.info(f"  {status_icon} Teste de Conexão com {ag.name}: {msg}")
            
            pending_count = 0
            for img in images:
                if force or key not in history.get(img.name, {}):
                    pending_count += 1
            logger.info(f"     -> {pending_count} arquivos pendentes para envio em {ag.name}.")
        logger.info("\n🧪 Dry-run finalizado com sucesso! Nenhuma imagem foi enviada.")
        return results

    # Live Upload Loop
    for key, ag in configured_agencies.items():
        logger.info(f"\n🚀 Despachando lote para: {ag.name} ({ag.protocol.upper()})...")
        
        pending_files = []
        for img in images:
            if force or key not in history.get(img.name, {}):
                pending_files.append(img)
            else:
                logger.debug(f"Ignorando {img.name} (já enviado para {ag.name} em {history[img.name][key]}).")

        if not pending_files:
            logger.info(f"  🎉 Todos os {len(images)} arquivos já foram enviados anteriormente para {ag.name}!")
            continue

        logger.info(f"  📤 Enviando {len(pending_files)} arquivos pendentes para {ag.name}...")
        
        for idx, file_path in enumerate(pending_files, 1):
            logger.info(f"[{idx}/{len(pending_files)}] Processando {file_path.name}...")
            
            success = False
            if ag.protocol == "sftp":
                success = upload_via_sftp(ag, file_path)
            else:
                success = upload_via_ftp(ag, file_path)

            if success:
                results[key] += 1
                if file_path.name not in history:
                    history[file_path.name] = {}
                history[file_path.name][key] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                save_upload_history(history)
            else:
                logger.error(f"  ❌ Falha definitiva ao enviar {file_path.name} para {ag.name}.")

    logger.info("\n" + "=" * 65)
    logger.info("🎉 RELATÓRIO FINAL DE DISTRIBUIÇÃO:")
    for key, ag in configured_agencies.items():
        logger.info(f"  - {ag.name}: {results[key]} arquivos enviados com sucesso.")
    logger.info(f"Histórico atualizado gravado em: {UPLOAD_HISTORY_FILE}")
    logger.info("=" * 65 + "\n")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StockCont Phase 5: Multi-Platform SFTP/FTP Distributor")
    parser.add_argument("--platform", default="all", help="Target agency: all, adobe, freepik, dreamstime, pond5, alamy, vecteezy, 123rf")
    parser.add_argument("--dry-run", action="store_true", help="Test credentials and simulate upload without transferring files")
    parser.add_argument("--force", action="store_true", help="Re-upload files even if already marked as sent in history")
    args = parser.parse_args()

    parser.add_argument("--images-dir", type=Path, default=None, help="Custom images directory")
    args = parser.parse_args()

    run_distributor(target_platform=args.platform, dry_run=args.dry_run, force=args.force, images_dir=args.images_dir)
