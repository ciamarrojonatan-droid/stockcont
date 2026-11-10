# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: MiniMax H3 Cinematic V2 Turbo — Fallback de Vídeo sem Marca D'água (FeiHou Nó #107 / ADR-11)
- **Status da Sprint**: [CONCLUÍDO & TOTALMENTE OPERACIONAL]:
  1. **Topologia RunningHub MiniMax H3 (Workflow 2118560390471745537)**:
     - Configurado como Conta 7 / `minimax_h3` em `src/factory/runninghub_bot.py`.
     - Ingestão de Prompt: Nó #35 (`PrimitiveStringMultiline` para prompts cinemáticos de câmera/ação).
     - Ingestão de Imagem de Referência: Nó #48 (`LoadImage` 图1 para imagem 16:9).
     - Duração do Vídeo: Nó #66 (`PrimitiveFloat`, padrão 10.0s).
     - Seletor de Resolução: Nó #62 (`ResolutionSelector` 16:9).
     - **Saída Mandatória de Vídeo sem Marca D'água**: Nó #107 (`FeiHouVideoPreview` - 'FeiHou-视频预览'), garantindo render MP4 HD com áudio e zero watermark do RunningHub.
     - Botão de Execução: Lite/Plus mandatório (ADR-08).
     - Cancelamento atômico pós-salvamento em disco para economia máxima de créditos de GPU.
  2. **Motor Dedicado `src/video/minimax_h3_engine.py`**:
     - `MiniMaxH3VideoEngine` com `build_cinematic_prompt` aderente às diretivas do MiniMax H3 / Hailuo Video-01 e DarkFactory T2V.
     - Geração via RunningHub RPA com fallback automático para síntese procedural de vídeo em 1080p 24fps com grão cinematográfico orgânico (via OpenCV/cv2).
     - Retorno com dataclass `H3VideoResult` (`video_path`, `duration`, `engine`, `has_watermark=False`).
  3. **Endpoints REST no Dashboard SPA**:
     - `POST /api/v1/video/minimax_h3`: Disparo sob demanda de vídeo cinemático com imagem de referência e parâmetros de câmera/iluminação.
  4. **Validação & Testes Automatizados**:
     - `tests/test_minimax_h3_video.py` (12/12 passing).
     - `tests/test_runninghub_execution_mode.py` (44/44 passing).
     - Suíte completa do repositório: **326/326 testes aprovados (100% green)**.
- **Última Atualização**: 2026-11-10 02:40
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **MiniMax H3 Cinematic (Fallback Vídeo)** | 🟢 Operacional & Calibrado | **Workflow 2118560390471745537 (Conta 7)**: Prompt #35 \| Imagem #48 (图1) \| Duração #66 (10s) \| **Vídeo sem watermark #107 FeiHou** \| Lite/Plus (ADR-08/11) | `/api/v1/video/minimax_h3` |
| **Conta 4: Audio Command Center** | 🟢 Operacional & Calibrado | **CosyVoice + MiniMax Music 3 + Sony Woosh Foley**: Trilha 4 atos (#15/#16/#14 ➔ #7) \| Foley V2A/T2A (#34/#46 ➔ Vídeo sem watermark #94 FeiHou + Áudio #9) \| Multitrack 3-Stem (-14 LUFS) | `/api/v1/music/generate`, `/api/v1/foley/generate`, `/api/v1/audio/mix` |
| **Hierarquia Vocal & NarratorLock** | 🟢 Ativo & Travado | **Tier 1 CosyVoice ➔ Tier 2 Kokoro ➔ Tier 3 Deepgram**: Invariante de voz única por vídeo garantido via `narrator_locks.json` | `python main.py --video` |
| **Google Flow Industrial API** | 🟢 Operacional & Calibrado | **FastAPI REST Server (`src/integrations/google_flow/`)**: Swagger em `/docs` \| Família Veo 3.1 (Quality/Fast/Lite, 8s) + Omni 1.2 Flash (5s) + Imagen 3 \| Auto-Desambiguação conversacional autônoma no chat \| Perfil persistente \| Criação de projetos \| Download com upscale nativo 1K/2K/4K \| Injeção IPTC/EXIF \| Stripping de áudio (`-an`) \| Ledger SHA-256 | `python main.py --flow-serve` ou `--flow-generate` |
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
