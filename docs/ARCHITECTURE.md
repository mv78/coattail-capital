# Architecture Document: Coat Tail Capital

> "Riding smart money so you don't have to think"

## Document Control

| Field | Value |
|---|---|
| **Project** | Coat Tail Capital (CTC) |
| **Version** | 1.0 |
| **Authors** | Mike Veksler (Principal Architect), Frank D'Avanzo (Head of Agentic AI & Strategic Fly-Bys, BMAD-Method Coach) |
| **Source PRD** | `docs/PRD.md` v1.0 |
| **ADRs** | `docs/ADR.md` (ADR-001 through ADR-007) |
| **Region** | us-west-2 (single region) |
| **Environment** | dev (single account) |

---

## 1. Architecture Overview

### 1.1 High-Level Data Flow — Generic Connector → Detector → Sink Pipeline

```mermaid
graph LR
    subgraph Connectors [Data Source Connectors]
        BN[Binance WS<br/>BaseConnector]
        CB[Coinbase WS<br/>BaseConnector]
        ETH[Ethereum RPC<br/>BaseConnector - Large]
        SOL[Solana RPC<br/>BaseConnector - Large]
    end

    subgraph Ingestion
        PR[Python Producer<br/>Connector Manager]
        KS[Kinesis Data Streams<br/>ON_DEMAND]
        DLQ[Kinesis DLQ<br/>Malformed Records]
    end

    subgraph Processing [EMR Serverless - PySpark 3.4]
        CL[ConfigLoader<br/>features.yaml + SSM]
        DQM[Data Quality Module<br/>Schema + Range + Dedup]
        MR[ModuleRegistry<br/>Active Detectors]
        PR2[PipelineRunner]
        D1[Detector 1<br/>BaseDetector]
        D2[Detector 2<br/>BaseDetector]
        DN[Detector N<br/>BaseDetector]
        AR[AlertRouter<br/>DDB + Iceberg]
    end

    subgraph Storage
        S3R[S3 Raw Zone<br/>Landing + DLQ]
        S3P[S3 Processed Zone<br/>Iceberg Tables]
        S3C[S3 Checkpoint<br/>Spark State]
        DDB[DynamoDB<br/>Hot Alerts / TTL 24h]
        GC[Glue Data Catalog<br/>Iceberg Metadata]
    end

    subgraph Serving
        LF[Lake Formation<br/>Governance]
        ATH[Athena<br/>Ad-hoc SQL]
        LAM[Lambda + API GW<br/>REST API]
        DASH[React Dashboard<br/>S3 + CloudFront]
    end

    subgraph Operations
        SF[Step Functions<br/>Batch Orchestration]
        EB[EventBridge<br/>Daily 02:00 UTC]
        CW[CloudWatch<br/>Dashboard + Alarms]
        SNS[SNS<br/>Notifications]
    end

    BN --> PR
    CB --> PR
    ETH -.-> PR
    SOL -.-> PR
    PR --> KS
    KS --> DLQ
    KS --> DQM
    CL --> MR
    MR --> PR2
    DQM --> PR2
    PR2 --> D1
    PR2 --> D2
    PR2 --> DN
    D1 --> AR
    D2 --> AR
    DN --> AR
    AR --> S3P
    AR --> DDB
    DQM -.-> S3R
    PR2 --> S3C
    S3P --> GC
    GC --> LF
    LF --> ATH
    DDB --> LAM
    LAM --> DASH
    EB --> SF
    SF --> PR2
    CW --> SNS
```

_Dashed lines indicate Large tier components (disabled in Small/Medium)._

### 1.2 ASCII Data Flow (Whiteboard Version)

