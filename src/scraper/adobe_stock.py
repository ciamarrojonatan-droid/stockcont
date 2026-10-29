import argparse
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
IMAGES_DIR = DATA_DIR / "images"
TRENDS_FILE = DATA_DIR / "trends.json"
SESSION_DIR = BASE_DIR / "chrome_session"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("AdobeStockScout")

def setup_directories() -> None:
    """Ensure data directories exist."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Diretórios verificados: Imagens={IMAGES_DIR}, Sessão={SESSION_DIR}")

def download_image(url: str, item_id: str) -> str | None:
    """Download an image and save it locally in data/raw/images/."""
    safe_item_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(item_id))
    if not safe_item_id:
        safe_item_id = f"unknown_{int(time.time())}"

    try:
        response = httpx.get(url, timeout=12.0)
        response.raise_for_status()

        parsed_url = urlparse(url)
        ext = Path(parsed_url.path).suffix or ".jpg"
        if not ext.startswith("."):
            ext = ".jpg"

        filename = f"{safe_item_id}{ext}"
        filepath = IMAGES_DIR / filename

        with open(filepath, "wb") as f:
            f.write(response.content)

        return str(filepath.relative_to(BASE_DIR)).replace("\\", "/")
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error(f"Erro de rede ao baixar imagem {url}: {e}")
    except OSError as e:
        logger.error(f"Erro de arquivo ao salvar {url}: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar {url}: {e}")

    return None

def parse_download_count(text: str) -> int:
    """Helper to convert download string (e.g. '100,000+', '10K+') into an integer for ranking."""
    if not text:
        return 0
    clean = text.replace(",", "").replace("+", "").strip().upper()
    try:
        if "M" in clean:
            return int(float(clean.replace("M", "")) * 1_000_000)
        if "K" in clean:
            return int(float(clean.replace("K", "")) * 1_000)
        return int(clean)
    except Exception:
        return 0

def scrape_contributor_insights(
    content_type: str = "photo",
    max_items: int = 20,
    min_downloads: int = 0,
    deep_profile: bool = False,
    headless: bool = False
) -> list[dict[str, Any]]:
    """
    Scrapes top-selling images and top contributors directly from
    Adobe Stock Contributor Insights (https://contributor.stock.adobe.com/en/insights/best/contributors).
    Uses a persistent browser session so login is preserved.
    """
    setup_directories()
    scraped_data: list[dict[str, Any]] = []
    insights_url = "https://contributor.stock.adobe.com/en/insights/best/contributors"

    logger.info("=" * 65)
    logger.info("🚀 Iniciando Fase 1: Olheiro de Insights (Adobe Stock Contributor)")
    logger.info(f"URL Alvo: {insights_url}")
    logger.info(f"Tipo: {content_type} | Máx Itens: {max_items} | Perfil Profundo: {deep_profile}")
    logger.info("=" * 65)

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": SESSION_DIR,
            "headless": headless,
            "viewport": {"width": 1280, "height": 800},
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized"
            ]
        }

        # Conectar ao Chrome existente se estiver com porta de depuração ou abrir nova janela Chromium dedicada
        browser = None
        is_cdp = False
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            logger.info("⚡ Conectado com sucesso ao Chrome existente via porta 9222!")
            is_cdp = True
        except Exception:
            pass

        if not browser:
            browser = p.chromium.launch_persistent_context(**launch_kwargs)

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            logger.info("Navegando para o portal Adobe Stock Contributor...")
            page.goto(insights_url, wait_until="domcontentloaded", timeout=45000)

            # 1. Verificar se é necessário fazer Login
            time.sleep(3)
            current_url = page.url
            if any(k in current_url for k in ["auth.services.adobe.com", "adobelogin", "login", "signin"]):
                page.bring_to_front()
                print("\n" + "=" * 70, flush=True)
                print("🔐 LOGIN NECESSÁRIO NO ADOBE STOCK CONTRIBUTOR", flush=True)
                print("👉 Por favor, faça login na sua conta da Adobe na janela do Chrome aberta.", flush=True)
                print("⏳ O bot está aguardando você concluir o login (sessão será salva)...", flush=True)
                print("=" * 70 + "\n", flush=True)

                start_wait = time.time()
                logged_in = False
                last_log = time.time()
                while time.time() - start_wait < 600: # Aguarda até 10 minutos
                    time.sleep(2)
                    c_url = page.url
                    if "contributor.stock.adobe.com" in c_url and "auth.services.adobe.com" not in c_url:
                        logger.info("✅ Login detectado com sucesso!")
                        logged_in = True
                        time.sleep(3)
                        break
                    if time.time() - last_log > 15:
                        logger.info(f"⏳ Aguardando login no navegador... (Ainda em: {c_url[:55]}...)")
                        last_log = time.time()

                if not logged_in:
                    logger.error("Tempo limite de login esgotado.")
                    browser.close()
                    return []

            # Garantir que estamos na URL de insights
            if "insights/best/contributors" not in page.url:
                logger.info("Redirecionando para a página de Best Contributors...")
                page.goto(insights_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

            # 2. Fechar Modal 'How It works' se estiver presente
            logger.info("Verificando se há modais abertos ('How It works')...")
            try:
                page.keyboard.press("Escape")
                time.sleep(0.5)
                # Tenta clicar no botão de fechar (X)
                close_selectors = [
                    "button[aria-label*='close' i]",
                    "button.close",
                    "[class*='close']",
                    "button:has-text('✕')",
                    "button:has-text('Close')"
                ]
                for sel in close_selectors:
                    close_btn = page.locator(sel)
                    if close_btn.count() > 0 and close_btn.first.is_visible():
                        close_btn.first.click()
                        time.sleep(0.5)
                        break
            except Exception as e:
                logger.debug(f"Aviso ao tratar modal: {e}")

            # 3. Selecionar a aba de categoria (Photos, Illustrations, Vectors)
            target_tab = "Photos"
            if content_type.lower() in ["illustration", "illustrations"]:
                target_tab = "Illustrations"
            elif content_type.lower() in ["vector", "vectors"]:
                target_tab = "Vectors"
            elif content_type.lower() in ["video", "videos", "footage"]:
                target_tab = "Videos"

            logger.info(f"Selecionando aba '{target_tab}' em Recent Top Sellers...")
            try:
                tab_locator = page.locator(f"button:has-text('{target_tab}'), a:has-text('{target_tab}'), [role='tab']:has-text('{target_tab}')")
                if tab_locator.count() > 0:
                    tab_locator.first.click()
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"Não foi possível clicar na aba {target_tab}: {e}")

            # Rolagem suave para carregar os contribuidores
            for _ in range(2):
                page.mouse.wheel(0, 800)
                time.sleep(1.2)

            # 4. Extração dos perfis de contribuidores e imagens top sellers
            logger.info("Analisando perfis com maior volume de vendas...")
            contributors_data = page.evaluate(r"""() => {
                const results = [];
                // Identificar links de perfil de contribuidores
                const profileLinks = Array.from(document.querySelectorAll('a')).filter(a => 
                    a.textContent.includes('View profile') || (a.href && a.href.includes('/contributor/'))
                );

                for (const link of profileLinks) {
                    // Subir na hierarquia até achar o card/linha completa com dados e fotos
                    let container = null;
                    let curr = link.parentElement;
                    for (let i = 0; i < 7; i++) {
                        if (curr) {
                            if (curr.querySelectorAll('img').length >= 2) {
                                container = curr;
                                break;
                            }
                            curr = curr.parentElement;
                        }
                    }
                    if (!container) {
                        container = link.closest('section, article, div[class*="row"], div[class*="card"], div') || link.parentElement;
                    }

                    const cardText = container ? container.innerText : "";
                    
                    // Extrair Downloads
                    let downloads = "N/A";
                    const lifetimeMatch = cardText.match(/LIFETIME\s*DOWNLOADS\s*[\r\n:]*\s*([^\r\n]+)/i);
                    if (lifetimeMatch) {
                        downloads = lifetimeMatch[1].trim();
                    } else {
                        const dlMatch = cardText.match(/([\d,]+K?\+?)\s*(?:downloads)?/i);
                        if (dlMatch) downloads = dlMatch[1].trim();
                    }

                    // Extrair Nome
                    let name = "Contributor";
                    const lines = cardText.split('\n').map(l => l.trim()).filter(l => l);
                    for (let l of lines) {
                        if (!l.toUpperCase().includes('LIFETIME') && !l.toUpperCase().includes('DOWNLOAD') && !l.includes('View profile') && l.length > 1 && l.length < 35) {
                            name = l;
                            break;
                        }
                    }

                    // Coletar imagens exibidas para esse contribuidor
                    const images = [];
                    // Busca imagens no container e também em elementos irmãos próximos
                    let searchArea = container;
                    if (container && container.querySelectorAll('img').length <= 1 && container.parentElement) {
                        searchArea = container.parentElement;
                    }

                    if (searchArea) {
                        const imgs = searchArea.querySelectorAll('img');
                        for (const img of imgs) {
                            const src = img.src || img.getAttribute('data-lazy') || img.getAttribute('data-src');
                            const alt = img.alt || '';
                            if (src && !src.includes('avatar') && !src.includes('profile')) {
                                let assetId = "";
                                const parentA = img.closest('a');
                                if (parentA && parentA.href) {
                                    const m = parentA.href.match(/(\d{7,12})/);
                                    if (m) assetId = m[1];
                                }
                                if (!assetId) {
                                    const m = src.match(/_F_(\d{7,12})_/);
                                    if (m) assetId = m[1];
                                }
                                if (!assetId) {
                                    const m = src.match(/(\d{7,12})/);
                                    if (m) assetId = m[1];
                                }
                                images.push({
                                    id: assetId || ('gen_' + Math.floor(Math.random() * 10000000)),
                                    title: alt || 'Best Seller Asset',
                                    src: src,
                                    detail_url: parentA ? parentA.href : ''
                                });
                            }
                        }
                    }

                    results.push({
                        name: name,
                        downloads: downloads,
                        profile_url: link.href,
                        images: images
                    });
                }
                return results;
            }""")

            logger.info(f"Foram encontrados {len(contributors_data)} perfis no painel de Top Sellers.")

            # Ordenar perfis pelos que mais vendem
            contributors_data.sort(
                key=lambda c: parse_download_count(c.get("downloads", "")),
                reverse=True
            )

            seen_ids = set()

            for contrib in contributors_data:
                name = contrib.get("name", "Unknown")
                downloads_str = contrib.get("downloads", "N/A")
                downloads_num = parse_download_count(downloads_str)
                profile_url = contrib.get("profile_url", "")
                images = contrib.get("images", [])

                logger.info(f"⭐ Perfil: {name} | Downloads: {downloads_str} | Imagens no grid: {len(images)}")

                if min_downloads > 0 and downloads_num < min_downloads:
                    logger.info(f"Ignorando {name} por estar abaixo de {min_downloads} downloads.")
                    continue

                for img_data in images:
                    if len(scraped_data) >= max_items:
                        break

                    item_id = str(img_data.get("id"))
                    if item_id in seen_ids:
                        continue

                    title = img_data.get("title") or f"Top Seller by {name}"
                    img_url = img_data.get("src")
                    if not img_url or not img_url.startswith("http"):
                        continue

                    seen_ids.add(item_id)
                    logger.info(f"Baixando imagem best-seller [{item_id}] de {name} ({downloads_str})...")
                    local_path = download_image(img_url, item_id)

                    if local_path:
                        scraped_data.append({
                            "id": item_id,
                            "title": title,
                            "contributor_name": name,
                            "contributor_downloads": downloads_str,
                            "profile_url": profile_url,
                            "content_type": content_type,
                            "source": "contributor_insights",
                            "original_url": img_url,
                            "local_path": local_path,
                            "scraped_at": time.time()
                        })

                if len(scraped_data) >= max_items:
                    break

                # 5. Modo Perfil Profundo: Visitar portfólio dos maiores vendedores
                if deep_profile and profile_url and len(scraped_data) < max_items:
                    logger.info(f"🔎 Explorando portfólio completo de {name} ({profile_url})...")
                    try:
                        profile_page = browser.new_page()
                        # Adiciona filtro de mais baixados se for URL de busca
                        p_url = profile_url + ("&order=nb_downloads" if "?" in profile_url else "?order=nb_downloads")
                        profile_page.goto(p_url, wait_until="domcontentloaded", timeout=25000)
                        time.sleep(2)
                        profile_page.mouse.wheel(0, 1000)
                        time.sleep(1)

                        extra_items = profile_page.locator("article.search-result-cell, [data-content-id], div.search-result-cell").all()
                        for extra in extra_items:
                            if len(scraped_data) >= max_items:
                                break
                            e_id = extra.get_attribute("data-content-id")
                            if not e_id or e_id in seen_ids:
                                continue
                            e_img = extra.locator("img").first
                            if e_img.count() == 0:
                                continue
                            e_title = e_img.get_attribute("alt") or f"Top asset by {name}"
                            e_src = e_img.get_attribute("src") or e_img.get_attribute("data-lazy")
                            if not e_src or not e_src.startswith("http"):
                                continue

                            seen_ids.add(e_id)
                            logger.info(f"Extraindo asset do portfólio [{e_id}]...")
                            l_path = download_image(e_src, e_id)
                            if l_path:
                                scraped_data.append({
                                    "id": e_id,
                                    "title": e_title,
                                    "contributor_name": name,
                                    "contributor_downloads": downloads_str,
                                    "profile_url": profile_url,
                                    "content_type": content_type,
                                    "source": "contributor_portfolio",
                                    "original_url": e_src,
                                    "local_path": l_path,
                                    "scraped_at": time.time()
                                })
                        profile_page.close()
                    except Exception as e:
                        logger.warning(f"Erro ao extrair portfólio de {name}: {e}")

        except PlaywrightTimeoutError:
            logger.error("Timeout aguardando carregamento da página de Contributor Insights.")
        except Exception as e:
            logger.error(f"Erro inesperado durante raspagem de insights: {e}")
        finally:
            browser.close()

    save_data(scraped_data)
    return scraped_data

def build_adobe_stock_url(
    query: str = "trending",
    order: str = "relevance",
    content_type: str = "all"
) -> str:
    """Construct a clean, valid search URL for Adobe Stock with niche parameters."""
    base_url = "https://stock.adobe.com/search"
    params: dict[str, Any] = {
        "k": query,
        "order": order,
        "safe_search": "1",
    }

    if content_type == "photo":
        params["filters[content_type:photo]"] = "1"
    elif content_type == "illustration":
        params["filters[content_type:illustration]"] = "1"
    elif content_type in ["video", "footage"]:
        params["filters[content_type:video]"] = "1"

    return f"{base_url}?{urlencode(params)}"

def scrape_adobe_stock_trends(
    query: str = "trending",
    order: str = "relevance",
    content_type: str = "all",
    max_items: int = 20,
    headless: bool = False
) -> list[dict[str, Any]]:
    """Scrape trending images from Adobe Stock matching a niche or topic (Public Search)."""
    setup_directories()
    scraped_data: list[dict[str, Any]] = []

    search_url = build_adobe_stock_url(query=query, order=order, content_type=content_type)
    logger.info(f"Navegando para busca pública do Adobe Stock: {search_url} (máx: {max_items})")

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": SESSION_DIR,
            "headless": headless,
            "viewport": {"width": 1280, "height": 800},
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized"
            ]
        }
        browser = p.chromium.launch_persistent_context(**launch_kwargs)

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            
            try:
                page.wait_for_selector("article.search-result-cell, div.search-result-cell, [data-content-id]", timeout=15000)
            except Exception:
                time.sleep(3)

            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(random.uniform(1.0, 1.8))

            items = page.locator("article.search-result-cell, div.search-result-cell, [data-content-id]")
            all_items = items.all()
            logger.info(f"Encontrados {len(all_items)} itens potenciais na busca pública.")

            seen_ids = set()
            for item in all_items:
                if len(scraped_data) >= max_items:
                    break

                try:
                    item_id = item.get_attribute("data-content-id")
                    if not item_id or item_id in seen_ids:
                        continue

                    img_locator = item.locator("img").first
                    if img_locator.count() == 0:
                        continue

                    title = img_locator.get_attribute("alt") or "Untitled"
                    img_url = img_locator.get_attribute("src") or img_locator.get_attribute("data-lazy")

                    if not img_url or not img_url.startswith("http"):
                        continue

                    seen_ids.add(item_id)
                    logger.info(f"Extraindo asset [{item_id}]: {title[:40]}...")
                    local_path = download_image(img_url, item_id)

                    if local_path:
                        scraped_data.append({
                            "id": item_id,
                            "title": title,
                            "niche": query,
                            "source": "public_search",
                            "original_url": img_url,
                            "local_path": local_path,
                            "scraped_at": time.time()
                        })

                except Exception as e:
                    logger.warning(f"Erro ao extrair item: {e}")

                time.sleep(random.uniform(0.2, 0.5))

        except PlaywrightTimeoutError:
            logger.error("Timeout aguardando resultados do Adobe Stock.")
        except Exception as e:
            logger.error(f"Erro inesperado durante raspagem pública: {e}")
        finally:
            browser.close()

    save_data(scraped_data)
    return scraped_data

def save_data(data: list[dict[str, Any]]) -> None:
    """Save scraped metadata to JSON without duplicating existing entries."""
    if not data:
        logger.warning("Nenhum dado novo para salvar.")
        return

    existing_data: list[dict[str, Any]] = []
    if TRENDS_FILE.exists():
        try:
            with open(TRENDS_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("trends.json corrompido. Iniciando novo arquivo.")

    existing_ids = {str(item["id"]) for item in existing_data if "id" in item}
    new_items = [item for item in data if str(item["id"]) not in existing_ids]

    combined_data = existing_data + new_items

    with open(TRENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Salvos {len(new_items)} novos itens. Total acumulado em trends.json: {len(combined_data)}.")

def main() -> None:
    parser = argparse.ArgumentParser(description="StockCont - Adobe Stock Trend & Contributor Insights Scraper")
    parser.add_argument("--mode", "-m", default="insights", choices=["insights", "search"], help="Modo de extração: 'insights' (Contributor Top Sellers) ou 'search' (busca pública por termo)")
    parser.add_argument("--query", "-q", default="trending", help="Palavra-chave/nicho para busca pública (usado quando mode=search)")
    parser.add_argument("--order", "-o", default="relevance", choices=["relevance", "nb_downloads", "creation"], help="Ordenação na busca pública")
    parser.add_argument("--type", "-t", default="photo", choices=["all", "photo", "illustration", "vector", "video"], help="Tipo de asset (photo, illustration, vector, video, all)")
    parser.add_argument("--max-items", type=int, default=15, help="Quantidade máxima de imagens para capturar")
    parser.add_argument("--min-downloads", type=int, default=0, help="Filtro mínimo de downloads do contribuidor (ex: 10000)")
    parser.add_argument("--deep-profile", action="store_true", help="Minerar também portfólio completo dos maiores contribuidores")
    parser.add_argument("--headless", action="store_true", help="Executar em modo headless (sem janela)")

    args = parser.parse_args()

    if args.mode == "insights":
        scrape_contributor_insights(
            content_type=args.type,
            max_items=args.max_items,
            min_downloads=args.min_downloads,
            deep_profile=args.deep_profile,
            headless=args.headless
        )
    else:
        scrape_adobe_stock_trends(
            query=args.query,
            order=args.order,
            content_type=args.type,
            max_items=args.max_items,
            headless=args.headless
        )

if __name__ == "__main__":
    main()
