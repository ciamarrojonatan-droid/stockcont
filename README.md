# StockCont 📈🤖

> **Plataforma Autônoma Industrial de Inteligência Preditiva de Mercado, Engenharia Reversa Multimodal, Produção Generativa 4K/8K, Pipeline de Vídeo Cinematográfico, Catalogação Binária IPTC/EXIF/MP4, Gestão de Cotas Deslizantes (Rolling 7D), Daemon 24/7 com Auto-Purga de SSD, Distribuição Multi-Agência e Dashboard Web SPA iOS 27 Liquid Glass.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Pytest-131_Passed_100%25-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Gemini Multimodal](https://img.shields.io/badge/Google_Gemini-Multimodal_Vision_v3.0-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![ComfyUI Dual RPA](https://img.shields.io/badge/ComfyUI-Dual_Account_RPA-FF6F00?style=for-the-badge&logo=blender&logoColor=white)](https://www.runninghub.ai/)
[![Video Pipeline](https://img.shields.io/badge/Video-4K_I2V_%26_ProRes-E11D48?style=for-the-badge&logo=quicktime&logoColor=white)](https://ffmpeg.org/)
[![Metadata](https://img.shields.io/badge/Metadata-Binary_IPTC_%26_EXIF_%26_MP4-8A2BE2?style=for-the-badge)](https://iptc.org/)
[![UI Design](https://img.shields.io/badge/Design_System-iOS_27_Liquid_Glass-007AFF?style=for-the-badge&logo=apple&logoColor=white)](https://developer.apple.com/design/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 📑 Sumário Executivo

1. [Visão Geral do Sistema](#-visão-geral-do-sistema)
2. [Arquitetura de Alto Nível & Topologia da Esteira](#-arquitetura-de-alto-nível--topologia-da-esteira)
3. [Dashboard Web SPA Local (iOS 27 Liquid Glass)](#-dashboard-web-spa-local-ios-27-liquid-glass)
4. [Detalhamento Técnico das Fases do Pipeline](#-detalhamento-técnico-das-fases-do-pipeline)
   - [Fase 1: O Olheiro Preditivo (Radar Sazonal D+75, Saturation Index & Hydrator)](#fase-1-o-olheiro-preditivo-radar-sazonal--saturation-index)
   - [Fase 2: O Diretor de Arte v3.0 (Prompts de 700–1.000 Palavras & Copy-Space)](#fase-2-o-diretor-de-arte-v30-prompts-de-7001000-palavras--copy-space)
   - [Pipeline de Vídeo Cinematográfico (Fases 1 a 5 de Vídeo)](#-pipeline-de-vídeo-cinematográfico-fases-1-a-5-de-vídeo)
   - [Fase 3: A Fábrica RPA Dual-Account (Conta 1 Raw Producer & Conta 2 SeedVR 8K)](#fase-3-a-fábrica-rpa-dual-account)
   - [Módulo QC: Curadoria Multimodal & Prevenção OOM](#-módulo-qc-curadoria-multimodal--prevenção-oom)
   - [Fase 4: O Catalogador (300 DPI, Injeção IPTC/EXIF/MP4 & CSV Incremental)](#fase-4-o-catalogador-300-dpi-injeção-binária-iptcexif-mp4--csv)
   - [Fase 5: O Distribuidor com Cotas Deslizantes (Rolling 7D)](#fase-5-o-distribuidor-com-cotas-deslizantes-rolling-7d)
   - [O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)](#-o-cofre-cloud-google-drive--auto-purga-inteligente-de-ssd)
   - [Motor Autônomo 24/7 (Daemon Supervisor & Watchdog Windows)](#-motor-autônomo-247-daemon-supervisor--watchdog-windows)
5. [Orquestrador Mestre CLI (`main.py`) & Scripts de Execução](#-orquestrador-mestre-cli-mainpy--scripts-de-execução)
6. [Estrutura do Repositório & Gestão de Dados](#-estrutura-do-repositório--gestão-de-dados)
7. [Contratos de Dados (Data Schemas v3.0)](#-contratos-de-dados-data-schemas-v30)
8. [Matriz Estratégica Multi-Agência & Proteção Anti-Ban Alamy](#-matriz-estratégica-multi-agência--proteção-anti-ban-alamy)
9. [Instalação, Configuração & Execução](#-instalação-configuração--execução)
10. [Resiliência Operacional & Decisões de Engenharia (ADRs)](#-resiliência-operacional--decisões-de-engenharia-adrs)

---

## 🔭 Visão Geral do Sistema

O **StockCont** é um ecossistema autônomo industrial de inteligência preditiva de dados, engenharia reversa multimodal e automação robótica (RPA) projetado para cobrir o ciclo comercial completo de ativos digitais criados por inteligência artificial (imagens 4K/8K e vídeos cinematográficos) para as principais plataformas mundiais de **microstock** (Adobe Stock, Freepik, 123RF, Dreamstime, Pond5, Vecteezy, Ingram Image).

Operando como um **fundo quantitativo de ativos digitais de alta demanda**, o sistema elimina o empirismo e a operação manual:
1. **Antecipa Janelas Comerciais B2B (D+75 dias)**: Calcula dinamicamente as datas de compra das corporações globais via **Seasonal Forecasting Radar** e audita a densidade de concorrentes com o **Niche Saturation Index** para atacar nichos *Blue Ocean*.
2. **Engenharia Reversa Visual Multimodal v3.0**: Dissecciona as referências mais vendidas do mundo via Gemini Vision e sintetiza **prompts de 700 a 1.000 palavras**, aplicando leis de iluminação Kelvin, física de materiais (dispersão subsuperficial, reflexos de Fresnel) e **Copy-Space adaptativo** (35% a 50% de espaço negativo para design editorial e corporativo).
3. **Pipeline Industrial de Vídeo**: Multiplicador Image-to-Video (I2V) com síntese temporal 4D (500 a 800 palavras), geração em 16:9 Landscape e 9:16 Vertical Reels, motor de loops contínuos sem emendas, stripping obrigatório de áudio (`-an`) e masterização em Apple ProRes 422 HQ e MP4.
4. **Fábrica RPA Dual-Account no RunningHub ComfyUI**:
   - **Conta 1 (Raw Producer)**: 42 nós `PromptList` simultâneos, renderizando até 210 prompts por lote na janela de 40 minutos com saída no nó #121.
   - **Curadoria Multimodal (QC)**: Auditoria visual via Gemini Vision com empacotamento em zips de 10 (`approved_batch.zip`) para evitar estouro de memória (OOM).
   - **Conta 2 (SeedVR 8K Upscaler)**: Ingestão de zips no nó #5 e preview 1 a 1 no nó #55, com cancelamento atômico pós-última imagem renderizada.
5. **Catalogação Binária Física (IPTC / EXIF / MP4 Atoms) & 300 DPI**: Grava metadados definitivos nos bytes das imagens e vídeos, garantindo preenchimento automático de 100% dos campos ao submeter nas agências.
6. **Gestor de Cotas Deslizantes (Rolling 7-Day Quotas)**: Monitora os limites semanais de submissão por agência, despacha lotes de forma seletiva e calcula contagem regressiva para liberação de novas vagas.
7. **Produção Contínua 24/7 com Auto-Purga Inteligente de SSD**: Daemon com heartbeat atômico e watchdog Windows (`run_24_7.bat`). Mantém cofre em nuvem no Google Drive e remove ativos pesados do disco local somente após envio garantido a todas as agências ativas.
8. **Centro de Comando Web SPA no Estilo Apple iOS 27 Liquid Glass**: Interface moderna com tokens HIG, vidros translúcidos, controles segmentados, telemetria em tempo real, monitor de cotas semanais e galeria com inspeção binária IPTC/EXIF.

---

## 🏗 Arquitetura de Alto Nível & Topologia da Esteira

```mermaid
flowchart TD
    subgraph S1["Fase 1: Olheiro Preditivo & Scout"]
        A1["Seasonal Forecasting Radar<br/>(Janela D+75 dias)"] --> B1["Niche Saturation Analyzer<br/>(Blue Ocean Scoring)"]
        B1 --> C1["Adobe Stock Contributor Scraper<br/>(Playwright Headless/Headed)"]
        C1 --> D1["Concurrent Reference Hydrator<br/>(src/scraper/hydrator.py)"]
        D1 --> E1[("data/raw/trends.json<br/>+ data/raw/images/")]
    end

    subgraph S2["Fase 2: O Diretor de Arte v3.0"]
        E1 --> F2["Gemini Vision Director v3.0<br/>(6 Camadas & Copy-Space)"]
        F2 --> G2[("data/processed/prompts.json<br/>(700-1000 Palavras / Prompt)")]
        E1 --> F2V["Video Director 4D Temporal<br/>(src/analyzer/video_director.py)"]
        F2V --> G2V[("data/processed/video_prompts.json<br/>(500-800 Palavras / 16:9 & 9:16)")]
    end

    subgraph S3["Fase 3: A Fábrica RPA Dual-Account"]
        G2 --> H3["PromptQueueManager (SHA-256)"]
        H3 --> I3["Conta 1: Raw Producer<br/>(42 nós PromptList / até 210 prompts)"]
        I3 --> J3[("data/staging/images/<br/>(Renders 4K Brutos)")]
        J3 --> K3["Gemini Vision QC Inspector<br/>(Curadoria & Empacotamento Zip de 10)"]
        K3 --> L3["Conta 2: SeedVR 8K Upscaler<br/>(Ingestão Zip #5 ➔ Preview #55)"]
        L3 --> M3[("data/final/images/<br/>(JPGs 8K Master)")]
    end

    subgraph S4["Fase 4: O Catalogador & Conformidade"]
        M3 --> N4["Mastering 300 DPI + IPTC/EXIF<br/>(iptcinfo3 + piexif)"]
        G2V --> N4V["Video Cataloger & FFmpeg Engine<br/>(Mudo -an + Metadados MP4/MOV)"]
        N4 --> O4["Validação de Conformidade Técnica<br/>(src/cataloger/platform_compliance.py)"]
        N4V --> O4
        O4 --> P4[("adobe_stock_upload.csv<br/>+ pond5_upload.csv")]
    end

    subgraph S5["Fase 5: Distribuidor, Cotas & O Cofre"]
        O4 --> Q5["Rolling 7D Quota Manager<br/>(src/uploader/quota_manager.py)"]
        Q5 --> R5["Despacho Multi-Agência SFTP/FTP<br/>(Adobe, Freepik, 123RF, Pond5...)"]
        Q5 -.->|Bloqueio Anti-Ban ADR-05| BLK["⛔ ALAMY (Bloqueio IA Ativo)"]
        O4 --> S5["Cofre Cloud Google Drive<br/>(src/backup/gdrive_backup.py)"]
        R5 & S5 --> T5["Auto-Purga Inteligente do SSD<br/>(Libera disco pós-distribuição 100%)"]
    end

    subgraph S6["Módulo Supervisor 24/7 & Telemetria"]
        U6["Daemon 24/7 Supervisor<br/>(src/orchestrator/daemon.py)"] -.-> S1 & S2 & S3 & S4 & S5
        U6 --> V6["Watchdog Windows (run_24_7.bat)<br/>+ Task Scheduler"]
        U6 --> W6["Dashboard Web SPA (FastAPI)<br/>Estilo Apple iOS 27 Liquid Glass"]
    end
```

---

## 🖥️ Dashboard Web SPA Local (iOS 27 Liquid Glass)

O StockCont conta com uma aplicação web moderna em Single-Page Application (FastAPI), com arquitetura reativa, streaming de logs via Server-Sent Events (SSE) e design unificado no padrão **Apple iOS 27 Liquid Glass** (HIG Design Tokens):

* **Superfície Transparente & Blur Vibrante**: Fundo em `#1C1C1E` e `#2A2A2C`, bordas sutis com gradientes lineares especulares e cantos arredondados contínuos (*continuous squircle*).
* **Controles Segmentados em Cápsula (`.pickerStyle(.tabs)`)**: Alternância ultra-fluida entre abas com transições refinadas e estado ativo destacado em azul iOS (`#007AFF` e `#0088FF`).
* **KPI Cards em Inset Grouped**: 6 cartões de métricas em tempo real (Tendências mineradas, Prompts prontos, Fila ComfyUI, Assets em disco, Catalogados com IPTC e Uploads confirmados).
* **Nova Aba "🤖 Produção 24/7"**:
  - Hero Card de estado do Daemon com badge pulsante (🟢 Rodando 24/7 / ⏹️ Parado).
  - Telemetria do Cofre: Assets em disco, engatilhados, 100% distribuídos, no Google Drive e purgados do SSD.
  - Monitor de Cotas Semanais (Rolling 7D) com barras de progresso coloridas por plataforma e contagem regressiva para liberação de novas vagas.
  - Botões de Ação Rápida: Iniciar em Background, Abrir Janela Console Supervisionada (`run_24_7.bat`) e Parar.
* **Galeria de Ativos com Modal IPTC/EXIF**: Grid responsivo com carregamento sob demanda. O clique em qualquer imagem inspeciona instantaneamente as tags IPTC, dimensões, resolução em DPI e conformidade gravada no cabeçalho binário.
* **Radar Sazonal Interativo**: Painel de micro-nichos calculados para a janela D+75 com botão `🚀 Minerar este Nicho` em 1 clique.

Para iniciar o Dashboard:
```bash
python main.py --dashboard
```
*Acesse no navegador:* `http://localhost:8501`

---

## 🔬 Detalhamento Técnico das Fases do Pipeline

### Fase 1: O Olheiro Preditivo (*Radar Sazonal & Saturation Index*)
* **Módulos Centrais**: [`src/scraper/adobe_stock.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/scraper/adobe_stock.py), [`src/analyzer/seasonal_radar.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/analyzer/seasonal_radar.py), [`src/analyzer/saturation_index.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/analyzer/saturation_index.py), [`src/scraper/hydrator.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/scraper/hydrator.py)
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

* 🟢 **Blue Ocean** ($\text{Score} \ge 0.025$): Alta demanda e baixa concorrência. Produção imediata.
* 🟡 **Competição Moderada** ($0.005 \le \text{Score} < 0.025$): Exige forte diferenciação estética e copy-space.
* 🔴 **Red Ocean** ($\text{Score} < 0.005$): Nicho saturado. O sistema recomenda refinar a busca.

#### 3. Concurrent Reference Hydrator (`--sync-raw`)
Módulo com pool de threads para download concorrente de miniaturas de referência listadas em `trends.json` que estejam pendentes em disco.

---

### Fase 2: O Diretor de Arte v3.0 (*Prompts de 700–1.000 Palavras & Copy-Space*)
* **Módulo Central**: [`src/analyzer/director.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/analyzer/director.py)
* **Objetivo**: Engenharia reversa visual via Gemini Vision e produção de **exatamente 10 prompts cinematográficos ultra-densos (700 a 1.000 palavras por prompt)** com **Copy-Space adaptativo** (35% a 50% de espaço limpo).

#### As 6 Camadas Mandatórias do Prompt v3.0:
1. **Spatial Architecture & Narrative Staging (120–150 palavras)**: Coordenadas espaciais tridimensionais, profundidade de campo, enquadramento de primeiro plano e sujeito em plano médio.
2. **Physical Materiality & Micro-Textures (120–150 palavras)**: Dispersão subsuperficial (*SSS*) em tecidos e pele, micro-arranhões em metais escovados, reflexos Fresnel em vidros arquitetônicos e partículas atmosféricas.
3. **Multi-Point Lighting Kelvin Architecture (120–150 palavras)**: Configuração de estúdio e sol, relação entre luz principal (*Key*), luz de preenchimento difusa (*Fill*), contorno (*Rim/Kicker*) e temperatura de cor precisa em Kelvin (ex: 3200K tungstênio vs 5600K daylight).
4. **Optical Camera & Lens Fingerprint (100–130 palavras)**: Assinatura óptica de lentes de cinema (35mm, 50mm, 85mm), aberturas físicas (f/1.4, f/2.8), curvatura de foco suave, bokeh esférico e granulação tátil.
5. **Adaptive Copy-Space & Graphic Usability (120–150 palavras)**: Reserva intencional de 35% a 50% do enquadramento como área negativa limpa para inserção de títulos por designers gráficos.
6. **Commercial Buyer Intent & Compliance (100–120 palavras)**: Modelagem orientada a personas B2B (`saas_landing_page`, `ad_agency_hero`, `corporate_annual_report`) e conforms legais livres de marcas comerciais.

---

### 🎬 Pipeline de Vídeo Cinematográfico (Fases 1 a 5 de Vídeo)
* **Módulos Centrais**: [`src/video/ffmpeg_processor.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/video/ffmpeg_processor.py), [`src/video/video_metadata.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/video/video_metadata.py), [`src/analyzer/video_director.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/analyzer/video_director.py), [`src/cataloger/video_cataloger.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/cataloger/video_cataloger.py)
* **Objetivo**: Produzir e distribuir clipes de vídeo em movimento (I2V) a partir de imagens de alta fidelidade para monetização em vídeo no Adobe Stock Video e Pond5.

#### Destaques de Engenharia do Pipeline de Vídeo:
* **Diretor de Fotografia de Vídeo (Fase 2 de Vídeo)**: Gera prompts cinemáticos de 500 a 800 palavras especializados em cinemática de câmera (*dolly forward*, *orbital pan*, *subtle crane up*) para proporções 16:9 Landscape e 9:16 Vertical Reels.
* **FFmpeg Probing & Conformidade Técnica**: Audita codecs, duração (5 a 60 segundos), framerates comerciais (23.976, 25, 29.97, 30 fps) e resolução 4K/FHD.
* **Seamless Loop Engine**: Análise e crossfade de bordas para geração de vídeos em loop perfeito.
* **Remoção Mandatória de Áudio (`-an`)**: Microstocks rejeitam sumariamente vídeos com ruído residual de IA; o StockCont aplica stripping garantido de streams de áudio.
* **Gravação de Metadados em Átomos QuickTime/MP4**: Título comercial, descrição e tags injetados diretamente na estrutura do container de vídeo.
* **Masterização Apple ProRes 422 HQ**: Exportação em ProRes via switch `--prores` para compradores de alto valor no Pond5.

Comandos CLI de Vídeo:
```bash
# Executar Diretor de Vídeo (Fase 2 de Vídeo):
python main.py --video --phase 2

# Executar Catalogador de Vídeo (Fase 4 de Vídeo):
python main.py --video --phase 4

# Catalogar com geração de Apple ProRes 422 HQ para Pond5:
python main.py --video --phase 4 --prores

# Distribuição de Vídeos:
python main.py --video --phase 5 --platform pond5
```

---

### Fase 3: A Fábrica RPA Dual-Account
* **Módulos Centrais**: [`src/factory/runninghub_bot.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/factory/runninghub_bot.py), [`src/factory/prompt_queue.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/factory/prompt_queue.py), [`src/factory/stealth_profile.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/factory/stealth_profile.py)
* **Objetivo**: Operação industrial do ComfyUI no RunningHub com segregação em duas contas de execução para máxima vazão e custo-benefício.

#### 1. Topologia da Conta 1 (Raw Producer - 210 Prompts por Lote)
* **Workflow 2113606426114670593**: 42 nós `PromptList` simultâneos (#128, #129, #130, #131, #204, #218, #224, #223, etc.), injetando 5 prompts por nó = **210 prompts por lote** dentro da janela de 40 minutos do RunningHub.
* **Captura no Nó #121**: Monitoramento do nó de saída para download dos renders brutos em `data/staging/images/`.

#### 2. Topologia da Conta 2 (SeedVR 8K Upscaler)
* **Ingestão Zip no Nó #5**: Ingestão de pacotes curados de 10 imagens.
* **Preview Instantâneo no Nó #55**: Captura 1 a 1 dos renders em 8K diretamente para `data/final/images/`.
* **Cancelamento Atômico**: Cancela a tarefa excedente na fila imediatamente após a última imagem ser renderizada, poupando créditos de GPU.

#### 3. Fila Criptográfica com Hashing SHA-256
* Cada prompt tem seu hash canônico gerado e mantido em `data/processed/generation_history.json`.
* Idempotência garantida: Prompts idênticos jamais são regerados em caso de reinicialização.

---

### 🔍 Módulo QC: Curadoria Multimodal & Prevenção OOM
* **Módulo Central**: [`src/analyzer/qc_inspector.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/analyzer/qc_inspector.py)
* **Auditoria Visual via Gemini Vision**: Inspeciona as imagens geradas pela Conta 1 contra deformações anatômicas, artefatos visuais ou texto distorcido.
* **Empacotamento em Lotes de 10 (`approved_batch.zip`)**: Agrupa apenas imagens aprovadas em zips leves de exatamente 10 unidades, prevenindo estouro de VRAM na GPU durante o upscale 8K da Conta 2.
* Comandos CLI:
  ```bash
  python main.py --qc --qc-mode auto
  python main.py --upscale
  ```

---

### Fase 4: O Catalogador (300 DPI, Injeção Binária IPTC/EXIF/MP4 & CSV)
* **Módulos Centrais**: [`src/cataloger/adobe_csv_maker.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/cataloger/adobe_csv_maker.py), [`src/cataloger/platform_compliance.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/cataloger/platform_compliance.py), [`src/cataloger/reembed_compliance.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/cataloger/reembed_compliance.py)
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
* **Módulos Centrais**: [`src/uploader/ftp_distributor.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/uploader/ftp_distributor.py), [`src/uploader/quota_manager.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/uploader/quota_manager.py)
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

### ☁️ O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)
* **Módulo Central**: [`src/backup/gdrive_backup.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/backup/gdrive_backup.py)
* **Backup no Google Drive**: Sincronização automática para `G:\Meu Drive\StockCont_backup` com livro-razão `gdrive_backup_history.json`.
* **Auto-Purga Inteligente de SSD**: Ativos gerados em 8K ocupam espaço significativo em disco. O StockCont remove com segurança o arquivo do SSD local **apenas quando duas condições simultâneas forem satisfeitas**:
  1. Confirmação registrada de backup no Google Drive.
  2. Confirmação de upload com sucesso em **todas** as agências ativas configuradas.
* **Restauração Completa (`--restore`)**: Recupera todo o catálogo, CSVs e históricos a partir do Google Drive caso necessário.

---

### 🤖 Motor Autônomo 24/7 (Daemon Supervisor & Watchdog Windows)
* **Módulo Central**: [`src/orchestrator/daemon.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/orchestrator/daemon.py)
* **Loop Contínuo Pipelined**:
  1. **Buffer de Prompts**: Monitora a fila; se pendentes < 50, dispara automaticamente as Fases 1 e 2.
  2. **Conta 1 (Raw Producer)**: Renderiza lotes de até 210 prompts no RunningHub ComfyUI.
  3. **QC Multimodal**: Audita via Gemini Vision e agrupa aprovados em zips de 10.
  4. **Conta 2 (SeedVR 8K)**: Renderiza upscales 8K dos zips.
  5. **Fase 4**: Cataloga IPTC/EXIF 300 DPI e salva no Cofre Google Drive.
  6. **Fase 5**: Despacha assets respeitando as cotas deslizantes.
  7. **Auto-Purga**: Libera o SSD de ativos 100% distribuídos e salvos em nuvem.
* **Resiliência Máxima**:
  - Heartbeat atômico persistido em `data/processed/daemon_state.json`.
  - Pacing sleep responsivo (padrão 300s) com interrupção instantânea sob comando.
  - **`run_24_7.bat`**: Watchdog do Windows que captura crashes e reinicia a esteira em 30 segundos.
  - **`scripts/setup_windows_task.ps1`**: Registra o daemon no Agendador de Tarefas do Windows para inicialização automática no logon do sistema.

---

## 🎮 Orquestrador Mestre CLI (`main.py`) & Scripts de Execução

```bash
# ==========================================
# DASHBOARD WEB SPA (iOS 27 LIQUID GLASS)
# ==========================================
# Iniciar servidor local (http://localhost:8501):
python main.py --dashboard

# Iniciar dashboard em background sem abrir o navegador:
python main.py --dashboard --no-browser --port 8501

# ==========================================
# STATUS DO PIPELINE & COTAS SEMANAIS
# ==========================================
# Exibir telemetria completa de todas as fases, cofre e daemon:
python main.py --status

# Exibir relatório visual das cotas deslizantes (Rolling 7D):
python main.py --quotas

# Exibir previsão do Radar Sazonal (D+75 dias) e nichos Blue Ocean:
python main.py --seasonal

# ==========================================
# PRODUÇÃO CONTÍNUA 24/7 & WATCHDOG
# ==========================================
# Executar o daemon supervisor contínuo:
python main.py --daemon

# Iniciar via script supervisor watchdog do Windows (auto-restart após falhas):
.\run_24_7.bat

# ==========================================
# FASE 1: OLHEIRO (SCRAPER & DEMANDA)
# ==========================================
# Minerar Contributor Insights dos Top Sellers mundiais:
python main.py --phase 1 --mode insights --type photo --max-items 20

# Minerar com perfil aprofundado dos maiores contribuidores:
python main.py --phase 1 --mode insights --deep-profile --max-items 30

# Buscar por palavra-chave pública ordenada por downloads:
python main.py --phase 1 --mode search --query "biotech longevity laboratory" --order nb_downloads --max-items 15

# Baixar miniaturas de referências pendentes concorrentemente:
python main.py --sync-raw

# ==========================================
# FASE 2: DIRETOR DE ARTE v3.0 (700-1000 PALAVRAS)
# ==========================================
python main.py --phase 2

# ==========================================
# PIPELINE DE VÍDEO CINEMATOGRÁFICO
# ==========================================
# Diretor de Fotografia de Vídeo (Fase 2 de Vídeo):
python main.py --video --phase 2

# Catalogador de Vídeo (Fase 4 de Vídeo - Mudo -an + Metadados QuickTime/MP4):
python main.py --video --phase 4

# Catalogador com masterização Apple ProRes 422 HQ para Pond5:
python main.py --video --phase 4 --prores

# ==========================================
# FASE 3: A FÁBRICA RPA DUAL-ACCOUNT (RUNNINGHUB)
# ==========================================
# Conta 1 (Raw Producer - Lote de até 210 prompts):
python main.py --phase 3 --account 1 --batch-size 210

# Conta 1 via batch script de conveniência:
.\run_conta1.bat

# Curadoria Visual QC (Gemini Vision):
python main.py --qc --qc-mode auto

# Conta 2 (SeedVR 8K Upscaler em packs de 10):
python main.py --phase 3 --account 2 --batch-size 10
# ou simplesmente:
python main.py --upscale
.\run_conta2.bat

# ==========================================
# FASE 4: O CATALOGADOR (IPTC/EXIF/300 DPI)
# ==========================================
python main.py --phase 4

# ==========================================
# O COFRE: BACKUP & RESTORE GOOGLE DRIVE
# ==========================================
# Executar backup manual para o Google Drive:
python main.py --backup

# Restaurar catálogo completo a partir do Google Drive:
python main.py --restore

# ==========================================
# FASE 5: DISTRIBUIÇÃO MULTI-AGÊNCIA
# ==========================================
# Simulação de envio (teste de conexões e cotas sem transferir):
python main.py --phase 5 --dry-run

# Upload para todas as agências com cotas livres:
python main.py --phase 5 --platform all

# Upload específico (ex: adobe, pond5, freepik, 123rf):
python main.py --phase 5 --platform adobe
```

---

## 📂 Estrutura do Repositório & Gestão de Dados

```text
stockcont/
├── .env                              # Variáveis de ambiente (GEMINI_API_KEY, CREDENCIAIS FTP/SFTP)
├── .env.example                      # Template de configuração
├── main.py                           # Orquestrador CLI Mestre e Ponto de Entrada Unificado
├── README.md                         # Documentação técnica e arquitetura do projeto
├── PROJECT_CONTEXT.md                # Single Source of Truth (SSOT) para agentes autônomos
├── CLAUDE.md                         # Instruções operacionais para Claude Code
├── AGENTS.md                         # Protocolo de orquestração e mandatos de autonomia
├── requirements.txt                  # Dependências Python travadas
├── state.md                          # Quadro vivo de estado e telemetria das sprints
├── run_24_7.bat                      # Script watchdog Windows para produção contínua 24/7
├── run_conta1.bat                    # Atalho de execução para Conta 1 (Raw Producer 210 prompts)
├── run_conta2.bat                    # Atalho de execução para Conta 2 (SeedVR 8K Upscaler)
├── start.bat                         # Atalho de inicialização do Dashboard Web SPA
│
├── chrome_session/                   # Sessão persistente do Chrome para Scraper (Fase 1)
├── playwright_session/               # Sessão persistente para RPA RunningHub (Fase 3)
│
├── data/
│   ├── raw/
│   │   ├── trends.json               # Dados minerados da Fase 1 (títulos, links, IDs)
│   │   └── images/                   # Miniaturas de referências mais vendidas
│   ├── staging/
│   │   ├── images/                   # Renders 4K brutos da Conta 1 aguardando QC
│   │   └── packs/                    # Zips curados de 10 imagens para Conta 2 (SeedVR 8K)
│   ├── processed/
│   │   ├── prompts.json              # Prompts comerciais de imagens (700-1000 palavras)
│   │   ├── video_prompts.json        # Prompts cinematográficos de vídeo (500-800 palavras)
│   │   ├── generation_history.json   # Livro-razão criptográfico SHA-256 da Fábrica
│   │   ├── upload_history.json       # Livro-razão de envios multi-agência com timestamps
│   │   ├── gdrive_backup_history.json# Histórico atômico de sincronização com Google Drive
│   │   ├── daemon_state.json         # Heartbeat em tempo real do Daemon 24/7
│   │   ├── adobe_stock_upload.csv    # Planilha de metadados e backup para Adobe Stock
│   │   └── pond5_upload.csv          # Planilha de metadados para Pond5 Video
│   └── final/
│       ├── images/                   # Imagens 8K catalogadas prontas com metadados IPTC/EXIF
│       ├── videos/                   # Vídeos MP4/ProRes prontos com átomos e áudio mudo
│       └── rejected/                 # Imagens reprovadas na auditoria QC do Gemini Vision
│
├── src/
│   ├── analyzer/
│   │   ├── director.py               # Fase 2: Diretor de Arte (Prompts 700-1000 palavras)
│   │   ├── video_director.py         # Fase 2 de Vídeo: Diretor 4D Temporal (16:9 & 9:16)
│   │   ├── qc_inspector.py           # Curadoria Visual Multimodal via Gemini Vision
│   │   ├── seasonal_radar.py         # Motor de Previsão de Demanda Sazonal (D+75 dias)
│   │   └── saturation_index.py       # Analisador de Saturação de Mercado (Blue Ocean)
│   ├── backup/
│   │   └── gdrive_backup.py          # O Cofre: Backup e Restore no Google Drive
│   ├── cataloger/
│   │   ├── adobe_csv_maker.py        # Fase 4: Catalogador de Imagens (IPTC/EXIF/300 DPI)
│   │   ├── video_cataloger.py        # Fase 4 de Vídeo: Catalogador (Átomos MP4 & ProRes)
│   │   ├── platform_compliance.py    # Motor de Validação Técnica e Bloqueio Anti-Ban
│   │   └── reembed_compliance.py     # Utilitário de regravação em lote de metadados
│   ├── dashboard/
│   │   ├── app.py                    # Servidor FastAPI e rotas REST do Dashboard
│   │   ├── readers.py                # Leitores seguros e atômicos de telemetria
│   │   ├── runner.py                 # Executor assíncrono de fases via subprocess
│   │   ├── schemas.py                # Contratos Pydantic de dados da interface
│   │   └── static/                   # SPA Frontend (HTML, CSS iOS 27 Liquid Glass, JS)
│   ├── factory/
│   │   ├── prompt_queue.py           # Gestor de Fila com Hashing SHA-256 e Topologias
│   │   ├── runninghub_bot.py         # Fase 3: A Fábrica RPA ComfyUI (Dual-Account)
│   │   └── stealth_profile.py        # Perfis anti-detecção e resiliência a popups
│   ├── orchestrator/
│   │   └── daemon.py                 # Daemon 24/7 Supervisor com Auto-Purga de SSD
│   ├── scraper/
│   │   ├── adobe_stock.py            # Fase 1: Olheiro Playwright (Insights & Busca)
│   │   └── hydrator.py               # Download concorrente multi-thread de referências
│   ├── uploader/
│   │   ├── ftp_distributor.py        # Fase 5: Distribuidor SFTP/FTP Multi-Agência
│   │   └── quota_manager.py          # Gestor de Cotas Semanais Deslizantes (Rolling 7D)
│   └── video/
│       ├── ffmpeg_processor.py       # Probing FFmpeg, áudio mudo (-an) e ProRes
│       └── video_metadata.py         # Injeção binária em átomos MP4 e QuickTime
│
├── scripts/
│   ├── setup_windows_task.ps1        # Registro no Agendador de Tarefas do Windows
│   └── run_pipeline.bat              # Script auxiliar para execução de pipeline
│
└── tests/
    ├── test_cataloger.py              # Testes de gravação IPTC/EXIF e 300 DPI
    ├── test_daemon.py                 # Testes do loop contínuo e auto-purga de SSD
    ├── test_dashboard.py              # Testes da API REST e endpoints do Dashboard
    ├── test_director.py               # Testes do gerador de prompts 700-1000 palavras
    ├── test_distributor.py            # Testes de conexão SFTP/FTP multi-agência
    ├── test_gdrive_backup.py          # Testes de sincronização do Google Drive
    ├── test_hydrator.py               # Testes do downloader concorrente de referências
    ├── test_matrix.py                 # Testes da matriz de distribuição e políticas
    ├── test_pipeline_e2e.py           # Testes de integração de ponta a ponta
    ├── test_platform_compliance.py    # Testes de conformidade e bloqueio anti-ban Alamy
    ├── test_predictive_intelligence.py# Testes do Radar Sazonal e Saturation Index
    ├── test_prompt_queue.py           # Testes do gestor de fila e livro-razão SHA-256
    ├── test_qc_pipeline.py            # Testes de curadoria multimodal e zips de 10
    ├── test_quota_manager.py          # Testes da janela deslizante de 7 dias de cotas
    ├── test_stealth_profile.py        # Testes de evasão de bot e resiliência a popups
    └── test_video_pipeline.py         # Testes do motor de vídeo FFmpeg e metadados MP4
```

---

## 📄 Contratos de Dados (Data Schemas v3.0)

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

## 🌐 Matriz Estratégica Multi-Agência & Proteção Anti-Ban Alamy

| Plataforma | Protocolo | Tipo de Ativo | Política de IA | Gestão no StockCont |
| :--- | :--- | :--- | :--- | :--- |
| **Adobe Stock** | SFTP | Imagens 8K & Vídeos | ✅ Aceito *(Tag IA requerida)* | Suporte nativo / Lê IPTC e átomos MP4 |
| **Freepik Contributor** | FTP | Imagens 8K | ✅ Aceito em escala massiva | Suporte nativo / Despacho com cotas |
| **Dreamstime** | FTP | Imagens 8K | ✅ Aceito *(IA no Caption)* | Suporte nativo / Pré-formatação de texto |
| **Pond5** | FTP | Vídeos 4K & ProRes | ✅ Aceito *(Preço customizável)*| Suporte nativo / Apple ProRes 422 HQ |
| **123RF** | FTP | Imagens 8K | ✅ Aceito | Suporte nativo / Gestor de cotas |
| **Vecteezy** | FTP | Imagens & Vetores | ✅ Aceito | Suporte nativo / Leitura IPTC |
| **Ingram Image** | FTP | Imagens 8K | ✅ Aceito | Suporte nativo / Gestor de cotas |
| **Alamy** | SFTP/FTP | Imagens & Vídeos | ⛔ **TERMINANTEMENTE PROIBIDO PARA IA** | 🛡️ **BLOQUEIO ATIVO ANTI-BAN (ADR-05)** |

> ### ⚠️ ALERTA MANDATÓRIO DE COMPLIANCE — ALAMY (ADR-05)
> A **Alamy proíbe terminantemente qualquer conteúdo gerado por IA** (Seção 1.3 do Contrato de Contribuinte). Submeter IA à Alamy acarreta **banimento sumário da conta e perda definitiva de todos os rendimentos acumulados**.
> O StockCont possui proteção ativa em [`src/cataloger/platform_compliance.py`](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta/stockcont/src/cataloger/platform_compliance.py) que **bloqueia programaticamente qualquer tentativa de upload de asset IA para a Alamy**, exibindo aviso no console e mantendo o contribuinte seguro.

---

## 🚀 Instalação, Configuração & Execução

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
* `GEMINI_API_KEY`: Chave da API do Google Gemini.
* `RUNNINGHUB_ACCOUNT1_API_KEY`: Credencial da Conta 1 (Raw Producer).
* `RUNNINGHUB_ACCOUNT2_API_KEY`: Credencial da Conta 2 (SeedVR 8K).
* Credenciais de SFTP/FTP das agências (Adobe, Freepik, 123RF, Pond5, etc.).
* `GDRIVE_BACKUP_PATH`: Caminho da pasta local do Google Drive (ex: `G:\Meu Drive\StockCont_backup`).

### 4. Executando a Suíte de Testes
```bash
.\venv\Scripts\pytest
```
*Resultado esperado:* **131 passed (100% verde)**.

---

## 🛡 Resiliência Operacional & Decisões de Engenharia (ADRs)

1. **ADR-01: Blindagem de Encoding UTF-8 em Windows**: Todo I/O de console, rede e persistência é forçado para UTF-8 no bootstrap de `main.py` e utilitários, neutralizando falhas crônicas de `cp1252` em terminais Windows.
2. **ADR-02: Escrita Atômica Transacional com `.tmp`**: Todos os arquivos JSON críticos (`prompts.json`, `trends.json`, `generation_history.json`, `upload_history.json`, `daemon_state.json`) são serializados primeiramente em arquivos temporários `.tmp` com identificadores únicos de processo e substituídos atomicamente via `os.replace()`.
3. **ADR-03: Fila Criptográfica Idempotente com Hashing SHA-256**: Cada prompt gera um hash canônico SHA-256 único a partir de seu texto normalizado, impedindo regerações duplicadas e economizando custos e tempo de GPU.
4. **ADR-04: Reconhecimento Híbrido (Dual-Source) IPTC vs CSV**: O Catalogador executa ambas as ações simultaneamente: injeta tags IPTC/EXIF fisicamente nos bytes do arquivo e anexa a linha correspondente na planilha CSV.
5. **ADR-05: Proteção Ativa Anti-Ban Multi-Agência (Alamy)**: Bloqueio programático irrestrito para impedir qualquer upload de assets gerados por IA para a Alamy, preservando a conta do contribuinte contra sanções contratuais.
6. **ADR-06: Segregação Dual-Account RPA & Prevenção OOM**: Separação física entre a Conta 1 (geração bruta de até 210 prompts por lote) e a Conta 2 (upscale 8K em pacotes curados de 10 imagens), garantindo estabilidade de hardware e economia máxima de créditos.
7. **ADR-07: Auto-Purga Segura com Cofre Híbrido**: O arquivo pesado é purgado do SSD local exclusivamente após o upload com sucesso em todas as agências ativas e a confirmação registrada de backup no Google Drive.

---

## 📜 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.