```
[Connector 1] ──┐
[Connector 2] ──┤
[Connector N] ──┘
        │
        ▼
[Python Producer] ──→ [Kinesis ON_DEMAND] ──→ [Data Quality Module]
                            │                         │
                       [Kinesis DLQ]            pass   │   fail
                                                │      └──→ [S3 DLQ Zone]
                                                ▼
                                         [PipelineRunner]
                                    (reads config/features.yaml)
                                                │
                              ┌─────────────────┼─────────────────┐
                              ▼                 ▼                 ▼
                        [Detector 1]      [Detector 2]      [Detector N]
                        BaseDetector      BaseDetector       BaseDetector
                              │                 │                 │
                              └─────────────────┼─────────────────┘
                                                │
                                         [AlertRouter]
                                           │       │
                                    [DynamoDB]  [S3 Iceberg]
                                  Hot Alerts    via Glue Catalog
                                    (24h TTL)       │
                                        │      [Lake Formation]
                                        │           │
                                [Lambda + API GW]  [Athena SQL]
                                        │
                                [React Dashboard]
```

---

## 2. Service Inventory

| Service | Role | Resource Name | ADR | Justification |
|---|---|---|---|---|
| **Kinesis Data Streams** | Stream ingestion | `coattail-trades` | ADR-001 | ON_DEMAND, no shard management, 10-60x cheaper than MSK at our scale |
| **Kinesis DLQ** | Dead letter queue | `{prefix}-trades-dlq` | — | 48h retention for malformed record investigation |
| **EMR Serverless** | Spark compute | `{prefix}-spark` (EMR 7.0) | ADR-003 | Pay-per-second, Spark 3.4, zero idle cost, full PySpark control |
| **S3** | Lakehouse storage | 4 buckets: raw, processed, checkpoint, athena | — | Tiered lifecycle, AES256 encryption, versioning on processed |
| **Apache Iceberg** | Table format | Via Glue Catalog | ADR-002 | ACID, time-travel, schema/partition evolution, AWS-native |
| **Glue Data Catalog** | Metadata | `{prefix}_lakehouse` | — | Central schema registry, Iceberg catalog, Athena integration |
| **DynamoDB** | Hot alert store | `{prefix}-alerts` | — | PAY_PER_REQUEST, TTL 24h, SSE enabled, 2 GSIs |
| **Lambda** | API compute | 3 batch functions + API handler | — | Pay-per-invocation, zero idle cost |
| **API Gateway** | REST API | — | — | Throttling, caching, CORS |
| **Step Functions** | Batch orchestration | `{prefix}-batch-workflow` | ADR-004 | Zero idle cost, visual workflow, native EMR integration |
| **EventBridge** | Scheduling | Daily 02:00 UTC (disabled default) | ADR-004 | Serverless cron, no minimum cost |
| **Lake Formation** | Data governance | Hybrid IAM + LF mode | ADR-005 | Database/table permissions, LF-Tags, analyst role |
| **CloudWatch** | Monitoring | Dashboard + 3 alarms | — | Native integration, billing alarm at $25 |
| **SNS** | Notifications | `{prefix}-alarms` | — | Alarm delivery, Step Functions failure alerts |
| **SSM Parameter Store** | Configuration | 6 parameters | — | No secrets in code, service discovery |

---

## 3. Data Schemas

### 3.1 Ingestion: Unified Trade Event (Kinesis Payload)

All CEX connectors normalize to this schema:

```json
{
  "event_id": "uuid",
  "exchange": "binance|coinbase",
  "symbol": "BTC-USDT",
  "price": 67432.50,
  "quantity": 0.5,
  "quote_volume": 33716.25,
  "side": "buy|sell",
  "timestamp": "2025-02-05T10:30:00.123Z",
  "ingestion_timestamp": "2025-02-05T10:30:00.456Z"
}
```

### 3.2 Base Alert Record

All modules emit alerts conforming to this **base schema**. The `alert_type` field is an **open string** — new modules register new types without schema changes (see `docs/MODULE_REGISTRY.md` for the alert type registry).

| Column | Type | Description |
|---|---|---|
| `alert_id` | STRING | UUID |
| `alert_type` | STRING | Open string — e.g., `volume_spike`, `whale_trade`, `consensus_bullish` |
| `module_id` | STRING | Source module (e.g., `MOD-001`) |
| `symbol` | STRING | Trading pair |
| `exchange` | STRING | Source exchange (or `null` for cross-exchange/on-chain) |
| `severity` | STRING | `low \| medium \| high \| critical` |
| `detected_at` | TIMESTAMP | Alert generation time |
| `message` | STRING | Human-readable alert text |
| `ttl_epoch` | LONG | DynamoDB TTL (detected_at + 24h) |
| `details` | STRING (JSON) | Module-specific payload (see below) |

