# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: Cinematic Video Pipeline: 60-30-10 Color Psychology & Semiotics, DoP & Composition, 35mm Film Science, Pacing, OTIO & Tactical Graphics
- **Status da Sprint**: [CONCLUÍDO] Integração do ecossistema completo de engenharia cromática 60-30-10, semiótica psicológica, direção de fotografia (DoP), composição visual e masterização cinematográfica open-source:
  1. **Motor de Semiótica & Psicologia das Cores 60-30-10 (`src/video/color_psychology.py`)**:
     - **Regra Proporcional 60-30-10 Calibrada**: 60% Cor Dominante (Base / Atmosfera ambiental de bunker/espaço), 30% Cor Secundária (Sujeito / Estrutura / Vestimenta militar), 10% Cor de Acento (Punctum visual / Alarme / Ponto focal emocional).
     - **7 Arquétipos Semióticos Registrados**:
       - `cold_war_paranoia`: 60% Concreto Subterrâneo (`#141920`), 30% Oliva Militar Soviético (`#324233`), 10% Fósforo Radar CRT Verde (`#00FF66`). Tensão split-complementary de espionagem.
       - `nuclear_dread_siren`: 60% Preto Carbono (`#0B0D11`), 30% Aço Industrial Tungstênio (`#4A3F35`), 10% Vermelho Sangue Sirene (`#FF1122`). Urgência existencial e contagem regressiva.
       - `cyber_espionage`: 60% Abismo Obsidiana (`#060C16`), 30% Aço Cobalto Tático (`#1C385C`), 10% Ciano Neon Elétrico (`#00E5FF`). Precisão cirúrgica de guerra eletrônica.
       - `deep_space_void`: 60% Vácuo Cósmico Puro (`#020306`), 30% Titânio Criogênico (`#334155`), 10% Âmbar de Radiação Corona (`#F59E0B`). Isolamento cósmico e silêncio.
       - `bio_pathogen_hazard`: 60% Cinza Estéril Clínico (`#202428`), 30% Ocre Hazmat (`#B45309`), 10% Violeta Esterilização UV (`#8B5CF6`). Contaminação e quarentena.
       - `gordon_willis_noir`: 60% Preto Aveludado Subexposto (`#070707`), 30% Madeira e Couro Sépia (`#3E2718`), 10% Luz de Recorte Âmbar (`#EAB308`). Corrupção moral e conspiração nas sombras.
       - `fincher_muted_sage`: 60% Carvão Mudo Dessaturado (`#1A1F24`), 30% Verde Celadon Sálvia (`#3D4A41`), 10% Lâmpada de Tungstênio Solitária (`#F59E0B`). Investigação obsessiva.
     - **Auditor de Paleta por K-Means (Visão Computacional)**: Agrupamento em $k=3$ clusters, medição de desvio da proporção 60-30-10, cálculo do Score de Aderência (0-100), mapeamento do arquétipo mais próximo e renderização da cartela anotada com swatch banner (`_palette_603010.jpg`).
     - **Comandos CLI**: `python main.py --list-palettes`, `python main.py --color-palette <archetype>` e `python main.py --audit-palette <image_path>`.
  2. **Motor de Direção de Fotografia (DoP) & Engenharia de Composição (`src/video/cinematography_dop.py`)**:
     - **Catálogo de Ópticas de Cinema**: Lentes Anamórficas (Panavision C-Series 40mm T2.3, Cooke Anamorphic/i 35mm T2.3, Arri Master Anamorphic 50mm T1.9) com squeeze 2.0x/1.8x, bokeh oval e flares horizontais característicos; e Esféricas Prime (Zeiss Supreme 21mm T1.5, Leica Summilux-C 35mm T1.4, Arri Signature 75mm T1.8 e Laowa Probe 24mm T14 macro periscópica).
     - **Geometria de Enquadramento Cinematográfico**: Regra dos Terços (Power Points & Lead Room), Espiral de Ouro de Fibonacci, Simetria Central 1-Point Kubrickiana, Dutch Angle (canted 12° para pânico institucional), Dirty Single com 35% de oclusão em primeiro plano e Ângulo Baixo Opressor.
     - **Arquitetura de Iluminação & Chiaroscuro**: Razão Key-to-Fill calculada (16:1 Gordon Willis Noir, 8:1 Suspense Militar, 4:1 Rembrandt), balanço Dual-Kelvin (Key 2800K Tungstênio vs Fill 6500K Ciano/Luar) e névoa volumétrica com feixes Tyndall.
     - **Auditor de Keyframes por Visão Computacional**: Extração automática de tomadas estratégicas (Abertura, Golden Ratio $0.618$, Clímax) com cálculo de energia nos terços (Sobel Gradient), contraste dinâmico chiaroscuro, bias de temperatura de cor e renderização de imagens anotadas com guias translúcidas de enquadramento (Cyan Thirds Grid, Gold Power Points, 2.39:1 CinemaScope crop).
     - **Injeção de Prompts DoP no DarkFactory T2V**: Enriquecimento automático das tomadas MiniMax H3 e Google Veo 2 com parâmetros estritos de câmera, lente, abertura e iluminação.
     - **Comandos CLI**: `python main.py --dop-plan`, `python main.py --audit-keyframe <path>` e `python main.py --extract-keyframes <video_path>`.
  3. **Motor de Ciência de Cor & Emulação de Película 35mm (`src/video/cinematic_color.py`)**:
     - 6 perfis cinematográficos calibrados: `kodak_2383` (Christopher Nolan), `fuji_eterna` (David Fincher), `bleach_bypass` (Spielberg/Kaminski), `oppenheimer_mono` (Double-X 65mm P&B puro), `cold_war_noir` (documentos confidenciais) e `cyber_tactical` (Denis Villeneuve).
     - Granulação analógica realista (`noise=c0s=X:c0f=t+u`) e matte anamórfico CinemaScope 2.39:1.
     - Comandos CLI: `python main.py --cinematic-profiles` e `python main.py --cinematic-grade <profile> --video-in <path>`.
  4. **Analisador de Ritmo & Pacing Cinematográfico - "The Editor's Brain" (`src/video/pacing_analyzer.py`)**:
     - Cálculo de Mean Shot Length (MSL em segundos), Cortes Por Minuto (CPM), Tension Pacing Index (0 a 100) e penalidade por monotonia rítmica.
     - Comando CLI: `python main.py --analyze-pacing <video_path>`.
  5. **Ponte de Intercâmbio Universal OpenTimelineIO (`src/video/otio_exporter.py`)**:
     - Geração de timelines padronizadas `.otio` (Pixar / ASWF) compatíveis com **DaVinci Resolve Studio**, Premiere Pro, Final Cut Pro e Blender.
     - Estrutura multitrack completa: V1 (Tomadas Principais), V2 (Grafismos Táticos), A1 (Voz EBU R128), A2 (Trilha Zimmer), A3 (Foley Diegético) e marcadores de capítulos.
     - Comando CLI: `python main.py --export-otio`.
  6. **Motor de Motion Graphics Tático & Overlays (`src/video/tactical_graphics.py`)**:
     - Carimbo militar angulado 'TOP SECRET // DECLASSIFIED // LEVEL 5', HUD de radar militar e Lower-thirds em tipografia monoespaçada.
     - Comandos CLI: `python main.py --tactical-hud` e `python main.py --tactical-stamp`.
  7. **Cobertura Total de Testes**: **224 testes automatizados passando com 100% de sucesso** (zero regressões).
