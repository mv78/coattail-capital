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

### Agent Discovery

All agents are registered in **`agents.json`** for Claude Code discovery. You can:

- View all agents and their roles: `cat agents.json | jq '.agents[] | {name, role, file}'`
- See which agent to use: `cat agents.json | jq '.quick_reference."I want to..."'`
- Follow a workflow: `cat agents.json | jq '.workflows'`

---

## Agent Specifications

See individual files below. For quick reference, see `agents.json`:

| Agent | Role | File | Use When |
|---|---|---|---|
| **BMAD Expert** | Process reviewer & coach | `bmad-expert-agent.md` | Validating BMAD compliance, getting next steps |
| **Business Analyst** | Requirements engineer | `ba-agent.md` | Writing PRD from business goals |
| **Solutions Architect** | System designer | `architect-agent.md` | Designing architecture from PRD |
| **Data Engineer** | Code builder | `data-engineer-agent.md` | Building PySpark streaming code |
| **DevOps Engineer** | Infrastructure builder | `devops-agent.md` | Building Terraform & CI/CD |
| **Security Engineer** | Security reviewer | `security-agent.md` | Security review & hardening |
| **QA Engineer** | Test designer | `qa-agent.md` | Designing tests & quality gates |
