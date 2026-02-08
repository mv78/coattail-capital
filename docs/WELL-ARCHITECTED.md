# AWS Well-Architected Framework Review: Coat Tail Capital

> "Riding smart money so you don't have to think"

## Document Control

| Field | Value |
|---|---|
| **Project** | Coat Tail Capital (CTC) |
| **Version** | 1.0 |
| **Authors** | Mike Veksler (Principal Architect), Frank D'Avanzo (Head of Agentic AI & Strategic Fly-Bys, BMAD-Method Coach) |
| **Framework Version** | AWS WAF 2024 (6 pillars) |
| **Scope** | Full platform review |

---

## Pillar 1: Operational Excellence

**Design Principle:** Perform operations as code. Make frequent, small, reversible changes.

### Decisions

| Area | Implementation | Evidence |
|---|---|---|
| **Infrastructure as Code** | All resources in Terraform (8 modules, 12 variables, 13 outputs) | `infra/` — single `terraform apply` deploys full stack |
| **CI/CD** | GitHub Actions: lint, type-check, test, terraform validate, security scan | `.github/workflows/ci.yml` — blocking quality gates |
| **Observability** | CloudWatch dashboard (5 widgets), 3 alarms, custom `CryptoPulse/*` metrics | `infra/modules/monitoring/` |
| **Runbooks** | Hour-by-hour execution guide with rollback procedures | `docs/RUNBOOK.md` |
| **Start/Stop Lifecycle** | Shell scripts for cost-controlled demo operation | `scripts/start.sh`, `scripts/stop.sh` |
| **Configuration Management** | SSM Parameter Store for runtime config (6 parameters) | No secrets in code, service discovery via SSM |
| **Agent Specs** | 7 BMAD agent prompts with input/output contracts | `agents/` — reproducible AI-assisted development |

### Improvement Opportunities

- Add structured logging with correlation IDs across streaming jobs
- Add CloudWatch anomaly detection on the `RecordsProcessed` metric
- Create operational dashboards per streaming job (not just infrastructure)

---

## Pillar 2: Security

**Design Principle:** Apply security at all layers. Enable traceability.

### Decisions

| Area | Implementation | Evidence |
|---|---|---|
| **IAM Least Privilege** | 3 roles scoped to specific ARNs: EMR (read/write specific buckets), Producer (write-only to 1 stream), Lambda (read-only on 1 table) | `infra/modules/iam/main.tf` |
| **Encryption at Rest** | AES256 with bucket key (S3), KMS AWS-managed key (Kinesis), SSE (DynamoDB) | All storage modules |
| **Encryption in Transit** | TLS for all AWS API calls, WSS for exchange WebSockets | AWS SDK defaults + WebSocket config |
| **No Secrets in Code** | SSM Parameter Store for config, no API keys for public data sources | 6 SSM parameters in `main.tf` |
| **Data Governance** | Lake Formation with database/table permissions, LF-Tags for classification | `infra/modules/lake-formation/` |
| **Analyst Access Control** | Dedicated analyst role with MFA requirement, read-only permissions | Lake Formation module |
| **Security Scanning** | tfsec + checkov in CI pipeline (blocking) | `.github/workflows/ci.yml` |
| **Public Data Only** | No PII, no user data, no API keys for data ingestion | PRD Section 11 (AI Safety) |

### Improvement Opportunities

- Add VPC + VPC Endpoints for network isolation (see Architecture doc: production recommendation)
- Scope Lambda `AWSLambdaBasicExecutionRole` to specific log groups
- Add WAF in front of API Gateway for rate limiting
- Enable CloudTrail for Lake Formation audit logging

---

## Pillar 3: Reliability

**Design Principle:** Automatically recover from failure. Test recovery procedures.

### Decisions

| Area | Implementation | Evidence |
|---|---|---|
| **Dead Letter Queue** | Kinesis DLQ stream (48h retention) for malformed records | `infra/modules/kinesis/` |
| **Spark Checkpointing** | S3-based checkpoints every 60s with TRIM_HORIZON recovery | Architecture doc Section 4.5 |
| **Data Quality DLQ** | S3 DLQ zone with categorized failure paths (malformed, incomplete, invalid) | PRD Section 9.4 |
| **Idempotent Writes** | DynamoDB `alert_id` as partition key prevents duplicate alerts | `main.tf` DynamoDB table |
| **Watermarking** | 30s (volume), 15s (spread) for late data tolerance | Architecture doc Section 4 |
| **Multi-AZ by Default** | Kinesis, S3, DynamoDB, Lambda — all multi-AZ natively | AWS managed |
| **Batch Error Handling** | Step Functions retry + catch patterns, SNS failure alerts | `infra/modules/step-functions/` |
| **S3 Versioning** | Enabled on processed bucket (Iceberg metadata protection) | `infra/modules/s3-lakehouse/` |

### Improvement Opportunities

- Add circuit breaker pattern for exchange WebSocket disconnections
- Configure EMR Serverless job retry policy (currently single attempt)
- Add DynamoDB PITR for disaster recovery (disabled for cost savings)
- Test Iceberg time-travel recovery procedure end-to-end

---

## Pillar 4: Performance Efficiency

