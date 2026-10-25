---
name: stockcont-pipeline
description: >-
  Executes, monitors, and orchestrates the 5-phase StockCont pipeline
  end-to-end or phase-by-phase with automated pre-flight checks,
  error recovery, and state synchronization. Use when running /pipeline.
---

# StockCont Pipeline Orchestrator (`/pipeline`)

Orquestrador unificado para execução autônoma das 5 fases da esteira StockCont.

## 🧭 Comportamento dos Parâmetros

| Comando | Ação |
| :--- | :--- |
| `/pipeline` | Detecta a próxima fase pendente analisando o estado atual e executa |
| `/pipeline --phase 1` | Executa a Fase 1: Mineração de tendências (Scout) |
| `/pipeline --phase 2` | Executa a Fase 2: Geração de prompts v3.0 (700-1000 palavras) com Gemini Vision |
| `/pipeline --phase 3` | Executa a Fase 3: A Fábrica RPA RunningHub ComfyUI |
| `/pipeline --phase 4` | Executa a Fase 4: Catalogador (Injeção IPTC/EXIF + CSV) e backup em nuvem |
| `/pipeline --phase 5` | Executa a Fase 5: Distribuição SFTP/FTP multi-agência |
| `/pipeline --all` | Executa todas as fases pendentes em sequência com validação contínua |

---

## 🔬 Protocolo de Execução por Fase

### Fase 1: Olheiro (Scout)
- **Pré-requisitos**: Conexão de rede ativa.
- **Execução**:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 1 --mode insights --type photo --max-items 20
  ```
- **Pós-validação**: Verificar se `data/raw/trends.json` foi atualizado e referências existem em `data/raw/images/`.

### Fase 2: Diretor de Arte v3.0
- **Pré-requisitos**: `data/raw/trends.json` com ao menos 1 item e `GEMINI_API_KEY` configurada no `.env`.
- **Execução**:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 2
  ```
- **Pós-validação**: Verificar se `data/processed/prompts.json` possui os prompts de 700 a 1.000 palavras com copy-space.

### Fase 3: A Fábrica (RunningHub ComfyUI RPA)
- **Pré-requisitos**: Prompts com status `pending` em `data/processed/prompts.json`.
- **Execução**:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 3 --node 192 --batches 1
  ```
  Para processar toda a fila pendente:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 3 --node 192 --all-batches
  ```
- **Pós-validação**: Validar se novos renders 4K foram salvos em `data/final/images/` e registrados em `generation_history.json`.

### Fase 4: O Catalogador & Backup
- **Pré-requisitos**: Imagens 4K em `data/final/images/`.
- **Execução**:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 4
  ```
- **Pós-validação**: Conferir injeção binária IPTC/EXIF e sincronização em `data/processed/adobe_stock_upload.csv`. Dispara backup Google Drive se configurado.

### Fase 5: O Distribuidor
- **Pré-requisitos**: Ativos catalogados em `data/final/images/` e credenciais SFTP/FTP no `.env`.
- **Execução de Teste**:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 5 --dry-run
  ```
- **Execução de Produção**:
  ```powershell
  .\venv\Scripts\python.exe main.py --phase 5 --platform all
  ```

---

## 🛡️ Gestão de Erros & Auto-Recuperação
1. Se uma fase falhar com timeout de rede, aplicar backoff exponencial (5s, 15s, 30s) com até 3 retentativas automáticas.
2. Se a API do Gemini retornar HTTP 429, o motor alternará automaticamente entre `gemini-3.5-flash-lite` e `gemini-3.8-flash`.
3. Ao finalizar qualquer fase, atualize obrigatoriamente o `state.md`.
