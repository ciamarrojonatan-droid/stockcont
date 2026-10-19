# Estado do Projeto: StockCont (AI Stock Generator)

## 📌 Visão Geral
Sistema autônomo para inteligência de microstock, mineração de tendências, engenharia reversa multimodal de prompts, geração assistida por IA (ComfyUI via RunningHub) e catalogação automatizada com metadados IPTC/EXIF binários e distribuição SFTP/FTP multi-agência.

---

## 📊 Dashboard de Status Atual da Produção

| Etapa / Módulo | Status | Métricas Atuais em Produção |
| :--- | :--- | :--- |
| **Fase 1: Olheiro (Scout)** | 🟢 Concluído | 10 tendências mineradas (Top Sellers Adobe Stock) \| 10 referências em `data/raw/images/` |
| **Fase 2: Diretor de Arte** | 🟢 Concluído | 10 itens analisados \| **100 prompts comerciais gerados** com Gemini Vision |
| **Fase 3: A Fábrica (RunningHub)** | 🟢 Operacional | **86/100 prompts gerados (86% concluído)** \| **43 imagens 4K renderizadas** em `data/final/images/` |
| **Fase 4: O Catalogador** | 🟢 Concluído | **43 imagens JPG 4K com IPTC/EXIF embutidos** \| CSV `adobe_stock_upload.csv` atualizado |
| **Backup Google Drive** | 🟢 Operacional | **44 assets sincronizados** em `G:\Meu Drive\StockCont_backup` via modo `local_sync` |
| **Fase 5: O Distribuidor** | 🟢 Pronto | Módulo testado (`--dry-run` OK) \| Onboarding multi-agência em andamento |
| **Qualidade & Testes** | 🟢 100% Verde | **29 testes automatizados passando** (`pytest`) |

---

## 🚀 Progresso Detalhado das Fases

### Fase 1: O "Olheiro" (Trend Analyzer & Contributor Insights)
*Status: 🟢 Concluído & Otimizado*
- [x] Scraper desenvolvido em Python com Playwright (`src/scraper/adobe_stock.py`).
- [x] Suporte ao portal oficial **Adobe Stock Contributor Insights** (`https://contributor.stock.adobe.com/en/insights/best/contributors`).
- [x] Extração de contribuidores top sellers, lifetime downloads e assets mais vendidos.
- [x] Fechamento automático de modais e seleção de abas (Photos, Illustrations, Vectors).
- [x] Modo `--deep-profile` para minerar portfólios completos ordenados por volume.
- [x] Sessão persistente do Chrome (`chrome_session`) para login contínuo.
- [x] Modo alternativo de busca pública por termo/nicho (`--mode search`).
- [x] Armazenamento de metadados em `data/raw/trends.json` e imagens em `data/raw/images/`.

### Fase 2: Diretor de Arte (Engenharia de Prompts)
*Status: 🟢 Concluído & Otimizado*
- [x] Integração de alta velocidade com Gemini Multimodal via REST (`src/analyzer/director.py`).
- [x] `GEMINI_API_KEY` configurada no `.env` e validada via chamada direta REST (HTTP 200).
- [x] Modelos suportados e verificados: `gemini-3.5-flash-lite` e `gemini-3.8-flash`.
- [x] System Prompt v2.0 com análise em 8 dimensões (Subject, Style, Lighting, Composition, Color Science, Materials/Textures, Camera/Rendering, Commercial Positioning).
- [x] Geração estrita de 10 prompts comerciais derivados por imagem de referência.
- [x] Contrato JSON estruturado v2.0 com retrocompatibilidade automática.
- [x] Fila de 100 prompts salvos em `data/processed/prompts.json` com escrita atômica.

### Fase 3: A Fábrica (Geração em Massa, Fila Inteligente & Injeção Autônoma)
*Status: 🟢 Concluído & Otimizado*
- [x] Automação autônoma com Playwright para Runninghub ComfyUI (`src/factory/runninghub_bot.py`).
- [x] **Gerenciador de Fila e Ledger Dedicado** (`src/factory/prompt_queue.py`):
  - Hashing SHA-256 canônico de cada prompt contra duplicações.
  - Livro-razão atômico em `data/processed/generation_history.json`.
  - Atualização in-place de status em `data/processed/prompts.json` (`status: generated`).
  - Reconciliação automática com imagens já existentes em disco.
- [x] **Suporte a Múltiplos Lotes na mesma sessão do navegador**:
  - `python main.py --phase 3` (executa 1 lote de 10 prompts pendentes por padrão).
  - `python main.py --phase 3 --batches N` (executa N lotes consecutivos mantendo o navegador aberto).
  - `python main.py --phase 3 --all-batches` (processa todos os prompts pendentes até zerar a fila).
- [x] Resiliência a falhas parciais: marcação proporcional baseada em imagens efetivamente salvas em disco.
- [x] Limpeza automática de widgets excedentes em lotes com `< 10` prompts para evitar reexecução de prompts anteriores.
- [x] Injeção atômica de 10 prompts por lote nos nós `#128` e `#129`, com limpeza dos nós `#130` e `#131`.
- [x] Disparo automático via botão Executar Lite/Plus e monitoramento em tempo real do **Node #192** (saída 4K).
- [x] Cancelamento automático da tarefa em "Lista de tarefas" após salvar as imagens esperadas para poupar créditos.
- [x] Sessão persistente em `playwright_session`.

