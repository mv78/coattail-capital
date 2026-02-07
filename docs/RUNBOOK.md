# Weekend Runbook: Coat Tail Capital 🐋

> "Riding smart money so you don't have to think"

## Pre-Weekend Checklist (Do This Friday Night)

### Both Participants
- [ ] AWS account with admin access (or pre-provisioned IAM user)
- [ ] AWS CLI configured: `aws sts get-caller-identity` works
- [ ] Terraform 1.5+ installed: `terraform version`
- [ ] Python 3.11+ installed: `python3 --version`
- [ ] Claude Code CLI installed and authenticated: `claude --version`
- [ ] GitHub account with SSH key configured
- [ ] Docker installed (optional, for local Spark testing)
- [ ] VS Code or preferred editor ready

### Repository Setup
- [ ] One person creates the GitHub repo from this template
- [ ] Both add as collaborators
- [ ] Clone locally: `git clone git@github.com:YOUR_ORG/crypto-pulse-analytics.git`
- [ ] Create feature branches: `day1/infra`, `day1/producer`, `day2/spark`, `day2/dashboard`

### AWS Bootstrap
```bash
# Set your region
export AWS_REGION=us-west-2

# Run the state bootstrap (creates S3 bucket + DynamoDB for Terraform state)
./scripts/bootstrap-state.sh

# Uncomment the backend config in infra/backend.tf
# Then: terraform init
```

---

## Day 1 — Saturday (6-8 hours)

### Session 1A: BMAD Kickoff & Spec Review (2 hours)

**Goal:** Review specs, customize for your preferences, establish working patterns.

#### Hour 1: Claude Code Orientation (Mike focus)

```bash
# Mike: First Claude Code session — use it to explore the repo
claude "Read the docs/PRD.md and summarize the key technical decisions.
Then read agents/README.md and explain the BMAD workflow."

# Practice: Have Claude Code review a file
claude "Review infra/modules/iam/main.tf and check if IAM policies
follow least-privilege. Suggest improvements."
```

**Frank coaches Mike on:**
- Claude Code slash commands (`/help`, `/compact`, `/clear`)
- How to feed agent prompts as context
- Review-approve-commit workflow
- When to trust Claude Code output vs. when to verify

#### Hour 2: Spec Customization

```bash
# Run the Architect Agent to validate/enhance the architecture
claude "$(cat agents/architect-agent.md)

Review docs/PRD.md and docs/ARCHITECTURE.md (if exists).
Validate the service choices. Produce any updates to ARCHITECTURE.md
focusing on the PySpark Structured Streaming design and Iceberg table schema."
```

**Decisions to make together:**
- Which crypto pairs? (Default: BTC-USDT, ETH-USDT, SOL-USDT)
- Anomaly z-score threshold? (Default: 2.5)
- Whale threshold? (Default: $100K)
- AWS region? (Default: us-west-2)

**Commit:** Updated specs → `main` branch

---

### Session 1B: Infrastructure & Ingestion (4-6 hours)

#### Hours 3-4: Terraform Deploy

**Division of work:**
- **Frank:** Terraform modules review + apply
- **Mike:** Security review using the Security Agent

```bash
# Frank: Deploy infrastructure
cd infra
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan

# Verify outputs
terraform output
```

```bash
# Mike: Run Security Agent review
claude "$(cat agents/security-agent.md)

Review all files in infra/modules/ for security issues.
Focus on IAM policies, encryption, and public access.
Produce a brief security review."
```

**Checkpoint:** All infrastructure deployed, outputs saved.

#### Hours 5-6: Kinesis Producer

```bash
# Use Claude Code to build the producer from the Data Engineer spec
claude "$(cat agents/data-engineer-agent.md)

Build the Kinesis producer in src/producer/ that:
1. Connects to Binance WebSocket for btcusdt, ethusdt, solusdt @trade streams
2. Normalizes to the unified schema from docs/PRD.md section 6.3
3. Publishes to Kinesis with partition key = symbol
4. Handles reconnection with exponential backoff
5. Supports graceful shutdown

Use asyncio + websockets library. Include requirements.txt."
```

**Test the producer locally:**
```bash
cd src/producer
pip install -r requirements.txt

# Set environment variables
export KINESIS_STREAM_NAME=$(terraform -chdir=../../infra output -raw kinesis_stream_name)
export AWS_REGION=us-west-2
export SYMBOLS=btcusdt,ethusdt,solusdt

# Run for 2 minutes, verify records in Kinesis
python main.py &
sleep 120
kill %1

# Check Kinesis metrics in CloudWatch (or use AWS CLI)
aws kinesis describe-stream-summary --stream-name $KINESIS_STREAM_NAME
```

