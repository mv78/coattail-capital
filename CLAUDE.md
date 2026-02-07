# Coat Tail Capital 🐋

> "Riding smart money so you don't have to think"

## Project Overview

Real-time whale tracking and alpha scoring platform built with PySpark Structured Streaming on AWS. This is a portfolio project demonstrating Principal-level Big Data Architecture skills.

**Contributors:**
- Mike Veksler — Principal Architect, PySpark Lead (GitHub: mveksler)
- Frank D'Avanzo — Engineering Manager, BMAD Coach (GitHub: TheFrankBuilder)

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
├── docs/                      # Documentation
│   ├── PRD.md                 # Product requirements (START HERE)
│   ├── ARCHITECTURE.md        # System design (generate this)
│   ├── WELL-ARCHITECTED.md    # AWS WAF analysis (generate this)
│   ├── ADR.md                 # Architecture decision records
│   └── RUNBOOK.md             # Weekend execution guide
├── agents/                    # BMAD agent prompts
│   ├── ba-agent.md            # Business Analyst
│   ├── architect-agent.md     # Solutions Architect
│   ├── data-engineer-agent.md # Data Engineer
│   ├── security-agent.md      # Security Engineer
│   ├── devops-agent.md        # DevOps Engineer
│   └── qa-agent.md            # QA Engineer
├── infra/                     # Terraform infrastructure
│   ├── main.tf                # Root module composition
│   ├── variables.tf           # Input variables
│   ├── outputs.tf             # Output values
│   └── modules/               # Terraform modules
│       ├── kinesis/
│       ├── s3-lakehouse/
│       ├── emr-serverless/
│       ├── glue/
│       ├── iam/
│       ├── monitoring/
│       ├── step-functions/
│       └── lake-formation/
├── src/                       # Application code (to be built)
│   ├── producer/              # Kinesis producer
│   ├── spark-jobs/
│   │   ├── streaming/         # Real-time jobs
│   │   ├── batch/             # Historical/reprocessing
│   │   └── common/            # Shared modules
│   ├── api/                   # Lambda handlers
│   └── dashboard/             # React frontend
├── scripts/                   # Operational scripts
│   ├── start.sh
│   ├── stop.sh
│   └── bootstrap-state.sh
└── tests/                     # Test files (to be built)
```

## Development Workflow

### Using BMAD Agents

This project uses BMAD (Business-Manager-Architect-Developer) method. Each agent in `agents/` is a specialized prompt. To use an agent:

```bash
# Load an agent's context and give it a task
claude "$(cat agents/data-engineer-agent.md)

Build the Kinesis producer in src/producer/ that connects to Binance WebSocket..."
```

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
- PRD with data quality, batch processing sections
- 6 BMAD agent specifications
- 9 Terraform modules (Kinesis, S3, EMR, Glue, IAM, Monitoring, Step Functions, Lake Formation)
- 6 Architecture Decision Records
- Weekend runbook
- GitHub Actions CI

### 🚧 To Build (Application Code)
- [ ] Kinesis producer (Binance + Coinbase WebSocket)
- [ ] PySpark streaming jobs (volume anomaly, whale detector, spread calculator)
- [ ] Data quality module
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
4. `agents/data-engineer-agent.md` — Detailed specs for PySpark jobs

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
- **Architecture:** `docs/ARCHITECTURE.md` (to be generated)
- **Runbook:** `docs/RUNBOOK.md`
- **Mike's LinkedIn:** https://www.linkedin.com/in/mikeveksler-798b7913
- **Frank's GitHub:** https://github.com/TheFrankBuilder
