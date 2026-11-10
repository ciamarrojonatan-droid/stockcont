# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: Kokoro-82M Local Neural Narration (`bm_george` Default Voice)
- **Status da Sprint**: [CONCLUÍDO & TOTALMENTE OPERACIONAL]:
  1. **Motor Local Neural Kokoro-82M ONNX (Custo Zero)**:
     - Voz padrão oficial para documentários: **`bm_george`** (Narrador britânico clássico com gravidade, barítono solene no estilo BBC / Christopher Nolan).
     - Roteamento e seleção dinâmica: suporte a **`bm_lewis`** (urgência e tensão da Guerra Fria), **`am_adam`** e outros via `--voice <id>` em tempo de execução.
     - Detecção automática de idioma (`en-gb` para vozes britânicas `b*`, `en-us` para americanas `a*`).
  2. **Cadeia de Masterização Broadcast (Curva Ableton Live Complex Pro)**:
     - Filtro passa-altas 60Hz + Boost de calor 90Hz (+2.5dB) + Corte de lama 350Hz (-1.5dB) + Presença 3.5kHz (+2.0dB).
     - Compressão dinâmica (threshold -18dB, ratio 3:1) + Normalização EBU R128 (-14 LUFS).
     - Geração dupla de masters: WAV 24-bit 48kHz para timeline de edição e MP3 320kbps 44.1kHz para visualização instantânea.
     - Legendas sincronizadas SRT (`pilot_bm_george_full.srt`, `pilot_bm_lewis_full.srt`) geradas automaticamente.
  3. **Comandos CLI Operacionais**:
     - `py darkfactory/src/generate_pilot_audio.py` (executa narração e masterização padrão com `bm_george`)
     - `py darkfactory/src/generate_pilot_audio.py --voice bm_lewis` (executa com voz alternativa)
     - `py darkfactory/src/kokoro_fallback.py --voice bm_george --scene 1`
  4. **Validação & Testes Automatizados**:
     - `tests/test_kokoro_voice.py` (4/4 passing)
     - `tests/test_gemini_api.py` (3/3 passing)
     - `darkfactory/tests/test_kokoro_fallback.py` (7/7 passing)
     - Suíte DarkFactory completa (77/77 passing) e StockCont (238/238 passing).
- **Última Atualização**: 2026-11-09 21:35
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
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
