# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: DarkFactory Cinema Dashboard — Autonomous Faceless YouTube Studio (:8502) & Cross-Link StockCont (:8501)
- **Status da Sprint**: [CONCLUÍDO] Implementação ponta a ponta do Dashboard Web SPA nativo para o DarkFactory, perfeitamente integrado e desacoplado:
  1. **Servidor Standalone FastAPI no DarkFactory (`darkfactory/src/dashboard/app.py` na porta 8502)**:
     - 24 rotas REST e SSE ativas, ciclo de vida com cleanup de processos órfãos e CORS aberto para interoperabilidade com o StockCont.
     - Suporte a streaming de mídia para áudios, vídeos 4K (com chunks parciais HTTP), legendas .srt e frames de b-roll.
     - Empacotador in-memory ZIP otimizado (`/api/download-package/{video_id}`) em modo `ZIP_STORED` (milissegundos de latência).
  2. **Design System Apple HIG iOS 27 Liquid Glass Cinema Edition (`cinema_dash.css`)**:
     - Estética dark obsidian (`#050608`), vidro volumétrico, acentos Ouro Theatrical (`#FFD700`), Âmbar (`#FF9F0A`) e Roxo Diretor (`#BF5AF2`).
     - Ícone claquete 3D pura (`favicon.svg`) e animações fluidas de pulso LED e hover.
  3. **Cockpit Completo com 6 Abas Táticas (Nolan Cinema Studio)**:
     - **Aba 1 (Cockpit Geral & KPIs)**: Disparador de produções E2E por tema histórico, botões de fases 1-5, controle do Daemon 24/7 e telemetria de cotas Google Flow (Omni 1.2 / Veo 3.1).
     - **Aba 2 (Roteiro 3 Fios de Nolan)**: Visualização da estrutura não-linear (Fio A: Relógio Lento, Fio B: Relógio Rápido, Fio C: Pós-Impacto), loglines e títulos alternativos de alto CTR.
     - **Aba 3 (Fila Visual)**: Monitor de prompts e status para Google Veo 3.1 4K (8s, 2.39:1 anamórfico), Gemini Omni Flash 1.2 (15s) e MMAudio/Whoosh.
     - **Aba 4 (Sound Lab 4-Stems)**: Mixer virtual Web Audio API (`audio_mixer.js`) com faders verticais de ganho, VU meters animados e botões MUTE / SOLO para Voz (CosyVoice/Kokoro), Trilha Lyria, Foley e Master Mix (-14 LUFS).
     - **Aba 5 (Central 1-Click Approval & SEO)**: Player 4K anamórfico (`video_player.js`) com alternância de letterbox 2.39:1, legendas .srt multilíngues dinâmicas, seletor de miniaturas A/B/C Test & Compare, scorecard 100% Green Dollar e 3 ações executivas de publicação (Não-Listado, Público, Quarentena).
     - **Aba 6 (Daemon 24/7 & Logs SSE)**: Terminal cyberpunk ao vivo com streaming SSE (`/api/stream-logs`), auto-scroll e histórico de quarentena.
  4. **Cross-Link Bidirecional Unificado**:
     - Pílula tátil "DarkFactory Cinema (:8502)" adicionada aos cabeçalhos de `index.html` e `video.html` no StockCont.
     - Barra de alternância "StockCont Microstock (:8501) ⇄ DarkFactory Cinema (:8502)" ativa no topo do DarkFactory.
  5. **Scripts de Execução & Suíte de Testes 100% Verde**:
     - `run_dashboard.bat` na raiz do `darkfactory` para inicialização com 1 clique do uvicorn e abertura automática do navegador.
     - Suíte `tests/test_dashboard_api.py` com 9 testes automatizados cobrindo todos os fluxos e endpoints REST, executando em 1.71s.
- **Última Atualização**: 2026-11-08 05:10
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
