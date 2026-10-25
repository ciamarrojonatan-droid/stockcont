---
name: stockcont-mine
description: >-
  One-shot autonomous niche exploration: scouts top sellers, downloads
  visual references, and synthesizes 10 cinematic 700-1000 word prompts
  with adaptive copy-space via Gemini Vision. Use when running /mine <niche>.
---

# StockCont Autonomous Niche Miner (`/mine`)

Comando *one-shot* para descoberta de mercado e engenharia de prompts imediatos sobre um nicho específico.

## 🧭 Uso & Sintaxe

```bash
/mine "<nicho comercial>"
```

*Exemplos*:
- `/mine "biotech longevity laboratory"`
- `/mine "clean energy hydrogen plant"`
- `/mine "fintech algorithmic trading workstation"`
- Se invocado sem argumentos (`/mine`), o comando consulta o **Radar Sazonal (D+75 dias)** e seleciona o micro-nicho Blue Ocean de maior pontuação.

---

## ⚡ Fluxo de Execução Autônoma (Fases 1 + 2)

### Passo 1: Mineração de Referências (Fase 1)
O agente executa o scraper público filtrando pelos ativos mais baixados do Adobe Stock:
```powershell
.\venv\Scripts\python.exe main.py --phase 1 --mode search --query "<nicho>" --order nb_downloads --type photo --max-items 10
```
- Valida que as referências e previews foram salvos em `data/raw/images/`.
- Registra metadados e contagem de downloads em `data/raw/trends.json`.

### Passo 2: Engenharia Reversa Multimodal v3.0 (Fase 2)
O agente aciona o Diretor de Arte:
```powershell
.\venv\Scripts\python.exe main.py --phase 2
```
- Analisa as referências baixadas com Gemini Vision (`gemini-3.5-flash-lite` ou `gemini-3.8-flash`).
- Gera exatamente **10 prompts ultra-densos (700 a 1.000 palavras em inglês)** por referência.
- Garante reserva de 35% a 50% de Copy-Space limpo para compradores corporativos B2B.
- Salva atomicamente em `data/processed/prompts.json`.

### Passo 3: Sincronização & Relatório
1. Executa a leitura de métricas e atualiza o `state.md`.
2. Exibe o resumo com:
   - Quantidade de referências mineradas.
   - Total de prompts de 700-1000 palavras adicionados à fila de produção da Fase 3.
   - Próximo passo sugerido: `python main.py --phase 3 --node 192`.
