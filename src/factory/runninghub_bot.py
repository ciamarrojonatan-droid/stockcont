import json
import logging
import time
from pathlib import Path
from typing import Any, List
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

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

def load_prompts(batch_size: int = DEFAULT_BATCH_SIZE) -> str:
    """Load prompts and format them for the batch node."""
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            data: List[dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        logger.error("Prompts file not found!")
        return ""
    except json.JSONDecodeError:
        logger.error("Failed to parse the prompts JSON file!")
        return ""
        
    all_prompts: List[str] = []
    for item in data:
        for p in item.get("generated_prompts", []):
            all_prompts.append(p["prompt"].replace("\n", " ").strip())
            
    # Take the first 'batch_size' prompts
    batch = all_prompts[:batch_size]
    logger.info(f"Loaded {len(batch)} prompts for this batch.")
    return "\n".join(batch)

def run_factory_bot() -> None:
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    prompts_text = load_prompts(batch_size=DEFAULT_BATCH_SIZE)
    if not prompts_text:
        return
        
    with sync_playwright() as p:
        # Use a persistent context so you don't have to login every time
        user_data_dir = BASE_DIR / "playwright_session"
        with p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            accept_downloads=True
        ) as browser:
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            logger.info("Opening Runninghub... Please login if necessary.")
            page.goto("https://www.runninghub.ai/") # Replace with the exact workflow URL if needed
            
            input("👉 INTERAÇÃO HUMANA NECESSÁRIA:\n1. Faça login no Runninghub se necessário.\n2. Abra o seu Workflow.\n3. Dê zoom para que o node de 'Save Image' fique no CENTRO da tela.\n4. Quando estiver tudo pronto, aperte [ENTER] aqui no terminal para o bot assumir...")
            
            logger.info("Iniciando injeção de prompts...")
            
            input("👉 Clique dentro da caixa de texto do seu nó de Prompts (para focar o cursor) e aperte [ENTER] no terminal...")
            
            # O bot "digita" os prompts na caixa que está selecionada
            page.evaluate("navigator.clipboard.writeText(arguments[0])", prompts_text)
            page.keyboard.press("Control+V")
            logger.info("Prompts colados com sucesso!")
            
            # Clicar em Queue Prompt / Generate
            logger.info("Procurando o botão de gerar...")
            try:
                queue_btn = page.locator("button:has-text('Queue'), button:has-text('Generate'), #queue-button").first
                queue_btn.click(timeout=5000)
                logger.info("Geração iniciada! Aguardando o término (pode levar vários minutos)...")
            except PlaywrightTimeoutError:
                logger.error("Timeout: Não achei o botão de gerar automaticamente. Por favor clique nele.")
                input("Aperte [ENTER] após clicar em gerar...")
            except PlaywrightError as e:
                logger.error(f"Erro do Playwright ao clicar no botão gerar: {e}")
                input("Aperte [ENTER] após clicar em gerar...")

            # Aguardar o pop-up de erro
            logger.info("Monitorando tela em busca do pop-up de erro...")
            # A maioria dos erros no ComfyUI/Runninghub aparecem em um dialog
            error_dialog = page.locator(".comfy-modal, dialog, .error-popup").locator("button:has-text('OK'), button:has-text('Close')").first
            
            # Fica tentando achar o botão de OK do erro (isso trava até o erro aparecer)
            error_dialog.wait_for(state="visible", timeout=0) # timeout=0 significa esperar para sempre
            error_dialog.click()
            logger.info("Pop-up de erro detectado e fechado!")
            
            # Tempo pro pop-up sumir visualmente
            time.sleep(1)

            logger.info("Iniciando download da imagem no canvas...")
            # Clica com o botão direito bem no meio da tela (onde você deixou o nó 'Save Image')
            viewport_size = page.viewport_size
            if viewport_size:
                center_x = viewport_size["width"] / 2
                center_y = viewport_size["height"] / 2
                page.mouse.click(center_x, center_y, button="right")
                time.sleep(0.5)
            
            # Agora clica em "Save Image" no menu de contexto
            try:
                with page.expect_download(timeout=10000) as download_info:
                    save_option = page.locator("td:has-text('Save Image'), li:has-text('Save Image'), div:has-text('Save Image')").first
                    save_option.click()
                
                download = download_info.value
                filepath = FINAL_IMAGES_DIR / download.suggested_filename
                download.save_as(filepath)
                logger.info(f"SUCESSO! Imagens salvas em: {filepath}")
            except PlaywrightTimeoutError:
                logger.error("Timeout ao aguardar o evento de download do navegador.")
                input("Por favor, faça o download manualmente e aperte [ENTER] para encerrar...")
            except PlaywrightError as e:
                logger.error(f"Falha ao automatizar o clique em 'Save Image'. Erro: {e}")
                input("Por favor, faça o download manualmente e aperte [ENTER] para encerrar...")
                
            logger.info("Fábrica finalizou este lote!")

if __name__ == "__main__":
    run_factory_bot()
