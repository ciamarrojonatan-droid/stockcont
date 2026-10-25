# Rules: The Factory RPA & Prompt Queue (`src/factory/`)

Regras e padrões obrigatórios para o módulo RPA do ComfyUI e gestão de fila:

1. **Gestor de Fila Criptográfica (`PromptQueueManager`)**:
   - Todo prompt possui hash SHA-256 canônico calculado sobre texto normalizado.
   - NUNCA submeta prompts à GPU sem antes verificar o ledger `data/processed/generation_history.json`.
   - Marque os prompts como `generated` atômica e incrementalmente à medida que os arquivos físicos 4K forem confirmados em `data/final/images/`.
2. **Topologia de Nós RunningHub ComfyUI**:
   - Nós `#128` e `#129`: Injeção dos prompts do lote (10 por lote).
   - Nós `#130` e `#131`: Limpeza obrigatória para lotes menores que 10 para evitar reaproveitamento residual de prompts antigos.
   - Nó `#192`: Saída 4K com upscale onde as imagens devem ser capturadas via monitoramento do DOM.
3. **Cancelamento Atômico de Tarefas Excedentes**:
   - Ao capturar a 10ª imagem do lote, o bot deve acessar a "Lista de tarefas" e cancelar a 11ª tarefa em fila para poupar créditos de GPU no RunningHub.
4. **Isolamento de Sessão Playwright**:
   - Utilize exclusivamente `playwright_session/` para o RunningHub, mantendo total separação do `chrome_session/` do Adobe Stock.
