# Estado do Projeto: StockCont (AI Stock Generator)

## 📌 Visão Geral
Sistema automatizado para análise de tendências de microstock, engenharia reversa multimodal de prompts, geração assistida por IA e catalogação inteligente com metadados IPTC/EXIF embutidos e CSV pronto para Adobe Stock.

## 🚀 Progresso das Fases

### Fase 1: O "Olheiro" (Trend Analyzer & Contributor Insights)
*Status: 🟢 Concluído & Otimizado*
- [x] Scraper desenvolvido em Python com Playwright (`src/scraper/adobe_stock.py`).
- [x] Suporte ao portal oficial **Adobe Stock Contributor Insights** (`https://contributor.stock.adobe.com/en/insights/best/contributors`).
- [x] Extração de contribuidores que mais vendem ("Recent top sellers"), seus lifetime downloads (ex: 100k+, 10k+) e respectivos assets mais vendidos.
- [x] Fechamento automático de modais ("How It works") e seleção de abas (Photos, Illustrations, Vectors).
- [x] Modo `--deep-profile` para minerar o portfólio completo dos maiores contribuidores ordenados por vendas.
- [x] Sessão persistente do Chrome (`chrome_session`) para manter o login do usuário ativo.
- [x] Modo alternativo de busca pública por termo/nicho (`--mode search`).
- [x] Armazenamento de metadados em `data/raw/trends.json` e imagens em `data/raw/images/`.

### Fase 2: Diretor de Arte (Engenharia de Prompts)
*Status: 🟢 Concluído & Otimizado*
- [x] Integração de alta velocidade com Gemini Multimodal via REST (`src/analyzer/director.py`).
- [x] Migração para o **System Prompt v2.0 (Visual DNA & Commercial Prompt Architect)** com análise rigorosa em 8 dimensões (Subject, Style, Lighting, Composition, Color Science, Materials/Textures, Camera/Rendering, Commercial Positioning).
- [x] Geração estrita de **exatamente 10 prompts comerciais derivados por lote/imagem** com scoring de confiança multidimensional.
- [x] Contrato JSON estruturado v2.0 com retrocompatibilidade automática (`prompt` populado a partir de `prompt_data.final_prompt`).
- [x] Integração aprimorada com a Fase 3 (`src/factory/runninghub_bot.py`), extraindo diretamente o `final_prompt` refinado para injeção nos nós ComfyUI `#128` e `#129`.
- [x] Fila de prompts salvos em `data/processed/prompts.json` com estrutura `prompt_data` e escrita atômica.

### Fase 3: A Fábrica (Geração em Massa & Injeção 100% Autônoma)
*Status: 🟢 Concluído & Otimizado*
- [x] Automação 100% autônoma com Playwright para Runninghub (`src/factory/runninghub_bot.py`).
- [x] Zero cliques manuais: espera ativa até o carregamento completo dos 83 nós do grafo.
- [x] Centralização da câmera no Node **#128 Easy-Use** e foco visível imediato em `prompt_1`.
- [x] Injeção atômica de **10 prompts por lote nos nós #128 e #129** (5 caixas por nó), com limpeza automática dos nós #130 e #131.
- [x] Sincronização direta via DOM + LiteGraph API com repintura forçada do canvas (`setDirtyCanvas`), eliminando risco de deleção acidental de nós via atalhos globais.
- [x] Disparo automático via botão Executar Lite/Plus (`button.beveled-btn-left.run-btn`) e monitoramento em tempo real do **Node #192** (saída final com Upscale 4K).
- [x] Captura streaming item a item: salva imediatamente cada uma das **10 imagens 4K** geradas no nó #192.
- [x] Cancelamento automático da task em "Lista de tarefas": imediatamente após salvar a **10ª imagem**, o bot clica em "Cancelar" para interromper o upscale da 11ª imagem excedente/irrelevante e poupar créditos/tempo.
- [x] Fluxo de persistência do Chrome com profile dedicado (`playwright_session`).

### Fase 4: O Catalogador (Metadados e SEO)
*Status: 🟢 Concluído & Testado de Ponta a Ponta*
- [x] Análise visual ultrarrápida (sub-3s) com Gemini Vision via REST (`src/cataloger/adobe_csv_maker.py`).
- [x] Título comercial otimizado e exatamente 50 palavras-chave ranqueadas por relevância.
- [x] Classificação automática da Categoria numérica nativa do Adobe Stock.
- [x] **Injeção binária de IPTC**: Object Name, Caption e Keywords gravados no JPG via `iptcinfo3` (preenchimento automático no portal do Adobe Stock).
- [x] **Injeção binária de EXIF**: ImageDescription, XPTitle e XPKeywords gravados via `piexif` (compatível com Windows, Lightroom e Bridge).
- [x] Conversão automática de PNG para JPG de alta qualidade (qualidade 98) caso o gerador produza arquivos PNG.
- [x] Exportação e atualização incremental do CSV `data/processed/adobe_stock_upload.csv`.

