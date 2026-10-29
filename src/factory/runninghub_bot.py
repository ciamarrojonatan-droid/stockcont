import os
import json
import logging
import sys
import time
import base64
import uuid
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Frame, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

PROMPTS_FILE: Path = BASE_DIR / "data" / "processed" / "prompts.json"
STAGING_IMAGES_DIR: Path = BASE_DIR / "data" / "staging" / "images"
FINAL_IMAGES_DIR: Path = BASE_DIR / "data" / "final" / "images"

# ══════════════════════════════════════════════════════
# Dual-Account Topologies & Configurations
# ══════════════════════════════════════════════════════

# Conta 1 PromptList Nodes: 42 nós (5 prompts/nó = até 210 prompts por execução de 40 min)
CONTA_1_PROMPT_NODES: List[int] = [
    # Grupo Original (30 prompts)
    128, 129, 130, 131, 204, 218,
    # Expansão para 210 prompts (36 novos nós PromptList = 180 prompts adicionais)
    224, 223, 222, 221, 219, 220,
    230, 229, 228, 227, 225, 226,
    236, 235, 234, 233, 231, 232,
    242, 241, 240, 239, 237, 238,
    254, 253, 252, 251, 249, 250,
    248, 247, 246, 245, 243, 244,
]

# Conta 1: Produtora Raw (até 210 prompts -> Nó #121 -> Salva todas de uma vez em staging)
CONTA_1_CONFIG = {
    "account": 1,
    "role": "raw_producer",
    "workflow_url": "https://www.runninghub.ai/pt-br/workflow/2113606426114670593?source=workspace",
    "workflow_id": "2113606426114670593",
    "prompt_nodes": CONTA_1_PROMPT_NODES,
    "output_node": 121,
    "default_batch_size": 210,
    "destination_dir": STAGING_IMAGES_DIR,
    "prefix": "raw",
    "save_mode": "batch_all",  # Salva todas de uma vez após a conclusão
    "session_dir_name": "playwright_session_raw",
}

# Conta 2: Consumidora SeedVR 2.5 8K Upscale (Nó #55 -> Salva 1 a 1 em tempo real)
CONTA_2_CONFIG = {
    "account": 2,
    "role": "seedvr_8k_upscaler",
    "workflow_url": "https://www.runninghub.ai/pt-br/workflow/2115663736840245249?source=workspace",
    "workflow_id": "2115663736840245249",
    "input_node": 5,  # Load Images (zip)
    "prompt_nodes": [],
    "output_node": 55,  # Preview Image (SeedVR 8K)
    "default_batch_size": 10,  # Máximo 10 imagens por zip para evitar VRAM OOM no KSampler #23
    "destination_dir": FINAL_IMAGES_DIR,
    "prefix": "upscaled_8k",
    "save_mode": "realtime_single",  # Salva 1 a 1 instantaneamente antes de sobrescrever
    "session_dir_name": "playwright_session_upscale",
}

# Default Active Configuration (Padrão: Conta 1 - Raw Producer)
DEFAULT_ACCOUNT: int = int(os.getenv("RUNNINGHUB_ACCOUNT", "1"))
DEFAULT_BATCH_SIZE: int = 210
DEFAULT_OUTPUT_NODE: int = 121
DEFAULT_PROMPT_NODES: List[int] = CONTA_1_PROMPT_NODES
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 800

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger: logging.Logger = logging.getLogger(__name__)


def get_account_config(account: int = 1) -> Dict[str, Any]:
    """Retorna o dicionário de configuração da conta selecionada."""
    if account == 2:
        return dict(CONTA_2_CONFIG)
    return dict(CONTA_1_CONFIG)


def load_prompts(batch_size: int = DEFAULT_BATCH_SIZE) -> List[str]:
    """Carrega prompts pendentes da fila priorizando Contributor Insights."""
    from src.factory.prompt_queue import PromptQueueManager
    mgr = PromptQueueManager()
    pending = mgr.get_pending_prompts(batch_size=batch_size)
    prompts = [p.prompt_text for p in pending]
    logger.info(f"Carregados {len(prompts)} prompts pendentes para este lote (Top Sellers priorizados).")
    return prompts


def get_node_images(page: Page, node_id: int) -> List[str]:
    """Extrai URLs de imagens renderizadas no nó especificado do ComfyUI/LiteGraph."""
    node_images = []
    for frame in page.frames:
        try:
            imgs = frame.evaluate("""(id) => {
                if (typeof window.app !== 'undefined' && window.app.graph) {
                    let node = window.app.graph.getNodeById(id);
                    if (node) {
                        let res = [];
                        if (node.imgs && node.imgs.length > 0) {
                            res.push(...node.imgs.map(i => i.src || i.currentSrc).filter(Boolean));
                        }
                        if (node.image && (node.image.src || node.image.currentSrc)) {
                            res.push(node.image.src || node.image.currentSrc);
                        }
                        return res;
                    }
                }
                return [];
            }""", node_id)
            if imgs:
                node_images.extend(imgs)
        except Exception:
            pass
    return node_images


