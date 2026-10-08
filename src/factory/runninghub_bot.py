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
            
            logger.info("Opening Runninghub Workflow... Please login if necessary.")
            try:
                page.goto("https://www.runninghub.ai/pt-br/workflow/2025818595460128770?source=workspace", wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                logger.warning(f"Aviso de rede ao abrir Runninghub ({e}). Prosseguindo com o navegador aberto...")
            
            # 1. Login interaction
            input("👉 INTERAÇÃO HUMANA NECESSÁRIA:\n1. Faça login se necessário.\n2. Abra o Workflow e posicione onde quiser.\n3. Quando estiver pronto, aperte [ENTER] aqui no terminal...")
            
            # 2. Inject prompts
            logger.info("Iniciando injeção de prompts...")
            input("👉 Aperte [ENTER] aqui no terminal e DEPOIS você terá 5 SEGUNDOS para voltar ao navegador e CLICAR na caixa de texto do seu prompt (nó CR Text)...")
            
            logger.info("⏳ Volte para o navegador e CLIQUE na caixa de texto! Começando em 5...")
            for i in range(5, 0, -1):
                logger.info(f"{i}...")
                time.sleep(1)
            logger.info("Escrevendo!")
            
            injetado = False
            for frame in page.frames:
                try:
                    res = frame.evaluate("""(text) => {
                        let el = document.activeElement;
                        if (el && (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT')) {
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
                logger.info("Todos os prompts foram injetados com sucesso pelo DOM!")
            else:
                logger.warning("Caixa não focada via DOM. Usando fallback de teclado...")
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.insert_text(prompts_text)

            # Capture existing images to ignore them
            initial_image_srcs = get_all_image_srcs(page)
            logger.info(f"Ignorando {len(initial_image_srcs)} imagens pré-existentes no canvas.")

            # 3. Click Executar
            logger.info("Procurando o botão de Executar (Lite/Plus)...")
            try:
                queue_btn = page.get_by_text("Executar").nth(1)
                queue_btn.click(timeout=5000)
                logger.info("Geração de Lote iniciada automaticamente!")
            except Exception as e:
                logger.error(f"Não achei o botão de gerar de forma automática: {e}")
                input("Aperte [ENTER] APÓS clicar no botão 'Executar' manualmente...")
            
            # 4. Monitor and save images
            expected_images = len(prompts_list)
            logger.info(f"⏳ Monitorando {expected_images} novas imagens. Acompanhe pelo terminal...")
            
            saved_srcs = set(initial_image_srcs)
            images_saved = 0
            start_wait_time = time.time()
            
            while images_saved < expected_images:
                current_srcs = get_all_image_srcs(page)
                new_srcs = current_srcs - saved_srcs
                
                for src in new_srcs:
                    if save_image_from_src(page, src):
                        images_saved += 1
                        logger.info(f"✅ Imagem {images_saved}/{expected_images} salva na pasta data/final/images!")
                        start_wait_time = time.time() # Reset timeout
                    saved_srcs.add(src) # Mark as processed whether success or fail to avoid retrying bad URLs
                
                # Check for timeout (e.g. 10 minutes without new images to allow slow generations)
                if time.time() - start_wait_time > 600:
                    logger.warning("⚠️ Tempo limite (10 minutos) atingido sem novas imagens. Encerrando lote...")
                    break
                    
                time.sleep(3) # Polling interval
                
            logger.info(f"🎉 Processo concluído! {images_saved} imagens geradas e salvas.")
            
            if images_saved > 0:
                # Wait a bit before closing
                time.sleep(3)

if __name__ == "__main__":
    run_factory_bot()
