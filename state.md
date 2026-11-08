# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: DarkFactory Cinema Engine & Research / Kokoro Fallback Grounding
- **Status da Sprint**: [CONCLUÍDO] Calibração de Produção Master para o DarkFactory / Documentários Históricos:
  1. **Research Engine Ground-Truth (`darkfactory/src/research_engine.py`)**: Extração factual automática via Wikipedia REST API e MediaWiki Search API. Mapeamento de fatos numéricos, figuras históricas, locações, datas e síntese de ganchos dramáticos e oportunidades visuais de B-roll. Eliminação de alucinações e conformidade estrita contra *AI slop*.
  2. **Kokoro TTS Local Fallback Engine (`darkfactory/src/kokoro_fallback.py`)**: Mapeamento de atuação (*acting direction*) a partir de instruções CosyVoice (`instruct_text`) para vozes e cadências do Kokoro-82M (`am_fenrir` para tensão/urgência, `am_onyx` para clima sombrio/grave, `am_adam` para documentário clássico). Fallback proxy transparente via Edge-TTS e transcode 16-bit 44.1kHz PCM WAV.
  3. **Orquestrador Central Atualizado (`darkfactory/run_pilot_pipeline.py`)**: Suporte a `--step research`, `--step tts-local` e modo 100% autônomo offline `--step all-local`.
  4. **Motor T2V Narrativo (`src/video/darkfactory_t2v.py`)**: Superação da limitação estática do I2V. Geração direta de cenas narrativas divididas em pares **Dual-Shot** de alta retenção (Shot A Drama/Tensão + Shot B Macro/Ação) com adapters para MiniMax H3 e Google Flow (Veo 2).
  5. **Cobertura de Testes**: 205 testes automatizados passando com 100% de sucesso (193 testes no StockCont + 12 testes no DarkFactory).
- **Última Atualização**: 2026-11-07 21:20
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
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **193 testes passando (100% verde)** | Regressão zero (21 suítes de teste) | `pytest tests/` |
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
