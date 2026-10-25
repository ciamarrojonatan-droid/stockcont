# StockCont — Master Project Context & Architecture

> **Single Source of Truth (SSOT)** para agentes autônomos, orquestradores (Antigravity & Claude Code) e engenharia de software do projeto StockCont.

---

## 1. Identidade & Propósito do Sistema

O **StockCont** é um ecossistema autônomo industrial de inteligência preditiva de mercado, engenharia reversa multimodal e automação robótica para microstock global (Adobe Stock, Freepik, 123RF, Pond5, Dreamstime, Alamy, Vecteezy, Ingram).

Diferente de fluxos manuais de geração com IA generativa, o StockCont opera como uma esteira quantitativa com 5 fases orquestradas:
1. **Fase 1: O Olheiro (Trend & Contributor Scout)** — Mineração de tendências, Top Sellers mundiais e nichos com Playwright headless/headed.
2. **Fase 2: O Diretor de Arte v3.0 (Prompt Architect)** — Análise visual multimodal via Gemini Vision e síntese de prompts de 700 a 1.000 palavras com Copy-Space adaptativo.
3. **Fase 3: A Fábrica (RunningHub ComfyUI RPA)** — Injeção de prompts no canvas LiteGraph do RunningHub, renderização 4K e fila idempotente com SHA-256.
4. **Fase 4: O Catalogador (Metadata & Injeção Binária)** — Auditoria visual de IA, conversão JPG 98%, gravação física de metadados binários IPTC/EXIF e atualização incremental de CSV.
5. **Fase 5: O Distribuidor (SFTP/FTP Mass Upload)** — Distribuição automatizada multi-agência com livro-razão criptográfico e backup em nuvem no Google Drive.
6. **Módulo Transversal: Dashboard Web SPA Local** — Servidor FastAPI (`http://localhost:8501`) com Dark Theme, streaming de logs e controle reativo de processos.

---

## 2. Mapa Detalhado do Pipeline de 5 Fases

```text
  [Radar Sazonal / Insights]
              │
              ▼
    [Fase 1: Olheiro]  ────────► data/raw/trends.json + data/raw/images/
              │
              ▼
    [Fase 2: Diretor]  ────────► data/processed/prompts.json (700-1000 palavras)
              │
              ▼
    [Fase 3: Fábrica]  ────────► data/final/images/ (Renders 4K brutos)
              │                  ↳ Ledger: data/processed/generation_history.json
              ▼
    [Fase 4: Catalogador] ─────► Injeção IPTC/EXIF nos JPGs + adobe_stock_upload.csv
              │                  ↳ Backup: G:\Meu Drive\StockCont_backup
              ▼
    [Fase 5: Distribuidor] ────► SFTP Adobe Stock / FTP Freepik, 123RF, Pond5, etc.
                                 ↳ Ledger: data/processed/upload_history.json
```

### Fase 1: O Olheiro Preditivo
- **Módulos Centrais**:
  - `src/scraper/adobe_stock.py`
  - `src/analyzer/seasonal_radar.py`
  - `src/analyzer/saturation_index.py`
- **Entradas**: Parâmetros de busca (nicho, tipo de ativo, ordenação) ou disparo de Contributor Insights.
- **Saídas**:
  - `data/raw/trends.json` (Array de objetos com `id`, `title`, `author`, `downloads`, `thumbnail_url`, `local_path`, `keywords`).
  - `data/raw/images/{item_id}.jpg` (Previews das referências mais vendidas).
- **Comandos CLI**:
  ```bash
  python main.py --seasonal
  python main.py --phase 1 --mode insights --type photo --max-items 20
  python main.py --phase 1 --mode search --query "biotech longevity laboratory" --order nb_downloads --max-items 15
  ```

### Fase 2: O Diretor de Arte v3.0
- **Módulos Centrais**:
  - `src/analyzer/director.py`
- **Entradas**: `data/raw/trends.json` e as imagens locais em `data/raw/images/`.
- **Saídas**: `data/processed/prompts.json` (Escrita atômica via `.tmp`).
- **Comandos CLI**:
  ```bash
  python main.py --phase 2
  ```
- **Especificação de Prompts v3.0**:
  - Exatamente **10 prompts derivados** por imagem de referência.
  - Cada prompt possui entre **700 e 1.000 palavras em inglês**.
  - 6 camadas mandatórias: Spatial Architecture, Physical Materiality & Textures, Multi-Point Lighting Kelvin, Optical Camera/Lens, Adaptive Copy-Space (35% a 50% de área limpa), Commercial Buyer Intent B2B.

### Fase 3: A Fábrica RPA ComfyUI
- **Módulos Centrais**:
  - `src/factory/runninghub_bot.py`
  - `src/factory/prompt_queue.py`
- **Entradas**: Prompts pendentes de `data/processed/prompts.json` priorizados por Contributor Insights.
- **Saídas**:
  - Renders 4K brutos salvos em `data/final/images/`.
  - Livro-razão SHA-256 atualizado em `data/processed/generation_history.json`.
  - Atualização in-place de status em `prompts.json` (`status: generated`).