### Fase 5: O Distribuidor (Multi-Platform SFTP/FTP Mass Upload)
*Status: 🟢 Concluído & Testado de Ponta a Ponta*
- [x] Módulo nativo autônomo desenvolvido em `src/uploader/ftp_distributor.py`.
- [x] Suporte multi-protocolo completo:
  - **SFTP** de alta segurança com `paramiko` para **Adobe Stock Contributor** (`sftp.contributor.adobestock.com:22`).
  - **FTP/FTPS** com `ftplib` para **Freepik**, **Dreamstime**, **Pond5**, **Alamy**, **Vecteezy** e **123RF**.
- [x] Livro-razão e histórico inteligente (`data/processed/upload_history.json`): evita reenvios desnecessários do mesmo arquivo para a mesma plataforma.
- [x] Sistema de retentativas com backoff exponencial contra instabilidades temporárias de rede.
- [x] Modo de simulação e validação prévia de conexões (`--dry-run`): testa credenciais e lista arquivos pendentes sem transferir bytes.
- [x] Filtro granular por plataforma (`--platform [adobe|freepik|dreamstime|pond5|alamy|vecteezy|123rf|all]`) e envio forçado (`--force`).
- [x] Integração total ao CLI Maestro (`python main.py --phase 5` e encadeamento em `python main.py --all`).

### ☁️ Módulo de Backup em Nuvem: Google Drive
*Status: 🟢 Concluído & Integrado ao Pipeline*
- [x] Módulo nativo autônomo em `src/backup/gdrive_backup.py`.
- [x] **Modo Nuvem (Google Drive API v3)**: Upload direto via Service Account (`service_account.json` ou string JSON no `.env`) ou OAuth 2.0. Descoberta e criação automática da pasta remota `StockCont_Backup`.
- [x] **Modo Sincronização Local**: Compatível com pasta local do Google Drive para Desktop (`GOOGLE_DRIVE_LOCAL_PATH="G:\Meu Drive\StockCont"`).
- [x] **Uploads Resumíveis em Chunks (`MediaFileUpload`)**: Otimizado para suportar imagens pesadas em 4K sem perda de conexão.
- [x] **Histórico Atômico (`data/processed/gdrive_backup_history.json`)**: Previne reenvios duplicados de assets já sincronizados.
- [x] **Disparo Automático**: Integrado para salvar automaticamente as imagens catalogadas logo após a **Fase 4** e no comando mestre `python main.py --backup` ou `python main.py --all`.
- [x] **Guia de Segurança GCP**: Documentado procedimento para desativação da trava organizacional `iam.disableServiceAccountKeyCreation` para emissão de chaves Service Account JSON.

---

## 🌐 Estratégia de Monetização Multi-Plataforma & Distribuição Open-Source

### 1. Matriz de Plataformas de Microstock & Mercados

| Categoria | Plataforma | Comissões / Modelo | Política de IA Generativa | Suporte a FTP / IPTC |
| :--- | :--- | :--- | :--- | :--- |
| **Tier Ouro (Volume Alto)** | **Adobe Stock** | 33% por download (líder global) | ✅ Totalmente aceito (marcar checkbox de IA) | SFTP nativo / Lê IPTC automático |
| **Tier Ouro (Volume Alto)** | **Freepik Contributor** | Pagamento por download no modelo pool | ✅ Aceito em alta escala | FTP nativo / Lê IPTC automático |
| **Tier Ouro (Volume Alto)** | **Vecteezy** | Pagamento por download (Free/Pro) | ✅ Aceito para imagens/vetores | FTP nativo / Lê IPTC automático |
| **Tier Prata (Volume Médio)** | **123RF** | 30% a 50% de comissão | ✅ Aceito | FTP nativo / Lê IPTC automático |
| **Tier Prata (Volume Médio)** | **Dreamstime** | 25% a 50% de comissão | ✅ Aceito | FTP nativo / Lê IPTC automático |
| **Tier Prata (Volume Médio)** | **Depositphotos** | 30% a 44% de comissão | ✅ Aceito | FTP nativo / Lê IPTC automático |
| **High-Ticket (Macrostock)** | **Alamy** | 40% a 50% (vendas de $20 a $150+) | ✅ Aceito (declarar IA nos metadados) | FTP nativo / Lê IPTC automático |
| **High-Ticket (Macrostock)** | **Pond5** | 40% (criador define o próprio preço) | ✅ Aceito para fotos e ilustrações | FTP nativo / Lê IPTC automático |
| **Packs Digitais (Venda Direta)** | **Creative Market** | 70% de lucro (packs temáticos $19 a $49) | ✅ Aceito como assets / packs criativos | Upload direto web (ZIP com JPGs) |
| **Packs Digitais (Venda Direta)** | **Etsy / Gumroad** | 90%+ margem de lucro líquido | ✅ Aceito (pacotes de texturas, backgrounds, mockups) | Upload web (ZIP) |
| **PROIBIDO (Não Enviar IA)** | **Shutterstock** | Não aceita IA externa | ❌ Proibido (só aceita IA gerada no motor interno deles) | N/A |
| **PROIBIDO (Não Enviar IA)** | **Getty Images / iStock**| Não aceita IA | ❌ Proibição total de IA generativa | N/A |

