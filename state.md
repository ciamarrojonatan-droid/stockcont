# StockCont Pipeline State
> Sincronizado automaticamente por hooks e comandos do ecossistema.

## Sprint Atual: Central de Comando Dedicada de Vídeo SPA (`/video`) & Estúdio I2V Multiplier
- **Status da Sprint**: [CONCLUÍDO] Nova página SPA dedicada exclusivamente a vídeos em `http://localhost:8501/video`, alternador tátil no Header (Imagens vs Vídeos), Player Cinema HTML5 com scrubbing nativo, Estúdio I2V direto de imagens 8K, conformação FFmpeg (-an) e 140 testes 100% verdes.
- **Última Atualização**: 2026-10-30 22:00
- **Modo Operacional**: Dual-Mode (Antigravity & Claude Code via SSOT `PROJECT_CONTEXT.md`)

---

## 📊 Métricas do Pipeline em Produção

| Fase / Módulo | Status | Contagem / Métricas | Próxima Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Dashboard Vídeo SPA (`/video`)** | 🟢 Ativo | **Dedicated Cinema Command Center**: URL dedicada `http://localhost:8501/video`, Player Cinema HTML5, 6 KPIs de vídeo, Fila 4D, Matriz e Estúdio I2V | Acessar via browser |
| **Dashboard Imagens SPA (`/`)** | 🟢 Ativo | **Design System iOS 27 Liquid Glass**: Alternador tátil no Header conectando Imagens (`/`) e Vídeos (`/video`) | `python main.py --dashboard` |
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
| **Conta 1: Raw Producer** | 🟢 Calibrada (210 Prompts) | **Workflow 2113606426114670593** \| 42 nós PromptList ➔ Capacidade: até 210 prompts/execução em 40 min | Integrado no Daemon |
| **Módulo QC: Curadoria & Quality Control** | 🟢 Calibrado | **Gemini Vision auto-audit ativo** \| Empacotamento em zips de 10 (`approved_batch.zip`) para prevenir OOM na GPU | Integrado no Daemon |
| **Conta 2: SeedVR 8K Upscaler** | 🟢 Calibrada & Pronta | **Workflow SeedVR 8K** \| Ingestão ZIP Nó #5 ➔ Preview Nó #55 (1 a 1 Real-Time) ➔ Auto-cancel na última imagem | Integrado no Daemon |
| **Fase 4: O Catalogador** | 🟢 Concluído | **190 assets catalogados** em `adobe_stock_upload.csv` \| Injeção obrigatória de 300 DPI + IPTC/EXIF | Integrado no Daemon |
| **Fase 5: O Distribuidor com Cotas** | 🟢 Protegido | **Despacho seletivo por plataforma**: Pausa agências com cotas esgotadas e prossegue nas demais \| Anti-Ban Alamy ativo | Integrado no Daemon |
| **Suíte de Testes (Pytest)** | 🟢 100% Verde | **140 testes passando (100% verde)** \| Regressão zero (17 suítes de teste) | `pytest tests/` |

---

## 🎬 Arquitetura da Central de Comando de Vídeo (`/video`)

### 1. Rota Dedicada & Experiência de Navegação Unificada
- **URL**: `http://localhost:8501/video`
- **Alternador Tátil de Mídia no Header**: Cápsula de vidro líquido presente em ambas as páginas (`/` e `/video`) permitindo transição com um clique entre Modo Imagens 8K e Modo Vídeos 4D.
- **Design System Mantido**: iOS 27 Liquid Glass, tokens Apple HIG, tipografia tripla (`Space Grotesk`, `Instrument Sans`, `Fira Code`) e prismas cibernéticos com iluminação volumétrica violeta/azul.

### 2. Seções e Abas Dedicadas a Vídeo
- **Galeria Cinema (Player)**:
  - Grid de cards de vídeo com poster, badges flutuantes (`4K UHD`, `Catalogado`/`Pendente CSV`, `Sem Áudio -an`) e contador de duração (`00:08`).
  - Modal Cinema com player nativo HTML5 (`<video controls autoplay loop>`), streaming de alta performance com suporte a scrub bar e painel com métricas de ffprobe, metadados de IA e status de CSV.
- **Fila de Prompts 4D**:
  - Tabela com filtros por proporção (`16:9 Landscape` vs `9:16 Vertical Reels`) e status (`Pendentes` / `Gerados`).
  - Ações em lote e modal para inspeção do prompt cinematográfico de 500 a 800 palavras.
- **Estúdio I2V (Imagens 8K ➔ Vídeo)**:
  - Exibe todos os renders 8K finalizados de `data/final/images/`.
  - Permite disparar o sintetizador de vídeo 4D do Gemini Vision para qualquer imagem com um clique.
- **Matriz de Distribuição de Vídeo**:
  - Controle de envio específico para **Adobe Stock Video** e **Pond5**.
- **Agências de Vídeo**:
  - Telemetria de protocolos SFTP e FTP com bloqueio ativo de IA para Alamy (ADR-05).
- **Timeline & Logs**:
  - Visualização ao vivo de processos em background (Scout, Director, Cataloger, Distributor).

---

## 🧪 Qualidade de Código & Testes
- **Total de Testes**: **140 testes automatizados** passando 100% verde (17 suítes de teste).
- **Novos Testes Adicionados**: `tests/test_video_dashboard.py` (9 novos testes cobrindo todas as rotas e regras de negócio do painel de vídeo).
