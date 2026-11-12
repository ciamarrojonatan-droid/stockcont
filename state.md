# StockCont Pipeline State

> Sincronizado em **2026-11-12** após o desacoplamento completo StockCont ↔ DarkFactory.

## 🔌 Status do Desacoplamento & Escopo Ativo
- **Arquitetura 100% Independente**: O `stockcont` opera de forma totalmente autônoma e desacoplada do repositório irmão `../darkfactory`.
- **Escopo Preservado no StockCont**:
  - Esteira principal de Imagens 8K (Fases 1–5 + Scoring Comercial + Rolling 7D Quotas + ADR-05 Anti-Ban Alamy + Cofre Cloud/Auto-Purga).
  - Pipeline de Stock Vídeo I2V 4K na **Conta 3** RunningHub (Workflow `2115926169974812674`: Load Image `#164` → Prompt `#17` → FeiHou Video `#185` via `Lite/Plus` obrigatório por ADR-08) + Catalogador Vídeo Fase 4 (`src/video/video_metadata.py` + áudio mudo `-an`).
  - **Google Flow Engine** (`src/integrations/google_flow/`): FastAPI REST Server + RPC/Playwright CLI (`--flow*`), Veo 3.1 / Omni 1.2 Flash / Imagen 3, hash SHA-256 e `-an` para microstock.
  - **Promo Motion B2B & Motion QA** (`src/video/promo_motion_director.py`, `src/video/hyperframes_engine.py`, `src/video/motion_qa.py`, `src/video/ffmpeg_processor.py`): overlays determinísticos e zero-trademark (`BANNED_TRADEMARK_TERMS`) com áudio mudo (`-an`).
  - **Dashboard Web SPA Local (`:8501`)**: `/` (Imagens 8K) e `/video` (Stock Video 4K & Promo B2B) protegidos por `DASHBOARD_ACCESS_TOKEN`.
- **Componentes Removidos para `../darkfactory`**: Módulos de narração/áudio/SFX/trilha (`CosyVoice`, `Kokoro`, `Deepgram`, `MiniMax Music 3`, `MiniMax H3`), `Nolan Director`, Knowledge Vault/Story Validator, Map Animator, Shorts 9:16, links `:8502`, Contas RunningHub 4/5/7 e ADRs 09–11.

---

## 📊 Telemetria Atual do Pipeline

| Fase / Módulo | Status | Métricas Verificadas no Ambiente |
| :--- | :--- | :--- |
| **Fase 1 — Olheiro (`Scout`)** | `ok` | **85** tendências em `data/raw/trends.json` · **0** imagens locais (`--sync-raw` disponível) |
| **Fase 2 — Diretor de Arte** | `ok` | **74** referências analisadas · **408** prompts de imagem em `data/processed/prompts.json` |
| **Fase 3 — Fábrica (Contas 1 & 2)** | `ok` | **408/408** prompts no ledger SHA-256 (**100.0%**) · `Lite/Plus` obrigatório (ADR-08) |
| **Fase 4 — Catalogador IPTC/EXIF** | `idle` | **207** assets registrados em `data/processed/adobe_stock_upload.csv` · **0** JPGs locais |
| **Fase 5 — Distribuidor & Cotas (7D)** | `idle` | **0/8** agências configuradas no `.env` · **700** vagas livres semanais (Alamy travada em `0` por ADR-05) |
| **Vídeo Stock 4K (Conta 3 & Flow)** | `ok` | **124** video prompts sintetizados (**1** gerado / **123** pendentes) · Workflow `2115926169974812674` |
| **Daemon 24/7 & Backup Cloud** | `idle` | Status: `STOPPED` (`0` ciclos) · Google Drive backup opcional não configurado |
| **Dashboard Web SPA (`:8501`)** | `ok` | Superfícies `/` e `/video` operacionais com auth `DASHBOARD_ACCESS_TOKEN` e headers CSP |
| **Suíte de Testes (`Pytest`)** | `ok` | **241 passed** (suíte completa incluindo testes `e2e`) · Revisões `code`/`python`/`security` aprovadas |

---

## 🚀 Próxima Ação Recomendada
- Pipeline `stockcont` 100% autônomo e pronto para operação: executar `python main.py --phase 3` (ou `--phase 1 -q "<nicho>"` / `--dashboard`).