### Fase 4: O Catalogador (Metadados SEO & IPTC/EXIF Binários)
*Status: 🟢 Concluído & Testado de Ponta a Ponta*
- [x] Análise visual ultrarrápida com Gemini Vision via REST (`src/cataloger/adobe_csv_maker.py`).
- [x] Geração de títulos comerciais e 50 palavras-chave ranqueadas por relevância.
- [x] Classificação da categoria numérica nativa do Adobe Stock.
- [x] **Injeção binária de IPTC**: Object Name, Caption e Keywords gravados no JPG via `iptcinfo3` (auto-preenchimento no Adobe Stock e agências FTP).
- [x] **Injeção binária de EXIF**: ImageDescription, XPTitle e XPKeywords gravados via `piexif` (compatível com Windows, Lightroom e Bridge).
- [x] Conversão automática de PNG para JPG de alta qualidade (qualidade 98).
- [x] Exportação e atualização incremental do CSV `data/processed/adobe_stock_upload.csv` (43+ assets catalogados).

### Fase 5: O Distribuidor & Expansão Multi-Agência
*Status: 🟢 Operacional & Em Onboarding*
- [x] Módulo autônomo desenvolvido em `src/uploader/ftp_distributor.py`.
- [x] Suporte multi-protocolo completo:
  - **SFTP** seguro com `paramiko` para **Adobe Stock Contributor** (`sftp.contributor.adobestock.com:22`).
  - **FTP/FTPS** com `ftplib` para **Freepik**, **Dreamstime**, **Pond5**, **Alamy**, **Vecteezy** e **123RF**.
- [x] Livro-razão e histórico inteligente (`data/processed/upload_history.json`) prevenindo reenvios duplicados.
- [x] Modo de simulação e validação prévia de conexões (`--dry-run`).
- [x] Filtro granular por plataforma (`--platform [adobe|freepik|dreamstime|pond5|alamy|vecteezy|123rf|all]`) e envio forçado (`--force`).
- [x] **Status do Onboarding nas Agências Parceiras**:
  - **Adobe Stock**: Pronto para disparo via SFTP.
  - **Freepik / Magnific Contributors**: Aplicação enviada com portfólio Behance focado em ativos 4K fotorrealistas e ComfyUI.
  - **Vecteezy**: Ativos comerciais organizados para submissão com licença **Pró** e categoria **Photo**; ticket aberto no suporte Zendesk para verificação manual de identidade via CNH Digital oficial (PDF com QR Code Vio).
  - **Alamy**: Cadastro de colaborador iniciado para monetização de alto valor ($20 a $150+ por ativo).

### ☁️ Módulo de Backup em Nuvem: Google Drive
*Status: 🟢 Concluído & Integrado ao Pipeline*
- [x] Módulo autônomo em `src/backup/gdrive_backup.py`.
- [x] Modo Sincronização Local ativo e validado com o Google Drive para Desktop (`G:\Meu Drive\StockCont_backup`).
- [x] Histórico atômico (`data/processed/gdrive_backup_history.json`) com 44 assets salvos.
- [x] Disparo automático após a catalogação da Fase 4 e via CLI `python main.py --backup`.

---

## 🎮 Comandos do Orquestrador Maestro (`main.py`)

| Comando | Função |
| :--- | :--- |
| `python main.py --status` | Dashboard completo de status da esteira e fila de prompts |
| `python main.py --phase 1 -q "nicho"` | Executa a mineração de tendências e referências |
| `python main.py --phase 2` | Gera 10 prompts comerciais derivados por imagem de referência |
| `python main.py --phase 3` | Executa 1 lote de 10 prompts pendentes no RunningHub |
| `python main.py --phase 3 --batches 5` | Executa 5 lotes consecutivos (50 imagens) mantendo o browser aberto |
| `python main.py --phase 3 --all-batches` | Processa todos os prompts pendentes até zerar a fila |
| `python main.py --phase 4` | Cataloga imagens, injeta IPTC/EXIF nos JPGs e atualiza o CSV |
| `python main.py --backup` | Sincroniza o backup dos assets no Google Drive |
| `python main.py --phase 5 --dry-run` | Valida credenciais e simula envio para as agências |
| `python main.py --phase 5 --platform adobe`| Realiza upload automático via SFTP para o Adobe Stock |
| `python main.py --all` | Executa a esteira de ponta a ponta de forma autônoma |

---

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub conectado e sincronizado.
- [x] Ambiente virtual Python (`venv`) com Python 3.11.9 e dependências atualizadas.
- [x] Dependências em `requirements.txt` (`playwright`, `pytest`, `pytest-playwright`, `httpx`, `google-generativeai`, `google-genai`, `Pillow`, `python-dotenv`, `piexif`, `iptcinfo3`, `paramiko`).
- [x] Binários do Playwright Chromium instalados e operacionais.
- [x] Chave `GEMINI_API_KEY` e caminho `GOOGLE_DRIVE_LOCAL_PATH` configurados no `.env`.
- [x] Resiliência de encoding no terminal Windows (UTF-8 sem falhas de cp1252).
- [x] **29 testes automatizados passando em `tests/` (`pytest`)**.
- [x] Protocolo de orquestração autônoma e skills ECC configurados.

---

## 🎯 Próximos Passos Operacionais
1. **Acompanhar Aprovação de Identidade no Vecteezy** (via suporte Zendesk).
2. **Configurar Credenciais SFTP/FTP no `.env`** para as plataformas aprovadas (Adobe Stock, Freepik, Vecteezy, Alamy).
3. **(Opcional) Finalizar os 14 Prompts Restantes**:
   ```cmd
   python main.py --phase 3 --all-batches
   python main.py --phase 4
   ```
4. **Disparar a Fase 5 de Distribuição Automática**:
   ```cmd
   python main.py --phase 5 --platform all
   ```
