# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: Sprints 7–9 — Word-Timed Documentary Sync, CC0 Foley & Reverse-Engineer, 0.5s Spatial Overlap QA & Dual Monetization
- **Status das Sprints 7–9**: [CONCLUÍDO & VERIFICADO]:
  1. **Sprint 7 — Voice Aligner Palavra-a-Palavra, Map Animator Offline & Documentary World Composer**:
     - `src/video/ffmpeg_processor.py` & `src/video/voice_router.py`: `decode_audio_pcm_mono()` + `probe_audio_duration()` em WAV/MP3/FFmpeg; remoção da duração hardcoded de 10s no CosyVoice/Kokoro com alinhamento automático `word_timings` e `word_triggers` preservando integralmente o invariante `NarratorLock` (ADR-09).
     - `src/video/voice_aligner.py`: `VoiceAligner` com segmentação por envelope de energia RMS, alinhamento silábico forçado (ou `faster_whisper` opcional), geração SRT e detecção de gatilhos por palavra-chave.
     - `src/video/map_animator.py`: `MapAnimator` offline com 6 teatros geopolíticos (`THEATER_PRESETS`), SVG semântico multi-camada (`grid`, `landmass`, `routes`, `pins`, `hud`), timeline seekable HTML/GSAP (`window.__timelines` com opção editorial 12fps) e render MP4 H.264 com proteção contra deadlock FFmpeg (`-v error -nostats`).
     - `src/video/documentary_composer.py` & `src/video/research_engine.py`: `DocumentaryComposer.compose_episode()` conectando `PublicDomainResearchEngine` (com `MediaAssetRef.local_path`), `VoiceAligner`, `MapAnimator`, Ken Burns em imagens DP, selos desencadeados no instante exato da fala (`TacticalGraphicsEngine`), `UniversalTimelineExporter` (`.otio`) e mux master A/V.
  2. **Sprint 8 — Biblioteca CC0 Foley, Corte de Dead-Air, J/L-Cuts & Video Reverse-Engineer**:
     - `src/video/foley_library.py`: `FoleyLibrary` com catálogo CC0-1.0 (`whoosh_subtle`, `stamp_slam`, `radar_ping`, `teletype_burst`, `sub_riser`), varredura opcional em `data/raw/sfx_cc0/`, mapeamento automático de gatilhos (`build_cues_from_triggers`) e mixador procedural de stem estéreo sem clipping.
     - `src/video/audio_engine.py`: `trim_dead_air()` comprimindo pausas silenciosas `>350ms` para respiro natural (`120ms`) e `mix_with_auto_foley()` acoplando síntese CC0 Foley ao mix 3-Stem `mix_multitrack_documentary()`.
     - `src/video/otio_exporter.py`: Suporte a split edits J-cut (`audio_lead_sec`) e L-cut (`audio_tail_sec`) em `TimelineClipRef` via `apply_jl_cut_offsets()`.
     - `src/video/video_reverse_engineer.py`: `VideoReverseEngineer` com corte por cenas (`CinematicPacingAnalyzer`), extração de folhas de contato 3-quadros PNG, modo `AUTO/T2VA/I2V/DUAL` (via `vision_callback`, Gemini Vision opcional ou heurística OpenCV), prompts prontos para MiniMax H3 + Google Veo 2 e auditoria `DarkFactoryStoryValidator`.
  3. **Sprint 9 — Auditor Espacial 0.5s, Compilador de Storyboard, Render Dual-Monetization & Dashboard SPA**:
     - `src/video/motion_qa.py`: `MotionQAInspector.audit_overlay_overlaps()` com varredura AABB par-a-par a cada `0.5s` e verificação de limites de quadro (`OverlayPlacement`, `OverlapAuditResult`).
     - `src/video/storyboard_compiler.py` & `src/video/story_validator.py`: `StoryboardCompiler` fatiando roteiro em trilhas visuais, auditando hook 5s (`CopyClarityResult.to_dict()`), manifesto Murch/MrBeast/Cron, colisão 0.5s e projeção financeira (`UnitEconomicsCalculator`).
     - `src/video/youtube_booster.py`: `render_tri_variant_thumbnails()` renderizando fisicamente 3 JPEGs cognitivos 1280×720 (`Pillow`) e `extract_monetizable_stock_brolls()` extraindo `>=3` B-rolls H.264 mudos (`-an`, `+faststart`) com catálogo e bloqueio Alamy derivado de `PLATFORM_RULES` (ADR-05).
     - `src/dashboard/` & `main.py`: 6 novos endpoints `/api/v1/*` protegidos por `_validate_workspace_file` (`/video/map-animate`, `/video/compose-dossier`, `/audio/foley-track`, `/video/reverse-engineer`, `/video/storyboard-compile`, `/youtube/render-monetization-pack`), painel `#sprint9-studio-panel` em `/video` e flags CLI (`--map-animate`, `--compose-dossier`, `--reverse-video`, `--compile-storyboard`).
  4. **Validação Automatizada Sprints 7–9**:
     - `tests/test_sprint7_documentary_sync.py` (6/6), `tests/test_sprint8_foley_and_reverse.py` (5/5), `tests/test_sprint9_storyboard_and_monetization.py` (4/4), `tests/test_spa_look_and_fix.py` (2/2 — total **17/17 passing**); suíte Sprints 4–6 (`20/20 passing`); suíte completa (**384 passed**, 3 falhas pré-existentes em `tests/test_kokoro_voice.py` por ausência local de `kokoro-v0_19.onnx` e áudios piloto).

