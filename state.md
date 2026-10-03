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
*Status: 🟡 Implementado (Aguardando Testes)*
- [x] Automação Híbrida RPA com Playwright para Runninghub (`src/factory/runninghub_bot.py`).
- [x] Injeção de Batch Prompts em node nativo.
- [x] Tratamento de pop-ups de erro e automação de download ("Save Image").
- [ ] O Pipeline de Upscale será resolvido pelo próprio workflow interno no Runninghub do usuário.

### Fase 4: O Catalogador (Metadados e SEO)
*Status: 🔴 Não Iniciado*
- [ ] Visão Computacional para ler a imagem final.
- [ ] Geração de Título e 50 palavras-chave (CSV export formatado para Adobe Stock).

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub inicializado e conectado.
- [x] Ambiente Virtual Python configurado (`venv` e `requirements.txt`).
- [x] Ambiente Antigravity/ECC configurado (`.agents/`).

## 🎯 Próximo Passo Imediato
- Validar a automação da Fábrica (Runninghub) executando `runninghub_bot.py` na máquina local, **OU** iniciar a arquitetura e desenvolvimento da **Fase 4 (O Catalogador)** para automatizar as palavras-chave para o Adobe Stock.
