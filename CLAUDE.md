# Coat Tail Capital 🐋

> "Riding smart money so you don't have to think"

## Project Overview

Real-time whale tracking and alpha scoring platform built with PySpark Structured Streaming on AWS. This is a portfolio project demonstrating Principal-level Big Data Architecture skills.

**Contributors:**
- Mike Veksler — Principal Architect, PySpark Lead (GitHub: mveksler)
- Frank D'Avanzo — Head of Agentic AI & Strategic Fly-Bys, BMAD-Method Coach (GitHub: TheFrankBuilder)

## Tech Stack

- **Streaming:** Kinesis Data Streams → PySpark Structured Streaming → Apache Iceberg
- **Compute:** EMR Serverless (Spark 3.4)
- **Storage:** S3 Iceberg lakehouse, DynamoDB (alerts), Glue Data Catalog
- **Orchestration:** Step Functions + EventBridge
- **Governance:** Lake Formation
- **IaC:** Terraform (modular, remote state in S3)
- **CI/CD:** GitHub Actions

## Repository Structure

```
coattail-capital/
├── _bmad/                     # BMAD v6 method (agents, workflows, configs)
│   ├── _config/               # Manifests, agent customizations
│   ├── core/                  # Core platform (bmad-master, brainstorming, party-mode)
│   └── bmm/                   # BMM module (10 agents, 25 workflows)
├── _bmad-output/              # BMAD artifacts (sprint-status, stories, specs)
│   ├── planning-artifacts/    # PRDs, architecture docs, epics
│   └── implementation-artifacts/ # Story files, tech specs
├── .claude/
│   └── commands/              # BMAD v6 slash commands (41 commands)
├── agents/                    # Legacy BMAD agent prompts (pre-v6 reference)
├── config/                    # Feature configuration
│   ├── features.yaml          # Active module config
│   └── tiers/                 # Tier definitions (small/medium/large)
├── docs/                      # Documentation
│   ├── PRD.md                 # Product requirements (START HERE)
│   ├── MODULE_REGISTRY.md     # Feature module catalog (11 modules)
│   ├── ARCHITECTURE.md        # System design
│   ├── WELL-ARCHITECTED.md    # AWS WAF analysis
│   ├── ADR.md                 # Architecture decision records
│   └── RUNBOOK.md             # Weekend execution guide
├── infra/                     # Terraform infrastructure
│   ├── main.tf                # Root module + tier locals + feature SSM
│   ├── variables.tf           # Input variables + feature_tier + module toggles
│   ├── outputs.tf             # Output values
│   └── modules/               # Terraform modules (8 modules)
├── src/                       # Application code (to be built)
│   ├── producer/              # Kinesis producer
│   ├── connectors/            # Data source implementations
│   ├── detectors/             # Feature module implementations
│   ├── spark-jobs/
│   │   ├── framework/         # Plugin framework (base classes)
│   │   ├── batch/             # Historical/reprocessing
│   │   └── common/            # Shared modules
│   ├── api/                   # Lambda handlers
│   └── dashboard/             # React frontend
├── scripts/                   # Operational scripts
└── tests/                     # Test files (to be built)
```

## Development Workflow

### BMAD v6 Method