### 3.3 Module-Specific Alert Details

Each module packs its unique data into the `details` JSON field:

**volume-anomaly (MOD-001):**
```json
{"z_score": 3.2, "window_volume": 1500000, "rolling_mean": 450000, "rolling_stddev": 318182, "window_start": "..."}
```

**whale-detector (MOD-002):**
```json
{"quote_volume": 250000, "price": 67432.50, "quantity": 3.71, "side": "buy"}
```

**spread-calculator (MOD-003):**
```json
{"spread_pct": 0.72, "exchange_a_vwap": 67450.00, "exchange_b_vwap": 66965.00, "window_start": "..."}
```

**consensus (MOD-007):**
```json
{"consensus_score": 82, "volume_signal": 0.3, "whale_signal": 0.3, "flow_signal": 0.4, "contributing_alerts": [...]}
```

This pattern allows the base alert schema to remain stable while modules add arbitrary detail.

### 3.4 Storage: Iceberg Tables

Tables follow a **core + module-created** pattern:

**Core Tables (always present):**

| Table | Owner | Partition Strategy | Location |
|---|---|---|---|
| `raw_trades` | Platform (ingestion) | `date(timestamp), symbol` | `s3://processed/raw_trades/` |
| `anomaly_alerts` | Platform (all modules write) | `date(detected_at), alert_type` | `s3://processed/anomaly_alerts/` |

**Module-Created Tables (created when module is active):**

| Table | Owner Module | Partition Strategy | Location |
|---|---|---|---|
| `volume_aggregates` | MOD-001 | `date(window_start), symbol` | `s3://processed/volume_aggregates/` |
| `whale_trades` | MOD-002 | `date(detected_at), symbol` | `s3://processed/whale_trades/` |
| `exchange_spreads` | MOD-003 | `date(window_start), symbol` | `s3://processed/exchange_spreads/` |
| `wallet_scores` | MOD-004 | `date(scored_at), blockchain` | `s3://processed/wallet_scores/` |
| `labeled_wallets` | MOD-005 | Unpartitioned | `s3://processed/labeled_wallets/` |
| `flow_direction` | MOD-006 | `date(window_start), symbol` | `s3://processed/flow_direction/` |
| `consensus_signals` | MOD-007 | `date(window_start), symbol` | `s3://processed/consensus_signals/` |
| `onchain_events` | MOD-008 | `date(block_timestamp), blockchain` | `s3://processed/onchain_events/` |
| `dex_trades` | MOD-009 | `date(swap_timestamp), blockchain, protocol` | `s3://processed/dex_trades/` |
| `predictive_scores` | MOD-010 | `date(scored_at), symbol` | `s3://processed/predictive_scores/` |
| `backtest_results` | MOD-011 | `date(backtest_date), module_id` | `s3://processed/backtest_results/` |

Module-created tables are provisioned by the detector on first run. Disabled modules = no table created. All tables use Iceberg hidden partitioning.

See `docs/MODULE_REGISTRY.md` for complete table specifications per module.

### 3.4 DynamoDB: Alerts Table Design

| Attribute | Type | Role |
|---|---|---|
| `alert_id` | S | Partition key |
| `detected_at` | S | Sort key (ISO timestamp) |
| `alert_type` | S | GSI-1 partition key |
| `symbol` | S | GSI-2 partition key |
| `ttl_epoch` | N | TTL attribute (24h auto-expiry) |

**Global Secondary Indexes:**

| GSI | Hash Key | Range Key | Purpose |
|---|---|---|---|
| `type-time-index` | `alert_type` | `detected_at` | GET /alerts?type=whale |
| `symbol-time-index` | `symbol` | `detected_at` | GET /alerts?symbol=BTC-USDT |

---

## 4. Streaming Architecture — Module Framework

All stream processing uses a modular pipeline architecture (ADR-007). A single PySpark Structured Streaming application loads active detectors from configuration and routes their output through a shared alert pipeline.

