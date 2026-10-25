# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## 🎯 Sprint Atual: Calibração de Autonomia Antigravity & Claude Code
- **Status da Sprint**: ✅ **Concluída com Sucesso (Fases 1, 2 e 3)**
- **Última Atualização**: 2026-10-25 05:15
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Fase 1: Olheiro (Scout)** | 🟢 Concluído | **25 tendências mineradas** \| 15 referências em `data/raw/images/` | Minerar novo nicho via `/mine` ou `--phase 1` |
| **Fase 2: Diretor de Arte** | 🟢 Concluído | **10 itens analisados** \| **100 prompts v3.0 prontos** (700-1000 palavras) | Fila pronta para geração |
| **Fase 3: A Fábrica (RunningHub)** | 🟢 Concluído | **100/100 prompts processados (100%)** \| Fila zerada | Disparar novo lote após nova Fase 2 |
| **Fase 4: O Catalogador** | 🟢 Concluído | **157 assets catalogados** em `adobe_stock_upload.csv` | Catalogar novos renders 4K |
| **Fase 5: O Distribuidor** | 🟡 Operacional | **2/8 agências configuradas** \| **61 assets enviados** em `upload_history.json` | Configurar credenciais das demais agências |
| **Nuvem: Google Drive Backup** | 🟢 Configurado | Modo `local_sync` ativo (`G:\Meu Drive\StockCont_backup`) | Sincronização contínua via `--backup` |
| **Dashboard Web SPA** | 🟢 Operacional | Servidor FastAPI ativo em `http://localhost:8501` | `python main.py --dashboard` |
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **69 testes passando (100% verde)** | Manter regressão zero |

---

## 🧭 Inventário Completo da Calibração

### Fase 1: Fundação (Contexto, Regras e Hooks) ✅
- [x] **SSOT**: `PROJECT_CONTEXT.md` (300+ linhas, arquitetura, ADRs, contratos v3.0).
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

### Fase 3: Automação Avançada, Scripts & MCP ✅
- [x] **MCP Server**: `.agents/mcp_config.json` configurado com Context7 MCP.
- [x] **Memória Persistente**: `.agents/memory/vault.md` com registro de decisões e aprendizados operacionais.
- [x] **Script Windows Batch**: `scripts/run_pipeline.bat` com `chcp 65001` e detecção de venv.
- [x] **Script PowerShell**: `scripts/run_pipeline.ps1` com suporte flexível a parâmetros e saída colorida.
- [x] **Agendamento Noturno**: `scripts/nightly_schedule.ps1` para execução autônoma noturna com log rotativo.
