# Rules: Scraper & Trend Mining (`src/scraper/`)

Regras e padrões obrigatórios para o módulo de scraping do Adobe Stock:

1. **Sessão Persistente**: Utilize o diretório `chrome_session/` para persistência de cookies e dados de login. Nunca delete ou limpe essa pasta sem comando explícito.
2. **Resiliência a Modais e Banners**: O portal Adobe Stock frequentemente exibe popups promocionais e consentimento de cookies. Use `page.locator(...).first` com timeouts seguros (3.000ms a 5.000ms) e `try/except` silencioso para fechar modais sem travar o scraping.
3. **Download Seguro de Previews**: Todo download de imagem via `httpx` deve ter timeout de 12.0s e sanitização de `item_id` com regex `[^a-zA-Z0-9_-]` para evitar quebras de sistema de arquivos.
4. **Modos de Operação**:
   - `insights`: Alvo `https://contributor.stock.adobe.com/en/insights/best/contributors` (requer sessão).
   - `search`: Alvo `https://stock.adobe.com/search` (público, sem login obrigatório).
5. **Persistência**: Gravações em `data/raw/trends.json` devem ser atômicas e preservar o array existente caso haja novos itens adicionados.