def save_image_from_src(
    page: Page,
    src: str,
    destination_dir: Optional[Path] = None,
    prefix: str = "raw",
) -> Optional[str]:
    """Salva a imagem do canvas/DOM em disco de forma transacional (.tmp)."""
    target_dir = destination_dir or STAGING_IMAGES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = target_dir / f"{prefix}_{uuid.uuid4().hex[:8]}.png"
    while filename.exists():
        filename = target_dir / f"{prefix}_{uuid.uuid4().hex[:8]}.png"
    tmp_filename = filename.with_suffix(".tmp")

    try:
        data: Optional[bytes] = None
        if src.startswith("data:image"):
            header, encoded = src.split(",", 1)
            raw_data = base64.b64decode(encoded)
            if len(raw_data) > 30000:
                data = raw_data
        elif src.startswith("blob:") or src.startswith("http"):
            # 1. Tentar extrair diretamente no contexto autenticado do navegador
            for frame in page.frames:
                try:
                    b64_data = frame.evaluate("""async (url) => {
                        const response = await fetch(url, { credentials: 'include' });
                        if (!response.ok) return null;
                        const blob = await response.blob();
                        return new Promise((resolve, reject) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.onerror = reject;
                            reader.readAsDataURL(blob);
                        });
                    }""", src)
                    if b64_data and "," in b64_data:
                        header, encoded = b64_data.split(",", 1)
                        decoded = base64.b64decode(encoded)
                        if len(decoded) > 30000:
                            data = decoded
                            break
                except Exception:
                    continue

            # 2. Fallback para urllib caso não tenha sido baixado e seja HTTP
            if data is None and src.startswith("http"):
                try:
                    req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=20) as response:
                        http_data = response.read()
                        if len(http_data) > 30000:
                            data = http_data
                except Exception:
                    pass

        if data:
            with open(tmp_filename, "wb") as f:
                f.write(data)
            tmp_filename.replace(filename)
            return filename.name
    except Exception as e:
        logger.debug(f"Falha ao processar src de imagem: {e}")
        if tmp_filename.exists():
            try:
                tmp_filename.unlink()
            except Exception:
                pass
    return None


def cancel_runninghub_task(page: Page, max_wait_sec: int = 45) -> bool:
    """Cancela a tarefa ativa no RunningHub ('Lista de tarefas') para poupar GPU."""
    logger.info("🛑 [Lista de tarefas] Localizando e acionando 'Cancelar' para a tarefa ativa...")
    start_time = time.time()

    while time.time() - start_time < max_wait_sec:
        try:
            has_cancel = False
            for frame in page.frames:
                for word in ["Cancelar", "Cancel", "取消"]:
                    try:
                        c = frame.get_by_text(word, exact=True)
                        if c.count() > 0 and c.first.is_visible():
                            has_cancel = True
                            break
                    except Exception:
                        pass
                if has_cancel:
                    break

            if not has_cancel:
                for drawer_sel in ["Lista de tarefas", "Tarefas", "Task"]:
                    try:
                        drawer_btn = page.get_by_text(drawer_sel)
                        if drawer_btn.count() > 0 and drawer_btn.first.is_visible():
                            logger.info(f"📂 Abrindo painel 'Lista de tarefas' ({drawer_sel})...")
                            drawer_btn.first.click(timeout=1500)
                            time.sleep(1.0)
                            break
                    except Exception:
                        pass

            clicked = False
            for frame in page.frames:
                try:
                    specific_cancel = frame.locator("xpath=//*[contains(text(), 'Gerando') or contains(text(), 'taskid')]/ancestor::*[position()<=5]//*[text()='Cancelar' or text()='Cancel' or text()='取消']")
                    if specific_cancel.count() > 0 and specific_cancel.first.is_visible():
                        logger.info("🎯 Botão 'Cancelar' da tarefa ativa encontrado! Clicando...")
                        specific_cancel.first.click(timeout=3000)
                        clicked = True
                        break
                except Exception:
                    pass
                if clicked:
                    break

            if not clicked:
                for frame in page.frames:
                    for word in ["Cancelar", "Cancel", "取消"]:
                        try:
                            general_cancels = frame.get_by_text(word, exact=True)
                            for idx in range(general_cancels.count()):
                                item = general_cancels.nth(idx)
                                if item.is_visible():
                                    logger.info(f"🎯 Botão '{word}' encontrado no painel! Clicando...")
                                    item.click(timeout=3000)
                                    clicked = True
                                    break
                        except Exception:
                            pass
                        if clicked:
                            break
                    if clicked:
                        break

            if clicked:
                time.sleep(1.0)
                for frame in page.frames:
                    for ok_word in ["Confirmar", "Sim", "OK", "Yes", "确定"]:
                        try:
                            confirm_btn = frame.locator(f"xpath=//*[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@class, 'confirm')]//*[text()='{ok_word}']")
                            if confirm_btn.count() == 0:
                                confirm_btn = frame.get_by_text(ok_word, exact=True)
                            if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
                                logger.info(f"🎯 Botão de confirmação '{ok_word}' clicado!")
                                confirm_btn.first.click(timeout=2000)
                                break
                        except Exception:
                            pass
                logger.info("✅ Tarefa cancelada com sucesso na 'Lista de tarefas'!")
                return True

        except Exception as e:
            logger.debug(f"Tentativa de cancelamento falhou nesta iteração: {e}")

        time.sleep(1.5)

    return False


