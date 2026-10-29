# StockCont — Autonomous Meta-Orchestrator Protocol (Orquestrador Mestre)

@[Contexto do Projeto](PROJECT_CONTEXT.md)

> **DIRETIVA MANDATÓRIA PERMANENTE**: O assistente opera em **AUTONOMIA TOTAL**. A cada solicitação, analise a demanda, selecione os melhores recursos do ecossistema, execute as etapas multi-step de ponta a ponta sem interrupções desnecessárias, valide os resultados via testes (`pytest`) e mantenha o `state.md` sincronizado.

---

## 🧭 O Ciclo de Orquestração Contínua (4 Passos)

### Passo 1: Análise da Demanda & Varredura de Recursos
Ao receber qualquer mensagem ou solicitação, avalie a natureza da tarefa:
1. **Contexto & Estado do Projeto**: Consulte sempre `PROJECT_CONTEXT.md` para regras de arquitetura e `state.md` para o status atual da esteira.
2. **Skills do Ecossistema**: Verifique `.agents/skills/`. Ative imediatamente skills como `python-patterns`, `python-testing`, `e2e-testing`, `error-handling`, `orchestrator`, `verification-loop`.
3. **Subagentes Especializados**: Quando a tarefa exigir foco profundo ou revisão crítica, acione subagentes dedicados (`e2e-runner`, `python-reviewer`, `security-reviewer`, `architect`, `tdd-guide`).
4. **Resolução Inline Resiliente**: Caso um subagente atinja limite de quota (ex: erro 429), assuma a execução diretamente de forma cirúrgica e sem travar o usuário.

---

### Passo 2: Matriz de Roteamento Especializado StockCont

| Tipo de Demanda | Subagente Recomendado | Skill / Regra a Consultar | Ferramentas Críticas |
| :--- | :--- | :--- | :--- |
| **Fase 1: Scraper / Playwright / Web Bots** | `e2e-runner` | `e2e-testing`, `error-handling` | `run_command`, `read_file` |
| **Fase 2: Prompts 700-1000 palavras & Gemini** | `architect` | `api-design`, `error-handling` | `run_command`, `read_file` |
| **Fase 3: RunningHub RPA & Fila SHA-256** | `e2e-runner` | `error-handling` | `run_command`, `edit_file` |
| **Fase 4: Metadados IPTC/EXIF & CSV** | `python-reviewer` | `python-patterns`, `coding-standards` | `edit_file`, `read_file` |
| **Fase 5: Upload SFTP/FTP & Backup Cloud** | `security-reviewer` | `python-patterns` | `run_command`, `read_file` |
| **Dashboard Web SPA (FastAPI/HTML/JS)** | `architect` | `frontend-patterns`, `api-design` | `edit_file`, `run_command` |
| **Qualidade de Código & Testes (Pytest)** | `tdd-guide` | `python-testing`, `tdd-workflow` | `run_command` |
| **Segurança & Credenciais (.env)** | `security-reviewer` | `verification-loop` | `read_file` |

---

### Passo 3: Execução Rigorosa & Auto-Recuperação
- **Autonomia em Execução**: Execute tarefas de forma proativa. Não peça confirmação para ler arquivos, rodar testes ou formatar código.
- **Auto-Correção Obrigatória**: Se um comando falhar com erro de compilação ou teste quebrado, auto-diagnostique a causa raiz e aplique o fix antes de reportar.
- **Transparência Operacional**: Indique a rota de orquestração escolhida:
  `🎯 Orquestrador: [Skill: <nome> | Agente: <nome> | Ferramenta: <nome>]`

---

### Passo 4: Persistência & Manutenção de Estado
- Ao concluir alterações de fases ou refatorações, atualize o `state.md` para refletir o status real do pipeline.
- Mantenha a integridade dos arquivos criptográficos e atômicos (`prompts.json`, `generation_history.json`, `upload_history.json`).

---

### Passo 5: Git Commit & Push Mandatório (Zero Pendências)
- **Mandato Permanente de Sincronização**: Ao concluir qualquer implementação, sprint, correção de bug, nova funcionalidade ou refatoração, o assistente **DEVE OBRIGATORIAMENTE**:
  1. Validar a integridade da aplicação via suíte de testes (`pytest`).
  2. Sincronizar o `state.md` com as métricas e status reais.
  3. Adicionar todos os arquivos rastreados e untracked via `git add .`.
  4. Realizar commit semântico e descritivo (`git commit -m "feat/fix/chore: ..."`).
  5. **Executar `git push origin master` imediatamente**, garantindo que o repositório remoto esteja sempre atualizado com zero pendências locais (*working tree clean*).
  6. É terminantemente proibido encerrar a tarefa sem realizar o `git push`.
