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
- [x] Engenharia reversa para "DNA visual" (estilo, iluminação, composição, paleta) e geração de prompts comerciais derivados.
- [x] Fila de **145 prompts prontos** (29 itens analisados) salvos em `data/processed/prompts.json` com estrutura `prompt_data` e escrita atômica.

### Fase 3: A Fábrica (Geração em Massa & Injeção 100% Autônoma)
*Status: 🟢 Concluído & Otimizado*
- [x] Automação 100% autônoma com Playwright para Runninghub (`src/factory/runninghub_bot.py`).
- [x] Zero cliques manuais: espera ativa até o carregamento completo dos 83 nós do grafo.
- [x] Centralização da câmera no Node **#128 Easy-Use** e foco visível imediato em `prompt_1`.
- [x] Injeção atômica e segura nos nós **#128, #129, #130 e #131** (5 caixas por nó = 20 caixas preenchidas por lote).
- [x] Sincronização direta via DOM + LiteGraph API com repintura forçada do canvas (`setDirtyCanvas`), eliminando risco de deleção acidental de nós via atalhos globais.
- [x] Disparo automático via botão Executar Lite/Plus (`button.beveled-btn-left.run-btn`) e monitoramento do Node #121 para download dos assets.
- [x] Priorização inteligente do lote: prompts minerados em Contributor Insights (Top Sellers Gorodenkoff e onephoto) são priorizados no carregamento de lotes.
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

- **Solução Open-Source Pronta**: **Xpiks** ([github.com/ribtoks/xpiks](https://github.com/ribtoks/xpiks))
  - Aplicativo desktop open-source (C++/Qt) para Windows, macOS e Linux.
  - Suporta catalogação e injeção de IPTC em lote.
  - Possui gerenciador de conexões FTP/FTPS simultâneo para despachar arquivos para múltiplas agências em paralelo.
- **Solução Nativa do Projeto (Roadmap Fase 5)**:
  - Criação de `src/uploader/ftp_distributor.py` utilizando bibliotecas nativas de Python (`ftplib` e `paramiko` para SFTP).
  - Distribuição automatizada com 1 comando: lê as imagens processadas da pasta `data/final/images/` e envia para todas as agências configuradas no `.env`.

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
- [x] Execução modular por fase: `python main.py --phase [1|2|3|4]`.
- [x] Suporte a argumentos de nicho diretamente no comando central (ex: `python main.py --phase 1 -q "minimalist office" -o nb_downloads`).
- [x] Modo de execução contínua encadeada: `python main.py --all`.

---

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub conectado e sincronizado.
- [x] Dependências atualizadas em `requirements.txt` (`piexif`, `iptcinfo3`, `httpx`, `pillow`, `google-genai`).
- [x] Resiliência de encoding no terminal Windows (UTF-8 sem falhas de cp1252).
- [x] Protocolo de orquestração autônoma e skills ECC configurados.

---

## 🎯 Próximo Passo Operacional
1. **Catalogar o Lote Gerado (Top Sellers Gorodenkoff/onephoto)**:
   `python main.py --phase 4`
   - O catalogador converterá as 20 fotos para JPG (qualidade 98), injetará os metadados IPTC/EXIF embutidos e atualizará o CSV `adobe_stock_upload.csv`.
2. **Submissão no Portal**:
   - Fazer upload das fotos processadas no portal Adobe Stock Contributor (ou via SFTP). Os metadados serão lidos instantaneamente.
3. **(Opcional / Futuro)**:
   - Configurar credenciais FTP para Freepik / Alamy / Vecteezy e plugar a Fase 5 (`src/uploader/ftp_distributor.py`).