def upload_zip_to_node(page: Page, frame: Optional[Frame], node_id: int, zip_path: Path) -> bool:
    """
    Injeta o arquivo ZIP no Nó ComfyUI especificado (ex: Nó #5 'Load Images (zip)').
    Aplica múltiplas estratégias concorrentes para máxima confiabilidade:
    1. Direct DOM input file injection no frame
    2. File chooser hook via Playwright com disparo de clique no widget
    3. Direct multipart upload via fetch('/upload/image') e atualização do widget LiteGraph
    """
    logger.info(f"📤 Iniciando upload do arquivo ZIP ({zip_path.name}) no Nó #{node_id}...")
    target_frame = frame or page.main_frame
    uploaded = False

    # Estratégia 1: Input file no DOM
    try:
        for f in page.frames:
            inputs = f.locator("input[type='file']")
            cnt = inputs.count()
            if cnt > 0:
                for i in range(cnt):
                    try:
                        inputs.nth(i).set_input_files(str(zip_path))
                        logger.info("🎯 Injetado arquivo ZIP via input[type='file'] no DOM.")
                        uploaded = True
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Aviso na verificação de inputs de arquivo: {e}")

    # Estratégia 2: File Chooser trigger
    try:
        with page.expect_file_chooser(timeout=2500) as fc_info:
            target_frame.evaluate("""(nodeId) => {
                if (typeof window.app === 'undefined' || !window.app.graph) return false;
                const node = window.app.graph.getNodeById(nodeId);
                if (node) {
                    if (window.app.canvas) {
                        window.app.canvas.centerOnNode(node);
                        window.app.canvas.selectNode(node);
                    }
                    if (node.widgets) {
                        for (let w of node.widgets) {
                            if (w.type === 'button' || (w.name && w.name.toLowerCase().includes('upload'))) {
                                if (typeof w.callback === 'function') {
                                    w.callback();
                                    return true;
                                }
                            }
                        }
                    }
                }
                return false;
            }""", node_id)
        fc = fc_info.value
        fc.set_files(str(zip_path))
        logger.info(f"🎯 Injetado arquivo ZIP via FileChooser no Nó #{node_id}.")
        uploaded = True
    except Exception:
        pass

    # Estratégia 3: Multipart upload direto via API ComfyUI & atualização do widget
    try:
        with open(zip_path, "rb") as f:
            b64_zip = base64.b64encode(f.read()).decode("utf-8")
        api_res = target_frame.evaluate("""async ({ nodeId, filename, b64Data }) => {
            let uploadedName = filename;
            try {
                const byteCharacters = atob(b64Data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: 'application/zip' });
                const file = new File([blob], filename, { type: 'application/zip' });

                const formData = new FormData();
                formData.append('image', file);
                formData.append('overwrite', 'true');
                formData.append('type', 'input');

                const resp = await fetch('/upload/image', {
                    method: 'POST',
                    body: formData,
                    credentials: 'include'
                });
                if (resp.ok) {
                    const data = await resp.json();
                    if (data && data.name) uploadedName = data.name;
                }
            } catch (err) {}

            if (typeof window.app !== 'undefined' && window.app.graph) {
                const node = window.app.graph.getNodeById(nodeId);
                if (node) {
                    if (window.app.canvas) {
                        window.app.canvas.centerOnNode(node);
                        window.app.canvas.selectNode(node);
                    }
                    if (node.widgets) {
                        for (let w of node.widgets) {
                            if (w.name && (w.name.toLowerCase().includes('zip') || w.name.toLowerCase().includes('file') || w.name.toLowerCase().includes('image') || w.type === 'combo' || w.type === 'customtext')) {
                                w.value = uploadedName;
                                if (w.inputEl) {
                                    w.inputEl.value = uploadedName;
                                    w.inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                                    w.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                                if (typeof w.callback === 'function') {
                                    try { w.callback(uploadedName); } catch(e) {}
                                }
                            }
                        }
                    }
                    if (window.app.graph.setDirtyCanvas) window.app.graph.setDirtyCanvas(true, true);
                    if (window.app.canvas && window.app.canvas.draw) window.app.canvas.draw(true, true);
                    return { success: true, uploadedName: uploadedName };
                }
            }
            return { success: false };
        }""", {"nodeId": node_id, "filename": zip_path.name, "b64Data": b64_zip})

        if api_res and api_res.get("success"):
            logger.info("🎯 Widget do Nó #%d atualizado com sucesso (%s).", node_id, api_res.get("uploadedName"))
            uploaded = True
    except Exception as e:
        logger.debug(f"Aviso no fallback de API do Nó #{node_id}: {e}")

    return uploaded


