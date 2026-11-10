# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: Conta 4 Audio Command Center (MiniMax Music 3 + Sony Woosh Foley + CosyVoice + Multitrack 3-Stem)
- **Status da Sprint**: [CONCLUÍDO & TOTALMENTE OPERACIONAL]:
  1. **MiniMax Music 3 (Soundtrack Engine)**:
     - Workflow ComfyUI `2120003151633174529` no RunningHub Conta 4.
     - Topologia: Nó #15 (`Text Multiline` para estilo musical), Nó #16 (`Text Multiline` para estrutura sinfônica de 4 partes), Nó #14 (`PrimitiveFloat` para duração, padrão 180s) e Nó #7 (`SaveAudioAdvanced` para saída lossless FLAC).
     - Módulo `src/video/minimax_music_engine.py` com arquétipos sinfônicos (Hans Zimmer, Ludwig Göransson, Cold War Espionage, Cyber Warfare) e fallback procedural resiliente.
  2. **Sony Woosh Foley & SFX Engine (V2A / T2A)**:
     - Workflow ComfyUI `2119999521484034049` no RunningHub Conta 4.
     - Topologia: Nó #34 (`VHS_LoadVideo` para ingestão V2A), Nó #46/56 (`ShowText`/Llama prompt para T2A), Nó #9 (`PreviewAudio` para áudio) e **Nó #94 (`FeiHouVideoPreview` para salvar vídeo em alta definição sem marca d'água do RunningHub)**.
     - Módulo `src/video/woosh_foley_engine.py` com presets de foley de tensão cinematográfica e fallback procedural offline.
  3. **Hierarquia Vocal & Unidade Narrativa (ADR-09)**:
     - `src/video/voice_router.py` com trava imutável de narrador (`NarratorLock`) persistida em `data/processed/narrator_locks.json` (CosyVoice Neural Tier 1, Kokoro Local Tier 2, Deepgram Aura Tier 3).
  4. **Mixador Multitrack 3-Stem (-14 LUFS EBU R128) (ADR-10)**:
     - `DarkFactoryAudioEngine.mix_multitrack_documentary` em `src/video/audio_engine.py`: mixagem inteligente de 3 canais (Voz 0dB referência + Trilha sonora com sidechain ducking de -14dB + Foley SFX -12dB).
  5. **Endpoints REST no Dashboard SPA**:
     - `/api/v1/music/generate`: Geração de trilha sonora orquestral via MiniMax Music 3.
     - `/api/v1/foley/generate`: Geração de efeitos sonoros com extração de vídeo sem watermark.
     - `/api/v1/audio/mix`: Mixagem multitrack 3-stem profissional.
  6. **Validação & Testes Automatizados**:
     - `tests/test_minimax_music.py` (10/10 passing).
     - `tests/test_woosh_foley.py` (10/10 passing).
     - `tests/test_runninghub_execution_mode.py` (26/26 passing, cobrindo todos os modos e Lite/Plus mandatório).
     - `tests/test_narration.py` (10/10 passing).
     - `tests/test_voice_and_audio_engines.py` (11/11 passing).
     - Suíte de testes completa do repositório: **308/308 testes aprovados (100% green)**.
- **Última Atualização**: 2026-11-10 02:05
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Conta 4: Audio Command Center** | 🟢 Operacional & Calibrado | **CosyVoice + MiniMax Music 3 + Sony Woosh Foley**: Trilha 4 atos (#15/#16/#14 ➔ #7) \| Foley V2A/T2A (#34/#46 ➔ Vídeo sem watermark #94 FeiHou + Áudio #9) \| Multitrack 3-Stem (-14 LUFS) | `/api/v1/music/generate`, `/api/v1/foley/generate`, `/api/v1/audio/mix` |
| **Hierarquia Vocal & NarratorLock** | 🟢 Ativo & Travado | **Tier 1 CosyVoice ➔ Tier 2 Kokoro ➔ Tier 3 Deepgram**: Invariante de voz única por vídeo garantido via `narrator_locks.json` | `python main.py --video` |
| **Google Flow Industrial API** | 🟢 Operacional & Calibrado | **FastAPI REST Server (`src/integrations/google_flow/`)**: Swagger em `/docs` \| Veo 2/3 + Imagen 3 \| Perfil persistente \| Criação de projetos \| Configuração de vídeo/imagem (model, ratio, duration, count, resolution 1K/2K/4K) \| Download com upscale nativo \| Injeção IPTC/EXIF \| Stripping de áudio (`-an`) \| Ledger SHA-256 | `python main.py --flow-serve` ou `--flow-generate` |
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