### 4.1 Pipeline Architecture

```
[Kinesis Stream] → [ConfigLoader] → [Data Quality Module] → [PipelineRunner]
                    reads features.yaml                           │
                    + SSM params                    ┌─────────────┼─────────────┐
                                                    ▼             ▼             ▼
                                              [Detector 1]  [Detector 2]  [Detector N]
                                              BaseDetector  BaseDetector   BaseDetector
                                                    │             │             │
                                                    └─────────────┼─────────────┘
                                                                  │
                                                           [AlertRouter]
                                                             │       │
                                                      [DynamoDB]  [S3 Iceberg]
```

**Key classes:**

| Class | Location | Responsibility |
|---|---|---|
| `BaseConnector` | `src/spark-jobs/framework/base_connector.py` | Data source abstraction |
| `BaseDetector` | `src/spark-jobs/framework/base_detector.py` | Detection logic interface |
| `AlertRouter` | `src/spark-jobs/framework/alert_router.py` | Routes alerts to DDB + Iceberg |
| `ModuleRegistry` | `src/spark-jobs/framework/module_registry.py` | Discovers and instantiates modules |
| `ConfigLoader` | `src/spark-jobs/framework/config_loader.py` | Reads YAML + SSM configuration |
| `PipelineRunner` | `src/spark-jobs/framework/pipeline_runner.py` | Orchestrates full pipeline |

### 4.2 Small Tier Detectors (Reference Implementations)

These three detectors ship as the default Small tier. See `docs/MODULE_REGISTRY.md` for detailed specs.

**MOD-001: Volume Anomaly Detection**
- **Window:** 60-second tumbling, 30s watermark
- **Logic:** Aggregate volume per `(symbol, exchange)`. Rolling 1-hour mean/stddev. Z-score flagging at `|z| > 2.5`.
- **Sinks:** `volume_aggregates` (all windows) + `anomaly_alerts` (flagged only) + DynamoDB

**MOD-002: Whale Detection**
- **Processing:** Per-record (no windowing)
- **Logic:** Filter `quote_volume > $100K`. Severity tiers: `>$100K` medium, `>$500K` high, `>$1M` critical.
- **Sinks:** `whale_trades` + `anomaly_alerts` + DynamoDB

**MOD-003: Cross-Exchange Spread**
- **Window:** 30-second tumbling, 15s watermark
- **Logic:** VWAP per `(symbol, exchange)`. Spread = `(a_vwap - b_vwap) / b_vwap * 100`. Flag `|spread| > 0.5%`.
- **Sinks:** `exchange_spreads` + `anomaly_alerts` + DynamoDB

### 4.3 Data Quality Module (`src/spark-jobs/common/quality.py`)

Config-driven quality checker shared by all detectors. Quality rules are loaded from configuration, allowing modules to define additional checks.

**Validation Pipeline:**
```
Raw Record → Schema Validation → Null Checks → Range Validation → Deduplication → Timeliness Check → Valid Record
                  │ fail              │ fail          │ fail             │ dup              │ late
                  ▼                   ▼               ▼                 ▼                  ▼
            [DLQ: malformed]  [DLQ: incomplete]  [DLQ: invalid]   [Dropped, logged]  [Flagged, processed]
```

**Default Rules (extensible via config):**

| Dimension | Rule | Action |
|---|---|---|
| Completeness | Required fields not null: `event_id`, `symbol`, `price`, `quantity`, `timestamp` | Route to DLQ |
| Validity | `price > 0`, `quantity > 0`, `symbol` in configured list | Route to DLQ |
| Timeliness | `timestamp` within 5 minutes of processing time | Flag as late, still process |
| Consistency | `quote_volume ≈ price × quantity` (±0.1% tolerance) | Log warning, still process |
| Uniqueness | No duplicate `event_id` within 1-hour window | Deduplicate, keep first |

**CloudWatch Metrics Published:**
- `RecordsProcessed`, `RecordsPassed`, `RecordsFailed`, `RecordsLate`, `RecordsDuplicate`
- `QualityScore` = `RecordsPassed / RecordsProcessed × 100`
- Alarm: `QualityScore < 95%` for 5 minutes

