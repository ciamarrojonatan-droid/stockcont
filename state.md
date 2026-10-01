# Estado do Projeto: StockCont (AI Stock Generator)

## 📌 Visão Geral
Sistema automatizado para análise de tendências, geração em massa e catalogação de assets (imagens e vídeos) gerados por IA para venda em plataformas de microstock (foco inicial: Adobe Stock).

## 🚀 Progresso das Fases

### Fase 1: O "Olheiro" (Trend Analyzer)
*Status: 🟡 Planejado (Aguardando início do código)*
- [x] Rascunho da arquitetura (tendencias.plan.md criado).
- [ ] Criar scraper ou integrador para buscar referências de "Mais Vendidos".
- [ ] Definir estrutura de armazenamento da fila de tendências.

### Fase 2: Diretor de Arte (Engenharia de Prompts)
*Status: 🔴 Não Iniciado*
- [ ] Script de integração com Google AI Pro (Gemini).
- [ ] Engenharia reversa de conceitos visuais para prompts de alta conversão.

### Fase 3: A Fábrica (Geração em Massa)
*Status: 🔴 Não Iniciado*
- [ ] Integração com Runninghub / ComfyUI.
- [ ] Pipeline de geração automática.
- [ ] Pipeline de Upscale (qualidade Adobe Stock).

### Fase 4: O Catalogador (Metadados e SEO)
*Status: 🔴 Não Iniciado*
- [ ] Visão Computacional para ler a imagem final.
- [ ] Geração de Título e 50 palavras-chave (CSV export).

## 🛠 Infraestrutura e DevOps
- [x] Repositório GitHub criado (`stockcont`).
- [x] Autenticação e Git inicializados.
- [x] Ambiente Antigravity/ECC configurado (`.agents/`).

## 🎯 Próximo Passo Imediato
- Desenvolver o script de coleta de dados (Fase 1), decidindo entre Python/Playwright para automação web ou input manual inicial via pasta.