- **Última Atualização**: 2026-11-08 04:14
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
| **Fase 5: O Distribuidor com Cotas** | 🟢 Protegido | **Despacho seletivo por plataforma**: Pausa agências com cotas esgotadas e prossegue nas demais \| Anti-Ban Alamy ativo | Integrado no Daemon |
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **283 testes passando (216 no StockCont + 67 no DarkFactory, 100% verde)** | Regressão zero (22 suítes de teste StockCont + 8 DarkFactory) | `pytest tests/` |
| **YouTube Booster & Compliance Bridge** | 🟢 Ativo & Operacional | **Motor YouTube Completo (`src/video/youtube_booster.py`)**: A/B/C Thumbnails, Series Playlists, Seamless Outro, 4K Codec Guard, Self-Certification e EDSA | `python main.py --youtube-boost` |
| **Agente Estratégico ("O Que Você Faria?")** | 🟢 Ativo & Registrado | **Subagente `what-would-you-do`** \| Skill `/wwyd` \| Hook `PreInvocation` em `.agents/hooks.json` \| Sócio sênior e avaliador de viabilidade | Invocável via subagente ou chat |

---

## 🎬 Arquitetura da Fábrica de Vídeo
- **DarkFactory T2V Engine**: `src/video/darkfactory_t2v.py`
  - Dual-Shot Architecture: Shot A (Tension/Character) + Shot B (Tactical Macro/Action)
  - Target Engines: MiniMax H3 (Hailuo) e Google Flow (Veo 2)
  - Filas de Exportação: `data/processed/minimax_t2v_queue.json` e `data/processed/google_veo_queue.json`
- **Workflow RunningHub (Fallback I2V)**: `https://www.runninghub.ai/pt-br/workflow/2115926169974812674?source=workspace`
  - Nó #164: Ingestão de Imagem
  - Nó #17: Injeção de Prompt
  - Nó #185: Saída sem marca d'água (Feihou Preview)
  - Botão Mandatório: `Lite/Plus`
