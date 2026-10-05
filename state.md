# Estado do Projeto: StockCont (AI Stock Generator)

## 📌 Visão Geral
Sistema automatizado para análise de tendências, geração em massa e catalogação de assets (imagens e vídeos) gerados por IA para venda em plataformas de microstock (foco inicial: Adobe Stock).

## 🚀 Progresso das Fases

### Fase 1: O "Olheiro" (Trend Analyzer)
*Status: 🟢 Concluído*
- [x] Rascunho da arquitetura (`tendencias.plan.md`).
- [x] Scraper desenvolvido em Python com Playwright (`src/scraper/adobe_stock.py`).
- [x] Armazenamento de imagens e JSON definidos em `data/raw/`.

### Fase 2: Diretor de Arte (Engenharia de Prompts)
*Status: 🟢 Concluído*
- [x] Integração com Google Gemini Vision 1.5/3.8-flash (`src/analyzer/director.py`).
- [x] Engenharia reversa para "DNA visual" e geração de prompts derivados.
- [x] Salva 5 prompts em lote no `data/processed/prompts.json`.

### Fase 3: A Fábrica (Geração em Massa)
*Status: 🟢 Concluído*
- [x] Automação Híbrida RPA com Playwright para Runninghub (`src/factory/runninghub_bot.py`).
- [x] Injeção de Batch Prompts otimizada (Instantânea via `insert_text`).
- [x] Salvamento manual aprovado (contorna instabilidades da engine de canvas fechada do ComfyUI).
- [x] O Pipeline de Upscale é resolvido pelo próprio workflow interno no Runninghub do usuário.

### Fase 4: O Catalogador (Metadados e SEO)
*Status: 🟢 Concluído*
- [x] Integração com a API moderna `google-genai` para Visão Computacional (`src/cataloger/adobe_csv_maker.py`).
- [x] Leitura automática de arquivos na pasta `data/final/images/`.
- [x] Geração de Título comercial e exatamente 50 palavras-chave perfeitas via Gemini 1.5 Flash.
- [x] Exportação final automatizada para o arquivo `data/processed/adobe_stock_upload.csv`, pronto para envio ao Adobe Stock.

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub conectado e sincronizado.
- [x] Ambiente Virtual Python configurado (`venv` e `requirements.txt`).
- [x] Ambiente Antigravity/ECC configurado (`.agents/`).

## 🎯 Próximo Passo Imediato
- O sistema principal está totalmente operacional! O fluxo diário agora consiste em:
  1. Rodar a Fase 1 e 2 para pesquisar e criar os prompts.
  2. Rodar a Fase 3 e salvar as imagens no diretório final.
  3. Rodar a Fase 4 para processar as imagens e subir o arquivo CSV gerado junto com as fotos no Adobe Stock.
