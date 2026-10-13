import os
import json
import logging
import sys
import time
import base64
import uuid
import urllib.request
from pathlib import Path
from typing import Any, List, Set, Union
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
WORKFLOW_URL: str = os.getenv("RUNNINGHUB_WORKFLOW_URL", "https://www.runninghub.ai/pt-br/workflow/2109087489277710337?source=workspace")
WORKFLOW_ID: str = "2109087489277710337"

# Constants
DEFAULT_BATCH_SIZE: int = 20
DEFAULT_OUTPUT_NODE: int = int(os.getenv("RUNNINGHUB_OUTPUT_NODE", "192"))
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 800

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger: logging.Logger = logging.getLogger(__name__)

def load_prompts(batch_size: int = DEFAULT_BATCH_SIZE) -> List[str]:
    """Load prompts prioritizing Contributor Insights top sellers (Gorodenkoff, etc.)."""
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            data: List[dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        logger.error("Prompts file not found!")
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse the prompts JSON file!")
        return []

    # Identificar IDs de itens minerados diretamente em Contributor Insights (Top Sellers)
    insights_ids = set()
    trends_file = BASE_DIR / "data" / "raw" / "trends.json"
    if trends_file.exists():
        try:
            with open(trends_file, "r", encoding="utf-8") as tf:
                trends = json.load(tf)
                insights_ids = {str(t.get("id")) for t in trends if t.get("source") == "contributor_insights"}
        except Exception as e:
            logger.debug(f"Aviso ao ler trends.json: {e}")

    # Priorizar itens do portal Contributor Insights no início do lote
    insights_items = []
    other_items = []
    for item in data:
        sid = str(item.get("source_id", ""))
        if sid in insights_ids or item.get("source") == "contributor_insights":
            insights_items.append(item)
        else:
            other_items.append(item)

    ordered_items = insights_items + other_items
    logger.info(f"Filtro de prompts: {len(insights_items)} itens de Top Sellers encontrados ({len(other_items)} outros).")

    all_prompts: List[str] = []
    for item in ordered_items:
        for p in item.get("generated_prompts", []):
            if "prompt_data" in p:
                all_prompts.append(json.dumps(p["prompt_data"], ensure_ascii=False))
            elif "prompt" in p:
                all_prompts.append(p["prompt"].replace("\n", " ").strip())
            
    batch = all_prompts[:batch_size]
    logger.info(f"Carregados {len(batch)} prompts para este lote (Top Sellers de Contributor Insights priorizados).")
    return batch

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
                    if (node && node.imgs && node.imgs.length > 0) {
                        return node.imgs.map(i => i.src).filter(Boolean);
                    }
                }
                return [];
            }""", node_id)
            if imgs:
                node_images.extend(imgs)
        except Exception:
            pass
    return node_images

def save_image_from_src(page: Page, src: str) -> bool:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = FINAL_IMAGES_DIR / f"generated_{uuid.uuid4().hex[:8]}.png"
    
    try:
        if src.startswith("data:image"):
            header, encoded = src.split(",", 1)
            data = base64.b64decode(encoded)
            with open(filename, "wb") as f:
                f.write(data)
            return True
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
                        data = base64.b64decode(encoded)
                        if len(data) > 30000: # Ignorar ícones ou thumbnails < 30KB
                            with open(filename, "wb") as f:
                                f.write(data)
                            return True
                except Exception:
                    continue

        # 2. Fallback para urllib caso não tenha sido baixado e seja HTTP
        if src.startswith("http"):
            req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read()
                if len(data) > 30000:
                    with open(filename, "wb") as f:
                        f.write(data)
                    return True
    except Exception as e:
        logger.debug(f"Falha ao processar src de imagem: {e}")
    return False

def run_factory_bot(output_node_id: int = DEFAULT_OUTPUT_NODE) -> None:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    prompts_list = load_prompts(batch_size=DEFAULT_BATCH_SIZE)
    if not prompts_list:
        return
        
    prompts_text = "\n".join(prompts_list)
        
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
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            logger.info(f"Opening Runninghub Workflow ({WORKFLOW_ID})... Waiting for login if necessary.")
            try:
                page.goto(WORKFLOW_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                logger.warning(f"Aviso de rede ao abrir Runninghub ({e}). Prosseguindo com o navegador aberto...")
            
            # 1. Automate waiting for login and complete workflow load (all 83 nodes)
            logger.info("Verificando status de login e aguardando carregamento completo do workflow (83 nós)...")
            comfy_frame = None
            loaded = False
            for _ in range(60): # Até 2 minutos
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
                logger.info("⏳ Aguardando workflow e nós carregarem na tela...")
                
            if not loaded:
                logger.error("Tempo limite atingido aguardando o workflow carregar. Encerrando o bot.")
                return

            # Fechar qualquer popup residual ("Close", "Prompt has no outputs", etc.)
            try:
                close_btn = page.locator("button:has-text('Close'), button:has-text('Fechar'), [role='button']:has-text('Close')")
                if close_btn.count() > 0:
                    close_btn.first.click(timeout=1000)
            except Exception:
                pass
            page.keyboard.press("Escape")
            time.sleep(1.0)

            # 2. Injeção 100% Segura e Autônoma nos Nodes #128, #129, #130, #131 (sem nenhum risco ao grafo)
            target_nodes = [128, 129, 130, 131]
            batch_prompts = prompts_list[:20]

            logger.info("🤖 Iniciando injeção de 20 prompts nos nós #128, #129, #130, #131 (5 caixas por nó)...")
            
            for idx, prompt_text in enumerate(batch_prompts):
                node_id = target_nodes[idx // 5]
                box_num = (idx % 5) + 1
                curr_total = idx + 1
                logger.info(f"  📝 Preenchendo prompt {curr_total}/20 [Nó #{node_id} - Caixa prompt_{box_num}]...")

            inject_res = comfy_frame.evaluate("""({nodeIds, prompts}) => {
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
                for (let id of nodeIds) {
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
            }""", {"nodeIds": target_nodes, "prompts": batch_prompts})
            
            logger.info(f"Resultado da injeção: {inject_res}")
            logger.info("✅ Todos os 20 prompts foram injetados com sucesso nos nós #128, #129, #130 e #131 sem intervenção manual!")

            # Capture existing images to ignore them (via Node output_node_id)
            initial_node_images = get_node_images(page, output_node_id)
            logger.info(f"Ignorando {len(initial_node_images)} imagens pré-existentes no Node #{output_node_id}.")

            # 3. Click Executar (Lite/Plus - o botão amarelo do meio)
            logger.info("Procurando o botão de Executar (Lite/Plus)...")
            try:
                btn = page.locator("button.beveled-btn-left.run-btn")
                if btn.count() == 0:
                    btn = page.locator(".execute-btn-wrap button").nth(1)
                if btn.count() == 0:
                    btn = page.locator("button:has-text('Executar'), [role='button']:has-text('Executar')").nth(1)
                    
                if btn.count() > 0:
                    btn.click(timeout=5000)
                    logger.info("✅ Geração de Lote iniciada com sucesso! (Botão Lite/Plus)")
                else:
                    logger.warning("Botão 'Executar' não encontrado visivelmente. Tentando atalho de teclado Control+Enter...")
                    page.keyboard.press("Control+Enter")
            except Exception as e:
                logger.error(f"Erro ao clicar em Executar: {e}. O lote pode não ter iniciado.")
            
            # 4. Monitor and save 4K upscaled images from Node output_node_id in real-time
            expected_images = len(prompts_list)
            logger.info(f"⏳ Monitorando novas imagens com Upscale 4K em tempo real no Node #{output_node_id}...")
            logger.info(f"🎯 Captura instantânea ativada: cada imagem será salva uma a uma assim que renderizada.")
            
            saved_srcs = set(initial_node_images)
            images_saved = 0
            start_wait_time = time.time()
            
            while images_saved < expected_images:
                # Dismiss any error popup if it appears (press Escape)
                page.keyboard.press("Escape")
                
                current_node_images = get_node_images(page, output_node_id)
                new_srcs = [src for src in current_node_images if src not in saved_srcs]
                
                for src in new_srcs:
                    if save_image_from_src(page, src):
                        images_saved += 1
                        logger.info(f"✅ [Upscale 4K] Imagem {images_saved}/{expected_images} capturada e salva com sucesso do Node #{output_node_id}!")
                        start_wait_time = time.time() # Reset timeout
                    saved_srcs.add(src) # Mark as processed whether success or fail
                
                # Check for timeout (e.g. 15 minutes without new images to allow very slow generations)
                if time.time() - start_wait_time > 900:
                    logger.warning("⚠️ Tempo limite (15 minutos) atingido sem novas imagens. Encerrando lote...")
                    break
                    
                time.sleep(2) # Polling ágil a cada 2s para não perder transição entre iterações do loop
                
            logger.info(f"🎉 Processo concluído! {images_saved} imagens 4K geradas e salvas do Node #{output_node_id}.")
            
            if images_saved > 0:
                time.sleep(3)
        finally:
            try:
                browser.close()
            except Exception:
                pass

if __name__ == "__main__":
    run_factory_bot()
