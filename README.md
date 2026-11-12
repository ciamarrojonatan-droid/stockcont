# StockCont

<p align="center">
  <img src="src/dashboard/static/logo.svg" alt="StockCont Logo — 5-Stage Mass Production Rig" width="460" />
</p>

> **Plataforma Autônoma Industrial de Inteligência Preditiva de Mercado, Engenharia Reversa Multimodal, Produção Generativa 4K/8K, Ecossistema DarkFactory de Vídeo & Áudio Cinematográfico (Google Flow Veo 3.1, MiniMax H3, MiniMax Music 3, HyperFrames, Motion QA & Shorts 9:16), Catalogação Binária IPTC/EXIF/MP4, Unit Economics & Scoring B2B, Cotas Deslizantes (Rolling 7D), Daemon 24/7 com Telemetria & Auto-Purga de SSD e Dashboard Web SPA iOS 27 Liquid Glass.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Pytest-391_Passed_(Core_Suite)-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Gemini Multimodal](https://img.shields.io/badge/Google_Gemini-Multimodal_Vision_v3.0-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Google Flow](https://img.shields.io/badge/Google_Flow-Veo_3.1_%26_Omni_Flash_1.2-1A73E8?style=for-the-badge&logo=google&logoColor=white)](src/integrations/google_flow/api_server.py)
[![ComfyUI Multi RPA](https://img.shields.io/badge/ComfyUI-Multi_Account_Lite%2FPlus-FF6F00?style=for-the-badge&logo=blender&logoColor=white)](https://www.runninghub.ai/)
[![Video & Motion](https://img.shields.io/badge/Video_&_Motion-4K_I2V_ProRes_9:16-E11D48?style=for-the-badge&logo=quicktime&logoColor=white)](https://ffmpeg.org/)
[![Metadata](https://img.shields.io/badge/Metadata-Binary_IPTC_%26_EXIF_%26_MP4-8A2BE2?style=for-the-badge)](https://iptc.org/)
[![UI Design](https://img.shields.io/badge/Design_System-iOS_27_Liquid_Glass-007AFF?style=for-the-badge&logo=apple&logoColor=white)](https://developer.apple.com/design/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## <img src="docs/icons/book.svg" width="20" height="20" /> Sumário Executivo

1. [Visão Geral do Sistema](#-visão-geral-do-sistema)
2. [Arquitetura de Alto Nível & Topologia da Esteira](#arquitetura-de-alto-nível--topologia-da-esteira)
3. [Dashboard Web SPA Local (iOS 27 Liquid Glass — `/` & `/video`)](#-dashboard-web-spa-local-ios-27-liquid-glass)
4. [Detalhamento Técnico das Fases do Pipeline](#detalhamento-técnico-das-fases-do-pipeline)
   - [Fase 1: O Olheiro Preditivo (Radar Sazonal D+75, Saturation Index & Hydrator)](#fase-1-o-olheiro-preditivo-radar-sazonal--saturation-index)
   - [Fase 2: O Diretor de Arte v3.0 (Image Codes, Unit Economics & Copy-Space)](#fase-2-o-diretor-de-arte-v30-prompts-de-7001000-palavras-image-codes--unit-economics)
   - [Pipeline de Vídeo Cinematográfico, Motion Engine & DarkFactory Studio (Sprints 1–11)](#-pipeline-de-vídeo-cinematográfico-motion-engine--darkfactory-studio-sprints-111)
   - [Google Flow Industrial REST API (Veo 3.1 / Omni 1.2 / Imagen 3)](#google-flow-industrial-rest-api-veo-31--omni-12--imagen-3)
   - [Fase 3: A Fábrica RPA Multi-Account (Lite/Plus Mandatório ADR-08)](#fase-3-a-fábrica-rpa-multi-account-liteplus-mandatório-adr-08)
   - [Módulo QC: Curadoria Multimodal & Prevenção OOM](#módulo-qc-curadoria-multimodal--prevenção-oom)
   - [Fase 4: O Catalogador (300 DPI, Injeção IPTC/EXIF/MP4 & CSV Incremental)](#fase-4-o-catalogador-300-dpi-injeção-binária-iptcexifmp4--csv)
   - [Fase 5: O Distribuidor com Cotas Deslizantes (Rolling 7D)](#fase-5-o-distribuidor-com-cotas-deslizantes-rolling-7d)
   - [O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)](#-o-cofre-cloud-google-drive--auto-purga-inteligente-de-ssd)
   - [Motor Autônomo 24/7 (Daemon Supervisor, AlertNotifier & Watchdog Windows)](#-motor-autônomo-247-daemon-supervisor--watchdog-windows)
5. [Orquestrador Mestre CLI (`main.py`) & Scripts de Execução](#orquestrador-mestre-cli-mainpy--scripts-de-execução)
6. [Estrutura do Repositório & Gestão de Dados](#estrutura-do-repositório--gestão-de-dados)
7. [Contratos de Dados (Data Schemas v3.0)](#-contratos-de-dados-data-schemas-v30)
8. [Matriz Estratégica Multi-Agência & Proteção Anti-Ban Alamy](#matriz-estratégica-multi-agência--proteção-anti-ban-alamy)
9. [Instalação, Configuração & Execução](#-instalação-configuração--execução)
10. [Resiliência Operacional & Decisões de Engenharia (ADRs)](#-resiliência-operacional--decisões-de-engenharia-adrs)

---

## <img src="docs/icons/globe.svg" width="20" height="20" /> Visão Geral do Sistema

O **StockCont** é um ecossistema autônomo industrial de inteligência preditiva de dados, engenharia reversa multimodal e automação robótica (RPA) projetado para cobrir o ciclo comercial completo de ativos digitais criados por inteligência artificial (imagens 4K/8K, loops B2B, documentários cinematográficos e Shorts 9:16) para as principais plataformas mundiais de **microstock** (Adobe Stock, Freepik, 123RF, Dreamstime, Pond5, Vecteezy, Ingram Image) e canais de alta retenção no YouTube.

Operando como um **fundo quantitativo de ativos digitais de alta demanda**, o sistema elimina o empirismo e a operação manual:
1. **Antecipa Janelas Comerciais B2B (D+75 dias) & Custos Unitários**: Calcula dinamicamente janelas de compra via **Seasonal Forecasting Radar** (integrado a sinais ao vivo com fallback offline), audita nichos com **Niche Saturation Index**, pontua ativos no **Commercial Scorer** (`Tier S/A`) e calcula ROI líquido por nicho no **Unit Economics Calculator** (`src/analyzer/unit_economics.py`).
2. **Engenharia Reversa Visual Multimodal v3.0 & 7 Image Codes**: Dissecciona referências mais vendidas via Gemini Vision e sintetiza **prompts de 700 a 1.000 palavras** nos modos `commercial`, `technical` (7 códigos estruturais: `/explodedview`, `/blueprint`, `/anatomy`, `/360view`, `/crosssection`, `/xray`, `/knolling`) ou `auto`, com **Copy-Space adaptativo** (35%–50%).
3. **Suite Completa de Vídeo, Motion & DarkFactory Studio (Sprints 1–11)**:
   - **Motores T2V/I2V Dual-Engine**: **Google Flow Industrial API** (`Veo 3.1`, `Omni 1.2 Flash`, `Imagen 3` com FastAPI REST Server `:8000`) + **MiniMax H3 Cinematic V2 Turbo** (Nó `#107 FeiHouVideoPreview` sem watermark).
   - **Motion Determinístico & QA Visual**: **HyperFrames & Anatomy Engine** (contratos HTML/CSS/GSAP `window.__timelines`, diagramas isométricos 4-tonalidades, gate 20s, 4 personalidades visuais & 3 *Zero-Blob Style Plates*), **MotionQA Inspector** (contraste WCAG, safe-zones mobile para Shorts/TikTok/Reels, varredura par-a-par `0.5s` anti-colisão, contact sheets 3×3) e **SVG Deconstructor** (raster-para-SVG semântico).
   - **Documentários Sincronizados & Shorts B2B**: **PublicDomainResearchEngine** (Wikipedia, Wikimedia PD/CC0, Internet Archive, NASA), **MapAnimator** offline (6 teatros geopolíticos), **VoiceAligner** palavra-a-palavra, **DocumentaryComposer**, **FoleyLibrary CC0**, corte de *dead-air* (`>350ms`) + *J/L-Cuts* em `.otio` (DaVinci Resolve), **VideoReverseEngineer**, **StoryboardCompiler**, **ShortsRepurposerEngine** (9:16 + `-an` stock) com **KineticCaptionEngine** e **PromoMotionDirector** B2B zero-trademark com auditoria *Anti-Sameness*.
   - **Áudio Cinematográfico & Knowledge Vault**: **Hierarquia Vocal Tripartite (`CosyVoice` -> `Kokoro` -> `Deepgram`)** protegida por **`NarratorLock`** (ADR-09), **MiniMax Music 3** 100% instrumental (zero vocais, FLAC `#7`), mixagem **3-Stem -14 LUFS** com sidechain ducking e regras destiladas dos **27 livros canônicos** (`master_knowledge.py`, `story_validator.py`).
4. **Fábrica RPA Multi-Account no RunningHub ComfyUI (Lite/Plus Mandatório - ADR-08)**:
   - **Conta 1 (Raw Producer)**: 42 nós `PromptList` simultâneos, até **210 prompts por lote** (saída no nó `#121`).
   - **Curadoria Multimodal (QC)** & **Conta 2 (SeedVR 8K Upscaler)**: Empacotamento em zips de 10 (prevenção OOM), ingestão no nó `#5` e saída 1 a 1 no nó `#55`.
   - **Contas Dedicadas de Mídia**: Conta 3 Vídeo 4K (`#164/#17/#185`), Conta 4 Audio Command Center (CosyVoice `#345/#355/#346` & MiniMax Music 3 `#15/#16/#14/#7`) e Conta 7 MiniMax H3 (`#35/#48/#66/#107`).
5. **Catalogação Binária Física (IPTC / EXIF / MP4 Atoms) & 300 DPI**: Grava metadados definitivos nos bytes das imagens e vídeos (com stripping `-an` e ProRes 422 HQ para Pond5).
6. **Gestor de Cotas Deslizantes (Rolling 7D) & Proteção Alamy (ADR-05)**: Distribuição seletiva multi-agência com bloqueio programático irrestrito da Alamy para ativos IA.
7. **Produção Contínua 24/7 com AlertNotifier & Auto-Purga Inteligente de SSD**: Daemon supervisor com heartbeat atômico, alertas via webhook (`ALERT_WEBHOOK_URL`), dead-man ping (`HEARTBEAT_PING_URL`), watchdog Windows (`run_24_7.bat`) e backup em nuvem no Google Drive.
8. **Centro de Comando Web SPA (`/`, `/video`) em Apple iOS 27 Liquid Glass**: Duas superfícies SPA sincronizadas (`/` para Imagens 8K em 9 abas + `/video` Cinema Command Center em 6 abas e estúdios integrados), protegidas por `DASHBOARD_ACCESS_TOKEN` em rotas mutáveis `/api/*` e interligadas ao **DarkFactory Cinema (:8502)**.

---

## Arquitetura de Alto Nível & Topologia da Esteira

```mermaid
flowchart TD
    subgraph S1["Fase 1: Olheiro Preditivo & Research Engine"]
        A1["Seasonal Forecasting Radar (D+75)<br/>+ Live Signal Boosters"] --> B1["Niche Saturation Analyzer<br/>+ Unit Economics ROI"]
        B1 --> C1["Adobe Stock Scraper (Playwright)<br/>+ PublicDomainResearchEngine"]
        C1 --> D1["Concurrent Hydrator<br/>(src/scraper/hydrator.py)"]
        D1 --> E1[("data/raw/trends.json<br/>+ data/raw/images/")]
    end

    subgraph S2["Fase 2: Diretor de Arte v3.0, Vídeo 4D & Roteiro"]
        E1 --> F2["Gemini Vision Director v3.0<br/>(commercial | 7 Image Codes | auto)"]
        F2 --> G2[("data/processed/prompts.json<br/>(700-1000 Palavras / Copy-Space)")]
        E1 --> F2V["Video Director 4D + Nolan T2V<br/>+ PromoMotionDirector (B2B -an)"]
        F2V --> G2V[("video_prompts.json + T2V Queues<br/>+ Storyboard & OTIO Timelines")]
    end

    subgraph S3["Fase 3: Fábrica Multi-Engine (Lite/Plus + Google Flow)"]
        G2 --> H3["PromptQueueManager (SHA-256)"]
        H3 --> I3["RunningHub Conta 1 (Raw 42 nós)<br/>➔ QC Zips 10 ➔ Conta 2 SeedVR 8K"]
        G2V --> I3V["RunningHub Contas 3/4/7 (Vídeo & Áudio)<br/>+ Google Flow API (Veo 3.1 / Omni 1.2)"]
        G2V --> HF["HyperFrames / MapAnimator / DocumentaryComposer<br/>+ MotionQA Gate (WCAG, 0.5s, Safe-Zones)"]
        I3 --> M3[("data/final/images/<br/>(JPGs 8K Master)")]
        I3V & HF --> M3V[("data/final/videos/ + audio/<br/>(4K MP4 / FLAC / Shorts 9:16)")]
    end

    subgraph S4["Fase 4: O Catalogador & Conformidade"]
        M3 --> N4["Mastering 300 DPI + IPTC/EXIF<br/>(iptcinfo3 + piexif)"]
        M3V --> N4V["Video Cataloger & FFmpeg Engine<br/>(Mudo -an + Átomos MP4 + ProRes 422)"]
        N4 & N4V --> O4["Platform Compliance & Bloqueio Alamy ADR-05<br/>(adobe_stock_upload.csv + pond5_upload.csv)"]
    end

    subgraph S5["Fase 5: Distribuidor, Cotas & O Cofre"]
        O4 --> Q5["Rolling 7D Quota Manager<br/>(src/uploader/quota_manager.py)"]
        Q5 --> R5["Despacho Multi-Agência SFTP/FTP<br/>(Adobe, Freepik, 123RF, Pond5...)"]
        Q5 -.->|Bloqueio Anti-Ban ADR-05| BLK["<img src="docs/icons/ban.svg" width="14" height="14" /> ALAMY (Bloqueio IA Ativo)"]
        O4 --> S5["Cofre Cloud Google Drive<br/>(src/backup/gdrive_backup.py)"]
        R5 & S5 --> T5["Auto-Purga Segura de SSD<br/>(Libera disco pós-distribuição 100%)"]
    end

    subgraph S6["Supervisor 24/7, Telemetria & SPA Dual"]
        U6["Daemon 24/7 + AlertNotifier<br/>(src/orchestrator/daemon.py)"] -.-> S1 & S2 & S3 & S4 & S5
        U6 --> V6["Watchdog Windows (run_24_7.bat)<br/>+ Task Scheduler + Heartbeat Ping"]
        U6 --> W6["Dashboard Web SPA (:8501)<br/>/ Imagens 8K & /video Cinema Studio"]
    end
```

---

## <img src="docs/icons/desktop.svg" width="20" height="20" /> Dashboard Web SPA Local (iOS 27 Liquid Glass)

O StockCont conta com duas interfaces web reativas em Single-Page Application (**FastAPI + SSE + Apple HIG iOS 27 Liquid Glass Tokens**), protegidas opcionalmente por token de acesso (`DASHBOARD_ACCESS_TOKEN` via `Authorization: Bearer` ou `X-Dashboard-Token`) em todas as rotas mutáveis `/api/*` (veja [`docs/REMOTE_TUNNEL_SETUP.md`](docs/REMOTE_TUNNEL_SETUP.md) para Tailscale Serve ou Cloudflare Zero Trust Tunnel):

* **Superfície Principal — Imagens 8K (`/`, 9 abas segmentadas)**:
  1. `Galeria`: Grid sob demanda com scoring comercial (`commercial_scorer.py`), tiers `S/A`, filtros B2B, badge de copy-space e modal binário **IPTC/EXIF + 300 DPI**.
  2. `Fila de Prompts`: Controle SHA-256 de prompts pendentes/gerados com ações em lote.
  3. `Curadoria & QC`: Auditoria Gemini Vision, empacotamento em zips de 10 e disparo da Conta 2 (`SeedVR 8K`).
  4. `Matriz de Distribuição`: Visão cruzada de envio arquivo × agência com disparo seletivo.
  5. `Agências`: Status operacional de plataformas e bloqueio ativo Alamy (ADR-05).
  6. `Timeline`: Streaming SSE de logs e histórico de execução de fases.
  7. `Radar Sazonal`: Micro-nichos `D+75`, índices de saturação `D / N` e mineração em 1 clique.
  8. `Cofre Cloud`: Sincronização e restauração completa Google Drive.
  9. `Produção 24/7`: Hero Card do Daemon, telemetria de purga de SSD e barras de **Cotas Semanais (Rolling 7D)**.
* **Superfície Cinema — Vídeo & Motion Command Center (`/video`, 6 abas + Estúdios Sprints 4–11)**:
  - Abas `Galeria Cinema` (Player HTML5 + inspeção de átomos Moov / áudio mudo `-an`), `Fila de Prompts 4D`, `Estúdio I2V (Imagens 8K ➔ Vídeo)`, `Matriz de Distribuição`, `Agências de Vídeo` e `Timeline & Logs`.
  - **Estúdios Integrados**:
    - *Telemetry Studio (Sprints 4–6)*: Disparadores de **Motion QA Gate**, **Cadence Blueprint** (beat-sync + BPM) e **SVG Deconstructor** (`/api/v1/video/motion-qa`, `/api/v1/video/cadence-blueprint`, `/api/v1/video/svg-deconstruct`).
    - *Documentary & Monetization Studio (Sprints 7–9)*: **Map Animator** (6 teatros geopolíticos SVG/GSAP/MP4), **Storyboard Compiler** com auditoria espacial 0.5s e geração de **Tri-Variant Thumbnails 1280×720** + B-rolls `-an` (`/api/v1/video/map-animate`, `/api/v1/video/compose-dossier`, `/api/v1/audio/foley-track`, `/api/v1/video/reverse-engineer`, `/api/v1/video/storyboard-compile`, `/api/v1/youtube/render-monetization-pack`).
    - *Shorts 9:16 & B2B Promo Studio (Sprints 10–11)*: Repurpose vertical `9:16` com safe-zones mobile (`youtube_shorts`, `tiktok`, `instagram_reels`) e legendas cinéticas ASS + gerador de packs **B2B Zero-Trademark (`-an`)** com auditoria Anti-Sameness (`/api/v1/video/repurpose-short`, `/api/v1/video/promo-motion-pack`).
  - **Cross-Workspace Switcher**: Alternância direta com o ecossistema **DarkFactory Cinema (`:8502`)**.

Para iniciar o Dashboard:
```bash
python main.py --dashboard
```
*Acesse:* `http://localhost:8501` *(Imagens 8K)* e `http://localhost:8501/video` *(Cinema & Motion)*

---

##  Detalhamento Técnico das Fases do Pipeline

### Fase 1: O Olheiro Preditivo (*Radar Sazonal & Saturation Index*)
* **Módulos Centrais**: [`src/scraper/adobe_stock.py`](src/scraper/adobe_stock.py), [`src/analyzer/seasonal_radar.py`](src/analyzer/seasonal_radar.py), [`src/analyzer/saturation_index.py`](src/analyzer/saturation_index.py), [`src/scraper/hydrator.py`](src/scraper/hydrator.py)
* **Objetivo**: Antecipar a demanda comercial das agências corporativas e filtrar nichos saturados antes de gastar créditos de GPU.

#### 1. Seasonal Demand Forecasting Radar (D+75 dias)
Empresas e agências adquirem ativos para campanhas com **60 a 90 dias de antecedência**:
* O motor projeta a janela do trimestre-alvo e gera micro-nichos recomendados.
* Exemplo: Em outubro, o radar projeta o trimestre **Q1 (Janeiro/Fevereiro)**, priorizando nichos corporativos de virada de ano, *FinTech Analytics Dashboards*, *Biotech Longevity Labs* e *Relatórios Corporativos ESG*.
* Consulta via CLI:
  ```bash
  python main.py --seasonal
  ```

#### 2. Niche Saturation Index ($D / N$)
Calcula a viabilidade matemática entre consumo e concorrência:
$$\text{Saturation Score} = \frac{\text{Downloads Médios dos Top Sellers}}{\max(\text{Total de Resultados Indexados}, 1)}$$

* <img src="docs/icons/status-green.svg" width="12" height="12" /> **Blue Ocean** ($\text{Score} \ge 0.025$): Alta demanda e baixa concorrência. Produção imediata.
* <img src="docs/icons/status-yellow.svg" width="12" height="12" /> **Competição Moderada** ($0.005 \le \text{Score} < 0.025$): Exige forte diferenciação estética e copy-space.
* <img src="docs/icons/status-red.svg" width="12" height="12" /> **Red Ocean** ($\text{Score} < 0.005$): Nicho saturado. O sistema recomenda refinar a busca.

#### 3. Concurrent Reference Hydrator (`--sync-raw`)
Módulo com pool de threads para download concorrente de miniaturas de referência listadas em `trends.json` que estejam pendentes em disco.

---

### Fase 2: O Diretor de Arte v3.0 (*Prompts de 700–1.000 Palavras, Image Codes & Unit Economics*)
* **Módulos Centrais**: [`src/analyzer/director.py`](src/analyzer/director.py), [`src/analyzer/commercial_scorer.py`](src/analyzer/commercial_scorer.py), [`src/analyzer/unit_economics.py`](src/analyzer/unit_economics.py)
* **Objetivo**: Engenharia reversa visual via Gemini Vision com geração de **10 prompts ultra-densos (700 a 1.000 palavras)** nos modos `commercial`, `technical` ou `auto` (`--director-mode`), **Copy-Space adaptativo** (35%–50%), scoring comercial de portfólio e análise financeira por nicho.

#### 7 Image Codes Técnicos (`--director-mode technical`):
Geração determinística de ilustrações técnicas B2B de alto ticket integrando `/explodedview`, `/blueprint`, `/anatomy`, `/360view`, `/crosssection`, `/xray` e `/knolling`, mantendo os padrões de 700–1.000 palavras e Copy-Space limpo.

#### Unit Economics & Commercial Scorer:
* [`src/analyzer/unit_economics.py`](src/analyzer/unit_economics.py): Quantifica custo unitário por ativo (Gemini Vision + QC + RunningHub Lite/Plus + SeedVR 8K), break-even de downloads e ROI ranqueado sobre `NICHE_DEFINITIONS` (`finance`, `biotech`, `podium`, `tech_space`, `abstract`).
* [`src/analyzer/commercial_scorer.py`](src/analyzer/commercial_scorer.py): Avalia potencial de vendas de 0 a 100 (`Tier S/A`) considerando usabilidade de Copy-Space, nicho B2B e conformidade IPTC.

#### As 6 Camadas Mandatórias do Prompt v3.0:
1. **Spatial Architecture & Narrative Staging (120–150 palavras)**: Coordenadas espaciais tridimensionais, profundidade de campo, enquadramento de primeiro plano e sujeito em plano médio.
2. **Physical Materiality & Micro-Textures (120–150 palavras)**: Dispersão subsuperficial (*SSS*) em tecidos e pele, micro-arranhões em metais escovados, reflexos Fresnel em vidros arquitetônicos e partículas atmosféricas.
3. **Multi-Point Lighting Kelvin Architecture (120–150 palavras)**: Configuração de estúdio e sol, relação entre luz principal (*Key*), luz de preenchimento difusa (*Fill*), contorno (*Rim/Kicker*) e temperatura de cor precisa em Kelvin (ex: 3200K tungstênio vs 5600K daylight).
4. **Optical Camera & Lens Fingerprint (100–130 palavras)**: Assinatura óptica de lentes de cinema (35mm, 50mm, 85mm), aberturas físicas (f/1.4, f/2.8), curvatura de foco suave, bokeh esférico e granulação tátil.
5. **Adaptive Copy-Space & Graphic Usability (120–150 palavras)**: Reserva intencional de 35% a 50% do enquadramento como área negativa limpa para inserção de títulos por designers gráficos.
6. **Commercial Buyer Intent & Compliance (100–120 palavras)**: Modelagem orientada a personas B2B (`saas_landing_page`, `ad_agency_hero`, `b2b_corporate_editorial`, `product_mockup`, `fintech_wellness_campaign`) livre de marcas comerciais.

---

### <img src="docs/icons/film.svg" width="18" height="18" /> Pipeline de Vídeo Cinematográfico, Motion Engine & DarkFactory Studio (Sprints 1–11)
* **Módulos Centrais**: [`src/analyzer/video_director.py`](src/analyzer/video_director.py), [`src/cataloger/video_cataloger.py`](src/cataloger/video_cataloger.py), [`src/video/ffmpeg_processor.py`](src/video/ffmpeg_processor.py), [`src/video/hyperframes_engine.py`](src/video/hyperframes_engine.py), [`src/video/motion_qa.py`](src/video/motion_qa.py), [`src/video/darkfactory_t2v.py`](src/video/darkfactory_t2v.py)
* **Objetivo**: Unificar em uma esteira contínua a produção de B-rolls comerciais I2V/T2V mudos (`-an`), motion graphics determinísticos 4K e documentários históricos de alta retenção.

#### Destaques por Bloco Tecnológico (Sprints 1–11):
* **Motion Engine Determinístico & Gate Visual (`HyperFrames` + `MotionQA` + `SVG Deconstructor`)**:
  - Contratos HTML/CSS/GSAP (`window.__timelines`, `paused: true`, PRNG Mulberry32 determinístico), diagramas isométricos 4-tonalidades, **4 personalidades visuais** (`cold_war_noir`, `clinical_fintech`, `executive_corporate`, `high_energy_hook`) e **3 plates Zero-Blob** (`blueprint_notebook`, `risograph_declassified`, `cut_paper_editorial`).
  - **MotionQA Gate**: Contraste WCAG (>= 4.5), safe-area de texto, detecção de freeze-frames/clipping, contact sheets 3×3 PNG, hook critique Nível 2 Gemini Vision e varredura espacial par-a-par a cada `0.5s` (`audit_overlay_overlaps`).
  - **SVG Deconstructor**: Converte rasters/emblemas em camadas SVG semânticas animáveis (`grid`, `mark`, `callouts`, `wordmark`) com player seekable.
* **Diretor Temporal 4D, Óptica DoP & Psicologia Cromática**:
  - `VideoDirector`: Prompts de 500–800 palavras (16:9 e 9:16), *Shot Card Recipes* e `CinematicColorGrader` (LUTs Kodak 2383, Fuji Eterna, Bleach-Bypass, Oppenheimer Mono, Cold War Noir, Cyber Tactical).
  - `CinematographyEngine` (7 lentes de cinema, 7 geometrias, razões Chiaroscuro) e `ColorPsychologyEngine` (7 paletas 60-30-10 + auditoria K-Means de keyframes).
* **Documentários Word-Timed, Mapas & Áudio Multitrack (Sprints 5, 7, 8 & 9)**:
  - **Voice Aligner + Map Animator + Documentary Composer**: Pesquisa factual pública em **PublicDomainResearchEngine** (Wikipedia, Wikimedia PD/CC0, Internet Archive, NASA), alinhamento silábico/RMS palavra-a-palavra, **6 teatros geopolíticos** offline SVG/GSAP/MP4 12fps, selos desencadeados na fala exata (`TacticalGraphicsEngine`), corte automático de *dead-air* (`>350ms`) e **J/L-Cuts** em **OpenTimelineIO** (`.otio`) para DaVinci Resolve.
  - **Hierarquia Vocal & `NarratorLock` (ADR-09)**: Tier 1 CosyVoice (`#345/#355 -> #346 FLAC`) ➔ Tier 2 Kokoro Neural (`bm_george`) ➔ Tier 3 Deepgram Aura (`aura-helios-en`), travado por vídeo em `narrator_locks.json`.
  - **MiniMax Music 3 & Foley CC0 (ADR-10)**: Trilha 100% instrumental (sem vocais) no Workflow `2120003151633174529` (`#15/#16/#14 -> #7 FLAC`), biblioteca `FoleyLibrary` CC0-1.0 e mixagem 3-Stem com sidechain ducking a **-14 LUFS (EBU R128)**.
  - **Video Reverse-Engineer & Storyboard Compiler**: Extrai sequências *T2VA/I2V* prontas para MiniMax H3 e Google Veo 2, fatiamento em storyboard orçado e **Dual Monetization Pack** (`youtube_booster.py`: lint fechado de título/thumb/capítulos, 3 thumbnails JPEG 1280×720 + B-rolls `-an`).
* **Shorts Verticais 9:16, Kinetic Captions & B2B Promo Motion (Sprints 10–11)**:
  - **ShortsRepurposer & KineticCaptions**: Extração centrada por saliência (`16:9 ➔ 9:16`), legendas `.ass` em 3 estilos (`editorial_karaoke`, `hormozi_pop`, `terminal_typewriter`), safe-zones mobile (`youtube_shorts`, `tiktok`, `instagram_reels`) e exportação paralela de B-roll vertical mudo (`-an`).
  - **PromoMotionDirector B2B Zero-Trademark**: Templates SaaS silenciosos `-an` (`onetake_bento_launch`, `cursor_spotlight_demo`, `kpi_metric_cascade`), filtro rigoroso de marcas registradas (`BANNED_TRADEMARK_TERMS`), auditoria vetorial **Anti-Sameness** e bloqueio Alamy (ADR-05).
* **Knowledge Vault (27 Livros Canônicos)**: Regras executáveis de Walter Murch, MrBeast, Lisa Cron, Jonah Berger, Brendan Kane, Derral Eves e Alex Hormozi em [`src/video/master_knowledge.py`](src/video/master_knowledge.py) e [`src/video/story_validator.py`](src/video/story_validator.py).

---

### Google Flow Industrial REST API (Veo 3.1 / Omni 1.2 / Imagen 3)
* **Módulos Centrais**: [`src/integrations/google_flow/`](src/integrations/google_flow/) (`api_server.py`, `service.py`, `auth_manager.py`, `stealth_driver.py`, `rpc_client.py`, `qc_curator.py`, `downloader.py`)
* **Servidor REST Dedicado (`http://localhost:8000/docs`)**:
  - Orquestra os modelos `veo-3.1-quality`, `veo-3.1-fast`, `veo-3.1-lite`, `omni-1.2-flash` e `imagen-3.0` nas proporções `16:9`, `9:16`, `1:1`, `4:3`, `2.39:1`.
  - Endpoints `/api/v1/health`, `/api/v1/models`, `/api/v1/auth/status`, `/api/v1/auth/login` (login interativo 1-clique Google), `/api/v1/projects`, `/api/v1/generate`, `/api/v1/jobs`, `/api/v1/jobs/{job_id}/upscale` (`1k`/`2k`/`4k`), `/api/v1/jobs/{job_id}/download` e `/api/v1/history` (ledger SHA-256).
  - Auto-aprovação autônoma de créditos, proteção anti-race condition com detecção resiliente de tiles (`flow-video-tile`), curadoria IA e stripping de áudio opcional (`--flow-strip-audio`).

---

### Fase 3: A Fábrica RPA Multi-Account (*Lite/Plus Mandatório ADR-08*)
* **Módulos Centrais**: [`src/factory/runninghub_bot.py`](src/factory/runninghub_bot.py), [`src/factory/prompt_queue.py`](src/factory/prompt_queue.py), [`src/factory/stealth_profile.py`](src/factory/stealth_profile.py), [`src/video/minimax_h3_engine.py`](src/video/minimax_h3_engine.py), [`src/video/minimax_music_engine.py`](src/video/minimax_music_engine.py)
* **Regra Inviolável de Execução (ADR-08)**: Em TODOS os workflows do RunningHub, o acionamento ocorre **exclusivamente pelo botão `Lite/Plus`** (botão do meio). O modo `Standard` é proibido e redirecionado automaticamente para `lite_plus`.

#### Topologia Especializada por Conta / Workflow:
* **Conta 1 — Raw Producer (`2113606426114670593`)**: 42 nós `PromptList` simultâneos (#128, #129, #130, #131, #204, #218...), 5 prompts por nó = **até 210 prompts por lote** na janela de 40 minutos com captura no nó `#121` em `data/staging/images/`.
* **Conta 2 — SeedVR 8K Upscaler (`2115663736840245249`)**: Ingestão zip curado de 10 imagens no nó `#5`, captura 1 a 1 no nó `#55` para `data/final/images/` e cancelamento atômico pós-última imagem renderizada.
* **Conta 3 — Pipeline Vídeo 4K (`2115926169974812674`)**: Ingestão de imagem no nó `#164` (`LoadImage`), prompt temporal no nó `#17` e saída 4K no nó `#185` (FeiHou Preview sem watermark) em `data/final/videos/`.
* **Conta 4 — Audio Command Center**: Narração **CosyVoice** lossless (`2118531898170486785`, nós `#345/#355/#352 -> #346 FLAC`) e trilha **MiniMax Music 3** 100% instrumental (`2120003151633174529`, nós `#15/#16/#14 -> #7 FLAC`).
* **Conta 7 — MiniMax H3 Cinematic V2 Turbo (`2118560390471745537`)**: Geração cinemática T2V/I2V com áudio sincronizado AAC (nós `#35`, `#48`, `#66`) e saída sem marca d'água no nó **`#107 FeiHouVideoPreview`** (ADR-11).

#### Fila Criptográfica com Hashing SHA-256:
* Cada prompt gera hash canônico único em `data/processed/generation_history.json`, impedindo regerações duplicadas.

---

###  Módulo QC: Curadoria Multimodal & Prevenção OOM
* **Módulo Central**: [`src/analyzer/qc_inspector.py`](src/analyzer/qc_inspector.py)
* **Auditoria Visual via Gemini Vision**: Inspeciona as imagens geradas pela Conta 1 contra deformações anatômicas, artefatos visuais ou texto distorcido.
* **Empacotamento em Lotes de 10 (`approved_batch.zip`)**: Agrupa apenas imagens aprovadas em zips leves de exatamente 10 unidades, prevenindo estouro de VRAM na GPU durante o upscale 8K da Conta 2.
* Comandos CLI:
  ```bash
  python main.py --qc --qc-mode auto
  python main.py --upscale
  ```

---

### Fase 4: O Catalogador (300 DPI, Injeção Binária IPTC/EXIF/MP4 & CSV)
* **Módulos Centrais**: [`src/cataloger/adobe_csv_maker.py`](src/cataloger/adobe_csv_maker.py), [`src/cataloger/platform_compliance.py`](src/cataloger/platform_compliance.py), [`src/cataloger/reembed_compliance.py`](src/cataloger/reembed_compliance.py)
* **Objetivo**: Garantir 100% de aceitação comercial e conformidade técnica antes da distribuição.

| Padrão / Tag ID | Conteúdo Injetado | Plataformas |
| :--- | :--- | :--- |
| **Resolução Física** | Forçado em **300 DPI** no cabeçalho JFIF | Todas as agências |
| **IPTC `2:05 (ObjectName)`** | Título comercial limpo (< 200 caracteres), sem corte | Adobe Stock, Freepik, Shutterstock, Lightroom |
| **IPTC `2:120 (Caption)`** | Obrigatoriamente iniciado com `"Generative AI illustration. [...]"` | Portais Web de Microstock |
| **IPTC `2:25 (Keywords)`** | **Exatamente 50 tags** com `["ai generated", "generative ai", ...]` | Adobe Stock, Freepik, Vecteezy, 123RF |
| **EXIF IFD0 `ImageDescription`** | Descrição comercial em UTF-8 | Windows Explorer, Mac Finder, Photoshop |
| **EXIF IFD0 `0x9C9B (XPTitle)`** | Título em UTF-16LE | Windows Explorer Propriedades |
| **EXIF IFD0 `0x9C9E (XPKeywords)`** | 50 tags separadas por vírgula em UTF-16LE | Windows Explorer Propriedades |
| **MP4/QuickTime Atoms** | Metadados de título, autor, copyright e tags no container | Adobe Stock Video, Pond5 |

> **Resultado**: Ao subir o arquivo via SFTP ou web, todos os campos são preenchidos automaticamente sem intervenção humana.

---

### Fase 5: O Distribuidor com Cotas Deslizantes (Rolling 7D)
* **Módulos Centrais**: [`src/uploader/ftp_distributor.py`](src/uploader/ftp_distributor.py), [`src/uploader/quota_manager.py`](src/uploader/quota_manager.py)
* **Objetivo**: Distribuição segura e escalável respeitando os limites semanais de upload de cada agência.

#### Gestor de Cotas Semanais Deslizantes (`src/uploader/quota_manager.py`):
* **Cálculo da Janela Móvel**: Computa envios onde `timestamp >= (now - 7 days)` a partir do livro-razão `upload_history.json`.
* **Despacho Seletivo**: Se uma agência atingir sua cota semanal, o envio para ela é pausado automaticamente enquanto o fluxo prossegue normalmente para as outras plataformas.
* **Contagem Regressiva para Próxima Vaga**: Calcula a projeção exata em dias, horas e minutos para quando o upload mais antigo sairá da janela de 7 dias.
* Consulta via CLI:
  ```bash
  python main.py --quotas
  ```

---

### <img src="docs/icons/cloud.svg" width="18" height="18" /> O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)
* **Módulo Central**: [`src/backup/gdrive_backup.py`](src/backup/gdrive_backup.py)
* **Backup no Google Drive**: Sincronização automática para `G:\Meu Drive\StockCont_backup` com livro-razão `gdrive_backup_history.json`.
* **Auto-Purga Inteligente de SSD**: Ativos gerados em 8K ocupam espaço significativo em disco. O StockCont remove com segurança o arquivo do SSD local **apenas quando duas condições simultâneas forem satisfeitas**:
  1. Confirmação registrada de backup no Google Drive.
  2. Confirmação de upload com sucesso em **todas** as agências ativas configuradas.
* **Restauração Completa (`--restore`)**: Recupera todo o catálogo, CSVs e históricos a partir do Google Drive caso necessário.

---

### <img src="docs/icons/robot.svg" width="18" height="18" /> Motor Autônomo 24/7 (Daemon Supervisor & Watchdog Windows)
* **Módulo Central**: [`src/orchestrator/daemon.py`](src/orchestrator/daemon.py)
* **Loop Contínuo Pipelined**:
  1. **Buffer de Prompts**: Monitora a fila; se pendentes < 50 (`--min-buffer`), dispara automaticamente as Fases 1 e 2.
  2. **Conta 1 (Raw Producer)**: Renderiza lotes de até 210 prompts no RunningHub ComfyUI via **Lite/Plus** (ADR-08).
  3. **QC Multimodal**: Audita via Gemini Vision e agrupa aprovados em zips de 10.
  4. **Conta 2 (SeedVR 8K)**: Renderiza upscales 8K dos zips.
  5. **Fase 4**: Cataloga IPTC/EXIF 300 DPI e salva no Cofre Google Drive.
  6. **Fase 5**: Despacha assets respeitando as cotas deslizantes.
  7. **Auto-Purga**: Libera o SSD de ativos 100% distribuídos e salvos em nuvem.
* **Resiliência & Telemetria Remota**:
  - Heartbeat atômico persistido em `data/processed/daemon_state.json`.
  - **AlertNotifier (`ALERT_WEBHOOK_URL`)**: Notificações em Discord/Slack/Telegram apenas por transição real de estado, sem spam em loops.
  - **Dead-Man Switch (`HEARTBEAT_PING_URL`)**: Ping HTTP para monitoramentos externos (ex: Healthchecks.io) a cada ciclo saudável.
  - Pacing sleep responsivo (padrão 300s) + **`run_24_7.bat`** (auto-restart em 30s) + **`scripts/setup_windows_task.ps1`**.

---

##  Orquestrador Mestre CLI (`main.py`) & Scripts de Execução

```bash
# ==========================================
# DASHBOARD WEB SPA (iOS 27 LIQUID GLASS)
# ==========================================
python main.py --dashboard                             # Inicia Web SPA (/ e /video) em http://localhost:8501
python main.py --dashboard --no-browser --port 8501    # Executa em background sem abrir o navegador

# ==========================================
# TELEMETRIA, COTAS, RADAR & UNIT ECONOMICS
# ==========================================
python main.py --status                                # Status global das fases, cofre e daemon
python main.py --quotas                                # Cotas semanais deslizantes (Rolling 7D)
python main.py --seasonal                              # Previsão D+75 + sinal ao vivo + nichos Blue Ocean
python main.py --unit-economics                        # Custo GPU/API, break-even e ROI por nicho

# ==========================================
# PRODUÇÃO CONTÍNUA 24/7 & WATCHDOG
# ==========================================
python main.py --daemon                                # Daemon contínuo (interval=300s, min-buffer=50)
.\run_24_7.bat                                         # Watchdog Windows com auto-restart

# ==========================================
# FASES 1 & 2: OLHEIRO & DIRETOR DE ARTE v3.0
# ==========================================
python main.py --phase 1 --mode insights --type photo --max-items 20
python main.py --phase 1 --mode search --query "biotech longevity laboratory" --order nb_downloads
python main.py --sync-raw                              # Download concorrente de referências pendentes
python main.py --phase 2 --director-mode technical     # Modes: commercial | technical (7 Image Codes) | auto

# ==========================================
# FASE 3, QC & COFRE (RUNNINGHUB LITE/PLUS)
# ==========================================
python main.py --phase 3 --account 1 --batch-size 210 --execute-mode lite_plus
.\run_conta1.bat
python main.py --qc --qc-mode auto                     # Curadoria visual Gemini Vision + packs de 10
python main.py --phase 3 --account 2 --batch-size 10   # ou: python main.py --upscale / .\run_conta2.bat
python main.py --phase 4                               # Catalogação 300 DPI + IPTC/EXIF + CSV
python main.py --backup                                # ou: python main.py --restore
python main.py --phase 5 --dry-run                     # Validação de credenciais e cotas
python main.py --phase 5 --platform all                # Upload multi-agência (Alamy bloqueada via ADR-05)

# ==========================================
# PIPELINE DE VÍDEO, MOTION & DARKFACTORY (SPRINTS 1-11)
# ==========================================
python main.py --video --phase 2                       # Diretor 4D Temporal (500-800 palavras)
python main.py --video --phase 3 --account 3           # RPA Conta 3 RunningHub Vídeo 4K
python main.py --video --phase 4 --prores              # Mudo (-an) + átomos MP4 + Apple ProRes 422 HQ
python main.py --t2v --t2v-archetype cold_war_espionage --t2v-export
python main.py --nolan-direct --nolan-topic "1983 Soviet Glitch"
python main.py --narration --script "..." --emotion solemn --speed 0.98
python main.py --research-topic "Stanislav Petrov"     # Pesquisa PD (Wikipedia/Wikimedia/IA/NASA)
python main.py --render-motion-hud --motion-template tactical_hud --motion-title "RADAR TRACK" --preview-20s
python main.py --dop-plan --dop-lens cooke_anamorphic_i --dop-lighting 8_to_1
python main.py --map-animate "Serpukhov-15 Crisis" --map-theater europe_cold_war
python main.py --compose-dossier "Operation Able Archer" --dossier-audio data/audio/narration.wav
python main.py --reverse-video clip.mp4 --reverse-mode DUAL
python main.py --compile-storyboard "Fintech Q4" --storyboard-niche finance
python main.py --repurpose-short "Cold War Hook" --short-style editorial_karaoke --short-safe-zone youtube_shorts
python main.py --promo-pack "Cloud Telemetry" --promo-preset onetake_bento_launch --promo-niche finance
python main.py --yt-lint --yt-title "..." --yt-thumb "..."

# ==========================================
# GOOGLE FLOW INDUSTRIAL REST API (VEO 3.1 / OMNI 1.2)
# ==========================================
python main.py --flow-login                            # Login interativo Google 1-clique
python main.py --flow-status                           # Valida cookies de sessão persistente
python main.py --flow-serve --flow-port 8000           # Inicia Swagger API em http://localhost:8000/docs
python main.py --flow-generate "Cinematic radar bunker..." --flow-model veo-3.1-quality --flow-upscale 4k --flow-strip-audio
python main.py --flow-process-queue                    # Processa fila data/processed/google_veo_queue.json
```

---

##  Estrutura do Repositório & Gestão de Dados

```text
stockcont/
├── .env                                  # Credenciais locais (GEMINI_API_KEY, FTP/SFTP, Tokens)
├── .env.example                          # Template completo de configuração (Agências, Drive, Segurança)
├── main.py                               # Orquestrador CLI Mestre e Ponto de Entrada Unificado
├── pytest.ini                            # Configuração padrão da suíte pytest
├── requirements.txt                      # Dependências Python travadas
├── README.md                             # Documentação técnica completa e ADRs
├── state.md                              # Quadro vivo de estado e telemetria das Sprints
├── AGENTS.md / CLAUDE.md / GEMINI.md / PROJECT_CONTEXT.md  # Governança & SSOT para agentes
├── run_24_7.bat / run_conta1.bat / run_conta2.bat / start.bat
│
├── docs/
│   ├── REMOTE_TUNNEL_SETUP.md            # Guia Tailscale Serve & Cloudflare Tunnel + Bearer Auth
│   └── icons/                            # Ícones SVG oficiais da documentação
│
├── chrome_session/                       # Perfis persistentes (Scraper Adobe & Google Flow)
├── playwright_session/                   # Sessão persistente para RPA RunningHub
│
├── data/
│   ├── raw/
│   │   ├── trends.json                   # Tendências mineradas da Fase 1
│   │   ├── images/                       # Referências visuais hidratadas
│   │   └── research_cache/               # Cache offline de APIs públicas (Wikipedia/IA/NASA)
│   ├── staging/                          # Renders 4K brutos (Conta 1) & packs Zip de 10 imagens
│   ├── processed/                        # prompts.json, video_prompts.json, queues T2V,
│   │                                     # generation_history.json, upload_history.json,
│   │                                     # narrator_locks.json, daemon_state.json, CSVs & dossiês
│   └── final/                            # images/ (8K), videos/ (MP4/ProRes -an), audio/, rejected/
│
├── src/
│   ├── analyzer/
│   │   ├── director.py                   # Diretor v3.0 (commercial, 7 Image Codes, auto)
│   │   ├── video_director.py             # Diretor 4D Temporal (16:9, 9:16 & Shot Cards)
│   │   ├── qc_inspector.py               # Curadoria visual multimodal Gemini Vision
│   │   ├── commercial_scorer.py          # Scoring comercial B2B (0-100 pts, Tier S/A)
│   │   ├── unit_economics.py             # Custo GPU/API, break-even e ROI por nicho
│   │   ├── seasonal_radar.py             # Radar Sazonal D+75 + sinal ao vivo
│   │   └── saturation_index.py           # Analisador de saturação Blue Ocean (D / N)
│   ├── backup/
│   │   └── gdrive_backup.py              # Cofre Google Drive (backup incremental & restore)
│   ├── cataloger/
│   │   ├── adobe_csv_maker.py            # Catalogador de Imagens (IPTC/EXIF/300 DPI + CSV)
│   │   ├── video_cataloger.py            # Catalogador de Vídeo (-an, átomos MP4 & ProRes)
│   │   ├── platform_compliance.py        # Validação técnica por agência & bloqueio Alamy ADR-05
│   │   └── reembed_compliance.py         # Utilitário de regravação em lote de metadados
│   ├── dashboard/
│   │   ├── app.py                        # FastAPI (/ , /video, SSE, auth DASHBOARD_ACCESS_TOKEN)
│   │   ├── readers.py                    # Leitores atômicos de estado e metadados
│   │   ├── runner.py                     # Executor assíncrono de tarefas via subprocess
│   │   ├── schemas.py                    # Contratos Pydantic da API REST (/api/v1/*)
│   │   └── static/                       # SPA Dual (index.html, video.html, CSS Liquid Glass, JS)
│   ├── factory/
│   │   ├── prompt_queue.py               # Fila criptográfica SHA-256 e mapeamento de topologias
│   │   ├── runninghub_bot.py             # RPA Multi-Account RunningHub (Lite/Plus obrigatório)
│   │   └── stealth_profile.py            # Evasão anti-bot e resiliência a popups
│   ├── integrations/google_flow/         # Google Flow Industrial REST API (Veo 3.1, Omni, Imagen)
│   │   ├── api_server.py / service.py / auth_manager.py / config.py
│   │   └── models.py / rpc_client.py / stealth_driver.py / qc_curator.py / downloader.py / cli.py
│   ├── orchestrator/
│   │   └── daemon.py                     # Daemon 24/7 Supervisor, AlertNotifier & Auto-Purga SSD
│   ├── scraper/
│   │   ├── adobe_stock.py                # Olheiro Playwright (Contributor Insights & busca)
│   │   └── hydrator.py                   # Downloader concorrente de referências visuais
│   ├── uploader/
│   │   ├── ftp_distributor.py            # Distribuidor SFTP/FTP multi-agência
│   │   └── quota_manager.py              # Gestor de cotas deslizantes Rolling 7D
│   └── video/                            # Ecossistema Vídeo, Motion, Áudio & Knowledge Vault (31 módulos)
│       ├── ffmpeg_processor.py / video_metadata.py / otio_exporter.py
│       ├── hyperframes_engine.py / motion_qa.py / svg_deconstructor.py
│       ├── audio_engine.py / foley_library.py / voice_engine.py / voice_router.py / voice_aligner.py
│       ├── minimax_h3_engine.py / minimax_music_engine.py / darkfactory_t2v.py
│       ├── cinematography_dop.py / cinematic_color.py / color_psychology.py / pacing_analyzer.py
│       ├── tactical_graphics.py / map_animator.py / documentary_composer.py / research_engine.py
│       ├── video_reverse_engineer.py / storyboard_compiler.py / youtube_booster.py
│       ├── kinetic_captions.py / shorts_repurposer.py / promo_motion_director.py
│       └── master_knowledge.py / knowledge_distiller.py / story_validator.py
│
├── scripts/                              # Task Scheduler, hooks git/session e utilitários CLI
└── tests/                                # 48 suítes Pytest cobrindo Fases 1-5, Google Flow,
                                          # MiniMax H3/Music 3, SPA Playwright e Sprints 1-11
```

---

## <img src="docs/icons/file-text.svg" width="20" height="20" /> Contratos de Dados (Data Schemas v3.0)

### Schema de Prompts Processados (`data/processed/prompts.json` - v3.0)
```json
[
  {
    "source_id": "2090056954",
    "source_title": "Faceless corporate analytics team reviewing dashboards...",
    "system_version": "3.0",
    "analysis_metadata": {
      "target_model": "model-agnostic-flux-comfyui",
      "analysis_confidence": 0.95
    },
    "generated_prompts": [
      {
        "id": 1,
        "concept": "FinTech High-Frequency Trading Desk & Data Analytics",
        "layout_type": "left_third_copy_space",
        "copy_space_zone": "left_35_percent",
        "target_buyer": "saas_landing_page",
        "prompt": "Cinematic wide commercial shot of a high-tech financial operations workstation... [700 a 1.000 palavras descrevendo física de materiais, iluminação Kelvin, lente de cinema e área limpa para tipografia]",
        "estimated_word_count": 820,
        "status": "pending"
      }
    ]
  }
]
```

---

##  Matriz Estratégica Multi-Agência & Proteção Anti-Ban Alamy

| Plataforma | Protocolo | Tipo de Ativo | Política de IA | Gestão no StockCont |
| :--- | :--- | :--- | :--- | :--- |
| **Adobe Stock** | SFTP | Imagens 8K & Vídeos | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito *(Tag IA requerida)* | Suporte nativo / Lê IPTC e átomos MP4 |
| **Freepik Contributor** | FTP | Imagens 8K | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito em escala massiva | Suporte nativo / Despacho com cotas |
| **Dreamstime** | FTP | Imagens 8K | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito *(IA no Caption)* | Suporte nativo / Pré-formatação de texto |
| **Pond5** | FTP | Vídeos 4K & ProRes | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito *(Preço customizável)*| Suporte nativo / Apple ProRes 422 HQ |
| **123RF** | FTP | Imagens 8K | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito | Suporte nativo / Gestor de cotas |
| **Vecteezy** | FTP | Imagens & Vetores | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito | Suporte nativo / Leitura IPTC |
| **Ingram Image** | FTP | Imagens 8K | <img src="docs/icons/check.svg" width="14" height="14" /> Aceito | Suporte nativo / Gestor de cotas |
| **Alamy** | SFTP/FTP | Imagens & Vídeos | <img src="docs/icons/ban.svg" width="14" height="14" /> **TERMINANTEMENTE PROIBIDO PARA IA** | <img src="docs/icons/shield.svg" width="14" height="14" /> **BLOQUEIO ATIVO ANTI-BAN (ADR-05)** |

> ### <img src="docs/icons/alert.svg" width="15" height="15" />️ ALERTA MANDATÓRIO DE COMPLIANCE — ALAMY (ADR-05)
> A **Alamy proíbe terminantemente qualquer conteúdo gerado por IA** (Seção 1.3 do Contrato de Contribuinte). Submeter IA à Alamy acarreta **banimento sumário da conta e perda definitiva de todos os rendimentos acumulados**.
> O StockCont possui proteção ativa em [`src/cataloger/platform_compliance.py`](src/cataloger/platform_compliance.py) que **bloqueia programaticamente qualquer tentativa de upload de asset IA para a Alamy**, exibindo aviso no console e mantendo o contribuinte seguro.

---

## <img src="docs/icons/terminal.svg" width="16" height="16" /> Instalação, Configuração & Execução

### 1. Pré-Requisitos
* Python 3.11 ou superior
* Google Chrome instalado
* FFmpeg instalado e adicionado ao PATH (para processamento de vídeo)
* Chave de API ativa do Google Gemini ([Google AI Studio](https://aistudio.google.com/))

### 2. Configuração do Ambiente
```bash
# 1. Clonar o repositório
git clone https://github.com/ciamarrojonatan-droid/stockcont.git
cd stockcont

# 2. Criar e ativar o ambiente virtual
python -m venv venv

# No Windows PowerShell:
.\venv\Scripts\Activate.ps1

# No Linux / macOS:
source venv/bin/activate

# 3. Instalar dependências e navegadores do Playwright
pip install -r requirements.txt
playwright install chromium
```

### 3. Configuração do Arquivo `.env`
Copie o template e configure suas credenciais:
```bash
cp .env.example .env
```
Campos essenciais:
* `GEMINI_API_KEY`: Chave da API do Google Gemini (Fase 2, QC e Reverse Engineer).
* Credenciais SFTP/FTP das agências (Adobe Stock, Freepik, 123RF, Dreamstime, Pond5, Vecteezy, Ingram) e limites `*_WEEKLY_LIMIT` (`ALAMY_WEEKLY_LIMIT=0`).
* `GOOGLE_DRIVE_LOCAL_PATH` / Service Account / OAuth para o Cofre Cloud.
* `DEEPGRAM_API_KEY` & `NASA_API_KEY`: Síntese vocal Tier 3 e acervo público de ciência/espaço.
* `DASHBOARD_ACCESS_TOKEN`: Token Bearer/`X-Dashboard-Token` opcional exigido em todas as rotas mutáveis `/api/*` quando exposto via túnel remoto (`docs/REMOTE_TUNNEL_SETUP.md`).
* `ALERT_WEBHOOK_URL` & `HEARTBEAT_PING_URL`: Alertas por transição de estado e ping dead-man do Daemon 24/7.
* `DIRECTOR_DEFAULT_MODE`: Modo padrão do Diretor de Arte (`auto`, `commercial` ou `technical`).

### 4. Executando a Suíte de Testes
```bash
# Suíte core offline + E2E Playwright SPA (sem dependência dos modelos binários locais Kokoro):
.\venv\Scripts\pytest --ignore=tests/test_kokoro_voice.py
```
*Resultado verificado:* **391 passed** *(Os 4 testes em `tests/test_kokoro_voice.py` validam modelos locais `kokoro-v0_19.onnx` e áudios piloto renderizados fora do versionamento Git).*

---

## <img src="docs/icons/shield.svg" width="20" height="20" /> Resiliência Operacional & Decisões de Engenharia (ADRs)

1. **ADR-01: Blindagem de Encoding UTF-8 em Windows**: Todo I/O de console, rede e persistência é forçado para UTF-8 no bootstrap de `main.py` e utilitários, neutralizando falhas crônicas de `cp1252` em terminais Windows.
2. **ADR-02: Escrita Atômica Transacional com `.tmp`**: Todos os arquivos JSON críticos (`prompts.json`, `trends.json`, `generation_history.json`, `upload_history.json`, `daemon_state.json`) são serializados primeiramente em arquivos temporários `.tmp` e substituídos atomicamente via `os.replace()`.
3. **ADR-03: Fila Criptográfica Idempotente com Hashing SHA-256**: Cada prompt gera um hash canônico SHA-256 único a partir de seu texto normalizado, impedindo regerações duplicadas e economizando custos e tempo de GPU.
4. **ADR-04: Reconhecimento Híbrido (Dual-Source) IPTC vs CSV**: O Catalogador executa ambas as ações simultaneamente: injeta tags IPTC/EXIF fisicamente nos bytes do arquivo e anexa a linha correspondente na planilha CSV.
5. **ADR-05: Proteção Ativa Anti-Ban Multi-Agência (Alamy)**: Bloqueio programático irrestrito para impedir qualquer upload de assets gerados por IA para a Alamy (incluindo B-rolls e packs Promo B2B), preservando a conta do contribuinte contra sanções contratuais.
6. **ADR-06: Segregação Dual-Account RPA & Prevenção OOM**: Separação física entre a Conta 1 (geração bruta de até 210 prompts por lote) e a Conta 2 (upscale 8K em pacotes curados de 10 imagens), garantindo estabilidade de hardware e economia máxima de créditos.
7. **ADR-07: Auto-Purga Segura com Cofre Híbrido**: O arquivo pesado é purgado do SSD local exclusivamente após o upload com sucesso em todas as agências ativas e a confirmação registrada de backup no Google Drive.
8. **ADR-08: Execução Mandatória via Botão Lite/Plus no RunningHub**: Todos os workflows (Conta 1 Raw Producer, Conta 2 SeedVR 8K Upscaler, Conta 3 Vídeo 4K, Conta 4 Audio Command Center e Conta 7 MiniMax H3) acionam **exclusivamente** o botão `Lite/Plus` (meio); chamadas a `Standard` são bloqueadas e redirecionadas em código.
9. **ADR-09: Hierarquia de Narração & Invariante `NarratorLock`**: Cadeia tripartite oficial (`Tier 1 CosyVoice -> Tier 2 Kokoro -> Tier 3 Deepgram`) com trava persistida por vídeo em `data/processed/narrator_locks.json`, garantindo narrador único em todas as cenas via `NarratorConsistencyViolationError`.
10. **ADR-10: Arquitetura Multitrack MiniMax Music 3 (100% Instrumental) & Mixagem 3-Stem -14 LUFS**: Workflow `2120003151633174529` condicionado estritamente sem vocais (`#15` metadados instrumentais, `#16` marcadores `[Instrumental]` puros, `#7` FLAC) e mixagem 3-Stem (`Voz` + `OST` com sidechain -14dB + `Foley CC0`) normalizada a -14 LUFS EBU R128.
11. **ADR-11: Fallback Cinemático MiniMax H3 via Nó FeiHou #107 sem Watermark**: Workflow `2118560390471745537` na Conta 7 (`#35` prompt, `#48` referência, `#66` duração), extração obrigatória pelo nó `#107` (`FeiHouVideoPreview`) com áudio AAC sem watermark e cancelamento atômico pós-gravação.

---

##  Licença

Distribuído sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.
