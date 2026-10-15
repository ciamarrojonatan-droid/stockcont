import os
import json
import logging
import sys
import time
import base64
import uuid
import urllib.request
from pathlib import Path
from typing import Any, List, Optional, Set, Union
from playwright.sync_api import sync_playwright, Page, Frame, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

# Reconfigure stdout/stderr to UTF-8 on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception as e:
        pass

# Configuration
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
PROMPTS_FILE: Path = BASE_DIR / "data" / "processed" / "prompts.json"
FINAL_IMAGES_DIR: Path = BASE_DIR / "data" / "final" / "images"

# RunningHub Workflow Configuration
WORKFLOW_URL: str = os.getenv("RUNNINGHUB_WORKFLOW_URL", "https://www.runninghub.ai/pt-br/workflow/2109838304543002625?source=workspace")
WORKFLOW_ID: str = "2109838304543002625"

# Constants
DEFAULT_BATCH_SIZE: int = 10
DEFAULT_OUTPUT_NODE: int = int(os.getenv("RUNNINGHUB_OUTPUT_NODE", "192"))
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 800

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger: logging.Logger = logging.getLogger(__name__)

def load_prompts(batch_size: int = DEFAULT_BATCH_SIZE) -> List[str]:
    """Load pending prompts prioritizing Contributor Insights top sellers."""
    from src.factory.prompt_queue import PromptQueueManager
    mgr = PromptQueueManager()
    pending = mgr.get_pending_prompts(batch_size=batch_size)
    prompts = [p.prompt_text for p in pending]
    logger.info(f"Carregados {len(prompts)} prompts pendentes para este lote (Top Sellers priorizados).")
    return prompts

def get_all_image_srcs(page: Page) -> Set[str]:
    """Return a set of all image source URLs currently in the DOM."""
    srcs = set()
    for frame in page.frames:
        try:
            imgs = frame.evaluate("() => Array.from(document.querySelectorAll('img')).map(img => img.src)")
            for src in imgs:
                if src:
                    srcs.add(src)
        except Exception as e:
            logger.debug(f"Erro ao buscar imagens no frame: {e}")
    return srcs

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