def close_unwanted_tabs(browser: Any, workflow_id: str) -> None:
    """Fecha abas secundárias promocionais ou de marketing que o RunningHub possa abrir ao carregar."""
    try:
        pages = []
        if hasattr(browser, "pages"):
            pages = list(browser.pages)
        elif hasattr(browser, "contexts") and browser.contexts:
            for ctx in browser.contexts:
                pages.extend(list(ctx.pages))

        if len(pages) > 1:
            for p in pages:
                try:
                    url = p.url.lower()
                    if workflow_id not in p.url and "task" not in url and "workbench" not in url:
                        logger.info(f"🛡️ [Anti-Popup] Fechando aba secundária/propaganda: {p.url}")
                        p.close()
                except Exception:
                    pass
    except Exception:
        pass


def dismiss_runninghub_popups(page: Page) -> bool:
    """Detecta e fecha automaticamente popups de marketing, avisos e modais promocionais do RunningHub."""
    dismissed = False
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    close_selectors = [
        ".ant-modal-close",
        ".ant-modal-close-x",
        ".el-dialog__headerbtn",
        ".el-dialog__close",
        "button[aria-label='Close']",
        "button[aria-label='close']",
        "button:has-text('Close')",
        "button:has-text('Fechar')",
        "button:has-text('Cancel')",
        "button:has-text('Dismiss')",
        "button:has-text('Got it')",
        "button:has-text('I know')",
        "button:has-text('我知道了')",
        "button:has-text('关闭')",
        "button:has-text('Skip')",
        "button:has-text('Remind me later')",
        "button:has-text('以后再说')",
        "button:has-text('×')",
        ".close-icon",
        ".modal-close",
        "[class*='close-btn']",
        "[class*='CloseBtn']",
        "[class*='closeBtn']",
        "[class*='dialog-close']",
        "[class*='modal-close']",
    ]

    for sel in close_selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()
            if count > 0:
                for i in range(count):
                    el = loc.nth(i)
                    if el.is_visible():
                        el.click(timeout=1000, force=True)
                        dismissed = True
                        logger.info(f"🛡️ [Anti-Popup] Fechou modal de marketing via seletor: {sel}")
                        time.sleep(0.3)
                        break
        except Exception:
            pass

    try:
        removed = page.evaluate("""() => {
            let count = 0;
            const selectors = [
                '.ant-modal-root:not(.comfy-modal)',
                '.ant-modal-wrap:not(.comfy-modal)',
                '.ant-modal-mask',
                '.el-overlay',
                '.v-modal',
                '[class*="marketing-modal"]',
                '[class*="banner-modal"]',
                '[class*="promotion-modal"]',
                '[class*="notice-modal"]',
                '[class*="activity-dialog"]',
                '[class*="guide-modal"]'
            ];
            for (let sel of selectors) {
                const els = document.querySelectorAll(sel);
                els.forEach(el => {
                    if (!el.querySelector('#graph-canvas') && !el.id.includes('canvas')) {
                        el.style.display = 'none';
                        el.remove();
                        count++;
                    }
                });
            }
            return count;
        }""")
        if removed and removed > 0:
            logger.info(f"🛡️ [Anti-Popup] Removidos {removed} overlays de marketing/bloqueio via DOM.")
            dismissed = True
    except Exception:
        pass

    return dismissed