- **Comandos CLI**:
  ```bash
  python main.py --phase 3 --node 192
  python main.py --phase 3 --batches 5
  python main.py --phase 3 --all-batches
  ```
- **Padrões de Engenharia**:
  - Nós ComfyUI: Injeção nos nós `#128` e `#129`, limpeza dos nós `#130` e `#131`, captura no nó de saída `#192`.
  - Hashing SHA-256 canônico de cada prompt para garantir idempotência.
  - Cancelamento atômico da 11ª tarefa excedente para economizar créditos de GPU.

### Fase 4: O Catalogador & Metadados Binários
- **Módulos Centrais**:
  - `src/cataloger/adobe_csv_maker.py`
  - `src/cataloger/reembed_compliance.py`
- **Entradas**: Imagens 4K em `data/final/images/`.
- **Saídas**:
  - Gravação binária física de tags IPTC e EXIF dentro do próprio JPG.
  - CSV incremental em `data/processed/adobe_stock_upload.csv`.
- **Comandos CLI**:
  ```bash
  python main.py --phase 4
  ```
- **Regras Estritas de Conformidade com IA**:
  - IPTC `2:05 (ObjectName)`: Título comercial limpo (< 200 caracteres), sem palavras cortadas.
  - IPTC `2:120 (Caption)`: Obrigatoriamente iniciado com `"Generative AI illustration. [Descrição detalhada]"`.
  - IPTC `2:25 (Keywords)`: Exatamente 50 tags ordenadas por relevância, com presença obrigatória de `["ai generated", "generative ai", "digital art", "illustration"]`.
  - EXIF IFD0: `ImageDescription` UTF-8, `0x9C9B (XPTitle)` e `0x9C9E (XPKeywords)` codificados em UTF-16LE para compatibilidade com o Windows Explorer e Lightroom.

### Fase 5: O Distribuidor & Expansão Multi-Agência
- **Módulos Centrais**:
  - `src/uploader/ftp_distributor.py`
  - `src/backup/gdrive_backup.py`
- **Entradas**: Imagens catalogadas em `data/final/images/`.
- **Saídas**:
  - Upload para servidores remotos via SFTP (`paramiko`) ou FTP (`ftplib`).
  - Histórico de uploads em `data/processed/upload_history.json`.
  - Backup local do Google Drive em `G:\Meu Drive\StockCont_backup`.
- **Comandos CLI**:
  ```bash
  python main.py --phase 5 --dry-run
  python main.py --phase 5 --platform adobe
  python main.py --phase 5 --platform all
  python main.py --backup
  ```

---

## 3. Decisões Arquiteturais (ADRs Inline)

### ADR-01: Blindagem de Encoding UTF-8 em Windows
- **Contexto**: O sistema roda primariamente em ambiente Windows onde consoles (`powershell`, `cmd`) operam por padrão em `cp1252`, gerando `UnicodeEncodeError` frequentes ao lidar com descrições ricas e caracteres acentuados.
- **Decisão**: Todos os scripts de entrada (`main.py`, hooks, bots) reconfiguram `sys.stdout` e `sys.stderr` explicitamente para `utf-8`. Todo I/O de arquivo usa `encoding="utf-8"`.

### ADR-02: Escrita Atômica Transacional com `.tmp`
- **Contexto**: Falhas de processo, quedas de energia ou interrupções de subagentes durante a escrita de JSONs com centenas de prompts (`prompts.json`, `generation_history.json`) corrompem a persistência.
- **Decisão**: Todo dump JSON é gravado primeiro em um arquivo temporário com identificador único (`.tmp.{pid}.{uuid}`) e substituído atomicamente no destino via `os.replace()` ou `Path.replace()`.

### ADR-03: Fila Criptográfica Idempotente com Hashing SHA-256
- **Contexto**: A geração de imagens consome créditos e tempo de GPU no RunningHub. Repetir prompts idênticos em lotes subsequentes causa desperdício financeiro.
- **Decisão**: Cada texto de prompt é normalizado (strip, lowercase, whitespace colapsado) e passa por `hashlib.sha256()`. O hash resultante é o identificador imutável persistido em `generation_history.json`.

### ADR-04: Reconhecimento Híbrido (Dual-Source) IPTC vs CSV
- **Contexto**: Submissão em lote para agências pode ocorrer via SFTP direto (onde a agência lê IPTC embutido) ou via upload web com CSV de metadados.
- **Decisão**: O Catalogador executa ambas as ações simultaneamente: injeta IPTC/EXIF fisicamente no cabeçalho binário do JPG e anexa a linha correspondente em `adobe_stock_upload.csv`.

---

## 4. Contratos de Dados (Data Schemas v3.0)

