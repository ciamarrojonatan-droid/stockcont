# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## 🎯 Sprint Atual: Produção Autônoma 24/7 (Supervisor Daemon) + Gestor de Cotas Semanais (Rolling 7D) & Cofre de Backup
- **Status da Sprint**: ✅ **Concluída com Sucesso: Esteira Contínua 24/7 com Pacing, Janela Deslizante de 7 Dias e Auto-Purga de SSD**
- **Última Atualização**: 2026-10-29 02:40
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Daemon 24/7 Supervisor** | 🟢 Operacional | **Motor Contínuo Pipelined (`src/orchestrator/daemon.py`)** \| Heartbeat atômico em `daemon_state.json` \| Watchdog Windows `run_24_7.bat` | `python main.py --daemon` ou `run_24_7.bat` |
| **Gestor de Cotas (Rolling 7D)** | 🟢 Ativo | **Janela deslizante de 7 dias (`src/uploader/quota_manager.py`)** \| 395 vagas semanais livres \| Proteção anti-burst e anti-penalização algorítmica | `python main.py --quotas` |
| **O Cofre (Google Drive + Purga SSD)** | 🟢 Protegido | **Cofre Híbrido com Auto-Purga Inteligente**: Arquivo no SSD é liberado apenas após envio a TODAS as agências ativas e confirmação no Google Drive | Operação contínua 24/7 |
| **Fase 1: Olheiro (Scout)** | 🟢 Concluído | **59 tendências mineradas** \| **59/59 referências sincronizadas** em `data/raw/images/` | Disparado pelo Daemon sob demanda (< 50 prompts) |
| **Fase 2: Diretor de Arte** | 🟢 Pronto | **Pré-flight auto-hydration + fallback textual gracioso** \| Suporte completo a Sandbox | Disparado pelo Daemon sob demanda |
| **Conta 1: Raw Producer** | 🟢 Calibrada (210 Prompts) | **Workflow 2113606426114670593** \| 42 nós PromptList (5 prompts/nó) ➔ Capacidade: até 210 prompts/execução em 40 min | Integrado no Daemon |
| **Módulo QC: Curadoria & Quality Control** | 🟢 70 Aprovadas (7 Packs) | **Gemini Vision auto-audit ativo** \| Empacotamento em zips de 10 (`approved_batch.zip`) para prevenir OOM na GPU | Integrado no Daemon |
| **Conta 2: SeedVR 8K Upscaler** | 🟢 Calibrada & Pronta | **Workflow SeedVR 8K** \| Ingestão ZIP Nó #5 ➔ Preview Nó #55 (1 a 1 Real-Time) ➔ Auto-cancel na última imagem | Integrado no Daemon |
| **Fase 4: O Catalogador** | 🟢 Concluído | **157 assets catalogados** em `adobe_stock_upload.csv` \| Injeção obrigatória de 300 DPI + IPTC/EXIF | Integrado no Daemon |
| **Fase 5: O Distribuidor com Cotas** | 🟢 Protegido | **Despacho seletivo por plataforma**: Pausa agências com cotas esgotadas e prossegue nas demais \| Anti-Ban Alamy ativo | Integrado no Daemon |
| **Dashboard Web SPA** | 🟢 Operacional | Servidor FastAPI ativo em `http://localhost:8501` com **Nova Aba "🤖 Produção 24/7"** (Controles, Medidores de Cotas e Status do Cofre) | `python main.py --dashboard` |
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **118 testes passando (100% verde)** \| Regressão zero | Manter integridade contínua |

---

## 🧭 Inventário Completo da Implementação 24/7