### 4.4 Checkpointing & Fault Tolerance

| Setting | Value | Rationale |
|---|---|---|
| Checkpoint location | `s3://{prefix}-checkpoint/` | Durable, survives job restarts |
| Checkpoint interval | 60 seconds | Balances latency vs. S3 write cost |
| Starting position | `TRIM_HORIZON` | Recovers from last checkpoint on restart |
| Output mode | Append (aggregates), Update (rolling stats) | Appropriate for each sink type |
| Watermark | Per-detector (30s default) | Tolerates network jitter without excessive latency |
| S3 checkpoint expiry | 7 days | Prevents stale checkpoint accumulation |

---

## 5. Batch Architecture

### 5.1 Step Functions Workflow

```mermaid
graph TD
    EB[EventBridge<br/>Daily 02:00 UTC] --> HL
    HL[HistoricalLoad<br/>Lambda - 512MB, 300s] --> SSJ
    SSJ[SubmitSparkJob<br/>EMR Serverless] --> WFJ
    WFJ[WaitForJob<br/>Poll every 60s] --> |succeeded| RQC
    WFJ --> |failed| SA
    RQC[RunQualityChecks<br/>Lambda - 256MB, 120s] --> CQP
    CQP{CheckQualityPassed} --> |yes| UC
    CQP --> |no| SA
    UC[UpdateCatalog<br/>Lambda - 128MB, 60s] --> PS
    PS[PublishSuccess<br/>CloudWatch Metric] --> END[Done]
    SA[SendAlert<br/>SNS Notification] --> PF
    PF[PublishFailure<br/>CloudWatch Metric] --> FAIL[Failed]
```

**Schedule:** Daily 02:00 UTC (disabled by default — enable for demo)

### 5.2 Historical Loader

**Purpose:** Backfill historical trade data from Binance REST API
**API:** `GET /api/v3/aggTrades` with time range pagination (max 1000/request)
**Output:** S3 raw zone as Parquet, partitioned by `date` and `symbol`

### 5.3 Reprocessing

**Purpose:** Recompute anomalies after algorithm changes using Iceberg time-travel
**Input:** `raw_trades` table at specific snapshot or time range
**Output:** `anomalies_reprocessed` table for comparison and optional swap

```sql
-- Read data as of a specific snapshot
SELECT * FROM glue_catalog.coattail_dev_lakehouse.raw_trades
VERSION AS OF 123456789;

-- Read data as of a specific timestamp
SELECT * FROM glue_catalog.coattail_dev_lakehouse.raw_trades
TIMESTAMP AS OF '2025-02-01 00:00:00';
```

---

## 6. IAM Role Inventory

| Role | Trust Policy | Key Permissions | Principle of Least Privilege |
|---|---|---|---|
| **EMR Execution** | `emr-serverless.amazonaws.com` | S3 read/write (3 specific buckets), Kinesis read (1 stream), DynamoDB write (1 table), Glue catalog (1 database), CloudWatch metrics/logs | Scoped to specific ARNs, CloudWatch conditioned on `CryptoPulse` namespace |
| **Producer** | `ec2.amazonaws.com`, `ecs-tasks.amazonaws.com`, `lambda.amazonaws.com` | Kinesis `PutRecord`, `PutRecords`, `DescribeStream` (1 stream only) | Write-only to specific stream ARN |
| **Lambda API** | `lambda.amazonaws.com` | DynamoDB `GetItem`, `Query`, `Scan` (1 table + GSIs), CloudWatch basic execution | Read-only on specific table ARN |
| **Step Functions** | `states.amazonaws.com` | EMR Serverless `StartJobRun`, `GetJobRun`, Lambda invoke (3 functions), SNS publish, CloudWatch metrics | Scoped to specific function and application ARNs |
| **Analyst** | `iam.amazonaws.com` (MFA required) | Athena `StartQueryExecution`, Glue `GetTable/GetDatabase`, S3 read (processed + athena), Lake Formation `GetDataAccess` | Read-only, MFA enforced, no write access |

---

## 7. Network Architecture

**Decision: No VPC for serverless-first design.**

