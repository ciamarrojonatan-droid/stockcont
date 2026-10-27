# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## 🎯 Sprint Atual: Arquitetura Dual-Account Producer-Consumer (Conta 1 Raw Batch + Conta 2 SeedVR 8K Real-Time)
- **Status da Sprint**: ✅ **Conta 1 Calibrada (42 Nós / 210 Prompts por Execução de 40 Min)**
- **Última Atualização**: 2026-10-27 03:25
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Fase 1: Olheiro (Scout)** | 🟢 Concluído | **59 tendências mineradas** \| **59/59 referências sincronizadas** em `data/raw/images/` | Minerar novo nicho via `/mine` ou `--phase 1` |
| **Fase 2: Diretor de Arte** | 🟢 Pronto | **Pré-flight auto-hydration + fallback textual gracioso** \| Suporte completo a Sandbox | Executar `python main.py --phase 2` |
| **Conta 1: Raw Producer** | 🟢 Calibrada (210 Prompts) | **Workflow 2113606426114670593** \| 42 nós PromptList (5 prompts/nó) ➔ Capacidade: até 210 prompts/execução em 40 min | Fila abastecida \| `python main.py --phase 3 --account 1` |
| **Conta 2: SeedVR 8K Upscaler** | 🟢 Calibrada & Pronta | **Workflow 2114903521153097729** \| Ingestão ZIP Nó #5 ➔ Preview Nó #55 (1 a 1 Real-Time) ➔ Auto-cancel | `python main.py --phase 3 --account 2` |
| **Módulo QC: Curadoria & Quality Control** | 🟢 Auto-Upscale Desativado | **22 aprovadas em approved_batch.zip** \| Triagem Gemini Vision pura (sem upscale local) | `python main.py --qc` |
| **Módulo Upscaler: 8K Commercial Grade** | 🟢 Pipeline Híbrida | **Conta 2 SeedVR 2.5 (Nuvem)** ou Local Lanczos HQ (300 DPI) | Executar Conta 2 para upscale IA |
| **Fase 4: O Catalogador** | 🟢 Concluído | **157 assets catalogados** em `adobe_stock_upload.csv` \| Injeção obrigatória de 300 DPI | Catalogar novos renders 8K |
| **Fase 5: O Distribuidor** | 🟢 Protegido | **Anti-Ban Safety Barrier Ativo** \| Bloqueio automático de IA para Alamy | Envio seguro para Adobe, Freepik, 123RF, Dreamstime, etc. |
| **Nuvem: Google Drive Backup & Restore** | 🟢 Concluído | **Restauração automática ativada no startup** \| 61 imagens sincronizadas e marcadas | Sincronização contínua via `--backup` e auto-pull no Dashboard |
| **Dashboard Web SPA** | 🟢 Operacional | Servidor FastAPI ativo em `http://localhost:8501` com nova aba **Curadoria & QC 8K** | `python main.py --dashboard` |
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **104 testes passando (100% verde)** | Manter regressão zero |

---

## 🧭 Inventário Completo da Calibração

### Fase 1: Fundação (Contexto, Regras e Hooks) ✅
- [x] **SSOT**: `PROJECT_CONTEXT.md` (300+ linhas, arquitetura, ADR-01 a ADR-05, contratos v3.0).
- [x] **Orquestrador Mestre**: `AGENTS.md` (Autonomia total, includes e matriz de roteamento).
- [x] **Dual-Mode Mirror**: `CLAUDE.md` (Compatibilidade total com Claude Code).
- [x] **Rules por Módulo**: `src/{scraper,analyzer,factory,cataloger,uploader}/AGENTS.md`.
- [x] **Lifecycle Hooks**: `.agents/hooks.json` com 4 handlers resilientes (`post_command_check.py`, `inject_state.py`, `session_start.py`, `stop_gate.py`).
- [x] **Estado Vivo**: `state.md`.
- [x] **Skill**: `/status` (`.agents/skills/stockcont-status/`).

### Fase 2: Workflows & Slash Commands ✅
- [x] **Skill**: `/pipeline` (`.agents/skills/stockcont-pipeline/`) — Execução granular ou end-to-end com auto-recovery.
- [x] **Skill**: `/mine` (`.agents/skills/stockcont-mine/`) — One-shot de nicho (Scout + Diretor de Arte 700-1000w).
- [x] **Skill**: `/review` (`.agents/skills/stockcont-review/`) — Multi-layer quality gate (Pytest + Python + Security + Ledgers).
- [x] **Skill**: `/deploy` (`.agents/skills/stockcont-deploy/`) — Test gate + inicialização do FastAPI Web SPA com health check.
- [x] **Auto-Recuperação Windows Sandbox**: Módulo de hidratação concorrente (`src/scraper/hydrator.py`), CLI `--sync-raw` / `--hydrate` e fallback textual gracioso no Diretor v3.0 (`reference_available: false`).

