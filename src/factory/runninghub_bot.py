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
FINAL_VIDEOS_DIR: Path = BASE_DIR / "data" / "final" / "videos"
STAGING_VIDEOS_DIR: Path = BASE_DIR / "data" / "staging" / "videos"
VIDEO_PROMPTS_FILE: Path = BASE_DIR / "data" / "processed" / "video_prompts.json"

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
    "execute_mode": "standard",
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
    "execute_mode": "standard",
}

# Video Pipeline: Geração e Upscale com Output Final em 4K
CONTA_VIDEO_CONFIG = {
    "account": 3,
    "role": "video_generator_4k",
    "workflow_url": os.getenv("RUNNINGHUB_VIDEO_WORKFLOW_URL", "https://www.runninghub.ai/pt-br/workflow/2115926169974812674?source=workspace"),
    "workflow_id": os.getenv("RUNNINGHUB_VIDEO_WORKFLOW_ID", "2115926169974812674"),
    "input_image_node": int(os.getenv("RUNNINGHUB_VIDEO_INPUT_NODE", "164")),  # Load Image: node #164
    "input_node": int(os.getenv("RUNNINGHUB_VIDEO_INPUT_NODE", "164")),
    "prompt_node": int(os.getenv("RUNNINGHUB_VIDEO_PROMPT_NODE", "17")),       # Prompt: node #17
    "output_video_node": int(os.getenv("RUNNINGHUB_VIDEO_OUTPUT_NODE", "157")),# Save video/video combine: node #157
    "output_node": int(os.getenv("RUNNINGHUB_VIDEO_OUTPUT_NODE", "157")),
    "prompt_nodes": [int(os.getenv("RUNNINGHUB_VIDEO_PROMPT_NODE", "17"))],
    "default_batch_size": 1,
    "destination_dir": FINAL_VIDEOS_DIR,
    "prefix": "final_4k_video",
    "save_mode": "video_output",
    "session_dir_name": "playwright_session_video",
    "upload_wait_sec": int(os.getenv("RUNNINGHUB_IMAGE_UPLOAD_WAIT_SEC", "30")),
    "execute_mode": "lite_plus",  # Botão do meio (Lite/Plus - cor amarela/ouro) mandatário para Vídeo 4K
}

# Default Active Configuration (Padrão: Conta 1 - Raw Producer)
DEFAULT_ACCOUNT: int = int(os.getenv("RUNNINGHUB_ACCOUNT", "1"))
DEFAULT_BATCH_SIZE: int = 210
DEFAULT_IMAGE_UPLOAD_WAIT_SEC: int = int(os.getenv("RUNNINGHUB_IMAGE_UPLOAD_WAIT_SEC", "30"))
DEFAULT_OUTPUT_NODE: int = 121
DEFAULT_PROMPT_NODES: List[int] = CONTA_1_PROMPT_NODES
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 800

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger: logging.Logger = logging.getLogger(__name__)


def get_account_config(account: Union[int, str] = 1) -> Dict[str, Any]:
    """Retorna o dicionário de configuração da conta selecionada ou do pipeline de vídeo."""
    acc_str = str(account).lower()
    if acc_str in ("2", "upscale", "seedvr"):
        return dict(CONTA_2_CONFIG)
    elif acc_str in ("3", "video", "video_4k", "video_generator_4k"):
        return dict(CONTA_VIDEO_CONFIG)
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