### Marco Anterior: Sprints 4–6 — Motion Personalities & Zero-Blob Plates, Motion QA Visual Gate, Beat-Sync Audio Engine, SVG Deconstructor & Playwright SPA Audit
- **Status das Sprints 4–6**: [CONCLUÍDO & VERIFICADO]:
  1. **Sprint 4 — Personalidades de Movimento, Zero-Blob Style Plates, Motion QA Gate & Linter 5s**:
     - `src/video/motion_qa.py`: `MotionQAInspector` com auditoria determinística Nível 1 (`compute_contrast_ratio` WCAG >= 4.5, `check_text_safe_area`, detecção de congelamento de frames e clipping em bordas, `generate_contact_sheet` 3x3 PNG atômico) + gancho Nível 2 Gemini Vision (`vision_critique`).
     - `src/video/hyperframes_engine.py`: 4 personalidades (`cold_war_noir`, `clinical_fintech`, `executive_corporate`, `high_energy_hook`), 3 plates Zero-Blob (`blueprint_notebook`, `risograph_declassified`, `cut_paper_editorial`), PRNG determinístico Mulberry32 (`seed` / `window.__hfRng`, zero `Math.random()`), render procedural blindado contra pipe deadlock (`stdout=DEVNULL` + `finally: proc.kill()`), escape XML seguro e `run_qa_gate`/`strict_qa`.
     - `src/video/tactical_graphics.py`, `src/video/story_validator.py` & `src/video/youtube_booster.py`: `validate_overlay_legibility()`, pre-check QA opcional em `composite_motion_overlay()`, `audit_5s_hook_clarity()` isolado à frase de abertura (`max_words=15`, zero buzzwords genéricas) integrado ao `DarkFactoryAuditReport` e `build_master_youtube_package()`.
  2. **Sprint 5 — Beat-Sync Audio Engine, Foley Sidechain Ducking, Cadence Blueprint & Shot Cards**:
     - `src/video/audio_engine.py`: `analyze_audio_transients()` (WAV nativo + fallback automático FFmpeg PCM para 24-bit/IEEE float + estimador BPM por mediana IBI), `snap_cut_times_to_beats()`, `foley_sidechain_ducking` em `mix_multitrack_documentary` e correção da flag FFmpeg `-b:a` em saídas `.wav`.
     - `src/video/pacing_analyzer.py`, `src/video/otio_exporter.py` & `src/analyzer/video_director.py`: `CadenceBlueprint` atômico via `get_ffprobe_binary()`, marcadores de batida e alinhamento de overlays no OTIO (`build_beat_markers`, `_align_clips_to_beats`) e catálogo `SHOT_CARD_RECIPES` (`get_shot_card_recipe`, `build_shot_card_directive`).
  3. **Sprint 6 — Raster → SVG Semântico Animável, Endpoints Blindados & Look-and-Fix SPA**:
     - `src/video/svg_deconstructor.py`: `RasterToAnimatedSVG` com extração de máscara, validação hex estrita (`^#[0-9a-fA-F]{6}$`), camadas semânticas (`grid`, `mark`, `callouts`, `wordmark`), `faithful_landing_iou`, `smoothness_gate_passed` e player seekable GSAP (`window.__timelines`) + template `deconstructed_emblem_vector`.
     - `src/dashboard/app.py`, `schemas.py`, `static/index.html`, `static/video.html`, `static/js/video.js`, `static/css/dashboard.css`: novos endpoints `/api/v1/video/motion-qa`, `/api/v1/video/cadence-blueprint` e `/api/v1/video/svg-deconstruct` com contenção de workspace (`_validate_workspace_file` anti-traversal), painel Telemetry Studio em `/video`, `escapeHtml` + `buildSprint6Headers()` consistentes no `video.js`, correção mobile `@media (max-width: 768px)` e remoção de `src=""` no modal de `index.html`.
     - Validação Playwright E2E (`tests/test_spa_look_and_fix.py`): auditoria Chromium desktop (`1440x900`) e mobile (`390x844`) em `/` e `/video` + novas suítes `tests/test_motion_qa_and_copy.py`, `tests/test_beat_sync_and_cadence.py` e `tests/test_svg_deconstructor.py`.