This project uses [BMAD v6.0.0-Beta.8](https://github.com/bmad-code-org/BMAD-METHOD) with Claude Code integration. The method provides 10 agents, 25 workflows, and 41 native slash commands.

**Get oriented:**
```
/bmad-help                          # What to do next, which workflow to run
/bmad-party-mode                    # Multi-agent group discussion
```

**Phase 1 — Analysis:**
```
/bmad-bmm-create-product-brief      # Business Analyst (Mary) creates product brief
/bmad-bmm-domain-research           # Domain research with web sources
/bmad-bmm-market-research           # Market/competitive research
```

**Phase 2 — Planning:**
```
/bmad-bmm-create-prd                # Product Manager (John) creates PRD
/bmad-bmm-validate-prd              # Validate existing PRD against BMAD standards
/bmad-bmm-create-ux-design          # UX Designer (Sally) creates UX spec
```

**Phase 3 — Solutioning:**
```
/bmad-bmm-create-architecture       # Architect (Winston) designs system
/bmad-bmm-create-epics-and-stories  # Break PRD into epics and stories
/bmad-bmm-check-implementation-readiness  # Gate check before coding
```

**Phase 4 — Implementation:**
```
/bmad-bmm-sprint-planning           # Generate sprint-status.yaml
/bmad-bmm-create-story              # Scrum Master (Bob) prepares next story
/bmad-bmm-dev-story                 # Developer (Amelia) implements story
/bmad-bmm-code-review               # Adversarial code review
/bmad-bmm-retrospective             # Post-epic retrospective
```

**Quick Flow (small tasks):**
```
/bmad-bmm-quick-spec                # Barry creates lean tech spec
/bmad-bmm-quick-dev                 # Barry implements from spec or instructions
```

**Load a specific agent directly:**
```
/bmad-agent-bmm-dev                 # Amelia — Senior Software Engineer
/bmad-agent-bmm-architect           # Winston — System Architect
/bmad-agent-bmm-sm                  # Bob — Scrum Master
/bmad-agent-bmm-qa                  # Quinn — QA Engineer
/bmad-agent-bmad-master             # BMad Master — Orchestrator
```

> **Note:** Legacy agent prompts are preserved in `agents/` for project-specific reference (especially `data-engineer-agent.md` with PySpark framework specs). BMAD v6 agents live in `_bmad/bmm/agents/`.

### Key Commands

```bash
# Deploy infrastructure
cd infra && terraform init && terraform apply

# Start streaming pipeline
./scripts/start.sh

# Stop streaming (save costs)
./scripts/stop.sh

# Run tests
pytest tests/ -v
```

## Current State

### ✅ Completed (Specs & Infrastructure)
- PRD with modular feature architecture (tiers: Small/Medium/Large)
- Module Registry with 11 feature modules (MOD-001 through MOD-011)
- Architecture document with generic connector → detector → sink pipeline
- Well-Architected Framework review (6 pillars)
- 9 Terraform modules + feature tier system (tier-aware EMR sizing, SSM parameters)
- 7 Architecture Decision Records (ADR-007: Modular Feature Architecture)
- Feature configuration system (config/features.yaml + tier YAMLs)
- Weekend runbook
- GitHub Actions CI
- BMAD v6.0.0-Beta.8 installed with Claude Code integration (10 agents, 25 workflows, 41 slash commands)

### 🚧 To Build (Application Code)
- [ ] Module framework (BaseConnector, BaseDetector, AlertRouter, ModuleRegistry, ConfigLoader, PipelineRunner)
- [ ] Connector implementations (Binance, Coinbase as BaseConnector subclasses)
- [ ] Small tier detectors (volume-anomaly, whale-detector, spread-calculator)
- [ ] Config-driven data quality module
- [ ] Kinesis producer with connector manager
- [ ] Batch jobs (historical loader, reprocessor)
- [ ] Lambda API handlers
- [ ] React dashboard

### 🔮 Future Phases
- [ ] On-chain whale tracking (Ethereum, Solana)
- [ ] Wallet alpha scoring
- [ ] Signal generation
- [ ] Hyperliquid execution engine

## Coding Standards

### Python
- Python 3.11+
- Type hints required
- Docstrings for public functions
- Use `ruff` for linting
- Use `mypy` for type checking
- Use `pytest` for testing

### PySpark
- DataFrame API only (no RDDs)
- Structured Streaming with checkpointing
- Watermarking for late data
- Iceberg sinks via Glue Catalog

### Terraform
- Modular design (one module per service group)
- All resources tagged
- Remote state in S3 with DynamoDB locking
- No hardcoded values

## Important Files to Read First

1. `docs/PRD.md` — Full requirements, schemas, data quality specs
2. `docs/ADR.md` — Why we chose Kinesis over MSK, Iceberg over Delta, etc.
3. `docs/RUNBOOK.md` — Hour-by-hour weekend execution plan
4. `agents/data-engineer-agent.md` — Detailed specs for PySpark jobs (legacy, still authoritative for framework)
5. `_bmad/_config/workflow-manifest.csv` — All available BMAD workflows
6. `_bmad/_config/agent-manifest.csv` — All available BMAD agents

## Environment Variables

```bash
# AWS
export AWS_REGION=us-west-2
export AWS_PROFILE=default  # or your profile

# Kinesis Producer
export KINESIS_STREAM_NAME=coattail-trades
export SYMBOLS=btcusdt,ethusdt,solusdt

# Spark Jobs (set via Terraform outputs)
export CHECKPOINT_BUCKET=coattail-dev-checkpoint-{account_id}
export PROCESSED_BUCKET=coattail-dev-processed-{account_id}
export ALERTS_TABLE=coattail-dev-alerts
export GLUE_DATABASE=coattail_dev_lakehouse
```

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires deployed infrastructure)
pytest tests/integration/ -v --tb=short

# Specific test file
pytest tests/unit/test_volume_anomaly.py -v
```

## Deployment

```bash
# First time setup
./scripts/bootstrap-state.sh
cd infra
terraform init

# Deploy all infrastructure
terraform plan -out=plan.tfplan
terraform apply plan.tfplan

# View outputs (stream names, bucket names, etc.)
terraform output

# Destroy when done
terraform destroy
```

## Cost Control

- Billing alarm at $25 (auto-configured)
- Use `./scripts/stop.sh` when not demoing
- EMR Serverless auto-stops after 15 min idle
- DynamoDB TTL expires alerts after 24h
- S3 lifecycle moves to IA after 30d, deletes after 90d

## Links

- **PRD:** `docs/PRD.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Runbook:** `docs/RUNBOOK.md`
- **Mike's LinkedIn:** https://www.linkedin.com/in/mikeveksler-798b7913
- **Frank's GitHub:** https://github.com/TheFrankBuilder
