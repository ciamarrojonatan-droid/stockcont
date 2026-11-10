# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: Google Flow Industrial REST API & Automation Engine (Veo 2/3 + Imagen 3)
- **Status da Sprint**: [CONCLUÍDO & TOTALMENTE OPERACIONAL]:
  1. **Arquitetura Hybrid Stealth Driver & Sessão Persistente**:
     - Implementado gerenciador `src/integrations/google_flow/auth_manager.py` com perfil persistente (`google_flow_session/`), suporte a login interativo 1-click headed (2FA/Passkey) e renovação automática de sessão em background via heartbeat.
     - Interceptor direto de endpoints internos RPC/REST do Google Labs (`src/integrations/google_flow/rpc_client.py`).
  2. **Ciclo de Vida Completo de Projetos & Geração Multi-Mídia**:
     - Criação isolada de projetos dedicados no Google Flow por lote/job (`src/integrations/google_flow/models.py`).
     - Suporte nativo a Text-to-Video (Veo 2/3), Image-to-Video, Frames-to-Video e Text-to-Image (Imagen 3).
     - Configurações completas: Aspect Ratios (16:9, 9:16, 1:1, 4:3, 2.39:1), Duração (5s/8s), Variações (1, 2, 4), Insumos ("Ingredients").
  3. **Curadoria Inteligente & Upscale Nativo Automatizado**:
     - Módulo QC (`src/integrations/google_flow/qc_curator.py`) com triagem multimodal Gemini Vision para eleger o melhor candidato antes do upscale.
     - Gatilho do Upscaler Nativo do Google Flow (4K/1080p) e download assíncrono com stream sanitizado (`src/integrations/google_flow/downloader.py`).
     - Ingestão direta em `data/final/videos` ou `data/final/images` com livro-razão SHA-256 (`data/processed/google_flow_history.json`).
  4. **FastAPI REST Server & Integração CLI StockCont**:
     - Servidor FastAPI assíncrono (`src/integrations/google_flow/api_server.py`) com documentação interativa Swagger em `http://localhost:8000/docs`.
     - Endpoints REST completos: `/api/v1/health`, `/api/v1/auth/status`, `/api/v1/auth/login`, `/api/v1/projects`, `/api/v1/generate`, `/api/v1/jobs/{id}`, `/api/v1/jobs/{id}/upscale`, `/api/v1/jobs/{id}/download`.
     - Integração na CLI raiz do StockCont (`python main.py --flow --help`, `--flow-status`, `--flow-serve`, `--flow-login`, `--flow-generate`, `--flow-process-queue`).
  5. **Validação & Testes Automatizados**:
     - `tests/test_google_flow_api.py` (10/10 passing).
     - Suíte de testes completa do repositório: **272/272 testes aprovados (100% green)**.