All services are serverless and communicate via AWS service endpoints:
- Kinesis, S3, DynamoDB, Glue, CloudWatch — all have public endpoints
- EMR Serverless — runs in AWS-managed VPC, no customer VPC needed
- Lambda — runs in AWS-managed network
- API Gateway — public endpoint with throttling

**Encryption:**
- At rest: AES256 (S3 bucket key), KMS (Kinesis), SSE (DynamoDB)
- In transit: TLS for all AWS API calls, WSS for exchange WebSocket connections

**Justification:** A customer VPC would add NAT Gateway costs (~$32/month) and PrivateLink endpoint costs with no security benefit for this architecture — all data is public market data, all storage is encrypted, and IAM provides access control. For enterprise deployments, a VPC with VPC endpoints would be recommended for compliance.

---

## 8. Monitoring Strategy

### 8.1 CloudWatch Dashboard Widgets

| Widget | Type | Metric | Purpose |
|---|---|---|---|
| Kinesis Incoming Records | Line chart | `IncomingRecords` | Verify data flowing |
| Kinesis Iterator Age | Line chart | `GetRecords.IteratorAgeMilliseconds` | Detect consumer lag |
| DynamoDB Write Capacity | Line chart | `ConsumedWriteCapacityUnits` | Alert activity monitor |
| Estimated Charges | Number | `EstimatedCharges` | Cost monitoring |
| Anomaly Alerts | Custom | `CryptoPulse/Alerts` | Alert volume tracking |

### 8.2 Alarms

| Alarm | Threshold | Evaluation | Action |
|---|---|---|---|
| Billing | > $25 | 1 of 1 periods (6h) | SNS notification |
| Kinesis Iterator Age | > 300,000 ms (5 min) | 3 of 3 periods (5 min) | SNS notification |
| DynamoDB Throttle | > 5 events | 2 of 2 periods (5 min) | SNS notification |
| Quality Score | < 95% | 5 minutes sustained | SNS notification |

### 8.3 Operational Metrics (Custom)

| Metric | Namespace | Published By |
|---|---|---|
| `RecordsProcessed` | `CryptoPulse/Quality` | Data Quality Module |
| `RecordsPassed` | `CryptoPulse/Quality` | Data Quality Module |
| `RecordsFailed` | `CryptoPulse/Quality` | Data Quality Module |
| `QualityScore` | `CryptoPulse/Quality` | Data Quality Module |
| `AnomalyCount` | `CryptoPulse/Alerts` | Streaming jobs |
| `WhaleCount` | `CryptoPulse/Alerts` | Whale detector |
| `SpreadAlertCount` | `CryptoPulse/Alerts` | Spread calculator |
| `BatchJobSuccess` | `CryptoPulse/Batch` | Step Functions |
| `BatchJobFailure` | `CryptoPulse/Batch` | Step Functions |

---

## 9. API Design

### 9.1 GET /alerts

**Query Parameters:**
| Param | Required | Default | Description |
|---|---|---|---|
| `type` | No | all | Any registered alert type (see `docs/MODULE_REGISTRY.md`) |
| `symbol` | No | all | e.g., `BTC-USDT` |
| `limit` | No | 50 | max 200 |
| `since` | No | 24h ago | ISO timestamp |

**DynamoDB Access Pattern:**
- No filter → Scan with `limit` (acceptable for low-volume table with TTL)
- By type → Query `type-time-index` GSI
- By symbol → Query `symbol-time-index` GSI
- By type + since → Query GSI with `detected_at > since` range condition

### 9.2 GET /metrics/{symbol}

**Response:** Aggregated current state for a symbol (latest volume window, latest spread, anomaly count, last whale).

**DynamoDB Access Pattern:** Query both GSIs filtered by symbol, aggregate in Lambda.

---

## 10. Cost Architecture — Per-Tier

Cost scales with the feature tier selected. Each tier adds modules and increases EMR sizing.

### 10.1 Active Cost by Tier