def upload_image_to_node(page: Page, frame: Optional[Frame], node_id: int, image_path: Path) -> bool:
    """
    Injeta uma imagem de referência no Nó ComfyUI especificado (ex: Nó #164 'Load Image').
    Aplica arquitetura multi-camadas de injeção e upload com verificação remota:
    1. ComfyUI API Upload via window.app.api.uploadImage() e window.app.api.fetchApi('/upload/image')
    2. ComfyUI API URL Discovery via window.app.api.apiURL('/upload/image')
    3. FileChooser nativo do Playwright disparado via clique nas coordenadas do botão do Nó
    4. DOM input[type='file'] no frame com despacho de DataTransfer e change event
    5. Sincronização do widget LiteGraph com inclusão obrigatória em options.values (prevenção de validação)
    6. Confirmação do arquivo via GET /view?filename=... no backend ComfyUI
    """
    logger.info(f"📤 Injetando imagem de referência ({image_path.name}) no Nó #{node_id}...")
    target_frame = frame or page.main_frame
    uploaded = False

    # 1. Certificar que nenhum modal/toast prévio esteja bloqueando
    dismiss_runninghub_popups(page)

    # 2. Upload via API nativa do ComfyUI (window.app.api) com verificação de status HTTP 200
    try:
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        api_res = target_frame.evaluate("""async ({ nodeId, filename, b64Data, mimeType }) => {
            const result = {
                apiSuccess: false,
                uploadedName: null,
                backendConfirmed: false,
                nodeConfigured: false,
                errors: [],
                log: []
            };

            let fileObj = null;
            try {
                const byteCharacters = atob(b64Data);
                const byteNumbers = new Uint8Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const blob = new Blob([byteNumbers], { type: mimeType });
                fileObj = new File([blob], filename, { type: mimeType, lastModified: Date.now() });
            } catch (e) {
                result.errors.push("Erro ao criar File/Blob: " + e.message);
                return result;
            }

            // TENTATIVA 1: window.app.api.uploadImage (função nativa oficial do ComfyUI)
            if (window.app && window.app.api && typeof window.app.api.uploadImage === 'function') {
                try {
                    const resp = await window.app.api.uploadImage(fileObj, '', true);
                    if (resp && resp.name) {
                        result.uploadedName = resp.name;
                        result.apiSuccess = true;
                        result.log.push("Upload via app.api.uploadImage com sucesso: " + resp.name);
                    }
                } catch (e) {
                    result.errors.push("uploadImage falhou: " + e.message);
                }
            }

            // TENTATIVA 2: window.app.api.fetchApi('/upload/image') com headers e host do ComfyUI
            if (!result.apiSuccess && window.app && window.app.api && typeof window.app.api.fetchApi === 'function') {
                try {
                    const formData = new FormData();
                    formData.append('image', fileObj);
                    formData.append('overwrite', 'true');
                    formData.append('type', 'input');

                    const resp = await window.app.api.fetchApi('/upload/image', {
                        method: 'POST',
                        body: formData
                    });
                    if (resp && (resp.ok || resp.status === 200)) {
                        const data = await resp.json();
                        if (data && data.name) {
                            result.uploadedName = data.name;
                            result.apiSuccess = true;
                            result.log.push("Upload via app.api.fetchApi('/upload/image') com sucesso: " + data.name);
                        }
                    } else if (resp) {
                        result.errors.push("fetchApi status: " + resp.status + " " + resp.statusText);
                    }
                } catch (e) {
                    result.errors.push("fetchApi falhou: " + e.message);
                }
            }

            // TENTATIVA 3: fetch com URL resolvida por window.app.api.apiURL('/upload/image')
            if (!result.apiSuccess && window.app && window.app.api && typeof window.app.api.apiURL === 'function') {
                try {
                    const uploadUrl = window.app.api.apiURL('/upload/image');
                    const formData = new FormData();
                    formData.append('image', fileObj);
                    formData.append('overwrite', 'true');
                    formData.append('type', 'input');

                    const resp = await fetch(uploadUrl, {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    });
                    if (resp && (resp.ok || resp.status === 200)) {
                        const data = await resp.json();
                        if (data && data.name) {
                            result.uploadedName = data.name;
                            result.apiSuccess = true;
                            result.log.push("Upload via apiURL ('" + uploadUrl + "') com sucesso: " + data.name);
                        }
                    } else if (resp) {
                        result.errors.push("apiURL fetch status: " + resp.status + " " + resp.statusText);
                    }
                } catch (e) {
                    result.errors.push("apiURL fetch falhou: " + e.message);
                }
            }

            // TENTATIVA 4: window.app.handleFile(fileObj) (ComfyUI drag & drop handler)
            if (!result.apiSuccess && window.app && typeof window.app.handleFile === 'function') {
                try {
                    if (window.app.graph) {
                        const targetNode = window.app.graph.getNodeById(nodeId);
                        if (targetNode && window.app.canvas) {
                            window.app.canvas.centerOnNode(targetNode);
                            window.app.canvas.selectNode(targetNode);
                        }
                    }
                    await window.app.handleFile(fileObj);
                    result.log.push("Disparado window.app.handleFile()");
                    result.apiSuccess = true;
                    result.uploadedName = filename;
                } catch (e) {
                    result.errors.push("handleFile falhou: " + e.message);
                }
            }

            // TENTATIVA 5: Input elements no DOM via DataTransfer
            if (!result.apiSuccess) {
                try {
                    const fileInputs = Array.from(document.querySelectorAll("input[type='file']"));
                    for (const inp of fileInputs) {
                        const dt = new DataTransfer();
                        dt.items.add(fileObj);
                        inp.files = dt.files;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        result.log.push("Disparado DataTransfer em input[type='file']");
                    }
                } catch (e) {
                    result.errors.push("DOM DataTransfer falhou: " + e.message);
                }
            }

            // TENTATIVA 6: Fallback fetch no endpoint relativo
            if (!result.apiSuccess) {
                for (const fallbackPath of ['/upload/image', '/api/upload/image']) {
                    try {
                        const formData = new FormData();
                        formData.append('image', fileObj);
                        formData.append('overwrite', 'true');
                        formData.append('type', 'input');

                        const resp = await fetch(fallbackPath, {
                            method: 'POST',
                            body: formData,
                            credentials: 'include'
                        });
                        if (resp && (resp.ok || resp.status === 200)) {
                            const data = await resp.json();
                            if (data && data.name) {
                                result.uploadedName = data.name;
                                result.apiSuccess = true;
                                result.log.push("Upload via fallback path ('" + fallbackPath + "') com sucesso: " + data.name);
                                break;
                            }
                        }
                    } catch (e) {}
                }
            }

            const finalName = result.uploadedName || filename;

            // CONFIGURAÇÃO DO NÓ #nodeId NO GRAFO COMFYUI
            if (typeof window.app !== 'undefined' && window.app.graph) {
                const node = window.app.graph.getNodeById(nodeId);
                if (node) {
                    if (window.app.canvas) {
                        window.app.canvas.centerOnNode(node);
                        window.app.canvas.selectNode(node);
                    }
                    if (node.widgets) {
                        for (let w of node.widgets) {
                            if (w.name && (w.name.toLowerCase().includes('image') || w.name.toLowerCase().includes('file') || w.type === 'combo' || w.type === 'customtext')) {
                                // MANDATÓRIO: Registrar finalName em w.options.values para passar na validação estrita do ComfyUI
                                if (w.options && Array.isArray(w.options.values)) {
                                    if (!w.options.values.includes(finalName)) {
                                        w.options.values.push(finalName);
                                    }
                                }
                                w.value = finalName;
                                if (w.inputEl) {
                                    w.inputEl.value = finalName;
                                    w.inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                                    w.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                                if (typeof w.callback === 'function') {
                                    try { w.callback(finalName); } catch (e) {}
                                }
                                result.nodeConfigured = true;
                            }
                        }
                    }

                    // Tentar anexar à propriedade de upload se disponível
                    if (node.fileInput) {
                        try {
                            const dt = new DataTransfer();
                            dt.items.add(fileObj);
                            node.fileInput.files = dt.files;
                            node.fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                        } catch (e) {}
                    }

                    if (window.app.graph.setDirtyCanvas) window.app.graph.setDirtyCanvas(true, true);
                    if (window.app.canvas && window.app.canvas.draw) window.app.canvas.draw(true, true);
                }
            }

            // VERIFICAÇÃO REMOTA NO BACKEND COMFYUI
            if (window.app && window.app.api && typeof window.app.api.fetchApi === 'function') {
                try {
                    const checkResp = await window.app.api.fetchApi('/view?filename=' + encodeURIComponent(finalName) + '&type=input');
                    if (checkResp && (checkResp.ok || checkResp.status === 200)) {
                        result.backendConfirmed = true;
                        result.log.push("Arquivo verificado e confirmado no backend ComfyUI (/view?filename=" + finalName + ")!");
                    }
                } catch (e) {}
            }

            return result;
        }""", {"nodeId": node_id, "filename": image_path.name, "b64Data": b64_img, "mimeType": mime})

        if api_res:
            for l_msg in api_res.get("log", []):
                logger.info(f"  [Upload Nó #{node_id}] {l_msg}")
            if api_res.get("apiSuccess") or api_res.get("backendConfirmed"):
                logger.info(f"🎯 Imagem de referência ({api_res.get('uploadedName') or image_path.name}) confirmada e validada no Nó #{node_id}!")
                uploaded = True
            elif api_res.get("nodeConfigured"):
                logger.warning(f"⚠️ Widget do Nó #{node_id} configurado, mas sem confirmação explícita da API: {api_res.get('errors')}")
                uploaded = True
    except Exception as e:
        logger.debug(f"Aviso no upload via API ComfyUI do Nó #{node_id}: {e}")

    # 3. Fallback: FileChooser nativo do Playwright disparado via clique no botão do Nó
    if not uploaded:
        try:
            button_coords = target_frame.evaluate("""(nodeId) => {
                const node = window.app && window.app.graph ? window.app.graph.getNodeById(nodeId) : null;
                if (!node || !window.app.canvas) return null;
                window.app.canvas.centerOnNode(node);
                const canvas = window.app.canvas;
                const rect = canvas.canvas.getBoundingClientRect();
                let uploadWidget = null;
                let widgetIdx = 1;
                if (node.widgets) {
                    for (let i = 0; i < node.widgets.length; i++) {
                        const w = node.widgets[i];
                        if (w.type === 'button' || (w.name && w.name.toLowerCase().includes('upload'))) {
                            uploadWidget = w;
                            widgetIdx = i;
                            break;
                        }
                    }
                }
                const widgetY = (uploadWidget && uploadWidget.last_y) ? uploadWidget.last_y : (30 + widgetIdx * 25);
                const graphX = node.pos[0] + (node.size[0] / 2);
                const graphY = node.pos[1] + widgetY + 10;
                const screenX = rect.left + (graphX + canvas.ds.offset[0]) * canvas.ds.scale;
                const screenY = rect.top + (graphY + canvas.ds.offset[1]) * canvas.ds.scale;
                return { x: screenX, y: screenY };
            }""", node_id)

            if button_coords and "x" in button_coords:
                with page.expect_file_chooser(timeout=3500) as fc_info:
                    page.mouse.click(button_coords["x"], button_coords["y"])
                fc = fc_info.value
                fc.set_files(str(image_path))
                logger.info(f"🎯 Imagem injetada via clique direto no botão e FileChooser no Nó #{node_id}.")
                uploaded = True
        except Exception as e:
            logger.debug(f"Aviso no clique de FileChooser do Nó #{node_id}: {e}")

    # 4. Fallback: Inputs file no DOM de todos os frames
    if not uploaded:
        try:
            for f in page.frames:
                inputs = f.locator("input[type='file']")
                cnt = inputs.count()
                if cnt > 0:
                    for i in range(cnt):
                        try:
                            inputs.nth(i).set_input_files(str(image_path))
                            logger.info(f"🎯 Imagem injetada via input[type='file'] no frame {f.name or 'default'}.")
                            uploaded = True
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Aviso no input file do DOM: {e}")

    return uploaded


