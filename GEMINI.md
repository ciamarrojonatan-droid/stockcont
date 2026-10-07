# Autonomous Meta-Orchestrator Protocol (Orquestrador Mestre)

> **DIRETIVA MANDATÓRIA PERMANENTE**: A cada mensagem ou solicitação do usuário, o assistente DEVE executar este protocolo de orquestração antes de propor soluções, alterar arquivos ou responder. O objetivo é SEMPRE empregar a melhor combinação de ferramentas, skills, subagentes e workflows disponíveis no ecossistema do projeto.

---

## 🧭 O Ciclo de Orquestração Contínua (4 Passos)

### Passo 1: Análise da Demanda & Varredura de Recursos
Ao receber qualquer mensagem ou solicitação, avalie a natureza da tarefa:
1. **Skills do Ecossistema**: Verifique a lista de skills do sistema e do projeto (`.agents/skills/`). Se o tema envolver uma skill existente (ex.: `python-patterns`, `python-testing`, `e2e-testing`, `error-handling`, `api-design`, `verification-loop`, etc.), leia imediatamente o respectivo `SKILL.md` via `view_file` para internalizar os padrões exigidos.
2. **Subagentes Especializados**: Verifique se a demanda requer especialistas dedicados (`architect`, `code-architect`, `e2e-runner`, `python-reviewer`, `security-reviewer`, `silent-failure-hunter`, `build-error-resolver`, `performance-optimizer`, `planner`, etc.). Delegue via `invoke_subagent` sempre que exigir especialização profunda, isolamento de contexto ou revisão crítica.
3. **Workflows e Comandos**: Avalie se a tarefa corresponde a um fluxo padrão (`/plan`, `/goal`, `/learn`, `/python-review`, etc.).
4. **Ferramentas MCP & Core**: Selecione com precisão as ferramentas operacionais (`run_command`, `view_file`, `replace_file_content`, `write_to_file`, `manage_task`, `schedule`).

---

### Passo 2: Matriz de Roteamento Especializado

| Tipo de Demanda | Subagente Recomendado | Skill / Regra a Consultar | Ferramentas Críticas |
| :--- | :--- | :--- | :--- |
| **Scraper / Playwright / Web Bots** | `e2e-runner` | `e2e-testing`, `error-handling` | `run_command`, `view_file` |
| **Código Python & Padrões** | `python-reviewer` | `python-patterns`, `coding-standards` | `replace_file_content`, `view_file` |
| **Integração com LLM / Gemini Vision** | `architect` | `api-design`, `error-handling` | `run_command`, `view_file` |
| **Erros de Build / Falhas Silenciosas** | `build-error-resolver`, `silent-failure-hunter` | `agent-introspection-debugging` | `run_command`, `manage_task` |
| **Novas Features / Planejamento** | `planner`, `code-architect` | `/plan`, `dev-team` | `ask_question`, `write_to_file` |
| **Segurança & Revisão Pré-Merge** | `security-reviewer`, `code-reviewer` | `verification-loop`, `codehealth-mcp` | `view_file` |
| **Testes Automatizados (Pytest)** | `tdd-guide` | `python-testing`, `tdd-workflow` | `run_command` |

---

### Passo 3: Execução Rigorosa & Validação Cruzada
- **Não improvisar**: Se houver padrão estabelecido na skill relevante, siga as convenções estritas dela.
- **Revisão pós-código**: Após qualquer criação ou modificação de script funcional, acione o revisor correspondente (`python-reviewer`, `code-reviewer` ou `security-reviewer`).

---

### Passo 4: Transparência na Resposta
Ao executar ações no projeto, identifique brevemente a rota de orquestração escolhida no início ou conclusão da resposta:
`🎯 Orquestrador: [Skill: <nome> | Agente: <nome> | Ferramenta: <nome>]`
Isso garante visibilidade total de que os melhores recursos foram acionados para a tarefa.