### Marco Anterior: Sprints 1–3 — HyperFrames/Anatomy Motion, Image Codes, Unit Economics, Research Engine & Blindagem 24/7
- **Status das Sprints 1–3**: [CONCLUÍDO & VERIFICADO]:
  1. **Sprint 1 — DarkFactory Motion Engine & YouTube Closed-Loop**:
     - `src/video/hyperframes_engine.py`: `HyperFramesMotionEngine` com contrato HTML/CSS/GSAP (`window.__timelines`, `paused: true`, `data-start`, `data-duration`), diagramas isométricos 4-tonalidades inspirados em `wheresryan22/anatomy`, injeção automática de `C:\ffmpeg\bin` via `get_ffmpeg_binary()`, gate determinístico `<= 20s` (`render_preview_gate`) e fallback procedural H.264 sem dependências externas pesadas.
     - `src/video/otio_exporter.py` & `src/video/tactical_graphics.py`: Trilha `V2_Tactical_Overlays` no schema JSON e via biblioteca `opentimelineio` (com trilhas `A1`/`A2`/`A3` alinhadas e `.resolve().as_uri()`); `composite_motion_overlay()` e resolução FFmpeg Windows-safe em `TacticalGraphicsEngine`.
     - `src/video/youtube_booster.py`: Loop fechado com `parse_retention_csv()`, `lint_title_thumbnail_pair()`, `validate_youtube_chapters()` e `extract_shorts_candidates()` integrados em `build_master_youtube_package()` + endpoints `/api/v1/video/motion-overlay` e `/api/v1/youtube/lint-package`.
  2. **Sprint 2 — StockCont B2B Multiplier (Image Codes, 4K Motion & Unit Economics)**:
     - `src/analyzer/director.py`: Suporte a `DIRECTOR_MODES` (`commercial_b2b`, `image_codes_technical`), `TECHNICAL_CODES_SUPPLEMENT` cobrindo 7 códigos (`/explodedview`, `/blueprint`, `/anatomy`, `/360view`, `/crosssection`, `/xray`, `/knolling`) com 700–1.000 palavras e 35–50% copy-space, roteamento `--director-mode [commercial|technical|auto]` e templates B2B 4K mudos (`-an`).
     - `src/analyzer/unit_economics.py`: Custeio unitário Gemini + GPU + SeedVR 8K, break-even e ROI ranqueado sobre `NICHE_DEFINITIONS` + endpoint `GET /api/v1/analytics/unit-economics` e CLI `--unit-economics`.
  3. **Sprint 3 — Motor Factual Real, Radar Dinâmico & Blindagem 24/7**:
     - `src/video/research_engine.py`: `PublicDomainResearchEngine` consultando Wikipedia REST, Wikimedia Commons (filtro rígido de licenças `Public Domain` / `CC0` / `PD-USGov`), Internet Archive e NASA Open APIs com cache em `data/raw/research_cache/`, dossiês atômicos em `data/processed/research_dossiers/` e fallback offline para `data/raw/dossiers/`.
     - `src/analyzer/seasonal_radar.py`: `fetch_live_signal_boosters()` e `get_merged_seasonal_opportunities()` mantendo a âncora D+75 `SEASONAL_CALENDAR` com fallback offline resiliente.
     - Blindagem & Telemetria: `DASHBOARD_ACCESS_TOKEN` middleware (Bearer / `X-Dashboard-Token`) em rotas mutáveis `/api/*` (`src/dashboard/app.py`), `AlertNotifier` por transição de estado e ping dead-man em `src/orchestrator/daemon.py`, guia `docs/REMOTE_TUNNEL_SETUP.md` e flags CLI unificadas em `main.py`.