### 1. Motor de Cotas Semanais Deslizantes (`src/uploader/quota_manager.py`) ✅
- [x] **Cálculo da Janela Deslizante de 7 Dias**: Conta uploads onde `timestamp >= (now - 7 days)` a partir do livro-razão `upload_history.json`.
- [x] **Controle Granular por Agência**: Suporta limites individuais (`ADOBE_WEEKLY_LIMIT`, `FREEPIK_WEEKLY_LIMIT`, etc.) via `.env` ou defaults.
- [x] **Countdown para Próxima Vaga**: Calcula a projeção exata em dias, horas e minutos para quando o upload mais antigo da janela completar 7 dias.
- [x] **CLI de Consulta Rápida**: `python main.py --quotas` exibe barras de progresso visuais e status detalhado no terminal.

### 2. O Distribuidor com Quotas (`src/uploader/ftp_distributor.py`) ✅
- [x] **Despacho Seletivo**: Verifica vagas livres antes de enviar; se a agência atingir a cota, pausa o envio para aquela agência e prossegue nas demais.
- [x] **Capping Dinâmico**: Limita o lote de submissão ao número exato de slots restantes na semana.
- [x] **Preservação de Fila**: Assets excedentes permanecem no Cofre engatilhados para os próximos ciclos.
- [x] **Anti-Ban Alamy Preservado**: Bloqueio irrestrito de qualquer asset gerado por IA para Alamy (ADR-05).

### 3. O Daemon 24/7 & Auto-Purga Inteligente (`src/orchestrator/daemon.py`) ✅
- [x] **Loop Pipelined Contínuo**:
  - Buffer de Prompts: Abastece fila (Fase 1 + 2) se pendentes < `min_prompt_buffer` (padrão 50).
  - Conta 1 (Raw Producer): Processa lotes de até 210 prompts no RunningHub.
  - QC Automático: Curadoria multimodal via Gemini Vision e empacotamento em zips de 10.
  - Conta 2 (SeedVR 8K): Processa pacotes aprovados de 10 em 10.
  - Fase 4: Cataloga IPTC/EXIF 300 DPI e salva no Google Drive ("Cofre Cloud").
  - Fase 5: Despacha assets respeitando as cotas semanais deslizantes.
- [x] **Auto-Purga Inteligente de SSD**: Remove o JPG 8K do disco local apenas quando confirmado o upload em TODAS as agências ativas e confirmado o backup no Google Drive.
- [x] **Heartbeat Atômico**: Salva o estado vivo em `data/processed/daemon_state.json` via `.tmp` e `os.replace` (ADR-02).
- [x] **Pacing Sleep Responsivo**: Intervalo de descanso (padrão 300s = 5 min) com polling rápido para resposta imediata a sinais de pausa ou interrupção.

### 4. Scripts de Inicialização e Supervisão Windows ✅
- [x] **`run_24_7.bat`**: Script com loop supervisor watchdog que captura códigos de saída/crashes e reinicia a esteira automaticamente em 30 segundos.
- [x] **`scripts/setup_windows_task.ps1`**: Script PowerShell para registro automático no Agendador de Tarefas do Windows (Task Scheduler) no logon do sistema.

### 5. Dashboard Web SPA Integrado ✅
- [x] **Aba "🤖 Produção 24/7"**:
  - Hero card com badge interativo de status (🟢 Rodando 24/7 / ⏹️ Parado).
  - Métricas do Cofre: Assets no disco local, engatilhados, 100% distribuídos, no Google Drive e liberados do SSD.
  - Grid de Cotas Semanais: Cards com barras de progresso coloridas (Verde / Laranja / Roxo) e contagem regressiva para a próxima vaga.
  - Botões de Ação: Iniciar em Background, Iniciar em Janela de Console (`run_24_7.bat`) e Parar.
- [x] **Endpoints REST**: `/api/quotas`, `/api/daemon/status`, `/api/daemon/start`, `/api/daemon/stop`.

---

## 🧪 Qualidade de Código & Testes
- **Total de Testes**: **118 testes automatizados** passando 100% verde.
- **Regressão Zero**: Todos os testes legados, novos testes de cotas (`test_quota_manager.py`), daemon (`test_daemon.py`), distribuidor e dashboard continuam verdes.
