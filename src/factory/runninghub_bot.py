import json
import logging
import sys
import time
import base64
import uuid
import urllib.request
from pathlib import Path
from typing import Any, List, Set
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

# Reconfigure stdout/stderr to UTF-8 on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuration
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
PROMPTS_FILE: Path = BASE_DIR / "data" / "processed" / "prompts.json"
FINAL_IMAGES_DIR: Path = BASE_DIR / "data" / "final" / "images"

# Constants
DEFAULT_BATCH_SIZE: int = 20
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 800

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger: logging.Logger = logging.getLogger(__name__)

def load_prompts(batch_size: int = DEFAULT_BATCH_SIZE) -> List[str]:
    """Load prompts and return a list of strings."""
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            data: List[dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        logger.error("Prompts file not found!")
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse the prompts JSON file!")
        return []
        
    all_prompts: List[str] = []
    for item in data:
        for p in item.get("generated_prompts", []):
            all_prompts.append(p["prompt"].replace("\n", " ").strip())
            
    batch = all_prompts[:batch_size]
    logger.info(f"Loaded {len(batch)} prompts for this batch.")
    return batch

def get_all_image_srcs(page) -> Set[str]:
    """Return a set of all image source URLs currently in the DOM."""
    srcs = set()
    for frame in page.frames:
        try:
            imgs = frame.evaluate("() => Array.from(document.querySelectorAll('img')).map(img => img.src)")
            for src in imgs:
                if src:
                    srcs.add(src)
        except Exception:
            pass
    return srcs

def save_image_from_src(page, src: str) -> bool:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = FINAL_IMAGES_DIR / f"generated_{uuid.uuid4().hex[:8]}.png"
    
    try:
        if src.startswith("data:image"):
            header, encoded = src.split(",", 1)
            data = base64.b64decode(encoded)
            with open(filename, "wb") as f:
                f.write(data)
            return True
        elif src.startswith("blob:"):
            for frame in page.frames:
                try:
                    b64_data = frame.evaluate("""async (url) => {
                        const response = await fetch(url);
                        const blob = await response.blob();
                        return new Promise((resolve, reject) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.onerror = reject;
                            reader.readAsDataURL(blob);
                        });
                    }""", src)
                    if b64_data:
                        header, encoded = b64_data.split(",", 1)
                        data = base64.b64decode(encoded)
                        with open(filename, "wb") as f:
                            f.write(data)
                        return True
                except Exception:
                    continue
        elif src.startswith("http"):
            req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read()
                if len(data) > 30000: # Ignore tiny icons < 30KB
                    with open(filename, "wb") as f:
                        f.write(data)
                    return True
    except Exception as e:
        logger.debug(f"Falha ao processar src de imagem: {e}")
    return False

def run_factory_bot() -> None:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    prompts_list = load_prompts(batch_size=DEFAULT_BATCH_SIZE)
    if not prompts_list:
        return
        
    prompts_text = "\n".join(prompts_list)
        
    with sync_playwright() as p:
        user_data_dir = BASE_DIR / "playwright_session"
        with p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"]
        ) as browser:
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            
            logger.info("Opening Runninghub Workflow... Waiting for login if necessary.")
            try:
                page.goto("https://www.runninghub.ai/pt-br/workflow/2025818595460128770?source=workspace", wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                logger.warning(f"Aviso de rede ao abrir Runninghub ({e}). Prosseguindo com o navegador aberto...")
            
            # 1. Automate waiting for login and workflow load
            logger.info("Verificando status de login e aguardando carregamento do workflow...")
            workflow_url_part = "2025818595460128770"
            
            loaded = False
            for _ in range(60): # Até 5 minutos
                if workflow_url_part in page.url:
                    try:
                        # Checa se existe tela de canvas ou botões nativos do comfyui/runninghub
                        if page.locator("canvas").count() > 0 or page.locator("button:has-text('Executar'), [role='button']:has-text('Executar')").count() > 0:
                            loaded = True
                            break
                    except Exception:
                        pass
                time.sleep(5)
                logger.info("⏳ Aguardando login ou carregamento do workflow na tela...")
                
            if not loaded:
                logger.error("Tempo limite atingido aguardando o workflow carregar. Encerrando o bot.")
                return

            logger.info("✅ Workflow carregado! Iniciando injeção de prompts automática...")
            time.sleep(5) # Delay extra para garantir que iframes e nós do ComfyUI estejam instanciados

            # 2. Inject prompts automatically into the DOM/Canvas
            injetado = False
            for frame in page.frames:
                try:
                    res = frame.evaluate("""(text) => {
                        // Tentar achar LiteGraph do ComfyUI nativo no window.app
                        if (typeof window.app !== 'undefined' && window.app.graph) {
                            for (let node of window.app.graph._nodes) {
                                if (node.widgets && (node.type.includes('Text') || node.type.includes('Prompt') || node.title.includes('Text'))) {
                                    node.widgets[0].value = text;
                                    if(node.widgets[0].callback) node.widgets[0].callback(text);
                                }
                            }
                            window.app.graph.setDirtyCanvas(true, true);
                            return true;
                        }
                        
                        // Tentar achar textarea aberta do nó no DOM
                        let textareas = Array.from(document.querySelectorAll('textarea'));
                        if (textareas.length > 0) {
                            let el = textareas[0];
                            el.value = text;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        return false;
                    }""", prompts_text)
                    if res:
                        injetado = True
                        break
                except Exception:
                    pass
                    
            if injetado:
                logger.info("✅ Prompts injetados via DOM / App Graph com sucesso!")
            else:
                logger.warning("Caixa ou App Graph não encontrada diretamente. Usando fallback de injeção global...")
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.insert_text(prompts_text)

            # Capture existing images to ignore them (via Node 121 if possible)
            initial_node_images = []
            for frame in page.frames:
                try:
                    imgs = frame.evaluate("""() => {
                        if (typeof window.app !== 'undefined' && window.app.graph) {
                            let node = window.app.graph.getNodeById(121);
                            if (node && node.imgs) {
                                return node.imgs.map(i => i.src);
                            }
                        }
                        return [];
                    }""")
                    if imgs:
                        initial_node_images.extend(imgs)
                except Exception:
                    pass
            
            logger.info(f"Ignorando {len(initial_node_images)} imagens pré-existentes no Node #121.")

            # 3. Click Executar (Lite/Plus - o do meio)
            logger.info("Procurando o botão de Executar (Lite/Plus)...")
            try:
                # O usuário indicou que é o botão amarelo (o segundo botão Executar no topo)
                btn = page.locator("button:has-text('Executar'), [role='button']:has-text('Executar')").nth(1)
                if btn.count() > 0:
                    btn.click(timeout=5000)
                    logger.info("✅ Geração de Lote iniciada! (Botão Lite/Plus)")
                else:
                    logger.warning("Botão 'Executar' não encontrado visivelmente. Tentando atalho de teclado...")
                    page.keyboard.press("Control+Enter")
            except Exception as e:
                logger.error(f"Erro ao clicar em Executar: {e}. O lote pode não ter iniciado.")
            
            # 4. Monitor and save images from Node #121
            expected_images = len(prompts_list)
            logger.info(f"⏳ Monitorando novas imagens no Node #121. A geração pode levar mais de 2 minutos...")
            
            saved_srcs = set(initial_node_images)
            images_saved = 0
            start_wait_time = time.time()
            
            while images_saved < expected_images:
                # Dismiss any error popup if it appears (press Escape)
                page.keyboard.press("Escape")
                
                current_node_images = []
                for frame in page.frames:
                    try:
                        imgs = frame.evaluate("""() => {
                            if (typeof window.app !== 'undefined' && window.app.graph) {
                                let node = window.app.graph.getNodeById(121);
                                if (node && node.imgs) {
                                    return node.imgs.map(i => i.src);
                                }
                            }
                            return [];
                        }""")
                        if imgs:
                            current_node_images.extend(imgs)
                    except Exception:
                        pass
                
                new_srcs = set(current_node_images) - saved_srcs
                
                for src in new_srcs:
                    if save_image_from_src(page, src):
                        images_saved += 1
                        logger.info(f"✅ Imagem {images_saved}/{expected_images} salva na pasta data/final/images!")
                        start_wait_time = time.time() # Reset timeout
                    saved_srcs.add(src) # Mark as processed whether success or fail
                
                # Check for timeout (e.g. 15 minutes without new images to allow very slow generations)
                if time.time() - start_wait_time > 900:
                    logger.warning("⚠️ Tempo limite (15 minutos) atingido sem novas imagens. Encerrando lote...")
                    break
                    
                time.sleep(5) # Polling interval
                
            logger.info(f"🎉 Processo concluído! {images_saved} imagens geradas e salvas do Node #121.")
            
            if images_saved > 0:
                time.sleep(3)

if __name__ == "__main__":
    run_factory_bot()