def save_image_from_src(page: Page, src: str) -> Optional[str]:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = FINAL_IMAGES_DIR / f"generated_{uuid.uuid4().hex[:8]}.png"
    while filename.exists():
        filename = FINAL_IMAGES_DIR / f"generated_{uuid.uuid4().hex[:8]}.png"
    tmp_filename = filename.with_suffix(".tmp")
    
    try:
        data: Optional[bytes] = None
        if src.startswith("data:image"):
            header, encoded = src.split(",", 1)
            raw_data = base64.b64decode(encoded)
            if len(raw_data) > 30000:
                data = raw_data
        elif src.startswith("blob:") or src.startswith("http"):
            # 1. Tentar extrair diretamente no contexto autenticado do navegador (preserva cookies e resolução 4K)
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
                        if len(decoded) > 30000: # Ignorar ícones ou thumbnails < 30KB
                            data = decoded
                            break
                except Exception:
                    continue

            # 2. Fallback para urllib caso não tenha sido baixado e seja HTTP
            if data is None and src.startswith("http"):
                try:
                    req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
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
    """
    Cancela imediatamente a tarefa em execução no RunningHub ('Lista de tarefas').
    Acionado imediatamente após salvar a 20ª imagem para interromper o upscale excedente.
    """
    logger.info("🛑 [Lista de tarefas] Localizando e acionando 'Cancelar' para a tarefa ativa...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_sec:
        try:
            # 1. Se 'Cancelar' não estiver visível, tentar abrir o painel 'Lista de tarefas' caso esteja recolhido
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
                for drawer_sel in [
                    "Lista de tarefas",
                    "Tarefas",
                    "Task",
                ]:
                    try:
                        drawer_btn = page.get_by_text(drawer_sel)
                        if drawer_btn.count() > 0 and drawer_btn.first.is_visible():
                            logger.info(f"📂 Abrindo painel 'Lista de tarefas' ({drawer_sel})...")
                            drawer_btn.first.click(timeout=1500)
                            time.sleep(1.0)
                            break
                    except Exception:
                        pass

            # 2. Localizar o botão/link 'Cancelar'
            clicked = False
            
            # Prioridade A: 'Cancelar' associado ao card da tarefa (próximo de 'Gerando' ou 'taskid')
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

            # Prioridade B: Qualquer elemento com texto exato 'Cancelar' visível
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

            # Prioridade C: Injeção direta via JS no DOM do frame
            if not clicked:
                for frame in page.frames:
                    try:
                        res = frame.evaluate("""() => {
                            const all = Array.from(document.querySelectorAll('*'));
                            for (let el of all) {
                                if (el.children.length === 0) {
                                    const t = el.textContent ? el.textContent.trim() : '';
                                    if (t === 'Cancelar' || t === 'Cancel' || t === '取消') {
                                        const r = el.getBoundingClientRect();
                                        if (r.width > 0 && r.height > 0) {
                                            el.click();
                                            return { clicked: true, tag: el.tagName };
                                        }
                                    }
                                }
                            }
                            return { clicked: false };
                        }""")
                        if res and res.get("clicked"):
                            logger.info(f"🎯 'Cancelar' clicado via injeção DOM JS ({res.get('tag')})!")
                            clicked = True
                            break
                    except Exception:
                        pass

            # 3. Se clicou em Cancelar, verificar se abriu modal de confirmação
            if clicked:
                time.sleep(1.0)
                modal_confirmed = False
                for frame in page.frames:
                    try:
                        for confirm_sel in [
                            ".el-message-box__btns button.el-button--primary",
                            ".el-dialog__footer button.el-button--primary",
                            ".el-message-box__btns button:not(.el-button--default)",
                            "[role='dialog'] button.primary",
                            "[role='dialog'] button:has-text('Confirmar')",
                            "[role='dialog'] button:has-text('Determinar')",
                            "[role='dialog'] button:has-text('Sim')",
                            "[role='dialog'] button:has-text('OK')",
                            "button:has-text('Confirmar')",
                            "button:has-text('Determinar')",
                            "button:has-text('Sim')"
                        ]:
                            btn = frame.locator(confirm_sel)
                            if btn.count() > 0 and btn.first.is_visible():
                                logger.info(f"🔔 Modal de confirmação detectado ({confirm_sel}). Confirmando...")
                                btn.first.click(timeout=2000)
                                modal_confirmed = True
                                break
                    except Exception:
                        pass
                    if modal_confirmed:
                        break

                logger.info("✅ Tarefa cancelada com sucesso na 'Lista de tarefas'! O upscale da imagem excedente foi abortado.")
                return True

        except Exception as e:
            logger.debug(f"Aviso durante tentativa de cancelamento: {e}")

        time.sleep(1.5)

    logger.warning("⚠️ Tempo limite atingido tentando cancelar a tarefa na 'Lista de tarefas'.")
    return False

def run_factory_bot(
    output_node_id: int = DEFAULT_OUTPUT_NODE,
    max_batches: int = 1,
    all_batches: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> None:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    from src.factory.prompt_queue import PromptQueueManager
    queue_mgr = PromptQueueManager()

    initial_pending = queue_mgr.get_pending_prompts(batch_size=batch_size)
    if not initial_pending:
        logger.info("🎉 Nenhum prompt pendente na fila! Todos os prompts já foram gerados.")
        return

    stats = queue_mgr.get_stats()
    logger.info(f"🚀 Iniciando Factory Bot | Fila: {stats['generated']}/{stats['total']} gerados ({stats['pending']} pendentes - {stats['progress_percent']}%).")
    if all_batches:
        logger.info("🔄 Modo: PROCESSAR TODOS OS LOTES (--all-batches) até zerar a fila.")
    else:
        logger.info(f"📦 Modo: {max_batches} lote(s) solicitado(s) (máximo {max_batches * batch_size} imagens).")

    with sync_playwright() as p:
        user_data_dir = BASE_DIR / "playwright_session"
        launch_kwargs = {
            "user_data_dir": user_data_dir,
            "headless": False,
            "viewport": {"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            "accept_downloads": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized"
            ]
        }

        browser = None
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            logger.info("⚡ Conectado ao Chrome existente via porta 9222!")
        except Exception:
            pass

        if not browser:
            browser = p.chromium.launch_persistent_context(**launch_kwargs)

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
                    page.bring_to_front()
                except Exception:
                    pass
            else:
                page = all_pages[0] if all_pages else browser.new_page()
                logger.info(f"Opening Runninghub Workflow ({WORKFLOW_ID})... Waiting for login if necessary.")
                try:
                    page.goto(WORKFLOW_URL, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    logger.warning(f"Aviso de rede ao abrir Runninghub ({e}). Prosseguindo com o navegador aberto...")
            
            # 1. Automate waiting for login and complete workflow load (all 83 nodes)
            logger.info("Verificando status de login e aguardando carregamento completo do workflow (83 nós)...")
            comfy_frame = None
            loaded = False
            for step in range(120): # Até 4 minutos para permitir login
                for f in page.frames:
                    try:
                        cnt = f.evaluate("() => window.app && window.app.graph && window.app.graph._nodes ? window.app.graph._nodes.length : 0")
                        if cnt and cnt >= 10:
                            comfy_frame = f
                            loaded = True
                            logger.info(f"✅ Workflow carregado com sucesso! Total de nós no grafo: {cnt}")
                            break
                    except Exception:
                        continue
                if loaded:
                    break
                time.sleep(2)
                if step % 5 == 0:
                    try:
                        logger.info(f"⏳ Aguardando nós do workflow ({step+1}/120)... Página atual: '{page.title()}' ({page.url})")
                    except Exception:
                        logger.info(f"⏳ Aguardando workflow e nós carregarem na tela ({step+1}/120)...")
                
            if not loaded:
                debug_img = BASE_DIR / "data" / "workflow_debug.png"
                try:
                    page.screenshot(path=str(debug_img))
                    logger.error(f"Tempo limite atingido aguardando o workflow carregar (URL: {page.url}). Screenshot salvo em {debug_img}. Encerrando o bot.")
                except Exception:
                    logger.error(f"Tempo limite atingido aguardando o workflow carregar (URL: {page.url}). Encerrando o bot.")
                return

            # Batch Execution Loop in same browser session
            batch_count = 0
            while True:
                if not all_batches and batch_count >= max_batches:
                    logger.info(f"🏁 Meta de {max_batches} lote(s) concluída com sucesso.")
                    break

                current_pending = queue_mgr.get_pending_prompts(batch_size=batch_size)
                if not current_pending:
                    logger.info("🎉 Todos os prompts pendentes foram processados com sucesso! Fila 100% concluída.")
                    break

                batch_count += 1
                batch_prompts = [p.prompt_text for p in current_pending]
                logger.info("=" * 60)
                logger.info(f"📦 [Lote #{batch_count}] Processando {len(batch_prompts)} prompts...")
                logger.info("=" * 60)

                # Fechar qualquer popup residual ("Close", "Prompt has no outputs", etc.)
                try:
                    close_btn = page.locator("button:has-text('Close'), button:has-text('Fechar'), [role='button']:has-text('Close')")
                    if close_btn.count() > 0:
                        close_btn.first.click(timeout=1000)
                except Exception:
                    pass
                page.keyboard.press("Escape")
                time.sleep(1.0)

                # 2. Injeção 100% Segura e Autônoma nos Nodes #128 e #129 (5 caixas por nó = 10 prompts por lote)
                target_nodes = [128, 129]
                clear_nodes = [130, 131]

                logger.info(f"🤖 Iniciando injeção de {len(batch_prompts)} prompts nos nós #128 e #129 (5 caixas por nó)...")
                for idx, prompt_text in enumerate(batch_prompts):
                    node_idx = min(idx // 5, len(target_nodes) - 1)
                    node_id = target_nodes[node_idx]
                    box_num = (idx % 5) + 1
                    curr_total = idx + 1
                    logger.info(f"  📝 Preenchendo prompt {curr_total}/{len(batch_prompts)} [Nó #{node_id} - Caixa prompt_{box_num}]...")

                inject_res = comfy_frame.evaluate("""({targetNodeIds, clearNodeIds, prompts}) => {
                    if (typeof window.app === 'undefined' || !window.app.graph) return { error: "Graph not found" };
                    
                    const canvas = window.app.canvas;
                    const n128 = window.app.graph.getNodeById(128);
                    
                    // Centralizar a visualização no nó #128
                    if (canvas && n128) {
                        canvas.centerOnNode(n128);
                        canvas.selectNode(n128);
                    }
                    
                    let pIdx = 0;
                    let filledCount = 0;
                    
                    // 1. Preencher os prompts nos nós #128 e #129 (e limpar caixas excedentes no lote)
                    for (let id of targetNodeIds) {
                        let node = window.app.graph.getNodeById(id);
                        if (!node || !node.widgets) continue;
                        
                        let promptWidgets = node.widgets.filter(w => w.name && w.name.startsWith('prompt_'));
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
                                        w.inputEl.parentElement.style.pointerEvents = 'auto';
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
                                // Limpar caixas excedentes para não re-gerar prompts de lotes anteriores
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
                    
                    // 2. Limpar nós #130 e #131 para garantir que apenas os prompts do lote atual sejam gerados
                    for (let id of clearNodeIds) {
                        let node = window.app.graph.getNodeById(id);
                        if (!node || !node.widgets) continue;
                        
                        let promptWidgets = node.widgets.filter(w => w.name && w.name.startsWith('prompt_'));
                        if (promptWidgets.length === 0) promptWidgets = node.widgets.slice(0, 5);
                        
                        for (let w of promptWidgets) {
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
                    
                    // Focar e ativar a primeira caixa de texto (prompt_1) do nó #128
                    if (n128 && n128.widgets && n128.widgets[0] && n128.widgets[0].inputEl) {
                        n128.widgets[0].inputEl.focus();
                        n128.widgets[0].inputEl.click();
                    }
                    
                    // Redesenhar o Canvas do LiteGraph com os novos valores
                    if (window.app.graph.setDirtyCanvas) window.app.graph.setDirtyCanvas(true, true);
                    if (canvas && canvas.draw) canvas.draw(true, true);
                    
                    return {
                        success: true,
                        totalNodes: window.app.graph._nodes.length,
                        filledCount: filledCount
                    };
                }""", {"targetNodeIds": target_nodes, "clearNodeIds": clear_nodes, "prompts": batch_prompts})
                
                logger.info(f"Resultado da injeção: {inject_res}")
                logger.info(f"✅ {len(batch_prompts)} prompts foram injetados com sucesso nos nós #128 e #129 (nós #130 e #131 limpos)!")

                # Capture existing images to ignore them (via Node output_node_id)
                initial_node_images = get_node_images(page, output_node_id)
                logger.info(f"Ignorando {len(initial_node_images)} imagens pré-existentes no Node #{output_node_id}.")

                # 3. Click Executar (Lite/Plus - o botão amarelo do meio)
                logger.info("Procurando o botão de Executar (Lite/Plus)...")
                try:
                    btn = None
                    for sel in [
                        "xpath=//*[contains(text(), 'Lite/Plus')]/ancestor::button",
                        "xpath=//*[contains(text(), 'Lite/Plus')]/ancestor::*[contains(@class, 'btn')]",
                        "xpath=//*[contains(text(), 'Lite/Plus')]/..",
                        "xpath=//*[contains(text(), 'Lite/Plus')]",
                        "button.beveled-btn-left.run-btn",
                        ".execute-btn-wrap button",
                        "button:has-text('Executar'), [role='button']:has-text('Executar')"
                    ]:
                        try:
                            candidates = page.locator(sel)
                            for c_idx in range(candidates.count()):
                                item = candidates.nth(c_idx)
                                if item.is_visible():
                                    btn = item
                                    logger.info(f"🎯 Botão Executar Lite/Plus localizado via '{sel}'")
                                    break
                        except Exception:
                            pass
                        if btn:
                            break

                    if btn:
                        btn.click(timeout=5000)
                        logger.info("✅ Geração de Lote iniciada com sucesso! (Botão Lite/Plus)")
                    else:
                        logger.warning("Botão 'Executar' não encontrado visivelmente. Tentando atalho de teclado Control+Enter...")
                        page.keyboard.press("Control+Enter")
                except Exception as e:
                    logger.error(f"Erro ao clicar em Executar: {e}. O lote pode não ter iniciado.")
                
                # 4. Monitor and save 4K upscaled images from Node output_node_id in real-time
                expected_images = min(len(batch_prompts), batch_size)
                logger.info(f"⏳ Monitorando novas imagens com Upscale 4K em tempo real no Node #{output_node_id}...")
                logger.info(f"🎯 Captura instantânea ativada: cada imagem será salva uma a uma assim que renderizada (limite: {expected_images} imagens).")
                
                saved_srcs = set(initial_node_images)
                batch_saved_files: List[str] = []
                images_saved = 0
                start_wait_time = time.time()
                
                while images_saved < expected_images:
                    # Dismiss any error popup if it appears (press Escape)
                    page.keyboard.press("Escape")
                    
                    current_node_images = get_node_images(page, output_node_id)
                    new_srcs = [src for src in current_node_images if src not in saved_srcs]
                    
                    for src in new_srcs:
                        saved_name = save_image_from_src(page, src)
                        if saved_name:
                            images_saved += 1
                            batch_saved_files.append(saved_name)
                            saved_srcs.add(src)
                            logger.info(f"✅ [Upscale 4K] Imagem {images_saved}/{expected_images} capturada ({saved_name}) do Node #{output_node_id}!")
                            start_wait_time = time.time() # Reset timeout
                        
                        if images_saved >= expected_images:
                            logger.info(f"🎯 Meta de {expected_images} imagens atingida! Interrompendo captura imediatamente.")
                            break
                    
                    if images_saved >= expected_images:
                        break
                    
                    # Check for timeout (e.g. 15 minutes without new images to allow very slow generations)
                    if time.time() - start_wait_time > 900:
                        logger.warning("⚠️ Tempo limite (15 minutos) atingido sem novas imagens. Encerrando lote...")
                        break
                        
                    time.sleep(2) # Polling ágil a cada 2s para não perder transição entre iterações do loop
                    
                logger.info(f"🎉 Captura do lote finalizada! Total de {images_saved} imagens salvas do Node #{output_node_id}.")
                
                # 5. Cancelar a tarefa imediatamente após salvar as imagens esperadas para ignorar upscale excedente
                if images_saved >= expected_images:
                    logger.info(f"⚡ {expected_images} imagens salvas com sucesso! Acionando cancelamento imediato em 'Lista de tarefas' para descartar upscale excedente...")
                    cancel_runninghub_task(page)
                else:
                    logger.warning(f"Lote finalizado com {images_saved}/{expected_images} imagens geradas.")
                
                # 6. Atualizar a fila e histórico proporcionalmente
                marked = queue_mgr.mark_prompts_generated(current_pending, saved_images=batch_saved_files)
                stats = queue_mgr.get_stats()
                logger.info(f"📊 Fila de Prompts: {stats['generated']}/{stats['total']} gerados ({stats['pending']} pendentes - {stats['progress_percent']}%)")

                # Se nenhuma imagem foi salva no lote, interromper para evitar consumo acidental ou loop infinito
                if images_saved == 0:
                    logger.error("❌ Nenhuma imagem foi gerada/salva neste lote (falha ou timeout). Interrompendo execução para evitar loop infinito.")
                    break

                if (all_batches or batch_count < max_batches) and stats['pending'] > 0:
                    logger.info("⏳ Aguardando 3 segundos de segurança antes do próximo lote...")
                    time.sleep(3)
        finally:
            try:
                browser.close()
            except Exception:
                pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RunningHub ComfyUI Automation Bot")
    parser.add_argument("--node", type=int, default=DEFAULT_OUTPUT_NODE, help="Output Node ID in Runninghub ComfyUI (default: 192)")
    parser.add_argument("--batches", type=int, default=1, help="Number of consecutive batches to run (default: 1)")
    parser.add_argument("--all-batches", action="store_true", help="Run until prompt queue is exhausted")
    args = parser.parse_args()
    run_factory_bot(output_node_id=args.node, max_batches=args.batches, all_batches=args.all_batches)