### 4.1 Schema de Tendências Mineradas (`data/raw/trends.json`)
```json
[
  {
    "id": "2090056954",
    "title": "Minimalist corporate workspace with modern laptop",
    "author": "CreativePro",
    "category": "photo",
    "downloads": 1420,
    "thumbnail_url": "https://as1.ftcdn.net/...",
    "local_path": "data/raw/images/2090056954.jpg",
    "keywords": ["workspace", "business", "minimalist", "laptop"],
    "scraped_at": "2026-10-24T18:00:00Z"
  }
]
```

### 4.2 Schema de Prompts Processados (`data/processed/prompts.json`)
```json
[
  {
    "source_id": "2090056954",
    "source_title": "Minimalist corporate workspace...",
    "system_version": "3.0",
    "analysis_metadata": {
      "target_model": "model-agnostic-flux-comfyui",
      "analysis_confidence": 0.95
    },
    "generated_prompts": [
      {
        "id": 1,
        "concept": "FinTech High-Frequency Trading Desk",
        "layout_type": "left_third_copy_space",
        "copy_space_zone": "left_35_percent",
        "target_buyer": "saas_landing_page",
        "prompt": "Cinematic wide commercial shot... [700 a 1000 palavras]",
        "estimated_word_count": 820,
        "status": "pending"
      }
    ]
  }
]
```

### 4.3 Schema do Livro-Razão de Geração (`data/processed/generation_history.json`)
```json
{
  "a1b2c3d4e5f6...": {
    "prompt_text": "Cinematic wide commercial shot...",
    "generated_at": "2026-10-24T19:30:00Z",
    "batch_id": "batch_20261024_01",
    "output_file": "data/final/images/fintech_trading_desk_01.jpg"
  }
}
```

### 4.4 Schema do Livro-Razão de Upload (`data/processed/upload_history.json`)
```json
{
  "fintech_trading_desk_01.jpg": {
    "adobe": {
      "uploaded_at": "2026-10-24T20:15:00Z",
      "status": "success",
      "remote_path": "/uploads/fintech_trading_desk_01.jpg"
    },
    "123rf": {
      "uploaded_at": "2026-10-24T20:16:00Z",
      "status": "success"
    }
  }
}
```

---

## 5. Matriz de Agências & Suporte de Protocolos

| Agência | Protocolo | Host / Porta | Política de IA | Leitura IPTC |
| :--- | :--- | :--- | :--- | :--- |
| **Adobe Stock** | SFTP | `sftp.contributor.adobestock.com:22` | Aceito (Tag IA requerida) | Automática |
| **Freepik** | FTP | Host dedicado via painel | Aceito em escala | Automática |
| **Dreamstime** | FTP | `upload.dreamstime.com:21` | Aceito (IA no Caption) | Automática |
| **Pond5** | FTP | `ftp.pond5.com:21` | Aceito | Automática |
| **Alamy** | FTP/SFTP | Host dedicado | Aceito (Declarar IA) | Automática |
| **Vecteezy** | FTP | Host dedicado | Aceito (Fotos/Vetores) | Automática |
| **123RF** | FTP | `ftp.123rf.com:21` | Aceito | Automática |
| **Ingram** | FTP | Host dedicado | Aceito | Automática |

---

## 6. Diretivas de Roteamento de Subagentes & Ferramentas

Quando interagir com o código ou executar tarefas no StockCont, utilize este mapeamento de competências:

| Domínio de Tarefa | Arquivos / Diretórios Alvo | Subagente Especializado | Skills Relacionadas |
| :--- | :--- | :--- | :--- |
| Scraping & Automação Web | `src/scraper/`, `chrome_session/` | `e2e-runner` | `e2e-testing`, `error-handling` |
| Diretor de Arte & Gemini | `src/analyzer/`, `.env` | `architect` | `api-design`, `error-handling` |
| RPA ComfyUI & Fila | `src/factory/`, `playwright_session/` | `e2e-runner` | `error-handling` |
| Catalogador & IPTC/EXIF | `src/cataloger/`, `data/final/` | `python-reviewer` | `python-patterns` |
| Upload SFTP/FTP | `src/uploader/`, `src/backup/` | `security-reviewer` | `python-patterns` |
| Dashboard Web SPA | `src/dashboard/` | `architect` | `frontend-patterns`, `api-design` |
| Testes Automatizados | `tests/` | `tdd-guide` | `python-testing`, `tdd-workflow` |
| Orquestração Geral | `main.py`, `.agents/` | `planner` | `orchestrator`, `verification-loop` |

---

## 7. Diretiva Fundamental de Autonomia Operacional

O Antigravity e o Claude Code devem operar este repositório sob **autonomia total**:
1. **Nunca interromper para pedir confirmações triviais** de comandos de leitura, testes ou formatação.
2. **Auto-diagnosticar e corrigir erros de build ou runtime** utilizando a suíte de testes (`pytest`) antes de devolver a resposta.
3. **Persistir sempre o estado em `state.md`** ao concluir qualquer fase do pipeline.
4. **Preservar integridade dos livros-razão criptográficos** (`generation_history.json`, `upload_history.json`).