- **Última Atualização**: 2026-11-11
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `AGENTS.md`)

### Sprint Anterior: MiniMax Music 3 & MiniMax H3 Cinematic — Pipeline de Produção Multitrack (ADR-10/11)
- **Status da Sprint**: [CONCLUÍDO & TOTALMENTE OPERACIONAL]:
  1. **MiniMax Music 3 — 100% Instrumental sem Vocais (ADR-10)**:
     - Workflow 2120003151633174529 na Conta 5 / Audio Command Center.
     - Nó #15 (`caption`): Injeção obrigatória de metadados de estilo instrumental (`[Instrumental track, purely orchestral score, no vocals]`).
     - Nó #16 (`lyrics`): Erradicação total de texto em prosa descritiva; marcadores estruturais puros `[Instrumental]\n[Intro: Instrumental]...`.
     - Nó #14 (`PrimitiveFloat`): Duração em segundos (padrão 180.0s).
     - Nó #7 (`SaveAudioAdvanced`): Saída FLAC Lossless pura.
     - Botão Lite/Plus mandatório (ADR-08).
  2. **MiniMax H3 Cinematic V2 Turbo — T2V Puro com Áudio e Saída sem Marca D'água (ADR-11)**:
     - Workflow 2118560390471745537 na Conta 7 (`minimax_h3`).
     - Nó #35 (Prompt cinematográfico) + Nó #66 (Duração parametrizada, ex: 4.0s).
     - Modo T2V Puro: Ingestão de imagem desativada (Node #48 `LoadImage` é acionado EXCLUSIVAMENTE para I2V/REF2V sob demanda).
     - Nó #107 (`FeiHouVideoPreview`): Saída final de vídeo MP4 1080p com áudio sincronizado (AAC) sem watermark do RunningHub.
     - Botão Lite/Plus mandatório (ADR-08).
     - Render validado em GPU real: `minimax_h3_t2v_real_8b2b728d.mp4` (2.06 MB, 4.46s, 1824x1024 @ 24fps, áudio AAC, sem marca d'água).
     - Resiliência RPA aprimorada: detecção de vídeo via DOM no nó FeiHou e blindagem contra falsos positivos de `TarefaFalha` de tarefas históricas.
  3. **Validação & Testes Automatizados**:
     - `tests/test_minimax_h3_video.py` (13/13 passing).
     - `tests/test_minimax_music.py` (10/10 passing).
     - `tests/test_voice_and_audio_engines.py` (11/11 passing).
     - `tests/test_runninghub_execution_mode.py` (31/31 passing).

---

## 📊 Métricas do Pipeline em Produção

| **Fase / Módulo** | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Documentary Sync & Map Animator** | 🟢 Operacional | **`src/video/voice_aligner.py` + `map_animator.py` + `documentary_composer.py`**: Alinhamento silábico/RMS por palavra, 6 teatros offline SVG/GSAP/MP4 12fps, gatilhos de selos e `.otio` | `python main.py --map-animate "..."` / `--compose-dossier "..."` |
| **Foley CC0, J/L-Cuts & Reverse Video** | 🟢 Operacional | **`src/video/foley_library.py` + `video_reverse_engineer.py` + `audio_engine.py`**: 5 efeitos CC0-1.0, corte de dead-air `>350ms`, split edits J/L-cut e extração `AUTO/T2VA/I2V/DUAL` | `python main.py --reverse-video <clip.mp4>` |
| **Storyboard Budget & Dual Monetization** | 🟢 Operacional | **`src/video/storyboard_compiler.py` + `motion_qa.py` + `youtube_booster.py`**: Auditoria espacial 0.5s (`audit_overlay_overlaps`), 3 thumbs JPEG 1280×720 e `>=3` B-rolls `-an` com bloqueio Alamy | `python main.py --compile-storyboard "..."` |
| **Diretor de Arte (Image Codes v3.0)** | 🟢 Operacional | **`src/analyzer/director.py`**: Modos `commercial_b2b`, `image_codes_technical` (7 códigos OpusJake) e `auto` via `--director-mode` \| Prompts 700–1000 palavras + Copy-Space | `python main.py --phase 2 --director-mode technical` |
| **Motion Engine (HyperFrames & Anatomy)** | 🟢 Operacional | **`src/video/hyperframes_engine.py`**: Contratos GSAP `window.__timelines`, SVGs isométricos 4-tonalidades, gate 20s, 4 loops B2B 4K (`-an`) + composição `V2_Tactical_Overlays` | `python main.py --render-motion-hud` |
| **Unit Economics & ROI por Nicho** | 🟢 Operacional | **`src/analyzer/unit_economics.py`**: Custo unitário Gemini+GPU+Upscale, break-even e ROI ranqueado sobre `NICHE_DEFINITIONS` | `python main.py --unit-economics` |
| **Research Engine & Radar Dinâmico** | 🟢 Operacional | **`src/video/research_engine.py` + `seasonal_radar.py`**: Wikipedia/Wikimedia(PD/CC0)/IA/NASA + sinais ao vivo + fallback offline resiliente | `python main.py --research-topic "..."` |
| **Blindagem Dashboard & Telemetria 24/7** | 🟢 Ativo | **`DASHBOARD_ACCESS_TOKEN` + `AlertNotifier`**: Auth em rotas mutáveis `/api/*` e alertas por transição + heartbeat dead-man | `docs/REMOTE_TUNNEL_SETUP.md` |
| **MiniMax Music 3 (Soundtrack Engine)** | 🟢 100% Instrumental (Zero Vocais) | **Workflow 2120003151633174529**: Estilo #15 \| Estrutura Instrumental #16 (`[Instrumental]`) \| Duração #14 \| **Saída FLAC #7** \| Lite/Plus (ADR-08/10) | `/api/v1/music/generate` |
| **MiniMax H3 Cinematic (T2V & Áudio)** | 🟢 Operacional & Calibrado | **Workflow 2118560390471745537 (Conta 7)**: Prompt #35 \| Duração #66 (4.0s) \| T2V Puro (sem imagem) \| **Vídeo com áudio AAC sem watermark #107 FeiHou** \| Lite/Plus (ADR-08/11) | `/api/v1/video/minimax_h3` |
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
