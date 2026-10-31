# Rules: The Factory RPA & Prompt Queue (`src/factory/`)

Regras e padrões obrigatórios para o módulo RPA do ComfyUI e gestão de fila:

1. **Gestor de Fila Criptográfica (`PromptQueueManager`)**:
   - Todo prompt (imagem ou vídeo) possui hash SHA-256 canônico calculado sobre texto normalizado.
   - NUNCA submeta prompts à GPU sem antes verificar o ledger `data/processed/generation_history.json` (ou `video_generation_history.json`).
   - Marque os prompts como `generated` atômica e incrementalmente à medida que os arquivos físicos forem confirmados.

2. **Topologia de Nós RunningHub ComfyUI — Conta 1 (Raw Producer)**:
   - Workflow URL: `https://www.runninghub.ai/pt-br/workflow/2113606426114670593?source=workspace`
   - Nós de Injeção: 42 nós PromptList (`#128`, `#129`, `#130`, `#131`, `#204`, `#218`, `#224`, `#223`, `#222`, `#221`, `#219`, `#220`, `#230`, `#229`, `#228`, `#227`, `#225`, `#226`, `#236`, `#235`, `#234`, `#233`, `#231`, `#232`, `#242`, `#241`, `#240`, `#239`, `#237`, `#238`, `#254`, `#253`, `#252`, `#251`, `#249`, `#250`, `#248`, `#247`, `#246`, `#245`, `#243`, `#244`).
   - Capacidade por Lote: 5 prompts por nó = até 210 prompts por execução na janela de 40 minutos do RunningHub.
   - Nó de Captura Raw: `#121` (Preview Image).
   - Destino dos Renders Raw: `data/staging/images/`.
   - Registro Automático: cada render bruto capturado é imediatamente registrado no `QCInspector` (`data/processed/qc_manifest.json`).

3. **Topologia de Nós RunningHub ComfyUI — Conta 2 (SeedVR 2.5 8K Upscaler)**:
   - Workflow URL: `https://www.runninghub.ai/pt-br/workflow/2115663736840245249?source=workspace`
   - Ingestão ZIP: Nó `#5` (Load Images (zip)).
   - Nó de Captura Preview 8K: `#55` (Preview Image com monitoramento em tempo real 1 a 1 antes da sobrescrita).
   - Destino dos Upscales 8K: `data/final/images/`.

4. **Topologia de Nós RunningHub ComfyUI — Pipeline de Vídeo 4K (Geração & Upscale)**:
   - Workflow URL: `https://www.runninghub.ai/pt-br/workflow/2115926169974812674?source=workspace`
   - Workflow ID: `2115926169974812674`
   - Ingestão de Imagem / First Frame: Nó `#164` (`Load Image`).
   - Injeção de Prompt Temporal: Nó `#17` (`Prompt` / `Text`).
   - Saída / Output Final em 4K: Nó `#157` (`Save video/video combine`).
   - Destino dos Vídeos 4K: `data/final/videos/`.
   - Isolamento de Sessão Playwright: `playwright_session_video/`.

5. **Métricas e Cronômetro de Benchmark**:
   - O bot cronometra o tempo individual de cada ativo bruto/vídeo capturado e o tempo total do lote.
   - Ao concluir, emite o relatório executivo com a taxa média por ativo e a projeção para a sessão.

6. **Isolamento de Sessão Playwright**:
   - Conta 1 (Raw Producer): opera com `playwright_session_raw/` (ou `playwright_session/`).
   - Conta 2 (SeedVR 2.5 8K Upscaler): opera com `playwright_session_upscale/`.
   - Pipeline de Vídeo 4K (Conta 3): opera com `playwright_session_video/`.
