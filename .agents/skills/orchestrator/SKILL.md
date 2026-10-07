---
name: orchestrator
description: Master orchestrator that systematically inspects available skills, subagents, workflows, MCPs, and core tools on every user request to route execution dynamically to the best specialized assets.
---

# Master Orchestrator

This skill enforces continuous dynamic resource routing across all available skills, subagents, workflows, MCPs, and system tools in the workspace.

## 🎯 When to Activate
- Automatically activated on every user message or request via `AGENTS.md` / `GEMINI.md`.
- Explicitly invoked when the user asks for multi-agent coordination, tool selection, or workflow orchestration.

---

## 🔍 The 4-Step Orchestration Workflow

### 1. Request Triage & Scope Analysis
Categorize the incoming user intent:
- **Web Automation / Scraping**: Adobe Stock scraping, Runninghub bot, Playwright browser actions.
- **AI / LLM Integration**: Gemini Vision prompt analysis, schema design, vision tokens, quota handling.
- **Core Python Engineering**: Data pipelines, file operations, typing, async handling.
- **Bug Diagnosing / Silent Failures**: Unhandled exceptions, dropped downloads, hanging processes.
- **Architecture & System Design**: Pipeline scaling, adding new platforms (Freepik, Shutterstock).
- **Quality Assurance & Verification**: Unit/E2E testing, security audits, code reviews.

### 2. Available Resource Audit

#### Specialized Subagents (Delegated via `invoke_subagent`):
- `e2e-runner`: Playwright execution, browser stability, flakiness mitigation.
- `python-reviewer`: PEP 8 standards, typing annotations, Python idiomatic practices.
- `architect` / `code-architect`: System blueprinting, database & API design.
- `silent-failure-hunter`: Detecting swallowed errors, missing retry loops, unhandled edge cases.
- `build-error-resolver`: Python dependencies, venv issues, import breaks.
- `security-reviewer`: Leaked API keys, sanitization, unsafe external calls.
- `tdd-guide`: Test-driven development for new features.

#### Project & System Skills (Consulted via `view_file` on `SKILL.md`):
- `e2e-testing`: Playwright patterns and browser automation best practices.
- `python-patterns`: Idiomatic Python, typing, and architectural guidelines.
- `python-testing`: Pytest strategies, fixtures, mocking, and coverage.
- `api-design`: REST and SDK design patterns.
- `error-handling`: Resilient error wrapping and circuit breakers.
- `agent-introspection-debugging`: Structured post-mortem debugging.
- `verification-loop`: 6-phase verification before finishing a major task.

#### Core Execution Tools:
- `run_command`: Running tests, scripts, CLI tools.
- `view_file` / `replace_file_content` / `write_to_file`: Surgical file manipulation.
- `manage_task`: Managing asynchronous processes and background tasks.

---

### 3. Execution Plan & Tool Dispatch
1. **Identify the Lead Role**: Choose whether the primary agent handles it directly using a skill's instructions, or delegates to a specialized subagent.
2. **Read Skill Guidelines**: Always read the relevant `SKILL.md` before coding.
3. **Execute Surgically**: Implement changes with high precision.
4. **Post-Implementation Review**: Run the specialized reviewer agent or verify against test suites.

---

### 4. Visibility Badge
To keep the user informed, each action should report its chosen orchestration path:
`🎯 Orquestrador: [Skill: <nome> | Agente: <nome> | Ferramenta: <nome>]`