| Tier | EMR Config | Kinesis | DDB + Lambda | Total/Hour |
|---|---|---|---|---|
| **Small** | 4 vCPU, 8GB (3 detectors) | ~$0.50 | ~$0.02 | **~$0.82** |
| **Medium** | 6 vCPU, 12GB (7 detectors) | ~$0.63 | ~$0.07 | **~$1.40** |
| **Large** | 8 vCPU, 16GB (11 detectors + RPC) | ~$0.63 | ~$0.07 + $0.50 RPC | **~$2.50** |

### 10.2 Idle Mode (All Tiers)

| Service | Cost/Day |
|---|---|
| S3 storage (< 1GB) | < $0.01 |
| Everything else | $0.00 (serverless, scale-to-zero) |
| **Total idle** | **< $0.01/day** |

### 10.3 Cost Safety Controls

| Control | Mechanism | Threshold |
|---|---|---|
| Billing alarm | CloudWatch | $25 |
| EMR auto-stop | Auto-stop idle timeout | 15 minutes |
| DynamoDB TTL | Auto-purge old alerts | 24 hours |
| S3 lifecycle | Transition → IA → Delete | 30d → 90d |
| Checkpoint expiry | S3 lifecycle | 7 days |
| Athena results expiry | S3 lifecycle | 7 days |
| Start/Stop scripts | `scripts/start.sh`, `scripts/stop.sh` | Manual |
| Feature tier selection | `var.feature_tier` in Terraform | Controls EMR sizing |

---

## 11. Schema Evolution Strategy

Iceberg supports schema evolution without table rewrites:

```sql
-- Add a new column (instant metadata operation, no Parquet rewrite)
ALTER TABLE glue_catalog.coattail_dev_lakehouse.volume_aggregates
ADD COLUMN market_cap_rank INT;

-- Old data returns NULL for the new column
-- New data populates the field
-- Existing Parquet files are untouched
```

**Partition Evolution:** Iceberg allows changing partition schemes (e.g., from daily to hourly) without rewriting data. New data uses the new scheme; old data stays in place.

---

## 12. Deployment Architecture

### 12.1 Infrastructure (Terraform)

```
infra/
├── main.tf              # Root composition: 8 modules + DynamoDB + SSM
├── variables.tf         # 12 input variables with sensible defaults
├── outputs.tf           # 13 outputs for service discovery
├── providers.tf         # AWS provider config
├── backend.tf           # S3 remote state + DynamoDB locking
└── modules/
    ├── kinesis/          # Trade stream + DLQ
    ├── s3-lakehouse/     # 4 buckets with lifecycle policies
    ├── emr-serverless/   # Spark 3.4 application
    ├── glue/             # Data catalog database
    ├── iam/              # 3 roles with least-privilege policies
    ├── monitoring/       # Dashboard + 3 alarms + SNS
    ├── step-functions/   # 9-state batch workflow + 3 Lambdas + EventBridge
    └── lake-formation/   # Governance: permissions + LF-Tags + analyst role
```

### 12.2 Deployment Sequence

```bash
# 1. Bootstrap remote state
./scripts/bootstrap-state.sh

# 2. Deploy all infrastructure
cd infra && terraform init && terraform plan -out=plan.tfplan && terraform apply plan.tfplan

# 3. Verify outputs
terraform output

# 4. Start streaming
./scripts/start.sh

# 5. Stop when done
./scripts/stop.sh
```

### 12.3 CI/CD (GitHub Actions)

| Job | Trigger | Steps |
|---|---|---|
| `lint-and-test` | Push/PR to main | Python lint (ruff), type check (mypy), unit tests (pytest) |
| `terraform-validate` | Push/PR to main | `terraform fmt -check`, `terraform init -backend=false`, `terraform validate` |
| `security-scan` | Push/PR to main | tfsec, checkov — blocking on failure |

---

## 13. Extension Guide

This section explains how to extend Coat Tail Capital with new connectors, detectors, and tiers.

### 13.1 Adding a New Connector (Data Source)

1. **Create** `src/connectors/{name}_connector.py`
2. **Subclass** `BaseConnector`:
   ```python
   class KrakenConnector(BaseConnector):
       def connect(self) -> None: ...
       def normalize(self, raw: dict) -> TradeEvent: ...
       def health_check(self) -> bool: ...
       def shutdown(self) -> None: ...
   ```
