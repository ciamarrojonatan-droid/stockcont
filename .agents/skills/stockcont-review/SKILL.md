---
name: stockcont-review
description: >-
  Runs a comprehensive multi-layer quality gate: automated pytest suite,
  Python code standards check, security/credential audit, and data ledger
  integrity. Use when running /review.
---

# StockCont Comprehensive Quality Review (`/review`)

Comando integrado de auditoria de qualidade, segurança e testes do repositório StockCont.

## 🧭 O que este comando executa

1. **Gate Automatizado de Testes**:
   Executa toda a suíte de testes unitários e de integração:
   ```powershell
   .\venv\Scripts\python.exe -m pytest
   ```
   *Critério de aprovação*: **100% dos testes passando sem falhas**.

2. **Auditoria de Padrões Python & Resiliência**:
   - **Encoding**: Verifica se pontos de entrada contêm reconfiguração explícita para UTF-8 no Windows.
   - **Escrita Atômica**: Confirma se operações em `prompts.json`, `trends.json` e `generation_history.json` utilizam arquivos temporários (`.tmp`) com `os.replace()`.
   - **SHA-256**: Valida conformidade do cálculo de hash no `PromptQueueManager`.

3. **Auditoria de Segurança & Credenciais**:
   - Verifica se `.env` está estritamente listado no `.gitignore`.
   - Varre o histórico recente de commits e arquivos modificados em busca de chaves expostas acidentalmente.
   - Checa se permissões de API e URLs de agências seguem HTTPS e SFTP seguro.

4. **Auditoria de Integridade dos Livros-Razão (Ledgers)**:
   - Valida formatação sintática dos JSONs em `data/processed/`.
   - Confirma integridade do CSV `adobe_stock_upload.csv` e contagem de colunas.

5. **Relatório Consolidado**:
   Gera um relatório objetivo com veredicto final: `PASS (Pronto para Produção)` ou `FAIL (Ações Corretivas Requeridas)`.