def inject_video_prompt_to_node(frame: Frame, node_id: int, prompt_text: str) -> bool:
    """Injeta o texto do prompt no nó de texto especificado (Nó #17)."""
    try:
        res = frame.evaluate("""({nodeId, text}) => {
            if (typeof window.app === 'undefined' || !window.app.graph) return false;
            const node = window.app.graph.getNodeById(nodeId);
            if (!node || !node.widgets) return false;
            if (window.app.canvas) {
                window.app.canvas.centerOnNode(node);
                window.app.canvas.selectNode(node);
            }
            let targetWidget = node.widgets.find(w => w.name && (w.name.startsWith('prompt') || w.name.startsWith('text') || w.type === 'customtext'));
            if (!targetWidget && node.widgets.length > 0) targetWidget = node.widgets[0];
            if (targetWidget) {
                targetWidget.value = text;
                if (targetWidget.inputEl) {
                    if (targetWidget.inputEl.parentElement) {
                        targetWidget.inputEl.parentElement.style.display = 'block';
                        targetWidget.inputEl.parentElement.style.visibility = 'visible';
                    }
                    targetWidget.inputEl.value = text;
                    targetWidget.inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                    targetWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                }
                if (typeof targetWidget.callback === 'function') {
                    try { targetWidget.callback(text); } catch(e) {}
                }
                if (window.app.graph.setDirtyCanvas) window.app.graph.setDirtyCanvas(true, true);
                if (window.app.canvas && window.app.canvas.draw) window.app.canvas.draw(true, true);
                return true;
            }
            return false;
        }""", {"nodeId": node_id, "text": prompt_text})
        return bool(res)
    except Exception as e:
        logger.warning(f"Erro ao injetar prompt no nó #{node_id}: {e}")
        return False


def get_node_videos(page: Page, node_id: int) -> List[str]:
    """Extrai URLs ou referências de vídeos gerados estritamente no nó de saída (#157) do ComfyUI/LiteGraph, ignorando elementos marcados como pré-existentes."""
    node_videos = []
    for frame in page.frames:
        try:
            vids = frame.evaluate("""(id) => {
                let res = [];
                if (typeof window.app !== 'undefined' && window.app.graph) {
                    let node = window.app.graph.getNodeById(id);
                    if (node) {
                        if (node.video && (node.video.src || node.video.currentSrc)) {
                            const isOld = node.video.getAttribute && node.video.getAttribute('data-pre-existing') === 'true';
                            if (!isOld) res.push(node.video.src || node.video.currentSrc);
                        }
                        if (node.imgs && node.imgs.length > 0) {
                            res.push(...node.imgs.map(i => i.src || i.currentSrc).filter(Boolean));
                        }
                        if (node.widgets) {
                            for (let w of node.widgets) {
                                if (w.element && (w.element.tagName === 'VIDEO' || (w.element.querySelector && w.element.querySelector('video')))) {
                                    let v = w.element.tagName === 'VIDEO' ? w.element : w.element.querySelector('video');
                                    const isOld = v && v.getAttribute && v.getAttribute('data-pre-existing') === 'true';
                                    if (v && !isOld && (v.src || v.currentSrc)) {
                                        res.push(v.src || v.currentSrc);
                                    }
                                }
                                if (w.value && typeof w.value === 'string' && (w.value.endsWith('.mp4') || w.value.endsWith('.webm') || w.value.endsWith('.mov'))) {
                                    res.push('/view?filename=' + encodeURIComponent(w.value) + '&type=output');
                                }
                            }
                        }
                    }
                }
                return Array.from(new Set(res.filter(Boolean)));
            }""", node_id)
            if vids:
                node_videos.extend(vids)
        except Exception:
            pass
    return list(dict.fromkeys(node_videos))