---

### 2. Alternativa Open-Source ao Wirestock

O **Wirestock** cobra de 15% a 30% de comissão sobre os royalties do criador de forma vitalícia e centraliza as contas em nome deles. No nosso pipeline, como a Fase 4 (`src/cataloger/adobe_csv_maker.py`) já grava todos os metadados binários (**Title, Keywords, Description**) diretamente no arquivo JPG (`IPTC` + `EXIF`), não é necessário nenhum intermediário comissionado.

- **Solução Nativa do StockCont (Fase 5 Implementada)**:
  - `src/uploader/ftp_distributor.py` despacha diretamente para as agências via SFTP e FTP sem intermediários e com 100% dos royalties retidos pelo criador.

---

### 3. Onde Obter Credenciais de Upload FTP/SFTP

Em todas as agências que suportam envio em massa, o acesso FTP é gratuito para contribuidores:

1. **Adobe Stock (SFTP)**:
   - Acesse o portal: `https://contributor.stock.adobe.com/`
   - Clique em **Upload** no topo da página.
   - No painel lateral ou topo, clique em **"Generate password" / "Upload via SFTP"**.
   - Host: `sftp.contributor.adobestock.com`, Porta: `22`, Usuário e Senha gerados no painel.
2. **Freepik (FTP)**:
   - Acesse o painel de contribuidor: `https://contributor.freepik.com/`
   - Vá para a seção **Files > Upload Files**.
   - Localize o bloco de **FTP Credentials** (Host: `ftp.freepik.com`, Porta: `21`, seu ID e senha de FTP).
3. **Dreamstime (FTP)**:
   - Acesse a área de membro > **Management Area > FTP Upload**.
   - Host: `upload.dreamstime.com`, Porta: `21`.
4. **Pond5 (FTP)**:
   - Acesse a conta > **My Uploads > FTP Settings**.
   - Host: `ftp.pond5.com`, Porta: `21`.
5. **Alamy (FTP)**:
   - No portal de contribuinte Alamy > **Upload Images > Alamy FTP**.
   - Host: `upload.alamy.com`.
6. **123RF / Vecteezy**:
   - Disponíveis nas respectivas abas de upload em lote / FTP nos painéis de contribuidor.

---

## 🎮 Orquestrador Maestro Central (`main.py`)
*Status: 🟢 Operacional*
- [x] CLI unificado com dashboard visual de status: `python main.py --status`.
- [x] Execução modular por fase: `python main.py --phase [1|2|3|4|5]`.
- [x] Suporte a argumentos de nicho diretamente no comando central (ex: `python main.py --phase 1 -q "minimalist office" -o nb_downloads`).
- [x] Backup direto via CLI: `python main.py --backup` (com flag opcional `--dry-run`).
- [x] Modo de execução contínua encadeada: `python main.py --all` (executa da mineração, geração, catalogação, backup no Drive ao upload distribuído).

---

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub conectado e sincronizado.
- [x] Dependências atualizadas em `requirements.txt` (`piexif`, `iptcinfo3`, `httpx`, `pillow`, `google-genai`, `google-api-python-client`, `google-auth`, `paramiko`).
- [x] Resiliência de encoding no terminal Windows (UTF-8 sem falhas de cp1252).
- [x] 17 testes automatizados passando em `tests/` (`pytest`).
- [x] Protocolo de orquestração autônoma e skills ECC configurados.

---

## 🎯 Próximos Passos Operacionais
1. **Configurar Backup do Google Drive no `.env`**:
   - Inserir a chave `service_account.json` ou o caminho local em `GOOGLE_DRIVE_LOCAL_PATH`.
   - Testar com `python main.py --backup --dry-run`.
2. **Configurar Credenciais das Agências Desejadas no `.env`**:
   - Adicionar usuário e senha gerados no Adobe Stock (SFTP) e/ou Freepik (FTP).
   - Testar credenciais com `python main.py --phase 5 --dry-run`.
3. **Execução Automatizada Contínua**:
   ```powershell
   python main.py --all
   ```

