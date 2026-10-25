# StockCont Persistent Memory Vault

> Memória durável e compartilhada entre sessões, modelos e agentes do StockCont.

---

## 🧠 Aprendizados Operacionais & Resoluções de Problemas

### 1. Windows Console Encoding & UTF-8
- **Problema**: O Windows usa `cp1252` por padrão no PowerShell e CMD, causando quebras de `UnicodeEncodeError` com descrições ricas e metadados.
- **Resolução**: Em todos os pontos de entrada (`main.py`, hooks, scripts CLI), forçar `sys.stdout.reconfigure(encoding="utf-8")` e `sys.stderr.reconfigure(encoding="utf-8")`. Nos scripts `.bat`, usar `chcp 65001`.

### 2. Ciclo de Vida dos Hooks (`hooks.json`)
- **Problema**: O working directory ao executar comandos definidos em `.agents/hooks.json` é a própria pasta `.agents/`.
- **Resolução**: Referenciar scripts como `python scripts/<script_name>.py` (ou duplicar na raiz `.agents/.agents/scripts/` para blindagem absoluta contra variações de CWD). Todos os scripts de hook devem usar estritamente a stdlib do Python (`json`, `sys`, `os`, `datetime`) para não depender do ambiente virtual.

### 3. Fila de Geração ComfyUI Idempotente (RunningHub)
- **Problema**: Repetir geração de prompts idênticos consome tempo de GPU e créditos na plataforma.
- **Resolução**: Cálculo canônico de SHA-256 no `PromptQueueManager`. Atualização atômica em `generation_history.json`. Cancelamento atômico da 11ª tarefa para poupar créditos.

### 4. Isolamento das Sessões de Navegador
- **Problema**: Conflito de cookies e storage se o mesmo perfil de navegador fosse usado para Adobe Stock e RunningHub.
- **Resolução**: Divisão estrita em duas pastas: `chrome_session/` (Adobe Stock) e `playwright_session/` (RunningHub ComfyUI). NUNCA mesclar ou deletar sem solicitação explícita.

### 5. Conformidade com Agências de Microstock (IPTC/EXIF)
- **Problema**: Rejeição de IA por falta de declaração ou metadados quebrados.
- **Resolução**:
  - IPTC Caption e EXIF ImageDescription iniciam obrigatoriamente com `"Generative AI illustration. "`.
  - Exatamente 50 tags ordenadas por relevância, contendo `["ai generated", "generative ai", "digital art", "illustration"]`.
  - Higienização de nomes de arquivo sem preposições pendentes no final (`-on-a.jpg`).

---

## 📌 Histórico de Decisões Arquiteturais (ADRs Resumidas)
- **Dual-Mode**: Antigravity (`AGENTS.md`) e Claude Code (`CLAUDE.md`) compartilham `PROJECT_CONTEXT.md` como SSOT.
- **Single Page Application**: Dashboard FastAPI na porta 8501 com streaming assíncrono de logs via `_stream_pipe` e polling a cada 1.5s.
- **Backup Híbrido**: Google Drive para Desktop via espelhamento local (`G:\Meu Drive\StockCont_backup`) com livro-razão `gdrive_backup_history.json`.
