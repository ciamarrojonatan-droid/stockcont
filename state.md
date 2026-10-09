# Estado do Projeto: StockCont (AI Stock Generator)

## 📌 Visão Geral
Sistema automatizado para análise de tendências de microstock, engenharia reversa multimodal de prompts, geração assistida por IA e catalogação inteligente com metadados IPTC/EXIF embutidos e CSV pronto para Adobe Stock.

## 🚀 Progresso das Fases

### Fase 1: O "Olheiro" (Trend Analyzer)
*Status: 🟢 Concluído & Otimizado*
- [x] Scraper desenvolvido em Python com Playwright (`src/scraper/adobe_stock.py`).
- [x] Stealth antibot integrado com Chrome persistente (bypass de bloqueio 403 / DataDome).
- [x] Parametrização dinâmica por Nicho (`--query`, `--order`, `--type`, `--max-items`).
- [x] Filtros por ordem de relevância, mais baixados (`nb_downloads`) e tipo de asset (foto/ilustração).
- [x] Armazenamento de metadados em `data/raw/trends.json` (14 itens gravados) e imagens em `data/raw/images/`.

### Fase 2: Diretor de Arte (Engenharia de Prompts)
*Status: 🟢 Concluído & Otimizado*
- [x] Integração de alta velocidade com Gemini Multimodal via REST (`src/analyzer/director.py`).
- [x] Engenharia reversa para "DNA visual" (estilo, iluminação, composição, paleta) e geração de prompts comerciais derivados.
- [x] Fila de 70 prompts prontos salvos em `data/processed/prompts.json` com escrita atômica contra falhas.

### Fase 3: A Fábrica (Geração em Massa)
*Status: 🟢 Concluído*
- [x] Automação Híbrida RPA com Playwright para Runninghub (`src/factory/runninghub_bot.py`).
- [x] Injeção de Batch Prompts otimizada (Instantânea via `insert_text`).
- [x] Fluxo de persistência do Chrome com profile dedicado para manter login ativo.

### Fase 4: O Catalogador (Metadados e SEO)
*Status: 🟢 Concluído & Testado de Ponta a Ponta*
- [x] Análise visual ultrarrápida (sub-3s) com Gemini Vision via REST (`src/cataloger/adobe_csv_maker.py`).
- [x] Título comercial otimizado e exatamente 50 palavras-chave ranqueadas por relevância.
- [x] Classificação automática da Categoria numérica nativa do Adobe Stock.
- [x] **Injeção binária de IPTC**: Object Name, Caption e Keywords gravados no JPG via `iptcinfo3` (preenchimento automático no portal do Adobe Stock).
- [x] **Injeção binária de EXIF**: ImageDescription, XPTitle e XPKeywords gravados via `piexif` (compatível com Windows, Lightroom e Bridge).
- [x] Conversão automática de PNG para JPG de alta qualidade (qualidade 98) caso o gerador produza arquivos PNG.
- [x] Exportação e atualização incremental do CSV `data/processed/adobe_stock_upload.csv`.

---

## 🎮 Orquestrador Maestro Central (`main.py`)
*Status: 🟢 Operacional*
- [x] CLI unificado com dashboard visual de status: `python main.py --status`.
- [x] Execução modular por fase: `python main.py --phase [1|2|3|4]`.
- [x] Suporte a argumentos de nicho diretamente no comando central (ex: `python main.py --phase 1 -q "minimalist office" -o nb_downloads`).
- [x] Modo de execução contínua encadeada: `python main.py --all`.

---

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub conectado e sincronizado.
- [x] Dependências atualizadas em `requirements.txt` (`piexif`, `iptcinfo3`, `httpx`, `pillow`, `google-genai`).
- [x] Resiliência de encoding no terminal Windows (UTF-8 sem falhas de cp1252).
- [x] Protocolo de orquestração autônoma e skills ECC configurados.

---

## 🎯 Próximo Passo Operacional
1. Executar a Fase 1 com um nicho de alto interesse comercial:
   `python main.py --phase 1 -q "business technology team" -o nb_downloads -m 10`
2. Executar a Fase 2 para gerar os prompts:
   `python main.py --phase 2`
3. Executar a Fábrica no Runninghub para gerar as fotos:
   `python main.py --phase 3`
4. Executar o Catalogador para embutir metadados nas novas imagens e atualizar o CSV:
   `python main.py --phase 4`
5. Fazer upload das fotos no portal de contribuinte do Adobe Stock (o site lerá os metadados IPTC instantaneamente).