3. **Register** in `config/features.yaml` under `exchange_connectors` or `blockchain_connectors`
4. **Update** `docs/MODULE_REGISTRY.md` if any modules depend on this connector

### 13.2 Adding a New Detector (Feature Module)

1. **Reserve** a module ID (next `MOD-XXX`) in `docs/MODULE_REGISTRY.md`
2. **Create** `src/detectors/{name}_detector.py`
3. **Subclass** `BaseDetector`:
   ```python
   class LiquidityDetector(BaseDetector):
       module_id = "MOD-012"
       module_name = "liquidity-monitor"

       def configure(self, config: dict) -> None: ...
       def process(self, df: DataFrame) -> DataFrame: ...
       def alert_types(self) -> list[str]: ...
       def output_table(self) -> str: ...
   ```
4. **Add** module spec to `docs/MODULE_REGISTRY.md`
5. **Add** module ID to the appropriate tier YAML in `config/tiers/`
6. **The PipelineRunner** auto-discovers the module on next deploy

### 13.3 Adding a New Tier

1. **Create** `config/tiers/{tier_name}.yaml` listing active module IDs
2. **Add** tier to `infra/variables.tf` validation list
3. **Add** tier to `tier_modules` locals in `infra/main.tf`
4. **Define** EMR sizing for the new tier in the `tier_emr_config` locals
5. **Update** cost table in `docs/PRD.md` and `docs/ARCHITECTURE.md`

### 13.4 Design Principles

- **Single Spark application** — all detectors share one EMR cluster. One bill, simpler ops.
- **YAML config over database flags** — version-controlled, reviewable in PRs.
- **SSM for runtime, YAML for logic** — infrastructure config in SSM, module behavior in YAML.
- **Framework first, then modules** — build BaseDetector/BaseConnector before implementing specific jobs.
- **Module isolation** — each detector is testable independently with mock DataFrames.

---

## Appendix A: Alternatives Not Chosen

| Component | Chosen | Rejected | Why |
|---|---|---|---|
| Stream broker | Kinesis | MSK Serverless, MSK Provisioned | 10-60x cheaper, simpler (ADR-001) |
| Table format | Iceberg | Delta Lake, Hudi | AWS-native Glue support, partition evolution (ADR-002) |
| Compute | EMR Serverless | Glue Streaming, EKS | Full PySpark control, portfolio differentiation (ADR-003) |
| Orchestration | Step Functions | MWAA (Airflow), EventBridge-only | Zero idle cost, visual workflow (ADR-004) |
| Governance | Lake Formation | IAM-only | Principal-level demonstration, future column security (ADR-005) |
| Data quality | Custom PySpark | Great Expectations, Deequ | Streaming-native, lightweight, demonstrates fundamentals (ADR-006) |
| Dashboard | React + S3 | Grafana, QuickSight | Custom portfolio piece, no server cost |
| Alert store | DynamoDB | RDS, ElastiCache | Serverless pricing, TTL cleanup, schema flexibility |
| IaC | Terraform | CDK, CloudFormation | Multi-cloud portable, state management |
| Feature architecture | Module-based composition | Phase-based scoping | Extensibility, per-module cost control, Principal-level design (ADR-007) |

---

## Appendix B: Production Recommendations

For enterprise deployments beyond this portfolio project:

| Area | Portfolio Choice | Production Recommendation |
|---|---|---|
| Streaming | Kinesis ON_DEMAND | MSK Serverless for Kafka ecosystem clients |
| Networking | No VPC | VPC + VPC Endpoints + PrivateLink |
| DynamoDB | PITR disabled | PITR enabled, cross-region backup |
| Security scans | Blocking in CI | Blocking + pre-commit hooks + SAST |
| Monitoring | CloudWatch | CloudWatch + PagerDuty/OpsGenie integration |
| Multi-region | Single region | Active-passive with S3 replication |
| Auth | None (public API) | Cognito + API key + WAF |
| Data quality | Custom module | Great Expectations or Glue Data Quality |
| Schema registry | Glue Catalog only | Confluent Schema Registry (if MSK) |