**Design Principle:** Use serverless to remove operational burden. Go global in minutes.

### Decisions

| Area | Implementation | Evidence |
|---|---|---|
| **Serverless Compute** | EMR Serverless (auto-scaling), Lambda (per-invocation), DynamoDB (on-demand) | All services scale automatically |
| **Kinesis ON_DEMAND** | Auto-scaling shards, no capacity planning | ADR-001 |
| **EMR Initial Capacity** | Pre-warmed 1 driver (2 vCPU, 4GB) to reduce cold start | `infra/modules/emr-serverless/` |
| **Iceberg Table Format** | Hidden partitioning for query optimization, partition pruning | ADR-002 |
| **DynamoDB GSIs** | 2 GSIs (`type-time`, `symbol-time`) for efficient API query patterns | `main.tf` DynamoDB table |
| **S3 Bucket Keys** | Enabled for efficient SSE-S3 encryption (reduced KMS calls) | `infra/modules/s3-lakehouse/` |
| **Spark 3.4** | Latest EMR 7.0 runtime with improved Structured Streaming | ADR-003 |
| **Tumbling Windows** | 60s (volume), 30s (spread) — balances latency vs. compute | Architecture doc Section 4 |

### Improvement Opportunities

- Profile Spark job memory usage and right-size EMR max capacity
- Add API Gateway caching for GET /metrics (10s TTL matches dashboard poll interval)
- Consider Kinesis Enhanced Fan-Out if consumer count grows beyond 2

---

## Pillar 5: Cost Optimization

**Design Principle:** Implement cloud financial management. Adopt a consumption model.

### Decisions

| Area | Implementation | Evidence |
|---|---|---|
| **Serverless-First** | Every service is pay-per-use or scale-to-zero | No idle cost outside S3 storage |
| **Billing Alarm** | $25 threshold, 6h evaluation, SNS notification | `infra/modules/monitoring/` |
| **EMR Auto-Stop** | 15 minutes idle → automatic shutdown | `infra/modules/emr-serverless/` |
| **DynamoDB TTL** | Alerts auto-expire after 24h | `main.tf` DynamoDB table |
| **S3 Lifecycle** | Raw: IA at 30d, delete at 90d. Checkpoints: delete at 7d. Athena: delete at 7d | `infra/modules/s3-lakehouse/` |
| **Start/Stop Scripts** | Manual cost control for streaming components | `scripts/start.sh`, `scripts/stop.sh` |
| **DynamoDB PITR Disabled** | Cost savings for portfolio project (~$0.20/GB/month saved) | `main.tf` — `point_in_time_recovery = false` |
| **No NAT Gateway** | Serverless-first, no VPC needed — saves ~$32/month | Architecture doc Section 7 |

### Cost Summary

| Mode | Cost |
|---|---|
| Active demo | ~$0.82/hour |
| Idle | < $0.01/day |
| Monthly (2h demo/week) | ~$7-8/month |

### Improvement Opportunities

- Add a cost anomaly detector (AWS Cost Anomaly Detection — free)
- Add a Lambda-based auto-stop if billing exceeds $50 (emergency shutoff)
- Consider S3 Intelligent-Tiering for processed bucket if access patterns are unpredictable

---

## Pillar 6: Sustainability

**Design Principle:** Understand your impact. Minimize required resources.

### Decisions

| Area | Implementation | Evidence |
|---|---|---|
| **Right-Sized Compute** | EMR Serverless max 4 vCPU / 8GB — minimal for 3 streaming jobs | `infra/modules/emr-serverless/` |
| **Efficient Data Formats** | Parquet (columnar, compressed) via Iceberg — ~10x smaller than raw JSON | Iceberg table format |
| **Scale-to-Zero** | All services stop consuming resources when inactive | Serverless architecture |
| **Data Retention** | Aggressive lifecycle policies prevent unbounded storage growth | S3 lifecycle rules |
| **Minimal Polling** | Dashboard polls every 10s (not real-time WebSocket — reduces API calls) | PRD Section 10.2 |

### Improvement Opportunities

- Measure and document carbon footprint per demo session
- Consider Graviton instances if EMR Serverless supports ARM workers

---

## Summary Scorecard

| Pillar | Score (1-5) | Key Strength | Key Gap |
|---|---|---|---|
| Operational Excellence | 4 | Full IaC, CI/CD, runbooks, BMAD agents | No structured logging with correlation IDs |
| Security | 4 | Least-privilege IAM, encryption everywhere, LF governance | No VPC (justified for serverless), Lambda role could be tighter |
| Reliability | 4 | DLQ, checkpointing, watermarks, idempotent writes | No EMR job retry policy, PITR disabled |
| Performance Efficiency | 4 | Serverless auto-scaling, pre-warmed EMR, Iceberg partitioning | No API caching yet |
| Cost Optimization | 5 | ~$0.82/hr active, <$0.01/day idle, aggressive lifecycle | Could add auto-shutoff Lambda |
| Sustainability | 4 | Right-sized, efficient formats, scale-to-zero | No carbon footprint measurement |

**Overall: 4.2 / 5** — Strong Well-Architected compliance for a portfolio project. Gaps are documented with production recommendations in `docs/ARCHITECTURE.md` Appendix B.