**Checkpoint:** Records flowing into Kinesis. Take a screenshot for LinkedIn.

#### End of Day 1 Wrap-up
- [ ] All infrastructure deployed via Terraform
- [ ] Producer running and publishing to Kinesis
- [ ] Security review completed
- [ ] Both Frank and Mike have commits in the repo
- [ ] Discuss any scope adjustments for Day 2

---

## Day 2 — Sunday (6-8 hours)

### Session 2A: PySpark Streaming Jobs + Data Quality (4 hours)

#### Hours 1-2: Write PySpark Jobs with Data Quality

```bash
# Use Claude Code with the Data Engineer agent
claude "$(cat agents/data-engineer-agent.md)

Build the PySpark Structured Streaming jobs in src/spark-jobs/:

STREAMING JOBS:
1. volume_anomaly.py - 60s tumbling window, z-score detection
2. whale_detector.py - Threshold-based large trade detection  
3. spread_calculator.py - Cross-exchange VWAP spread

DATA QUALITY MODULE (src/spark-jobs/common/quality.py):
- DataQualityChecker class with configurable checks
- Completeness checks: event_id, symbol, price, quantity, timestamp NOT NULL
- Validity checks: price > 0, quantity > 0, symbol in allowed list
- Timeliness check: timestamp within 5 minutes (warning only)
- CloudWatch metrics: RecordsProcessed, RecordsPassed, RecordsFailed, QualityScore
- DLQ routing: Write failed records to s3://{raw_bucket}/dlq/{reason}/dt={date}/

All jobs should:
- Read from Kinesis using spark.readStream
- Run data quality checks FIRST via DataQualityChecker
- Use Iceberg sink for S3 writes via Glue catalog
- Write alerts to DynamoDB using foreachBatch
- Checkpoint to S3
- Include watermarking for late data (30 seconds)

Include common/ modules for shared schemas, configs, quality, writers.
Include a submit.sh script for EMR Serverless submission."
```

**Division of work:**
- **Frank:** Data quality module + volume anomaly job (demonstrates DQ expertise)
- **Mike:** Whale detector + spread calculator (building Spark skills)

#### Hours 3-4: Batch Jobs + Deploy to EMR Serverless

```bash
# Build batch reprocessing jobs
claude "Build the batch PySpark jobs in src/spark-jobs/batch/:

1. historical_loader.py - Fetch historical trades from Binance REST API, write to S3 raw zone
2. reprocess_anomalies.py - Read from Iceberg with time-travel, recompute anomalies
3. schema_evolution_demo.py - Demo adding a column to Iceberg table without rewrite

Include proper logging, error handling, and CloudWatch metrics."
```

```bash
# Upload PySpark jobs to S3
PROCESSED_BUCKET=$(terraform -chdir=infra output -raw processed_bucket)
aws s3 cp src/spark-jobs/ s3://$PROCESSED_BUCKET/jobs/ --recursive

# Submit volume anomaly job to EMR Serverless
EMR_APP_ID=$(terraform -chdir=infra output -raw emr_application_id)
EMR_ROLE_ARN=$(terraform -chdir=infra output -raw emr_execution_role_arn)

aws emr-serverless start-job-run \
  --application-id $EMR_APP_ID \
  --execution-role-arn $EMR_ROLE_ARN \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://'$PROCESSED_BUCKET'/jobs/streaming/volume_anomaly.py",
      "sparkSubmitParameters": "--conf spark.jars.packages=org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2"
    }
  }'

# Verify data quality metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace CryptoPulse/Quality \
  --metric-name QualityScore \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

**Checkpoint:** 
- PySpark jobs running on EMR Serverless
- Data quality metrics visible in CloudWatch (QualityScore > 99%)
- Data landing in Iceberg tables
- Failed records in DLQ (if any)

---

### Session 2B: Dashboard, Docs & LinkedIn (2-4 hours)

#### Hour 5: Lambda API + Dashboard

```bash
# Build Lambda API handlers
claude "Build a Lambda function in src/api/ that:
1. GET /alerts - queries DynamoDB alerts table with optional type/symbol/limit filters
2. GET /metrics/{symbol} - returns latest metrics for a symbol
Include requirements.txt and SAM/Terraform deployment config."

# Build React dashboard
claude "$(cat agents/architect-agent.md)

Build a minimal React dashboard in src/dashboard/ using Vite + Recharts + TailwindCSS:
1. Header with live/paused indicator
2. Alert feed - scrolling list of recent anomalies
3. Volume chart - bar chart per symbol with anomaly markers
4. Spread tracker - line chart of cross-exchange spread
5. System health - simple status indicators

