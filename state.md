# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: DarkFactory Knowledge Vault & Story Auditor — Ingestão Canônica dos 27 Livros de Referência (Cinema, Storytelling Neural & Viralidade YouTube)
- **Status da Sprint**: [CONCLUÍDO] Implementação ponta a ponta do motor de conhecimento e auditoria algorítmica destilado dos 27 livros em `C:\Users\WDAGUtilityAccount\Downloads\Nova pasta\darkfactory\livros`:
  1. **Destilação Semântica Canônica (`src/video/knowledge_distiller.py`)**:
     - Varredura e indexação dos 27 PDFs (Walter Murch, MrBeast, Lisa Cron, Derral Eves, Brendan Kane, Jonah Berger, Derek Thompson, Alex Hormozi, Nir Eyal, GaryVee).
     - Geração persistente e atômica de 6 arquivos JSON estruturados em `src/video/knowledge/` (`walter_murch_editing.json`, `mrbeast_production.json`, `lisa_cron_story.json`, `viral_retention_stepps.json`, `youtube_growth_packaging.json`, `master_knowledge_index.json`).
  2. **Motor Operacional Canônico (`src/video/master_knowledge.py`)**:
     - *Walter Murch Rule of Six*: Pesos inegociáveis (Emoção 51%, História 23%, Ritmo 10%, Eye-Trace 7%, Plano 2D 5%, Espaço 3D 4%) e Teoria do Piscar (*Blink Theory*).
     - *MrBeast First Minute Retention Law*: MSL <= 4.2s nos primeiros 60s, re-hook de confirmação entre 50s e 70s, zero dead air e banimento total de exit-cues.
     - *Lisa Cron Neuro-Storytelling*: Cadência de *Curiosity Gaps* a cada 20-25s, The Third Rail (conflito interno) e causalidade ("Portanto/Porém" vs "E depois").
     - *Jonah Berger STEPPS Vector*: Cálculo ponderado de potencial viral (0-100), moedas sociais secretas e emoções de alta excitabilidade fisiológica (*Dread/Awe*).
  3. **Auditor de Roteiro e Manifestos (`src/video/story_validator.py`)**:
     - Avaliador algorítmico `DarkFactoryStoryValidator` com scoring unificado (0 a 100), grading (A+, A, B, C, F), status de prontidão e roadmap de remediação.
  4. **Integração Nativa nos Módulos Existentes**:
     - `src/video/pacing_analyzer.py`: Incorpora `murch_rule_of_six_score` e `mrbeast_first_minute_compliant` em `PacingReport`.
     - `src/video/youtube_booster.py`: Incorpora `score_viral_stepps` e auditoria no pacote master de publicação.
     - `.agents/skills/nolan-dark-history-director/SKILL.md`: As 5 Leis Invioláveis dos Mestres adicionadas como diretrizes obrigatórias de roteirização.
  5. **Suíte de Testes 100% Verde**:
     - `tests/test_master_knowledge.py` (5 testes) e `tests/test_story_validator.py` (2 testes) passando com 100% de sucesso.
     - Total: **307 testes automatizados passando (231 StockCont + 76 DarkFactory)** com zero regressão.
- **Última Atualização**: 2026-11-08 05:45
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
| **DarkFactory Master Knowledge Vault** | 🟢 Ativo & Operacional | **Motor Canônico dos 27 Livros (`src/video/master_knowledge.py`, `story_validator.py`)**: Walter Murch (Rule of Six), MrBeast (First Minute Law), Lisa Cron (Curiosity Gaps) e Jonah Berger (STEPPS) | Integrado nativo no Showrunner |
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **307 testes passando (231 no StockCont + 76 no DarkFactory, 100% verde)** | Regressão zero (24 suítes de teste StockCont + 11 DarkFactory) | `pytest tests/` |
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