def run_factory_bot(
    account: int = DEFAULT_ACCOUNT,
    output_node_id: Optional[int] = None,
    max_batches: int = 1,
    all_batches: bool = False,
    batch_size: Optional[int] = None,
    prompt_nodes: Optional[List[int]] = None,
    destination_dir: Optional[Path] = None,
    session_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executa a Fábrica RPA adaptando o comportamento entre Conta 1 e Conta 2:
    - Conta 1 (Raw Producer): Injeta prompts (#128-#254) e salva todas as até 210 imagens brutas de uma vez no Nó #121 (janela de 40 min).
    - Conta 2 (SeedVR 8K Upscaler): Monitora o Nó #55 em tempo real (1 a 1 instantâneo) antes que a imagem seja sobrescrita!
    """
    cfg = get_account_config(account)
    out_node = output_node_id if output_node_id is not None else cfg["output_node"]
    input_node = cfg.get("input_node", 5)
    b_size = batch_size if batch_size is not None else cfg["default_batch_size"]
    target_nodes = prompt_nodes if prompt_nodes is not None else cfg["prompt_nodes"]
    target_dir = destination_dir if destination_dir is not None else cfg["destination_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    save_mode = cfg["save_mode"]  # 'batch_all' ou 'realtime_single'
    workflow_url = cfg["workflow_url"]
    workflow_id = cfg["workflow_id"]

    from src.factory.stealth_profile import (
        get_stealth_fingerprint,
        build_stealth_init_script,
        get_playwright_launch_options,
    )
    from src.factory.prompt_queue import PromptQueueManager
    from src.analyzer.qc_inspector import QCInspector
    queue_mgr = PromptQueueManager()
    qc_inspector = QCInspector()

    zip_path: Optional[Path] = None
    approved_files: List[str] = []
    expected_images_c2 = 0
    if account == 2:
        max_batch_for_zip = b_size if b_size else 10
        zip_path, approved_files = qc_inspector.package_approved_images(max_images=max_batch_for_zip, only_unprocessed=True)
        if not zip_path or not approved_files:
            logger.warning("❌ Nenhuma imagem aprovada pendente no QC para upscale na Conta 2!")
            return benchmark_stats
        expected_images_c2 = len(approved_files)
        logger.info(f"📦 [Conta 2] Pacote ZIP preparado com {expected_images_c2} imagens aprovadas (Anti-OOM: max {max_batch_for_zip}): {zip_path.name}")

    fp = get_stealth_fingerprint(account)
    stealth_script = build_stealth_init_script(fp)
    launch_kwargs = get_playwright_launch_options(account=account, base_dir=BASE_DIR)
    if session_dir:
        launch_kwargs["user_data_dir"] = session_dir
    user_data_dir = Path(launch_kwargs["user_data_dir"])

    logger.info("=" * 65)
    if account == 1:
        logger.info("🚀 INICIANDO FÁBRICA RPA — CONTA 1 (RAW PRODUCER)")
        logger.info(f"  • Modo de Salvamento: BATCH ALL (Todas de uma vez após render)")
        logger.info(f"  • Nós PromptList:     {target_nodes} (5 prompts/nó = até {len(target_nodes)*5} prompts)")
        logger.info(f"  • Nó de Preview Raw:  #{out_node}")
    else:
        logger.info("💎 INICIANDO FÁBRICA RPA — CONTA 2 (SEEDVR 2.5 8K UPSCALER)")
        logger.info(f"  • Modo de Salvamento: TEMPO REAL 1 A 1 (Salva instantâneo no Nó #{out_node})")
        logger.info(f"  • Alerta Anti-Overwrite: Captura imediata antes da próxima imagem substituir o nó!")
        logger.info(f"  • Nó Preview 8K:      #{out_node}")
    gpu_label = fp.webgl_renderer.split('(')[1].split(')')[0] if '(' in fp.webgl_renderer else 'Spoofed GPU'
    logger.info(f"  • Stealth Fingerprint: GPU {gpu_label}")
    logger.info(f"  • Stealth Hardware:    {fp.hardware_concurrency} cores | {fp.device_memory} GB RAM | {fp.screen_width}x{fp.screen_height}")
    logger.info(f"  • Workflow URL:       {workflow_url}")
    logger.info(f"  • Workflow ID:        {workflow_id}")
    logger.info(f"  • Sessão Browser:     {user_data_dir.name}")
    logger.info(f"  • Pasta Destino:      {target_dir}")
    logger.info("=" * 65)

    benchmark_stats = {
        "account": account,
        "role": cfg["role"],
        "batches_completed": 0,
        "total_images_saved": 0,
        "total_duration_sec": 0.0,
        "avg_sec_per_image": 0.0,
        "saved_files": [],
    }

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            logger.info("⚡ Conectado ao Chrome existente via porta 9222!")
        except Exception:
            pass

        if not browser:
            browser = p.chromium.launch_persistent_context(**launch_kwargs)

        try:
            if hasattr(browser, "add_init_script"):
                browser.add_init_script(stealth_script)
            elif hasattr(browser, "contexts") and browser.contexts:
                for ctx in browser.contexts:
                    ctx.add_init_script(stealth_script)
            logger.info(f"🛡️ Script stealth ativado com sucesso para Conta {account} ({fp.screen_width}x{fp.screen_height})!")
        except Exception as e:
            logger.warning(f"Aviso ao injetar script stealth no contexto: {e}")

        try:
            target_page = None
            all_pages = []
            if hasattr(browser, "contexts") and browser.contexts:
                for ctx in browser.contexts:
                    all_pages.extend(ctx.pages)
            elif hasattr(browser, "pages"):
                all_pages.extend(browser.pages)

            for p_cand in all_pages:
                try:
                    if "runninghub" in p_cand.url:
                        target_page = p_cand
                        logger.info(f"🎯 Aba existente do RunningHub encontrada ({p_cand.url})!")
                        break
                except Exception:
                    pass

            if target_page:
                page = target_page
                try:
                    page.evaluate(stealth_script)
                except Exception:
                    pass
                try:
                    page.bring_to_front()
                    if workflow_id not in page.url:
                        logger.info(f"Navegando para o workflow {workflow_id}...")
                        page.goto(workflow_url, wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass
            else:
                page = all_pages[0] if all_pages else browser.new_page()
                try:
                    page.evaluate(stealth_script)
                except Exception:
                    pass
                logger.info(f"Abrindo workflow ({workflow_id})...")
                try:
                    page.goto(workflow_url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    logger.warning(f"Aviso ao abrir RunningHub ({e}). Prosseguindo...")

            # Limpeza preventiva imediata de abas promocionais e popups de marketing
            time.sleep(1.5)
            close_unwanted_tabs(browser, workflow_id)
            dismiss_runninghub_popups(page)

            # 1. Aguardar carregamento dos nós no grafo (com detecção de login e anti-popup ativo)
            logger.info("Aguardando carregamento completo do workflow ComfyUI...")
            comfy_frame = None
            loaded = False
            for step in range(120):
                # Auto-dismiss de popups promocionais a cada 2 iterações
                if step % 2 == 0:
                    dismiss_runninghub_popups(page)
                    close_unwanted_tabs(browser, workflow_id)

                # Detectar tela de login para orientar o usuário
                try:
                    is_login = page.evaluate("() => document.body ? (document.body.innerText.includes('Faça login') || document.body.innerText.includes('Entrar') || window.location.href.includes('login')) : false")
                    if is_login and step % 5 == 0:
                        logger.info(f"🔑 [Conta {account}] Aguardando login do usuário na janela do navegador... (step {step+1}/120)")
                except Exception:
                    pass

                for f in page.frames:
                    try:
                        cnt = f.evaluate("() => window.app && window.app.graph && window.app.graph._nodes ? window.app.graph._nodes.length : 0")
                        if cnt and cnt >= 5:
                            comfy_frame = f
                            loaded = True
                            logger.info(f"✅ Workflow carregado! Total de nós no grafo: {cnt}")
                            break
                    except Exception:
                        continue
                if loaded:
                    break
                time.sleep(2)
                if step % 5 == 0 and not is_login:
                    logger.info(f"⏳ Aguardando nós ({step+1}/120)...")

            if not loaded:
                logger.error(f"Tempo limite atingido aguardando o workflow {workflow_id}. Encerrando.")
                return benchmark_stats

            batch_count = 0
            while True:
                if not all_batches and batch_count >= max_batches:
                    break

                current_pending = queue_mgr.get_pending_prompts(batch_size=b_size)
                if account == 1 and not current_pending:
                    logger.info("🎉 Fila de prompts zerada! Nenhum prompt pendente.")
                    break

                batch_count += 1
                batch_prompts = [p.prompt_text for p in current_pending]
                expected_images = min(len(batch_prompts), b_size) if account == 1 else expected_images_c2

                # Fechar popups residuais antes da injeção
                close_unwanted_tabs(browser, workflow_id)
                dismiss_runninghub_popups(page)
                time.sleep(0.5)

                # 2. Injeção de Prompts (Conta 1 apenas)
                if account == 1 and target_nodes:
                    logger.info(f"📝 Injetando {len(batch_prompts)} prompts nos nós {target_nodes}...")
                    inject_res = comfy_frame.evaluate("""({targetNodeIds, prompts}) => {
                        if (typeof window.app === 'undefined' || !window.app.graph) return { error: "Graph not found" };
                        const canvas = window.app.canvas;
                        const firstNode = window.app.graph.getNodeById(targetNodeIds[0]);
                        if (canvas && firstNode) {
                            canvas.centerOnNode(firstNode);
                            canvas.selectNode(firstNode);
                        }
                        let pIdx = 0;
                        let filledCount = 0;
                        for (let id of targetNodeIds) {
                            let node = window.app.graph.getNodeById(id);
                            if (!node || !node.widgets) continue;
                            let promptWidgets = node.widgets.filter(w => w.name && (w.name.startsWith('prompt') || w.name.startsWith('text') || w.type === 'customtext'));
                            if (promptWidgets.length === 0) promptWidgets = node.widgets.slice(0, 5);
                            for (let w of promptWidgets) {
                                if (pIdx < prompts.length) {
                                    let text = prompts[pIdx];
                                    w.value = text;
                                    if (w.inputEl) {
                                        if (w.inputEl.parentElement) {
                                            w.inputEl.parentElement.style.display = 'block';
                                            w.inputEl.parentElement.style.visibility = 'visible';
                                            w.inputEl.parentElement.style.zIndex = '1000';
                                        }
                                        w.inputEl.value = text;
                                        w.inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                                        w.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                                    }
                                    if (typeof w.callback === 'function') {
                                        try { w.callback(text); } catch(e) {}
                                    }
                                    pIdx++;
                                    filledCount++;
                                } else {
                                    w.value = "";
                                    if (w.inputEl) {
                                        w.inputEl.value = "";
                                        w.inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                                        w.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                                    }
                                    if (typeof w.callback === 'function') {
                                        try { w.callback(""); } catch(e) {}
                                    }
                                }
                            }
                        }
                        if (firstNode && firstNode.widgets && firstNode.widgets[0] && firstNode.widgets[0].inputEl) {
                            firstNode.widgets[0].inputEl.focus();
                            firstNode.widgets[0].inputEl.click();
                        }
                        if (window.app.graph.setDirtyCanvas) window.app.graph.setDirtyCanvas(true, true);
                        if (canvas && canvas.draw) canvas.draw(true, true);
                        return { success: true, filledCount: filledCount };
                    }""", {"targetNodeIds": target_nodes, "prompts": batch_prompts})
                    logger.info(f"✅ Injeção concluída ({inject_res.get('filledCount', 0)} prompts preenchidos).")
                elif account == 2 and zip_path:
                    logger.info(f"📤 [Conta 2] Injetando pacote ZIP no Nó #{input_node} (Load Images (zip))...")
                    upload_success = upload_zip_to_node(page, comfy_frame, input_node, zip_path)
                    if upload_success:
                        logger.info(f"✅ Pacote ZIP ({zip_path.name}) carregado com sucesso no Nó #{input_node}!")
                    else:
                        logger.warning(f"⚠️ Upload do ZIP concluído no Nó #{input_node}.")
                    time.sleep(2.0)

                # Captura pré-existente no nó de saída
                initial_node_images = get_node_images(page, out_node)
                logger.info(f"Ignorando {len(initial_node_images)} imagens pré-existentes no Node #{out_node}.")

                # 3. Disparar Execução
                logger.info("Acionando 'Executar' (Lite/Plus)...")
                try:
                    btn = None
                    for sel in [
                        "xpath=//*[contains(text(), 'Lite/Plus')]/ancestor::button",
                        "xpath=//*[contains(text(), 'Lite/Plus')]/ancestor::*[contains(@class, 'btn')]",
                        "xpath=//*[contains(text(), 'Lite/Plus')]",
                        "button.beveled-btn-left.run-btn",
                        "button:has-text('Executar'), [role='button']:has-text('Executar')"
                    ]:
                        try:
                            candidates = page.locator(sel)
                            for c_idx in range(candidates.count()):
                                item = candidates.nth(c_idx)
                                if item.is_visible():
                                    btn = item
                                    break
                        except Exception:
                            pass
                        if btn:
                            break

                    if btn:
                        btn.click(timeout=5000)
                        logger.info("✅ Geração iniciada no RunningHub!")
                    else:
                        page.keyboard.press("Control+Enter")
                except Exception as e:
                    logger.error(f"Erro ao clicar em Executar: {e}")

                # 4. Estratégia de Captura (Diferenciada por Conta)
                batch_saved_files: List[str] = []
                batch_start_time = time.time()
                saved_srcs = set(initial_node_images)
                images_saved = 0

                from src.analyzer.qc_inspector import QCInspector
                qc_inspector = QCInspector(staging_dir=target_dir)

                # ── ESTRATÉGIA A: CONTA 1 (Batch All — Salva todas de uma vez) ──
                if save_mode == "batch_all":
                    logger.info(f"⏳ [Conta 1] Monitorando renderização de até {expected_images} imagens raw no Node #{out_node} (janela de 40 min)...")
                    last_check_time = batch_start_time
                    last_count = 0
                    last_progress_log = 0

                    while True:
                        page.keyboard.press("Escape")
                        current_node_images = get_node_images(page, out_node)
                        new_srcs = [s for s in current_node_images if s not in initial_node_images]
                        current_count = len(new_srcs)

                        # Atualizar timestamp de inatividade sempre que novas imagens forem renderizadas
                        if current_count > last_count:
                            last_check_time = time.time()
                            last_count = current_count
                            if current_count - last_progress_log >= 5 or current_count >= expected_images:
                                elapsed = time.time() - batch_start_time
                                logger.info(f"  • Progresso detectado: {current_count}/{expected_images} imagens prontas no Nó #{out_node} ({elapsed/60:.1f}m decorridos)...")
                                last_progress_log = current_count

                        # Se atingiu a meta de imagens esperadas
                        if current_count >= expected_images:
                            logger.info(f"🎯 Todas as {expected_images} imagens raw renderizadas no Node #{out_node}!")
                            break

                        # Timeout de inatividade (15 min sem NENHUMA nova imagem produzida)
                        if time.time() - last_check_time > 900:
                            logger.warning(f"⚠️ Timeout de inatividade (15 min sem novas imagens). Salvando as {current_count} imagens disponíveis...")
                            break

                        # Timeout de segurança absoluta por execução (45 min para garantir conclusão dos 40 min)
                        if time.time() - batch_start_time > 2700:
                            logger.warning(f"⚠️ Limite máximo de execução (45 min) atingido. Salvando {current_count} imagens prontas...")
                            break

                        time.sleep(3)

                    # Salvar todas as imagens raw de uma vez só em staging
                    logger.info(f"💾 [Conta 1] Gravando todas as {len(new_srcs)} imagens raw em disco ({target_dir})...")
                    for idx, src in enumerate(new_srcs[:expected_images]):
                        saved_name = save_image_from_src(page, src, destination_dir=target_dir, prefix=cfg["prefix"])
                        if saved_name:
                            images_saved += 1
                            batch_saved_files.append(saved_name)
                            # Registrar no QC
                            prompt_idx = idx
                            p_item = current_pending[prompt_idx] if prompt_idx < len(current_pending) else None
                            p_hash = p_item.prompt_hash if p_item else ""
                            p_text = p_item.prompt_text if p_item else ""
                            try:
                                qc_inspector.register_staging_image(filename=saved_name, prompt_hash=p_hash, prompt_text=p_text)
                            except Exception:
                                pass

                # ── ESTRATÉGIA B: CONTA 2 (Real-Time Single — 1 a 1 antes de sobrescrever) ──
                else:
                    logger.info(f"⚡ [Conta 2] Monitoramento contínuo no Nó #{out_node} (salvando 1 a 1 em tempo real sem timeout)...")
                    last_save_time = batch_start_time
                    last_heartbeat_time = batch_start_time

                    while images_saved < expected_images:
                        page.keyboard.press("Escape")
                        current_node_images = get_node_images(page, out_node)
                        new_srcs = [s for s in current_node_images if s not in saved_srcs]

                        for src in new_srcs:
                            # Salva IMEDIATAMENTE antes que a próxima imagem substitua o Nó #55
                            saved_name = save_image_from_src(page, src, destination_dir=target_dir, prefix=cfg["prefix"])
                            if saved_name:
                                images_saved += 1
                                batch_saved_files.append(saved_name)
                                saved_srcs.add(src)
                                last_save_time = time.time()
                                elapsed = last_save_time - batch_start_time
                                logger.info(f"📸 [SeedVR 8K #{images_saved}/{expected_images}] Salva: {saved_name} ({elapsed:.1f}s decorridos) — Garantida antes da sobrescrita!")

                                # Marcar no QC Manifest que esta imagem foi upscalada com sucesso pelo SeedVR
                                if account == 2 and approved_files and (images_saved - 1) < len(approved_files):
                                    source_name = approved_files[images_saved - 1]
                                    try:
                                        m = qc_inspector.get_manifest()
                                        if source_name in m:
                                            m[source_name]["upscaled_by_seedvr"] = True
                                            m[source_name]["final_seedvr_image"] = saved_name
                                            m[source_name]["upscaled"] = True
                                            qc_inspector.save_manifest(m)
                                            logger.info(f"  🔗 [QC Manifest] Mapeado: {source_name} ➔ {saved_name}")
                                    except Exception as err:
                                        logger.debug(f"Aviso ao atualizar manifest: {err}")

                            if images_saved >= expected_images:
                                logger.info(f"🎯 Última imagem ({images_saved}/{expected_images}) capturada com sucesso!")
                                logger.info("🛑 Cancelando tarefa ativa no RunningHub na última imagem antes de a tarefa acabar...")
                                cancel_runninghub_task(page)
                                break

                        if images_saved >= expected_images:
                            break

                        # Heartbeat a cada 60s (Timeout de inatividade desativado conforme diretiva operacional)
                        now = time.time()
                        if now - last_heartbeat_time >= 60:
                            last_heartbeat_time = now
                            mins_since_last = int((now - last_save_time) // 60)
                            secs_since_last = int((now - last_save_time) % 60)
                            total_mins = int((now - batch_start_time) // 60)
                            logger.info(
                                f"⏳ [Conta 2] Monitorando Nó #{out_node}... "
                                f"({images_saved}/{expected_images} salvas | "
                                f"{mins_since_last}m{secs_since_last:02d}s aguardando renderização 8K | "
                                f"{total_mins}m total)"
                            )

                        time.sleep(1.0)  # Polling agressivo a cada 1s para capturar a transição exata

                # 5. Relatório de Benchmark
                total_duration = time.time() - batch_start_time
                avg_sec = total_duration / max(images_saved, 1)
                mins = int(total_duration // 60)
                secs = int(total_duration % 60)
                proj_40m = int((40 * 60) / max(avg_sec, 1))

                print("\n" + "=" * 65)
                print(f"🏁 RELATÓRIO DE BENCHMARK — CONTA {account} ({cfg['role'].upper()}):")
                print(f"  • Imagens Salvas:       {images_saved}/{expected_images}")
                print(f"  • Modo de Captura:      {'BATCH (Todas de uma vez)' if save_mode == 'batch_all' else 'REAL-TIME 1 a 1 (Anti-overwrite)'}")
                print(f"  • Tempo Total do Lote:  {mins}m {secs}s ({total_duration:.1f}s)")
                print(f"  • Tempo Médio por Img:  {avg_sec:.1f}s/imagem")
                print(f"  • Projeção em 40 min:   ~{proj_40m} imagens por sessão")
                print(f"  • Pasta Destino:        {target_dir}")
                print("=" * 65 + "\n")

                benchmark_stats["batches_completed"] += 1
                benchmark_stats["total_images_saved"] += images_saved
                benchmark_stats["total_duration_sec"] += total_duration
                benchmark_stats["avg_sec_per_image"] = avg_sec
                benchmark_stats["saved_files"].extend(batch_saved_files)

                # Cancelar tarefa residual para não consumir créditos extras
                if images_saved >= expected_images:
                    cancel_runninghub_task(page)

                if account == 1:
                    queue_mgr.mark_prompts_generated(current_pending[:images_saved], saved_images=batch_saved_files)

                if images_saved == 0:
                    break

            return benchmark_stats

        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RunningHub ComfyUI Automation Bot (Dual-Account)")
    parser.add_argument("--account", type=int, default=1, choices=[1, 2], help="RunningHub Account: 1 (Raw Producer) or 2 (SeedVR 8K Upscaler)")
    parser.add_argument("--node", type=int, default=None, help="Output Node ID (default: 121 for Conta 1, 55 for Conta 2)")
    parser.add_argument("--batch-size", type=int, default=210, help="Number of images per batch (default: 210)")
    parser.add_argument("--batches", type=int, default=1, help="Number of consecutive batches (default: 1)")
    parser.add_argument("--all-batches", action="store_true", help="Run until queue is exhausted")
    args = parser.parse_args()

    run_factory_bot(
        account=args.account,
        output_node_id=args.node,
        batch_size=args.batch_size,
        max_batches=args.batches,
        all_batches=args.all_batches,
    )
