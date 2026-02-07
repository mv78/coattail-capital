# BMAD Agent Specs for Coat Tail Capital 🐋

> "Riding smart money so you don't have to think"

## Overview

This directory contains the agent prompt specifications used in the [BMAD (Breakthrough Method for Agile AI Driven Development)](https://github.com/bmad-code-org/BMAD-METHOD) method. Each agent is a specialized Claude Code persona that produces specific artifacts consumed by downstream agents.

### Workflow Chain

```
                              BMAD Expert Agent
                          (Reviews & Coaches All Phases)
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
BA Agent → Architect Agent → Data Engineer Agent → DevOps Agent → Security Agent → QA Agent
   │              │                  │                  │               │              │
   ▼              ▼                  ▼                  ▼               ▼              ▼
  PRD      System Design      Spark Job Specs     Terraform +      Security       Test Specs
  User     Data Flow Docs     Schema DDL          CI/CD Configs    Review         Quality Gates
  Stories  Service Selection  Processing Logic    Deploy Scripts   IAM Policies   SLA Validation
```

### How to Use with Claude Code

Each agent file below can be used as a Claude Code task prompt. The recommended workflow:

1. Start a Claude Code session
2. Load the agent prompt as context: `claude "$(cat agents/ba-agent.md)"`
3. Provide the input artifacts referenced in the agent spec
4. Review the output, iterate, then commit to the repo
5. Move to the next agent in the chain

Alternatively, chain them in a single session by feeding outputs as inputs to the next agent.

---

## Agent Specifications

See individual files:
- `bmad-expert-agent.md` — BMAD-Method Expert (process reviewer & coach)
- `ba-agent.md` — Business Analyst
- `architect-agent.md` — Solutions Architect
- `data-engineer-agent.md` — Data Engineer
- `security-agent.md` — Security Engineer
- `devops-agent.md` — DevOps Engineer
- `qa-agent.md` — QA Engineer