- **Última Atualização**: 2026-11-10 00:35
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Google Flow Industrial API** | 🟢 Operacional & Calibrado | **FastAPI REST Server (`src/integrations/google_flow/`)**: Swagger em `/docs` \| Veo 2/3 + Imagen 3 \| Perfil persistente \| Upscale 4K \| Ledger SHA-256 | `python main.py --flow-serve` ou `--flow-status` |
| **DarkFactory Cinema T2V (YouTube Dark)** | 🟢 Operacional & Calibrado | **Motor T2V Dual-Shot (`src/video/darkfactory_t2v.py`)**: 3 cenas narrativas (6 tomadas Dual-Shot prontas) \| Filas MiniMax H3 e Google Veo 2 ativas | `python main.py --video --t2v` |
| **Pipeline de Vídeo (Fase 3: RunningHub)** | 🟢 Calibrado (Lite/Plus) | **Workflow 2115926169974812674**: Img #164 ➔ Prompt #17 ➔ Vídeo 4K #185 (Feihou Preview sem watermark) | Botão do Meio (Lite/Plus) Ativo | Playwright Stealth Conta 3 | `python main.py --phase 3 --video` |
| **Scoring Comercial & Filtros** | 🟢 Ativo & Operacional | **Motor Comercial (`src/analyzer/commercial_scorer.py`)**: 93 ativos analisados \| Score médio: 91.2 pts \| 70 Tier S, 23 Tier A \| 49 com Copy-Space (53%) | Explorar via Dashboard (`/`) |
| **Dashboard Vídeo SPA (`/video`)** | 🟢 Ativo | **Dedicated Cinema Command Center**: URL dedicada `http://localhost:8501/video`, Player Cinema HTML5, Fila 4D, Ação Fase 3 Direta e Estúdio I2V | Acessar via browser |
| **Dashboard Imagens SPA (`/`)** | 🟢 Ativo | **Design System iOS 27 Liquid Glass**: Filtros de Potencial de Vendas, Nichos B2B, Copy-Space, Ordenação Inteligente e KPIs de Portfólio | `python main.py --dashboard` |
| **Estúdio I2V (8K ➔ Vídeo)** | 🟢 Operacional | **Motor I2V Multiplier**: Seleção direta de imagens 8K em `data/final/images/` para síntese de 4 prompts 4D (Gemini Vision) | Integrado na aba Estúdio I2V |
| **Pipeline de Vídeo (Fases 1-5)** | 🟢 Operacional | **Motor I2V Multiplier (`src/video/`)** \| Probing FFmpeg, áudio mudo mandatória (`-an`), Seamless Loop Engine e injeção QuickTime/MP4 | `python main.py --video --status` |
| **Diretor de Arte de Vídeo** | 🟢 Pronto | **Síntese 4D Temporal (`src/analyzer/video_director.py`)** \| Prompts cinemáticos 500-800 palavras para 16:9 Landscape e 9:16 Vertical (Reels) | `python main.py --video --phase 2` |
| **Catalogador de Vídeo** | 🟢 Pronto | **Mastering & CSVs (`src/cataloger/video_cataloger.py`)** \| Injeção de metadados binários nos átomos MP4 + exportação para Adobe Stock Video e Pond5 | `python main.py --video --phase 4` |
| **Compliance de Vídeo** | 🟢 Ativo | **Validação Técnica (`src/cataloger/platform_compliance.py`)** \| 4K/FHD, duração 5-60s, codecs H.264/ProRes e Bloqueio Anti-Ban Alamy | Integrado na esteira |
| **Daemon 24/7 Supervisor** | 🟢 Operacional | **Motor Contínuo Pipelined (`src/orchestrator/daemon.py`)** \| Heartbeat atômico em `daemon_state.json` \| Watchdog Windows `run_24_7.bat` | `python main.py --daemon` ou `run_24_7.bat` |
| **Gestor de Cotas (Rolling 7D)** | 🟢 Ativo | **Janela deslizante de 7 dias (`src/uploader/quota_manager.py`)** \| 267 vagas semanais livres (100% livre) \| Cotas diferenciadas para vídeo | `python main.py --quotas` |
| **O Cofre (Google Drive + Purga SSD)** | 🟢 Protegido | **Cofre Híbrido com Auto-Purga Inteligente**: Arquivo no SSD é liberado apenas após envio a TODAS as agências ativas e confirmação no Google Drive | Operação contínua 24/7 |
| **Fase 1: Olheiro (Scout)** | 🟢 Concluído | **74 tendências mineradas** \| **98 referências sincronizadas** em `data/raw/images/` | Disparado pelo Daemon sob demanda (< 50 prompts) |
| **Fase 2: Diretor de Arte** | 🟢 Pronto | **408 prompts prontos** em `data/processed/prompts.json` \| Pré-flight auto-hydration ativo | Disparado pelo Daemon sob demanda |
| **Conta 1: Raw Producer** | 🟢 Calibrada (Lite/Plus) | **Workflow 2113606426114670593** \| 42 nós PromptList ➔ Capacidade: até 210 prompts/execução em 40 min (Botão Lite/Plus) | Integrado no Daemon |
| **Módulo QC: Curadoria & Quality Control** | 🟢 Calibrado | **Gemini Vision auto-audit ativo** \| Empacotamento em zips de 10 (`approved_batch.zip`) para prevenir OOM na GPU | Integrado no Daemon |
| **Conta 2: SeedVR 8K Upscaler** | 🟢 Calibrada (Lite/Plus) | **Workflow SeedVR 8K** \| Ingestão ZIP Nó #5 ➔ Preview Nó #55 (1 a 1 Real-Time) ➔ Auto-cancel na última imagem (Botão Lite/Plus) | Integrado no Daemon |
| **Fase 4: O Catalogador** | 🟢 Concluído | **190 assets catalogados** em `adobe_stock_upload.csv` \| Injeção obrigatória de 300 DPI + IPTC/EXIF | Integrado no Daemon |