### Fase 3: Arquitetura Dual-Account RunningHub (Conta 1 Raw + Conta 2 SeedVR 8K) ✅
- [x] **Conta 1 (Raw Producer)**:
  - Workflow: `https://www.runninghub.ai/pt-br/workflow/2113606426114670593?source=workspace`
  - Injeção: 42 nós PromptList (`#128`, `#129`, `#130`, `#131`, `#204`, `#218`, `#224`, `#223`, `#222`, `#221`, `#219`, `#220`, `#230`, `#229`, `#228`, `#227`, `#225`, `#226`, `#236`, `#235`, `#234`, `#233`, `#231`, `#232`, `#242`, `#241`, `#240`, `#239`, `#237`, `#238`, `#254`, `#253`, `#252`, `#251`, `#249`, `#250`, `#248`, `#247`, `#246`, `#245`, `#243`, `#244`).
  - Capacidade por Lote: 5 prompts por nó = até 210 prompts por lote na janela de 40 minutos do RunningHub.
  - Nó de saída: `#121` (Preview Image).
  - Estratégia de Salvamento: **Batch All** — monitora a renderização de até 210 imagens raw com timeout de inatividade autorrefrescante (15 min sem novas imagens) e teto máximo de 45 min, salvando todas em disco em `data/staging/images/`.
  - Sessão isolada: `playwright_session_raw/` (com fallback gracioso para `playwright_session/`).
  - **Stealth Fingerprint Conta 1**: Chrome 128, Windows 11 Enterprise, RTX 3080, 16 Cores, 16GB RAM, 1080p, ruído de canvas e spoofing de WebGL.
- [x] **Conta 2 (SeedVR 2.5 8K Upscaler Consumer)**:
  - Workflow: `https://www.runninghub.ai/pt-br/workflow/2114903521153097729?source=workspace`
  - Ingestão Anti-OOM: Empacotamento calibrado para **até 10 imagens por zip** (`approved_batch.zip`) para evitar estouro de VRAM no KSampler #23.
  - Rotação Incremental: Roda em blocos sucessivos (`only_unprocessed=True`), processando 10 imagens por rodada de 40 min até cobrir todas as 22 aprovadas.
  - Nó de entrada: `#5` (Load Images (zip)) — upload automatizado via Playwright / LiteGraph API.
  - Execução: Disparo do botão central `Lite/Plus Executar`.
  - Nó de saída: `#55` (Preview Image do SeedVR).
  - Estratégia de Salvamento: **Real-Time 1 a 1 Instantâneo** — polling a cada 1.0s com captura imediata antes que a próxima imagem sobrescreva o nó `#55`!
  - Auto-Cancel na última imagem: Acionamento imediato de `cancel_runninghub_task` assim que `images_saved >= expected_images` (10 imagens) para poupar GPU.
  - Sessão isolada: `playwright_session_upscale/` (zero conflito de cookies entre contas).
  - Destino: `data/final/images/`.
  - **Stealth Fingerprint Conta 2**: Chrome 129, Windows 11 Pro, RTX 4070, 12 Cores, 32GB RAM, 1440p, ruído de canvas e spoofing de WebGL.
- [x] **Injeção de Stealth Profile no RPA**: Integrado diretamente em `src/factory/runninghub_bot.py` via `launch_persistent_context` e injeção de script de spoofing (`add_init_script` e `evaluate`).

### Fase 4: Quality Control (QC) & Curadoria Híbrida com Gemini Vision + 8K Upscale ✅
- [x] **Motor de QC (`src/analyzer/qc_inspector.py`)**:
  - Auditoria multimodal automatizada via Gemini Vision (`gemini-3.5-flash-lite` / `gemini-3.8-flash`).
  - Rubrica técnica de microstock: detecção anatômica, copy-space (35-50% livre) e viabilidade comercial B2B.
  - Dual-Mode: `auto` (padrão, com nota mínima 7.5) vs `manual` (triagem visual no dashboard).
- [x] **Motor de Upscaling 8K (`src/factory/upscaler.py`)**:
  - Target 8K (7680px na borda longa, 300 DPI, JPG 98% qualidade).
  - Atualização automática em `generation_history.json` e `qc_manifest.json`.
- [x] **Dashboard Web SPA (Aba "Curadoria & QC")**:
  - Toggle Switch interativo `[🤖 Automático (Gemini Vision) | 👁️ Manual (Visual)]` com `Automático` como padrão.
  - Galeria de cards com previews, pílulas de score, badges 8K e botões de ação instantânea.
  - Disparo de lote: `⚡ Avaliar com Gemini` e `🚀 Upscale 8K Aprovadas`.
- [x] **Integração CLI (`main.py`)**:
  - `python main.py --phase 3 --account 1`: executa lote de até 210 imagens na Conta 1 (Raw Producer).
  - `python main.py --phase 3 --account 2`: executa upscale na Conta 2 (SeedVR 8K com captura 1 a 1).
  - `python main.py --qc`: executa QC nas imagens de staging.
  - `python main.py --upscale`: executa upscale 8K de imagens aprovadas.
- [x] **Garantia de Qualidade**: 104 testes automatizados passando 100% verde (regressão zero).
