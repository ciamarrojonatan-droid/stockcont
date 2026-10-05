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
            channel="chrome", # Usa o Chrome real instalado no PC (evita o bloqueio do Google)
            headless=False,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"] # Oculta que é um robô
        ) as browser:
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            logger.info("Opening Runninghub Workflow... Please login if necessary.")
            page.goto("https://www.runninghub.ai/pt-br/workflow/2025818595460128770?source=workspace")
            
            input("👉 INTERAÇÃO HUMANA NECESSÁRIA:\n1. Faça login no Runninghub se necessário.\n2. Abra o seu Workflow.\n3. Dê zoom para que o node de 'Save Image' fique no CENTRO da tela.\n4. Quando estiver tudo pronto, aperte [ENTER] aqui no terminal para o bot assumir...")
            
            logger.info("Iniciando injeção de prompts...")
            
            input("👉 Aperte [ENTER] aqui no terminal e DEPOIS você terá 5 SEGUNDOS para voltar ao navegador e CLICAR na sua ÚNICA caixa de texto (nó CR Text)...")
            
            logger.info("⏳ Volte para o navegador e CLIQUE na caixa de texto! Começando em 5...")
            time.sleep(1)
            logger.info("4...")
            time.sleep(1)
            logger.info("3...")
            time.sleep(1)
            logger.info("2...")
            time.sleep(1)
            logger.info("1... Escrevendo!")
            time.sleep(1)
            
            logger.info("Iniciando injeção de todos os prompts na caixa de texto...")
            # Opção B escolhida: Injetar todo o bloco de 20 prompts de uma só vez!
            # O ComfyUI e o Runninghub cuidarão de gerar o batch (usando PromptLine ou similar).
            
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
                logger.info("Todos os 20 prompts foram injetados com sucesso num único bloco de texto!")
            else:
                logger.warning("Caixa não focada. Usando fallback de Inserção Rápida...")
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                # insert_text cola todo o bloco de uma vez instantaneamente (como se fosse Ctrl+V)
                page.keyboard.insert_text(prompts_text)
            
            # Clicar em Executar (Botão do Meio - Lite/Plus)
            logger.info("Procurando o botão de Executar (Lite/Plus)...")
            try:
                queue_btn = page.get_by_text("Executar").nth(1)
                queue_btn.click(timeout=5000)
                logger.info("Geração de Lote iniciada!")
            except PlaywrightTimeoutError:
                logger.error("Não achei o botão de gerar. Por favor clique nele e aperte [ENTER].")
                input("Aperte [ENTER] após clicar em gerar...")
            except PlaywrightError as e:
                logger.error(f"Erro ao clicar: {e}")
                input("Aperte [ENTER] após clicar em gerar...")

            logger.info("A geração está rodando no site...")
            logger.info("👉 COMO O CANVAS DO COMFYUI É FECHADO, O SALVAMENTO AUTOMÁTICO É INSTÁVEL.")
            logger.info("👉 POR FAVOR, QUANDO AS IMAGENS TERMINAREM DE GERAR, SALVE-AS MANUALMENTE NA PASTA: data/final/images/")
            input("Aperte [ENTER] para encerrar o robô...")
            logger.info("Fábrica finalizou este lote!")

if __name__ == "__main__":
    run_factory_bot()
