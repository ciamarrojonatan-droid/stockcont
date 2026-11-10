# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: MiniMax Music 3 & MiniMax H3 Cinematic — Pipeline de Produção Multitrack (ADR-10/11)
- **Status da Sprint**: [CONCLUÍDO & TOTALMENTE OPERACIONAL]:
  1. **MiniMax Music 3 — 100% Instrumental sem Vocais (ADR-10)**:
     - Workflow 2120003151633174529 na Conta 5 / Audio Command Center.
     - Nó #15 (`caption`): Injeção obrigatória de metadados de estilo instrumental (`[Instrumental track, purely orchestral score, no vocals]`).
     - Nó #16 (`lyrics`): Erradicação total de texto em prosa descritiva; marcadores estruturais puros `[Instrumental]\n[Intro: Instrumental]...`.
     - Nó #14 (`PrimitiveFloat`): Duração em segundos (padrão 180.0s).
     - Nó #7 (`SaveAudioAdvanced`): Saída FLAC Lossless pura.
     - Botão Lite/Plus mandatório (ADR-08).
  2. **MiniMax H3 Cinematic V2 Turbo — Fallback de Vídeo sem Marca D'água (ADR-11)**:
     - Workflow 2118560390471745537 na Conta 7 (`minimax_h3`).
     - Nó #35 (Prompt cinematográfico) + Nó #48 (Imagem de referência 图1) + Nó #66 (Duração 10.0s).
     - Nó #107 (`FeiHouVideoPreview`): Saída final de vídeo sem watermark do RunningHub.
     - Botão Lite/Plus mandatório (ADR-08).
  3. **Validação & Testes Automatizados**:
     - `tests/test_minimax_music.py` (10/10 passing).
     - `tests/test_voice_and_audio_engines.py` (11/11 passing).
     - `tests/test_runninghub_execution_mode.py` (31/31 passing).
     - Suíte completa de testes: 100% green.
- **Última Atualização**: 2026-11-10 05:15
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **MiniMax Music 3 (Soundtrack Engine)** | 🟢 100% Instrumental (Zero Vocais) | **Workflow 2120003151633174529**: Estilo #15 \| Estrutura Instrumental #16 (`[Instrumental]`) \| Duração #14 \| **Saída FLAC #7** \| Lite/Plus (ADR-08/10) | `/api/v1/music/generate` |
| **MiniMax H3 Cinematic (Fallback Vídeo)** | 🟢 Operacional & Calibrado | **Workflow 2118560390471745537 (Conta 7)**: Prompt #35 \| Imagem #48 (图1) \| Duração #66 (10s) \| **Vídeo sem watermark #107 FeiHou** \| Lite/Plus (ADR-08/11) | `/api/v1/video/minimax_h3` |
| **Conta 4: Audio Command Center** | 🟢 Operacional & Calibrado | **CosyVoice + MiniMax Music 3**: Trilha 4 atos (#15/#16/#14 ➔ #7 FLAC) \| Narração Lossless CosyVoice (#345/#355 ➔ #346) \| Multitrack 3-Stem (-14 LUFS) | `/api/v1/music/generate`, `/api/v1/audio/mix` |
| **Hierarquia Vocal & NarratorLock** | 🟢 Ativo & Travado | **Tier 1 CosyVoice ➔ Tier 2 Kokoro ➔ Tier 3 Deepgram**: Invariante de voz única por vídeo garantido via `narrator_locks.json` | `python main.py --video` |
| **Google Flow Industrial API & RPA** | 🟢 Operacional & Calibrado | **FastAPI REST Server (`src/integrations/google_flow/`)**: Swagger em `/docs` \| Família Veo 3.1 (Quality/Fast/Lite, 8s) + Omni 1.2 Flash (5s) + Imagen 3 \| Auto-aprovação autônoma de permissão de créditos ('Sempre aprovar') \| Anti-race condition com verificação de busy/spinners \| Detecção resiliente de tiles (`flow-video-tile`, `flow-grid-tile-container`) \| Download com upscale nativo 1K/2K/4K com fallback 720p \| Audio stripping não-bloqueante (`-an`) \| Proteção contra profile lock (`try...finally`) \| Ledger SHA-256 \| Ativo gerado e baixado em disco: `Soviet_radar_bunker_rotating_beacon_faedd1a6.mp4` (3.78 MB) | `python main.py --flow-serve` ou `--flow-generate` |
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
