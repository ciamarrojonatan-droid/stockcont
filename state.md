# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: DarkFactory Cinema Engine & Speed-Matching Adaptativo (Zero-Loop)
- **Status da Sprint**: [CONCLUÍDO] Calibração de Produção Master para o DarkFactory / Documentários Históricos:
  1. **Speed-Matching Adaptativo (Eliminação do Loop Seco)**: Substituição mandatória de `-stream_loop -1` por cálculo dinâmico de `setpts = (target_duration / source_duration) * PTS`, preservando a fluidez contínua da câmera sem saltos repetitivos amadores.
  2. **Arquitetura Dual-Shot (Cena 1A + 1B)**: Suporte a múltiplos planos por cena longa. Cena 1 estruturada em Shot 1A (bunker/sirene, 0-8.44s) e Shot 1B (radar macro com as 5 ogivas balísticas americanas, 8.44-17.89s).
  3. **3D LUT de Documentário Histórico (Kodak 2383 / Bleach-Bypass)**: Mapeamento de cor em cubo 33x33x33 (`cold_war_documentary.cube`) com curva S de filme analógico, desaturação suave a 88%, sombras frias (verde-ciano militar soviético) e altas luzes âmbar.
  4. **Letterbox Anamórfico 2.39:1 & Legendas Broadcast**: Máscaras pretas de 140px superior e inferior sobre canvas 1080p, com legendas em 2 linhas máximas ancoradas com `MarginV=30` dentro da barra preta inferior (zero obstrução de personagens).
  5. **Sound Design Procedural (Impacto Braam Sub-Bass)**: Varredura exponencial de 85 Hz a 36 Hz ($t=0.0$ a $1.2$s) com saturação analógica (`tanh`) + batimentos cardíacos, relógio mecânico e clique de chave industrial.
  6. **Cobertura de Testes**: 187 testes automatizados passando com 100% de sucesso (20 suítes de teste).
- **Última Atualização**: 2026-11-06 04:15
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
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
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **187 testes passando (100% verde)** | Regressão zero (20 suítes de teste) | `pytest tests/` |
| **Agente Estratégico ("O Que Você Faria?")** | 🟢 Ativo & Registrado | **Subagente `what-would-you-do`** \| Skill `/wwyd` \| Hook `PreInvocation` em `.agents/hooks.json` \| Sócio sênior e avaliador de viabilidade | Invocável via subagente ou chat |

---

## 🎬 Arquitetura da Fábrica de Vídeo (RunningHub 4K)
- **Workflow URL**: `https://www.runninghub.ai/pt-br/workflow/2115926169974812674?source=workspace`
- **Workflow ID**: `2115926169974812674`
- **Load Image**: Nó `#164` (Ingestão de imagem de referência ou First Frame)
- **Prompt**: Nó `#17` (Injeção de prompt temporal cinematográfico 500-800 palavras)
- **Preview Video (Feihou Anti-Watermark)**: Nó `#185` (Captura direta de preview sem marca d'água da plataforma)
- **Botão de Execução**: `Lite/Plus` (Botão do meio - cor amarela/laranja)
- **Destino dos Vídeos 4K**: `data/final/videos/`
- **Playwright Stealth Profile 3**: RTX 4090 Workstation, 4K Display, sessão isolada `playwright_session_video/`