Fetch from API Gateway every 10 seconds.
Keep it clean and demo-ready."
```

#### Hour 6: Documentation & Principal-Level Polish

```bash
# Generate Well-Architected review
claude "$(cat agents/architect-agent.md)

Using the deployed architecture, write docs/WELL-ARCHITECTED.md with:
- One section per WAF pillar (all 6)
- Specific design decisions mapped to each pillar
- Tradeoffs acknowledged (this is a portfolio project, not production)
- Recommendations for production hardening"

# Verify ADRs are complete (already generated)
ls -la docs/ADR.md

# Test Step Functions batch workflow
SF_ARN=$(terraform -chdir=infra output -raw step_functions_arn)
aws stepfunctions start-execution \
  --state-machine-arn $SF_ARN \
  --input '{"date": "2025-02-04", "symbols": ["BTCUSDT"]}' \
  --name "test-run-$(date +%s)"

# Watch execution in console or CLI
aws stepfunctions describe-execution --execution-arn <EXECUTION_ARN>

# Test Lake Formation analyst role
ANALYST_ROLE=$(terraform -chdir=infra output -raw analyst_role_arn)
echo "Analyst role ready for Athena access: $ANALYST_ROLE"

# Generate comprehensive README
claude "Write a professional README.md for this repo that includes:
1. Project overview with architecture diagram (Mermaid)
2. Principal-level capabilities table (what this demonstrates)
3. Tech stack summary
4. Quick start guide including Step Functions batch
5. Cost analysis
6. Documentation links (PRD, Architecture, WAF, ADRs)
7. BMAD development methodology section
8. Contributors (Frank + Mike)
9. Well-Architected highlights table
10. AI safety statement
Make it LinkedIn-portfolio worthy for a Principal Architect role."
```

#### Hour 7-8: LinkedIn & Cleanup

- [ ] Run the QA agent for a final review
- [ ] Take demo screenshots (dashboard, CloudWatch, Athena query)
- [ ] Record a 2-minute demo video (optional but high impact)
- [ ] Draft LinkedIn posts:
  - **Frank's angle:** "Led a weekend sprint using BMAD agentic development to build a real-time streaming analytics platform. Mentored a colleague on PySpark + Claude Code."
  - **Mike's angle:** "Built a real-time crypto analytics platform using PySpark Structured Streaming on EMR Serverless. Designed with AWS Well-Architected principles. Looking for my next challenge in big data architecture."
- [ ] Run `scripts/stop.sh` to halt streaming and minimize costs

---

## Teardown (When Done Demoing)

```bash
# Stop streaming components
./scripts/stop.sh

# If fully done, destroy all infrastructure
cd infra
terraform destroy

# Delete Terraform state resources (optional)
./scripts/cleanup-state.sh
```

---

## Troubleshooting Quick Reference

| Problem | Fix |
|---|---|
| Kinesis throttling | Check shard count: `aws kinesis describe-stream-summary` |
| EMR job fails to start | Check execution role permissions, verify S3 paths |
| No data in Iceberg tables | Check Spark UI logs in S3, verify Glue catalog access |
| Producer disconnects | Check Binance WebSocket rate limits (5 connections/IP) |
| High costs | Run `./scripts/stop.sh` immediately, check billing dashboard |
| Terraform state lock | `terraform force-unlock <LOCK_ID>` |
| Dashboard CORS errors | Verify API Gateway CORS configuration |

---

## Key AWS CLI Commands Cheat Sheet

```bash
# Kinesis
aws kinesis list-streams
aws kinesis describe-stream-summary --stream-name crypto-pulse-trades
aws kinesis get-shard-iterator --stream-name crypto-pulse-trades --shard-id shardId-000000000000 --shard-iterator-type LATEST

# EMR Serverless
aws emr-serverless list-applications
aws emr-serverless list-job-runs --application-id <APP_ID>
aws emr-serverless get-job-run --application-id <APP_ID> --job-run-id <JOB_ID>
aws emr-serverless cancel-job-run --application-id <APP_ID> --job-run-id <JOB_ID>

# DynamoDB
aws dynamodb scan --table-name crypto-pulse-dev-alerts --limit 10
aws dynamodb describe-table --table-name crypto-pulse-dev-alerts

# Athena
aws athena start-query-execution --query-string "SELECT * FROM crypto_pulse_dev_lakehouse.volume_aggregates LIMIT 10" --result-configuration OutputLocation=s3://crypto-pulse-dev-athena-results-ACCOUNT_ID/

# Cost
aws ce get-cost-and-usage --time-period Start=2025-02-01,End=2025-02-06 --granularity DAILY --metrics UnblendedCost
```
