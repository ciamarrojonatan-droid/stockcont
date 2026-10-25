# Rules: Art Director & Vision Analysis (`src/analyzer/`)

Regras e padrões obrigatórios para o módulo de engenharia de prompts com Gemini Vision:

1. **Modelos Preferenciais**:
   - `gemini-3.5-flash-lite` (baixa latência e alto throughput).
   - `gemini-3.8-flash` (alta precisão descritiva).
   - Sempre utilize fallback dinâmico entre os modelos caso um apresente erro HTTP 429 ou 503.
2. **System Prompt v3.0 Ultra-Detailed Mandate**:
   - Todo prompt gerado em `generated_prompts` deve conter rigorosamente entre **700 e 1.000 palavras em inglês**.
   - Estrutura obrigatória em 6 camadas: Spatial Architecture (120-150w), Physical Materiality (120-150w), Multi-Point Lighting Kelvin (120-150w), Optical Camera/Lens (100-130w), Adaptive Copy-Space (120-150w), Commercial Buyer Intent (100-120w).
3. **Copy-Space Obrigatório**: O prompt deve reservar explicitamente entre 35% e 50% de área limpa (esquerda, direita ou topo) para sobreposição de tipografia corporativa.
4. **Resiliência de Rede**: Requisições REST via `httpx` com timeout estendido de 120s e lógica de retry com backoff exponencial para lidar com limites de quota da API do Gemini.
5. **Persistência Atômica**: O arquivo `data/processed/prompts.json` deve ser gravado via `.tmp` e `replace()` para evitar corrupção durante a serialização.
