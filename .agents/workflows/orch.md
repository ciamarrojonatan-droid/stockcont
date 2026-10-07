---
description: Run an orchestrator scan across all project skills, subagents, and tools for the current task.
argument-hint: "[task description]"
---

# /orch - Master Orchestration Command

This command audits all available skills, specialized subagents, and tools in the workspace to build and execute the optimal action plan for the provided task.

## Execution Steps:
1. **Analyze Task Domain**: Identify languages, frameworks, automation layers, and potential risks.
2. **Scan Registered Skills & Agents**: Match the requirements against project skills (`.agents/skills/`) and subagent personas (`.agents/agents/`).
3. **Dispatch to Best Specialist**:
   - If Playwright/Scraping -> `e2e-runner` + `e2e-testing` skill.
   - If Python logic/data -> `python-reviewer` + `python-patterns` skill.
   - If bug/crash -> `silent-failure-hunter` or `build-error-resolver`.
   - If architecture/feature -> `architect` + `/plan`.
4. **Execute & Report**: Provide full transparency with the selected toolchain.