def save_video_from_src(
    page: Page,
    src: str,
    destination_dir: Optional[Path] = None,
    prefix: str = "final_4k_video",
) -> Optional[str]:
    """Salva o vídeo do canvas/DOM/blob em disco de forma transacional (.tmp) (ADR-02)."""
    target_dir = destination_dir or FINAL_VIDEOS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = target_dir / f"{prefix}_{uuid.uuid4().hex[:8]}.mp4"
    while filename.exists():
        filename = target_dir / f"{prefix}_{uuid.uuid4().hex[:8]}.mp4"
    tmp_filename = filename.with_suffix(".tmp")

    try:
        data: Optional[bytes] = None
        if src.startswith("data:video"):
            header, encoded = src.split(",", 1)
            raw_data = base64.b64decode(encoded)
            if len(raw_data) > 50000:
                data = raw_data
        elif src.startswith("blob:") or src.startswith("http") or src.startswith("/"):
            # Extrair dentro do contexto autenticado do navegador
            for frame in page.frames:
                try:
                    b64_url = frame.evaluate("""async (url) => {
                        try {
                            const resp = await fetch(url, { credentials: 'include' });
                            if (!resp.ok) return null;
                            const blob = await resp.blob();
                            return new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.onerror = () => resolve(null);
                                reader.readAsDataURL(blob);
                            });
                        } catch (e) {
                            return null;
                        }
                    }""", src)
                    if b64_url and "," in b64_url:
                        header, encoded = b64_url.split(",", 1)
                        raw_data = base64.b64decode(encoded)
                        if len(raw_data) > 50000:
                            data = raw_data
                            break
                except Exception:
                    pass

            if data is None and src.startswith("http"):
                try:
                    req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=30) as response:
                        http_data = response.read()
                        if len(http_data) > 50000:
                            data = http_data
                except Exception:
                    pass

        if data:
            with open(tmp_filename, "wb") as f:
                f.write(data)
            tmp_filename.replace(filename)
            logger.info("🎬 Vídeo 4K gravado com sucesso: %s (%d KB)", filename.name, len(data) // 1024)
            return filename.name
    except Exception as e:
        logger.error("Erro ao salvar vídeo de '%s': %s", src[:60], e)
        if tmp_filename.exists():
            try:
                tmp_filename.unlink()
            except Exception:
                pass
    return None

def upload_zip_to_node(page: Page, frame: Optional[Frame], node_id: int, zip_path: Path) -> bool:
    """
    Injeta o arquivo ZIP empacotado no Nó ComfyUI (ex: Nó #5 'Load Images (zip)').
    Aplica arquitetura multi-camadas de injeção e upload com verificação remota:
    1. ComfyUI API Upload via window.app.api.uploadImage() e window.app.api.fetchApi('/upload/image')
    2. ComfyUI API URL Discovery via window.app.api.apiURL('/upload/image')
    3. FileChooser nativo do Playwright disparado via clique nas coordenadas do botão do Nó
    4. DOM input[type='file'] no frame com despacho de DataTransfer e change event
    5. Sincronização do widget LiteGraph com inclusão obrigatória em options.values
    6. Confirmação do arquivo via GET /view?filename=... no backend ComfyUI
    """
    logger.info(f"📤 Iniciando upload do arquivo ZIP ({zip_path.name}) no Nó #{node_id}...")
    target_frame = frame or page.main_frame
    uploaded = False

    # 1. Certificar que nenhum modal/toast prévio esteja bloqueando
    dismiss_runninghub_popups(page)

    # 2. Upload via API nativa do ComfyUI (window.app.api) com verificação de status HTTP 200
    try:
        with open(zip_path, "rb") as f:
            b64_zip = base64.b64encode(f.read()).decode("utf-8")

        api_res = target_frame.evaluate("""async ({ nodeId, filename, b64Data }) => {
            const result = {
                apiSuccess: false,
                uploadedName: null,
                backendConfirmed: false,
                nodeConfigured: false,
                errors: [],
                log: []
            };

            let fileObj = null;
            try {
                const byteCharacters = atob(b64Data);
                const byteNumbers = new Uint8Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const blob = new Blob([byteNumbers], { type: 'application/zip' });
                fileObj = new File([blob], filename, { type: 'application/zip', lastModified: Date.now() });
            } catch (e) {
                result.errors.push("Erro ao criar File/Blob ZIP: " + e.message);
                return result;
            }

            // TENTATIVA 1: window.app.api.uploadImage
            if (window.app && window.app.api && typeof window.app.api.uploadImage === 'function') {
                try {
                    const resp = await window.app.api.uploadImage(fileObj, '', true);
                    if (resp && resp.name) {
                        result.uploadedName = resp.name;
                        result.apiSuccess = true;
                        result.log.push("ZIP upload via app.api.uploadImage com sucesso: " + resp.name);
                    }
                } catch (e) {
                    result.errors.push("uploadImage ZIP falhou: " + e.message);
                }
            }

            // TENTATIVA 2: window.app.api.fetchApi('/upload/image')
            if (!result.apiSuccess && window.app && window.app.api && typeof window.app.api.fetchApi === 'function') {
                try {
                    const formData = new FormData();
                    formData.append('image', fileObj);
                    formData.append('overwrite', 'true');
                    formData.append('type', 'input');

                    const resp = await window.app.api.fetchApi('/upload/image', {
                        method: 'POST',
                        body: formData
                    });
                    if (resp && (resp.ok || resp.status === 200)) {
                        const data = await resp.json();
                        if (data && data.name) {
                            result.uploadedName = data.name;
                            result.apiSuccess = true;
                            result.log.push("ZIP upload via app.api.fetchApi('/upload/image') com sucesso: " + data.name);
                        }
                    } else if (resp) {
                        result.errors.push("fetchApi status: " + resp.status + " " + resp.statusText);
                    }
                } catch (e) {
                    result.errors.push("fetchApi falhou: " + e.message);
                }
            }

            // TENTATIVA 3: fetch com URL resolvida por window.app.api.apiURL('/upload/image')
            if (!result.apiSuccess && window.app && window.app.api && typeof window.app.api.apiURL === 'function') {
                try {
                    const uploadUrl = window.app.api.apiURL('/upload/image');
                    const formData = new FormData();
                    formData.append('image', fileObj);
                    formData.append('overwrite', 'true');
                    formData.append('type', 'input');

                    const resp = await fetch(uploadUrl, {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    });
                    if (resp && (resp.ok || resp.status === 200)) {
                        const data = await resp.json();
                        if (data && data.name) {
                            result.uploadedName = data.name;
                            result.apiSuccess = true;
                            result.log.push("ZIP upload via apiURL ('" + uploadUrl + "') com sucesso: " + data.name);
                        }
                    } else if (resp) {
                        result.errors.push("apiURL fetch status: " + resp.status + " " + resp.statusText);
                    }
                } catch (e) {
                    result.errors.push("apiURL fetch falhou: " + e.message);
                }
            }

            // TENTATIVA 4: Input elements no DOM via DataTransfer
            if (!result.apiSuccess) {
                try {
                    const fileInputs = Array.from(document.querySelectorAll("input[type='file']"));
                    for (const inp of fileInputs) {
                        const dt = new DataTransfer();
                        dt.items.add(fileObj);
                        inp.files = dt.files;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        result.log.push("Disparado DataTransfer ZIP em input[type='file']");
                    }
                } catch (e) {
                    result.errors.push("DOM DataTransfer falhou: " + e.message);
                }
            }

            const finalName = result.uploadedName || filename;

            // CONFIGURAÇÃO DO NÓ #nodeId NO GRAFO COMFYUI
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
                                if (w.options && Array.isArray(w.options.values)) {
                                    if (!w.options.values.includes(finalName)) {
                                        w.options.values.push(finalName);
                                    }
                                }
                                w.value = finalName;
                                if (w.inputEl) {
                                    w.inputEl.value = finalName;
                                    w.inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                                    w.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                                if (typeof w.callback === 'function') {
                                    try { w.callback(finalName); } catch (e) {}
                                }
                                result.nodeConfigured = true;
                            }
                        }
                    }

                    if (window.app.graph.setDirtyCanvas) window.app.graph.setDirtyCanvas(true, true);
                    if (window.app.canvas && window.app.canvas.draw) window.app.canvas.draw(true, true);
                }
            }

            // VERIFICAÇÃO REMOTA NO BACKEND COMFYUI
            if (window.app && window.app.api && typeof window.app.api.fetchApi === 'function') {
                try {
                    const checkResp = await window.app.api.fetchApi('/view?filename=' + encodeURIComponent(finalName) + '&type=input');
                    if (checkResp && (checkResp.ok || checkResp.status === 200)) {
                        result.backendConfirmed = true;
                        result.log.push("Arquivo ZIP verificado e confirmado no backend ComfyUI (/view?filename=" + finalName + ")!");
                    }
                } catch (e) {}
            }

            return result;
        }""", {"nodeId": node_id, "filename": zip_path.name, "b64Data": b64_zip})

        if api_res:
            for l_msg in api_res.get("log", []):
                logger.info(f"  [Upload Nó #{node_id}] {l_msg}")
            if api_res.get("apiSuccess") or api_res.get("backendConfirmed"):
                logger.info(f"🎯 Arquivo ZIP ({api_res.get('uploadedName') or zip_path.name}) confirmado e validado no Nó #{node_id}!")
                uploaded = True
            elif api_res.get("nodeConfigured"):
                logger.warning(f"⚠️ Widget do Nó #{node_id} configurado com ZIP, mas sem confirmação explícita da API: {api_res.get('errors')}")
                uploaded = True
    except Exception as e:
        logger.debug(f"Aviso no fallback de API do Nó #{node_id}: {e}")

    # 3. Fallback: FileChooser nativo do Playwright
    if not uploaded:
        try:
            with page.expect_file_chooser(timeout=3500) as fc_info:
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

    # 4. Fallback: Inputs file no DOM
    if not uploaded:
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
        "xpath=//*[contains(text(), 'Node threw an error')]/ancestor::div//button",
        "xpath=//*[contains(text(), 'Incorrect values') or contains(text(), 'Custom validation failed')]/ancestor::div//button",
        "xpath=//*[contains(text(), 'Incorrect values') or contains(text(), 'Custom validation failed')]/ancestor::*[contains(@class, 'modal') or contains(@class, 'dialog') or position()<=3]//*[contains(@class, 'close') or text()='×' or text()='X']",
        "xpath=//*[contains(text(), 'Custom validation failed')]/following-sibling::*[contains(@class, 'close')]",
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
        ".comfy-modal-close",
        ".comfy-modal button",
        ".comfy-modal svg",
        "xpath=//*[contains(text(), 'Node threw an error')]/ancestor::div//button",
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


def click_runninghub_execute(page: Page, mode: str = "lite_plus") -> bool:
    """
    Localiza e aciona o botão de execução correto no RunningHub:
    - 'lite_plus': Botão do meio (Lite/Plus - cor dourada/laranja), mandatário para o Pipeline de Vídeo 4K.
    - 'standard': Botão da esquerda (Lite/Standard - cor verde/ciano).
    - 'ultra': Botão da direita (Ultra-6000D - cor vermelha).
    """
    logger.info(f"🎯 Acionando botão de execução RunningHub [Modo: {mode.upper()}]...")
    clicked = False

    # 1. Tentar via JavaScript inteligente no contexto da página:
    # Identifica o label/badge do modo ('Lite/Plus', 'Lite/Standard', etc.) e associa geometricamente ao botão
    try:
        res = page.evaluate("""(targetMode) => {
            const mode = (targetMode || 'lite_plus').toLowerCase();
            const targetBadgeText = mode === 'lite_plus' ? 'Lite/Plus' : (mode === 'ultra' ? 'Ultra' : 'Standard');

            // 1. Localizar elemento badge com o texto do modo
            const allElements = Array.from(document.querySelectorAll("*"));
            const badgeEl = allElements.find(el => {
                const t = (el.innerText || el.textContent || '').trim();
                return t === targetBadgeText || t.includes(targetBadgeText);
            });

            // Coletar todos os botões de execução visíveis na barra superior
            const allBtns = Array.from(document.querySelectorAll("button, [role='button'], .run-btn, .beveled-btn-left, .beveled-btn-middle, .beveled-btn-center, .beveled-btn-right"));
            const runBtns = allBtns.filter(b => {
                if (b.offsetParent === null && b.offsetWidth === 0) return false;
                const txt = (b.innerText || b.textContent || '').trim();
                const rect = b.getBoundingClientRect();
                return rect.top < 200 && rect.width > 20 && (txt.includes('Executar') || txt.includes('Run') || b.className.includes('run-btn') || b.className.includes('beveled-btn'));
            });

            // Se encontramos o badge, encontrar o botão correspondente
            if (badgeEl) {
                // Caso A: O próprio badge está dentro do botão
                const parentBtn = badgeEl.closest("button, [role='button'], .run-btn");
                if (parentBtn) {
                    parentBtn.click();
                    const r = parentBtn.getBoundingClientRect();
                    return { success: true, method: 'closest_button', x: r.left + r.width / 2, y: r.top + r.height / 2 };
                }

                // Caso B: O botão é irmão ou filho do mesmo container pai (até 4 níveis)
                let parent = badgeEl.parentElement;
                for (let i = 0; i < 4 && parent; i++) {
                    const btn = parent.querySelector("button, [role='button'], .run-btn");
                    if (btn && (btn.innerText || btn.textContent || '').includes('Executar')) {
                        btn.click();
                        const r = btn.getBoundingClientRect();
                        return { success: true, method: 'container_button', x: r.left + r.width / 2, y: r.top + r.height / 2 };
                    }
                    parent = parent.parentElement;
                }

                // Caso C: Proximidade geométrica (o botão imediatamente abaixo do badge)
                const badgeRect = badgeEl.getBoundingClientRect();
                let closest = null;
                let minDist = Infinity;
                for (const b of runBtns) {
                    const bRect = b.getBoundingClientRect();
                    const dx = (bRect.left + bRect.width / 2) - (badgeRect.left + badgeRect.width / 2);
                    const dy = bRect.top - badgeRect.bottom;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < minDist) {
                        minDist = dist;
                        closest = b;
                    }
                }
                if (closest && minDist < 200) {
                    closest.click();
                    const r = closest.getBoundingClientRect();
                    return { success: true, method: 'geometrical_closest_to_badge', x: r.left + r.width / 2, y: r.top + r.height / 2, dist: minDist };
                }
            }

            // 2. Se for 'lite_plus' (botão do MEIO) e tivermos botões na barra superior:
            // Ordenar da esquerda para a direita
            if (runBtns.length >= 3) {
                runBtns.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                // runBtns[0] = Standard (esquerda)
                // runBtns[1] = Lite/Plus (MEIO)
                // runBtns[2] = Ultra (direita)
                const targetBtn = mode === 'lite_plus' ? runBtns[1] : (mode === 'ultra' ? runBtns[2] : runBtns[0]);
                targetBtn.click();
                const r = targetBtn.getBoundingClientRect();
                return { success: true, method: 'segmented_order_' + mode, index: mode === 'lite_plus' ? 1 : 0, x: r.left + r.width / 2, y: r.top + r.height / 2 };
            } else if (runBtns.length === 2 && mode === 'lite_plus') {
                // Se só tem 2, o Lite/Plus é o segundo
                runBtns.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                runBtns[1].click();
                const r = runBtns[1].getBoundingClientRect();
                return { success: true, method: 'second_of_two', x: r.left + r.width / 2, y: r.top + r.height / 2 };
            }

            // 3. Classes específicas do RunningHub
            if (mode === 'lite_plus') {
                for (const sel of [
                    '.beveled-btn-center',
                    '.beveled-btn-middle',
                    '.beveled-btn-mid',
                    '[class*="btn-center"]',
                    '[class*="btn-middle"]'
                ]) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {
                        el.click();
                        const r = el.getBoundingClientRect();
                        return { success: true, method: 'class_' + sel, x: r.left + r.width / 2, y: r.top + r.height / 2 };
                    }
                }
            }

            return { success: false };
        }""", mode)

        if res and res.get("success"):
            logger.info(f"✅ Botão Executar [{mode.upper()}] acionado via DOM evaluate ({res.get('method')})!")
            clicked = True
            # Também enviar clique via Playwright mouse nas coordenadas para garantir disparo de todos os event listeners
            if "x" in res and "y" in res and res["x"] > 0 and res["y"] > 0:
                try:
                    page.mouse.click(res["x"], res["y"])
                    logger.info(f"🖱️ Clique físico de mouse enviado nas coordenadas ({res['x']:.0f}, {res['y']:.0f}).")
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Aviso no clique evaluate do botão de execução: {e}")

    # 2. Fallback via seletores Playwright específicos para Lite/Plus (botão do meio)
    if not clicked:
        if mode == "lite_plus":
            plus_selectors = [
                # Botão que contém ou sucede diretamente o texto Lite/Plus
                "xpath=//*[contains(text(), 'Lite/Plus')]/ancestor::*[contains(@class, 'btn') or self::button]",
                "xpath=//*[contains(text(), 'Lite/Plus')]/following::button[1]",
                "xpath=//*[contains(text(), 'Lite/Plus')]/parent::*//button",
                "xpath=//*[contains(text(), 'Lite/Plus')]/ancestor::*[position()<=3]//button",
                "button.beveled-btn-center.run-btn",
                "button.beveled-btn-middle.run-btn",
                "button.beveled-btn-center",
                "button.beveled-btn-middle",
            ]
            for sel in plus_selectors:
                try:
                    candidates = page.locator(sel)
                    for c_idx in range(candidates.count()):
                        item = candidates.nth(c_idx)
                        if item.is_visible():
                            item.click(timeout=3000)
                            logger.info(f"✅ Botão Executar Lite/Plus (do meio) acionado via seletor: {sel}")
                            clicked = True
                            break
                except Exception:
                    pass
                if clicked:
                    break

            # Se ainda não clicou, pegar os botões 'Executar' visíveis e clicar no SEGUNDO (índice 1 = meio)
            if not clicked:
                try:
                    exec_btns = page.locator("button:has-text('Executar'), [role='button']:has-text('Executar')")
                    cnt = exec_btns.count()
                    if cnt >= 2:
                        # O botão do meio (Lite/Plus) é o de índice 1!
                        middle_btn = exec_btns.nth(1)
                        if middle_btn.is_visible():
                            middle_btn.click(timeout=3000)
                            logger.info("✅ Botão Executar Lite/Plus (do meio - índice 1) acionado com sucesso!")
                            clicked = True
                    elif cnt == 1:
                        exec_btns.first.click(timeout=3000)
                        clicked = True
                except Exception as e:
                    logger.debug(f"Aviso no fallback de índice para Lite/Plus: {e}")
        else:
            std_selectors = [
                "button.beveled-btn-left.run-btn",
                "button:has-text('Executar')",
            ]
            for sel in std_selectors:
                try:
                    candidates = page.locator(sel)
                    if candidates.count() > 0 and candidates.first.is_visible():
                        candidates.first.click(timeout=3000)
                        clicked = True
                        break
                except Exception:
                    pass

    # 3. Fallback de emergência (Control+Enter)
    if not clicked:
        logger.warning(f"⚠️ Não foi possível localizar o botão {mode.upper()} via seletores; disparando atalho Control+Enter...")
        page.keyboard.press("Control+Enter")
        clicked = True

    return clicked


def run_factory_bot(
    account: Union[int, str] = DEFAULT_ACCOUNT,
    output_node_id: Optional[int] = None,
    max_batches: int = 1,
    all_batches: bool = False,
    batch_size: Optional[int] = None,
    prompt_nodes: Optional[List[int]] = None,
    destination_dir: Optional[Path] = None,
    session_dir: Optional[Path] = None,
    input_image_path: Optional[Path] = None,
    custom_prompt_text: Optional[str] = None,
    upload_wait_sec: Optional[int] = None,
    execute_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executa a Fábrica RPA adaptando o comportamento entre Conta 1, Conta 2 e Pipeline de Vídeo 4K:
    - Conta 1 (Raw Producer): Injeta prompts (#128-#254) e salva todas as imagens brutas no Nó #121.
    - Conta 2 (SeedVR 8K Upscaler): Ingestão zip no Nó #5 e monitoramento tempo real 1 a 1 no Nó #55.
    - Pipeline de Vídeo 4K (Conta 3): Ingestão de imagem no Nó #164, Prompt no Nó #17 e saída de vídeo 4K no Nó #157.
    """
    if isinstance(account, str):
        if account.isdigit():
            account = int(account)
        elif account.lower() in ("video", "video_4k"):
            account = 3
    cfg = get_account_config(account)
    out_node = output_node_id if output_node_id is not None else cfg["output_node"]
    input_node = cfg.get("input_node", 5)
    b_size = batch_size if batch_size is not None else cfg["default_batch_size"]
    target_nodes = prompt_nodes if prompt_nodes is not None else cfg["prompt_nodes"]
    target_dir = destination_dir if destination_dir is not None else cfg["destination_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    save_mode = cfg["save_mode"]  # 'batch_all' ou 'realtime_single'
    effective_execute_mode = execute_mode or cfg.get("execute_mode", "lite_plus" if account == 3 else "standard")
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
    elif account == 2:
        logger.info("💎 INICIANDO FÁBRICA RPA — CONTA 2 (SEEDVR 2.5 8K UPSCALER)")
        logger.info(f"  • Modo de Salvamento: TEMPO REAL 1 A 1 (Salva instantâneo no Nó #{out_node})")
        logger.info(f"  • Alerta Anti-Overwrite: Captura imediata antes da próxima imagem substituir o nó!")
        logger.info(f"  • Nó Preview 8K:      #{out_node}")
    else:
        logger.info("🎬 INICIANDO FÁBRICA RPA — PIPELINE DE VÍDEO (GERAÇÃO & UPSCALE 4K)")
        logger.info(f"  • Modo de Salvamento: VÍDEO OUTPUT 4K (Nó #{out_node})")
        logger.info(f"  • Nó Ingestão Imagem: #{input_node} (Load Image)")
        logger.info(f"  • Nó Injeção Prompt:  #{cfg.get('prompt_node', 17)} (Prompt / Text)")
        logger.info(f"  • Nó de Saída Vídeo:  #{out_node} (Save video/video combine)")
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

                current_pending = queue_mgr.get_pending_prompts(batch_size=b_size) if account != 3 else []
                v_item = None
                ref_img = None
                p_text_video = ""

                if account == 1 and not current_pending:
                    logger.info("🎉 Fila de prompts zerada! Nenhum prompt pendente.")
                    break
                elif account == 3:
                    pending_v = queue_mgr.get_pending_video_prompts(batch_size=1)
                    if pending_v:
                        v_item = pending_v[0]
                    p_text_video = custom_prompt_text or (v_item.prompt_text if v_item else "")

                    if input_image_path and Path(input_image_path).exists():
                        ref_img = Path(input_image_path)
                    elif v_item and v_item.reference_image:
                        cand = BASE_DIR / v_item.reference_image if not Path(v_item.reference_image).is_absolute() else Path(v_item.reference_image)
                        if cand.exists():
                            ref_img = cand
                    if not ref_img and FINAL_IMAGES_DIR.exists():
                        cand_imgs = sorted(list(FINAL_IMAGES_DIR.glob("*.jpg")) + list(FINAL_IMAGES_DIR.glob("*.png")), key=lambda f: f.stat().st_mtime, reverse=True)
                        if cand_imgs:
                            ref_img = cand_imgs[0]

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
                elif account == 3:
                    if ref_img and ref_img.exists():
                        logger.info(f"📤 [Vídeo] Injetando imagem de referência ({ref_img.name}) no Nó #{input_node} (Load Image)...")
                        upload_image_to_node(page, comfy_frame, input_node, ref_img)
                    if p_text_video:
                        p_node = cfg.get("prompt_node", 17)
                        logger.info(f"📝 [Vídeo] Injetando prompt temporal de vídeo no Nó #{p_node}...")
                        inject_video_prompt_to_node(comfy_frame, p_node, p_text_video)
                        time.sleep(1.0)

                    # Espera mandatória de ~30s para o RunningHub carregar e salvar a imagem no servidor remoto
                    effective_wait = upload_wait_sec if upload_wait_sec is not None else cfg.get("upload_wait_sec", DEFAULT_IMAGE_UPLOAD_WAIT_SEC)
                    logger.info(f"⏳ [Vídeo] Aguardando {effective_wait}s para o servidor carregar a imagem no Nó #{input_node} (Load Image) antes de acionar Executar (Lite/Plus)...")
                    for s in range(effective_wait, 0, -5):
                        chunk = min(5, s)
                        logger.info(f"⏳ [Nó #{input_node} Load Image] Carregando imagem no servidor... {s}s restantes antes de liberar o botão Executar")
                        time.sleep(chunk)
                    logger.info(f"✅ [Nó #{input_node} Load Image] Janela de {effective_wait}s concluída com sucesso! Imagem pronta.")

                # Captura pré-existente no nó de saída
                initial_node_images = get_node_images(page, out_node) if account != 3 else []
                initial_node_videos: List[str] = []
                if account == 3:
                    # Registrar todos os vídeos presentes no nó e no DOM como blacklist permanente antes do disparo
                    initial_node_videos = get_node_videos(page, out_node)
                    for f in page.frames:
                        try:
                            dom_vids = f.evaluate("""() => {
                                const vEls = Array.from(document.querySelectorAll('video'));
                                return vEls.map(v => v.src || v.currentSrc).filter(Boolean);
                            }""")
                            if dom_vids:
                                initial_node_videos.extend(dom_vids)
                        except Exception:
                            pass
                    initial_node_videos = list(dict.fromkeys(initial_node_videos))
                    logger.info(f"🚫 [Vídeo] Registrados {len(initial_node_videos)} vídeos pré-existentes na blacklist antes da execução no Nó #{out_node}.")

                    # Limpar explicitamente o Nó #157 no ComfyUI e marcar elementos antigos com data-pre-existing='true'
                    try:
                        comfy_frame.evaluate("""(id) => {
                            if (typeof window.app !== 'undefined' && window.app.graph) {
                                const node = window.app.graph.getNodeById(id);
                                if (node) {
                                    if (node.video) {
                                        if (node.video.setAttribute) node.video.setAttribute('data-pre-existing', 'true');
                                        node.video.src = '';
                                    }
                                    node.video = null;
                                    node.imgs = [];
                                    if (node.widgets) {
                                        for (const w of node.widgets) {
                                            if (w.element && (w.element.tagName === 'VIDEO' || (w.element.querySelector && w.element.querySelector('video')))) {
                                                const v = w.element.tagName === 'VIDEO' ? w.element : w.element.querySelector('video');
                                                if (v) {
                                                    if (v.setAttribute) v.setAttribute('data-pre-existing', 'true');
                                                    v.src = '';
                                                }
                                            }
                                            if (w.value && typeof w.value === 'string' && (w.value.endsWith('.mp4') || w.value.endsWith('.webm') || w.value.endsWith('.mov'))) {
                                                w.value = '';
                                            }
                                        }
                                    }
                                }
                            }
                            const allVids = Array.from(document.querySelectorAll('video'));
                            allVids.forEach(v => { if (v.setAttribute) v.setAttribute('data-pre-existing', 'true'); });
                        }""", out_node)
                        logger.info(f"🧹 [Vídeo] Nó #{out_node} limpo e isolado no ComfyUI. Nenhum vídeo antigo será aceito.")
                    except Exception as e:
                        logger.debug(f"Aviso ao limpar Nó #{out_node}: {e}")
                else:
                    logger.info(f"Ignorando {len(initial_node_images)} imagens pré-existentes no Node #{out_node}.")

                # 3. Disparar Execução
                logger.info(f"Acionando botão de Execução ({effective_execute_mode.upper()})...")
                try:
                    clicked = click_runninghub_execute(page, mode=effective_execute_mode)
                    if clicked:
                        logger.info(f"✅ Geração iniciada no RunningHub via botão {effective_execute_mode.upper()}!")

                    # Verificação imediata pós-clique de modal de validação do ComfyUI
                    time.sleep(1.5)
                    has_val_err = False
                    for f in page.frames:
                        try:
                            val_err = f.evaluate("""() => {
                                const bodyText = document.body ? document.body.innerText : '';
                                if (bodyText.includes('Custom validation failed for node') || bodyText.includes('Incorrect values in the current workflow')) {
                                    return true;
                                }
                                return false;
                            }""")
                            if val_err:
                                has_val_err = True
                                break
                        except Exception:
                            pass
                    if has_val_err:
                        logger.warning("⚠️ Detectado alerta de validação no ComfyUI pós-execução. Fechando modal...")
                        dismiss_runninghub_popups(page)
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

                # ── ESTRATÉGIA C: PIPELINE DE VÍDEO 4K (Save video/video combine) ──
                elif save_mode == "video_output" or account == 3:
                    max_wait_video = int(os.getenv("RUNNINGHUB_VIDEO_MAX_WAIT_SEC", "3600"))  # 60 minutos (para acomodar renders de ~30 min)
                    logger.info(f"⏳ [Pipeline de Vídeo 4K] Monitorando renderização e upscale no Nó #{out_node} (aguardando conclusão da geração no RunningHub — ~30 min estimados)...")
                    video_saved = False
                    video_wait_start = time.time()
                    last_heartbeat = video_wait_start
                    generation_started = False

                    while True:
                        page.keyboard.press("Escape")

                        # 1. Verificar se a tarefa está ativamente 'Gerando' no RunningHub
                        task_state = {"isGenerating": False, "timer": None, "hasFailed": False}
                        try:
                            task_state = page.evaluate(r"""() => {
                                const bodyText = document.body ? document.body.innerText : '';
                                const isGenerating = /Gerando\s+\d{1,2}:\d{2}/i.test(bodyText) ||
                                                     /Gerando\s*\.{0,3}/i.test(bodyText) ||
                                                     /Fila/i.test(bodyText);
                                const timerMatch = bodyText.match(/Gerando\s+(\d{1,2}:\d{2})/);
                                const timer = timerMatch ? timerMatch[1] : null;
                                const hasFailed = bodyText.includes('TarefaFalha') && !isGenerating;
                                return { isGenerating, timer, hasFailed };
                            }""")
                        except Exception:
                            pass

                        is_generating = task_state.get("isGenerating", False)
                        timer_str = task_state.get("timer")
                        has_failed = task_state.get("hasFailed", False)

                        if is_generating:
                            generation_started = True

                        now = time.time()
                        elapsed_sec = int(now - video_wait_start)

                        # Heartbeat de log a cada 20 segundos
                        if now - last_heartbeat >= 20:
                            elapsed_min = elapsed_sec // 60
                            elapsed_rem = elapsed_sec % 60
                            if is_generating:
                                status_info = f"Gerando {timer_str or f'{elapsed_min}m {elapsed_rem}s'}"
                                logger.info(f"⏳ [Vídeo 4K] Renderização e upscale em andamento no RunningHub ({status_info} | estimativa ~30 min)...")
                            elif generation_started:
                                logger.info(f"⏳ [Vídeo 4K] Tarefa finalizada no RunningHub! Coletando novo vídeo 4K no Nó #{out_node} ({elapsed_min}m {elapsed_rem}s decorridos)...")
                            else:
                                logger.info(f"⏳ [Vídeo 4K] Aguardando início do processamento no servidor ({elapsed_sec}s decorridos)...")
                            last_heartbeat = now

                        # Se reportou falha na tarefa
                        if has_failed and generation_started:
                            logger.error("❌ Tarefa reportou 'TarefaFalha' no painel do RunningHub!")
                            break

                        # 2. Só verificar e extrair o vídeo NOVO quando NÃO estiver mais 'Gerando'
                        # E com segurança adicional de que não seja um resíduo pré-existente
                        if (not is_generating and generation_started) or (elapsed_sec >= 180 and not is_generating):
                            current_node_videos = get_node_videos(page, out_node)
                            new_vids = [v for v in current_node_videos if v not in initial_node_videos]

                            if new_vids:
                                target_vid = new_vids[0]
                                logger.info(f"🎥 Novo vídeo 4K detectado no Nó #{out_node}! Extraindo arquivo final...")
                                saved_name = save_video_from_src(page, target_vid, destination_dir=target_dir, prefix=cfg["prefix"])
                                if saved_name:
                                    saved_path = target_dir / saved_name
                                    # Validação de tamanho: vídeo 4K finalizado deve ter tamanho consistente (> 1 MB)
                                    if saved_path.exists() and saved_path.stat().st_size > 1000000:
                                        images_saved += 1
                                        batch_saved_files.append(saved_name)
                                        video_saved = True
                                        elapsed_total_min = elapsed_sec // 60
                                        elapsed_total_sec = elapsed_sec % 60
                                        logger.info(f"✅ Novo vídeo 4K gravado com sucesso: {saved_name} ({elapsed_total_min}m {elapsed_total_sec}s decorridos, {saved_path.stat().st_size // 1024} KB) em {target_dir.name}!")
                                        if v_item:
                                            queue_mgr.mark_video_prompts_generated([v_item], saved_videos=[saved_name])
                                        break
                                    else:
                                        sz = saved_path.stat().st_size // 1024 if saved_path.exists() else 0
                                        logger.warning(f"⚠️ Vídeo temporário detectado possui tamanho reduzido ({sz} KB). Continuando espera pelo render 4K completo...")

                        # Timeout de segurança de 60 minutos
                        if elapsed_sec > max_wait_video:
                            logger.warning(f"⚠️ Limite máximo de espera por renderização de vídeo atingido ({max_wait_video // 60} min).")
                            break

                        time.sleep(4)

                    # NUNCA cancelar a tarefa no RunningHub para Conta 3 (Vídeo), deixando o render persistir naturalmente

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
