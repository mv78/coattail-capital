# Product Requirements Document: Coat Tail Capital

## Document Control

| Field | Value |
|---|---|
| **Project** | Coat Tail Capital (CTC) |
| **Tagline** | Riding smart money so you don't have to think 🐋 |
| **Version** | 1.0 |
| **Authors** | Mike Veksler (Principal Architect), Frank D'Avanzo (Head of Agentic AI & Strategic Fly-Bys, BMAD-Method Coach) |
| **Method** | BMAD Agentic Spec-Driven Development |
| **Target Completion** | Weekend Sprint (2 sessions × 6-8 hours) |
| **Repository** | github.com/mveksler/coattail-capital |

---

## 1. Executive Summary

Coat Tail Capital is a real-time streaming analytics platform that ingests public cryptocurrency market data, detects anomalies (volume spikes, whale movements, cross-exchange price divergence), tracks wallet alpha scores, and surfaces actionable insights through a dashboard and alert API.

The project serves as both a functional analytics tool and a portfolio case study demonstrating modern big data architecture on AWS using AI-assisted, spec-driven development (BMAD method). It showcases PySpark Structured Streaming on EMR Serverless, event-driven architecture, AWS Well-Architected best practices, data quality engineering, and agentic AI development workflows.

**Future Vision:** Extend to prescriptive analytics with signal generation and autonomous execution via Hyperliquid perpetual futures.

### Business Justification

- **Skill Development:** Hands-on PySpark streaming + AWS big data services
- **Portfolio Impact:** Demonstrable real-time architecture for LinkedIn/Caylent positioning
- **AI-Assisted Development Showcase:** BMAD-method agents driving spec → code → deploy
- **Collaboration Model:** Two architects co-building with Claude Code as the development engine
- **Extensibility:** Foundation for prescriptive analytics and autonomous trading systems

---

## 2. Problem Statement

Cryptocurrency markets generate massive volumes of real-time data across multiple exchanges. Retail investors and analysts lack affordable, real-time tools to detect meaningful signals — volume anomalies, large-order (whale) activity, and cross-exchange arbitrage spreads — from this firehose of data.

Simultaneously, AWS practitioners need portfolio projects that demonstrate real-time streaming architecture at meaningful scale with production-grade patterns.

---

## 3. Target Users

| Persona | Description | Primary Need |
|---|---|---|
| **Portfolio Reviewer** | Hiring managers, Caylent leadership | Evaluate big data architecture skills |
| **Crypto Enthusiast** | Retail traders wanting market signals | Real-time anomaly alerts |
| **Technical Interviewer** | Assessing AWS + Spark expertise | See code, architecture, and decisions |
| **Fellow Engineers** | Learning from the repo | Reusable patterns and IaC templates |

---

## 4. Goals & Success Metrics

### 4.1 Functional Goals

| ID | Goal | Success Metric |
|---|---|---|
| G1 | Ingest real-time trade data from ≥2 crypto exchanges | Binance + Coinbase WebSocket streams active |
| G2 | Detect volume anomalies within 60-second windows | Z-score alerts fire within 90s of event |
| G3 | Identify whale trades (>$100K single transaction) | 95%+ detection rate on test data |
| G4 | Calculate cross-exchange price spreads in real-time | Spread calculations within 30s window |
| G5 | Store historical data in queryable lakehouse format | Athena queries return results on Iceberg tables |
| G6 | Surface insights via dashboard and API | Dashboard loads <3s, API responds <500ms |

### 4.2 Non-Functional Goals

| ID | Goal | Success Metric |
|---|---|---|
| NF1 | Cost-efficient: teardown when not demoing | Idle cost <$1/day, demo cost <$5/hour |
| NF2 | Infrastructure as Code: fully reproducible | Single `terraform apply` deploys everything |
| NF3 | Well-Architected compliance | Documented decisions per WAF pillar |
| NF4 | Security-first design | Least-privilege IAM, encryption at rest/transit |
| NF5 | Observable | CloudWatch dashboards, Spark UI metrics |
| NF6 | AI Safety documented | Data lineage, no PII, guardrails documented |

### 4.3 Portfolio Goals

| ID | Goal | Evidence |
|---|---|---|
| P1 | Demonstrate PySpark Structured Streaming mastery | Working streaming jobs with windowed aggregations |
| P2 | Demonstrate AWS big data architecture | Architecture diagram with service justifications |
| P3 | Demonstrate BMAD/agentic development | Agent specs, PR history, AI-generated artifacts |
| P4 | Demonstrate collaboration | Co-authored commits, review comments |
| P5 | Demonstrate Well-Architected thinking | WAF review document with pillar analysis |

---

## 4A. Module System

Coat Tail Capital uses a **composable feature module architecture** (ADR-007) instead of rigid scope phases. This enables:

- **Independent feature lifecycle** — modules can be enabled/disabled without touching other code
- **Right-sized cost** — pay only for the detection capabilities you need
- **Easy extensibility** — adding a feature = new module + config entry, not a rewrite

### Module Contract

Every feature module conforms to a standard interface defined in `docs/MODULE_REGISTRY.md`:

| Component | Description |
|---|---|
| **BaseConnector** | Data source abstraction (exchange WebSocket, blockchain RPC) |
| **BaseDetector** | Processing logic (windowed aggregation, threshold detection, scoring) |
| **AlertRouter** | Routes detector output to DynamoDB + S3 Iceberg sinks |
| **ModuleRegistry** | Discovers and instantiates active modules from configuration |
| **ConfigLoader** | Reads `config/features.yaml` + SSM parameters for runtime config |
| **PipelineRunner** | Orchestrates connectors → quality checks → detectors → sinks |

### Configuration

Modules are activated via YAML configuration (version-controlled) and SSM parameters (runtime):

```yaml
# config/features.yaml
feature_tier: small
symbols: [btcusdt, ethusdt, solusdt]
exchange_connectors: [binance-ws, coinbase-ws]
```

Tier definitions in `config/tiers/` map tier names to active module sets. Individual modules can be toggled via `enabled_modules` overrides in Terraform.

### Module Registry

All 11 modules are cataloged in `docs/MODULE_REGISTRY.md` with complete specs: data sources, dependencies, processing algorithms, output tables, alert types, and cost impact.

---

## 5. Scope — Feature Tiers

Coat Tail Capital uses a **modular feature architecture** where capabilities are composed from independent feature modules. Each tier is a superset of the previous, enabling right-sized deployments. See `docs/MODULE_REGISTRY.md` for complete module specifications.

### 5.1 Small Tier — Detect CEX Activity (~$0.82/hr)

The foundation: ingest CEX trade data, detect anomalies, and surface alerts.

| Component | Description |
|---|---|
| **Data Ingestion** | Python WebSocket producer → Kinesis Data Streams for configurable symbol pairs |
| **Modules** | `volume-anomaly` (MOD-001), `whale-detector` (MOD-002), `spread-calculator` (MOD-003) |
| **Storage** | S3 Iceberg tables via Glue Data Catalog, DynamoDB hot alerts (24h TTL) |
| **API** | Lambda + API Gateway — GET /alerts, GET /metrics/{symbol} |
| **Dashboard** | Single-page React app — live alerts, volume charts, spread tracker |
| **Platform** | Data quality framework, Terraform IaC, GitHub Actions CI/CD, Step Functions batch orchestration |

### 5.2 Medium Tier — Track Who Smart Money IS (~$1.40/hr)

Extends Small with identity and conviction analysis.

| Component | Description |
|---|---|
| **Includes** | All Small tier modules and infrastructure |
| **Modules** | `wallet-scorer` (MOD-004), `labeled-whales` (MOD-005), `flow-direction` (MOD-006), `consensus` (MOD-007) |
| **New Capabilities** | Wallet alpha scoring, known whale identity enrichment, buy/sell flow analysis, multi-signal consensus scoring |

### 5.3 Large Tier — Predict Where It's Going (~$2.50/hr)

Full platform with on-chain data and predictive analytics.

| Component | Description |
|---|---|
| **Includes** | All Medium tier modules and infrastructure |
| **Modules** | `onchain-ingester` (MOD-008), `dex-tracker` (MOD-009), `predictive-scorer` (MOD-010), `backtester` (MOD-011) |
| **New Capabilities** | Ethereum/Solana on-chain ingestion, DEX trade tracking, forward-looking probability scores, signal back-testing |

### 5.4 Out of Scope

- ML-based anomaly models (SageMaker integration) — potential future module
- Multi-region deployment
- User authentication / multi-tenancy
- Mobile app
- Automated trading execution / financial advice (AI safety boundary)

### 5.5 Principal-Level Platform Capabilities (All Tiers)

These cross-cutting capabilities ship with every tier:

- **Modular feature architecture** with config-driven module toggles (ADR-007)
- **Data quality framework** — PySpark-native validation, CloudWatch metrics, DLQ routing
- **Batch reprocessing** — historical backfill, Iceberg time-travel reprocessing
- **Orchestration** — Step Functions state machine, EventBridge scheduling
- **Schema evolution** — Iceberg schema evolution without table rewrites
- **Data governance** — Lake Formation with database-level permissions
- **Architecture decision records** — documented trade-offs (ADR-001 through ADR-007)

---

## 6. Data Sources — Connector Interface

Data ingestion uses a **BaseConnector** pattern. Each exchange or blockchain is a connector implementation that normalizes raw data into a unified schema. Connectors are enabled via configuration (`config/features.yaml`).

### 6.1 Connector Contract

Every data source connector implements:

```python
class BaseConnector(ABC):
    def connect(self) -> None: ...          # Establish connection
    def normalize(self, raw) -> TradeEvent: ... # Normalize to unified schema
    def health_check(self) -> bool: ...     # Connection health
    def shutdown(self) -> None: ...         # Graceful disconnect
```

### 6.2 CEX Connectors (Small Tier)

| Connector | Endpoint | Data | Auth |
|---|---|---|---|
| `binance-ws` | `wss://stream.binance.com:9443/ws/{symbol}@trade` | Price, quantity, timestamp, buyer/seller | None (public) |
| `coinbase-ws` | `wss://ws-feed.exchange.coinbase.com` | Executed trades with price, size, side | None (public) |

**Symbols:** Configurable via `config/features.yaml` (default: `btcusdt, ethusdt, solusdt`)

**Rate Limits:** Binance: max 5 WebSocket connections per IP (use combined stream endpoint). Coinbase: no stated limit for public channels.

### 6.3 Blockchain Connectors (Large Tier)

| Connector | Endpoint | Data | Auth |
|---|---|---|---|
| `ethereum-rpc` | Alchemy/Infura WebSocket | Blocks, transactions, token transfers | API key |
| `solana-rpc` | Helius/QuickNode WebSocket | Transactions, program logs | API key |

### 6.4 Unified Trade Event Schema

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

### 6.5 Adding a New Connector

1. Subclass `BaseConnector`
2. Implement `connect()`, `normalize()`, `health_check()`, `shutdown()`
3. Register in `src/connectors/` directory
4. Add to connector list in `config/features.yaml`
5. The producer auto-discovers and starts registered connectors

---

## 7. Architecture Overview

### 7.1 Data Flow

```
[Binance WS] ──┐
                ├──→ [Python Producer] ──→ [Kinesis Data Streams]
[Coinbase WS] ─┘           │                      │
                            │                      ▼
                     [CloudWatch]        [EMR Serverless - PySpark]
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                              [S3 Iceberg]   [DynamoDB]    [CloudWatch
                              Lakehouse]     Hot Alerts]    Metrics]
                                    │              │
                                    ▼              ▼
                              [Athena]      [Lambda + API GW]
                                                   │
                                                   ▼
                                           [React Dashboard]
```

### 7.2 AWS Services & Justification

| Service | Role | Why This Service |
|---|---|---|
| **Kinesis Data Streams** | Stream ingestion | Managed, scales on-demand, native Spark integration, no cluster management (vs. MSK) |
| **EMR Serverless** | Spark processing | Pay-per-second, no idle clusters, PySpark native, scales to zero |
| **S3 + Iceberg** | Lakehouse storage | Cost-effective, ACID transactions, time-travel queries, Athena-compatible |
| **Glue Data Catalog** | Metadata management | Central schema registry, Iceberg catalog, Athena integration |
| **DynamoDB** | Hot alert store | Single-digit ms reads, TTL for auto-cleanup, on-demand pricing |
| **Lambda** | API compute | Pay-per-invocation, scales to zero, <1s cold start |
| **API Gateway** | API management | Throttling, caching, CORS, usage plans |
| **Athena** | Ad-hoc analytics | Serverless SQL over Iceberg tables, pay per query |
| **CloudWatch** | Monitoring + alarms | Native integration, billing alarms, custom metrics |
| **Terraform** | IaC | Multi-provider, state management, modular, team standard |

### 7.3 Well-Architected Framework Alignment

| Pillar | Design Decision |
|---|---|
| **Operational Excellence** | IaC (Terraform), CI/CD (GitHub Actions), CloudWatch dashboards, runbooks, start/stop scripts |
| **Security** | Least-privilege IAM, KMS encryption at rest, TLS in transit, no secrets in code (SSM Parameter Store), OPA policy validation in CI |
| **Reliability** | Kinesis retry + DLQ, Spark checkpointing, Iceberg ACID writes, DynamoDB on-demand, multi-AZ by default |
| **Performance Efficiency** | EMR Serverless auto-scaling, Kinesis on-demand shards, DynamoDB on-demand capacity, Iceberg partition pruning |
| **Cost Optimization** | EMR Serverless (zero idle), start/stop scripts, S3 lifecycle policies, DynamoDB TTL, CloudWatch billing alarms at $25/$50 |
| **Sustainability** | Right-sized compute, serverless-first reduces idle waste, efficient data formats (Parquet/Iceberg) |

---

## 8. Streaming Processing — Module Framework

All stream processing uses a **BaseDetector** pattern. Each feature module (see `docs/MODULE_REGISTRY.md`) is a detector subclass loaded by the PipelineRunner based on configuration.

### 8.1 Detector Contract

```python
class BaseDetector(ABC):
    module_id: str               # e.g., "MOD-001"
    module_name: str             # e.g., "volume-anomaly"

    def configure(self, config: dict) -> None: ...   # Load thresholds, windows
    def process(self, df: DataFrame) -> DataFrame: ... # Core detection logic
    def alert_types(self) -> list[str]: ...           # Alert types this module emits
    def output_table(self) -> str: ...                # Iceberg table name
```

### 8.2 Pipeline Architecture

A single PySpark Structured Streaming application runs all active detectors:

```
[Kinesis Stream] → [Data Quality Module] → [PipelineRunner]
                                                │
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                              [Detector 1] [Detector 2] [Detector N]
                                    │           │           │
                                    └───────────┼───────────┘
                                                │
                                         [AlertRouter]
                                           │       │
                                    [DynamoDB]  [S3 Iceberg]
```

The `PipelineRunner` reads `config/features.yaml`, instantiates active detectors via `ModuleRegistry`, and routes each detector's output through the `AlertRouter`.

### 8.3 Small Tier Detectors (Reference Implementations)

Detailed algorithms for each module are specified in `docs/MODULE_REGISTRY.md`. Summary:

| Module | Window | Key Logic | Alert Type |
|---|---|---|---|
| `volume-anomaly` (MOD-001) | 60s tumbling | Z-score on rolling 1h mean/stddev, flag `\|z\| > 2.5` | `volume_spike` |
| `whale-detector` (MOD-002) | Per-record | Filter `quote_volume > $100K`, severity tiers | `whale_trade` |
| `spread-calculator` (MOD-003) | 30s tumbling | Cross-exchange VWAP comparison, flag `\|spread\| > 0.5%` | `spread_divergence` |

### 8.4 Checkpointing & Fault Tolerance

| Setting | Value | Rationale |
|---|---|---|
| Checkpoint location | `s3://{prefix}-checkpoint/` | Durable, survives job restarts |
| Checkpoint interval | 60 seconds | Balances latency vs. S3 write cost |
| Starting position | `TRIM_HORIZON` | Recovers from last checkpoint on restart |
| Watermark | 30s (volume), 15s (spread) | Tolerates network jitter |
| DLQ | Kinesis DLQ stream + S3 DLQ zone | Malformed records preserved for investigation |
| Idempotency | DynamoDB conditional puts on `event_id` | Prevents duplicate alerts |

### 8.5 Adding a New Detector

1. Subclass `BaseDetector` in `src/detectors/`
2. Implement `configure()`, `process()`, `alert_types()`, `output_table()`
3. Register module in `docs/MODULE_REGISTRY.md`
4. Add module ID to tier config in `config/tiers/`
5. The `PipelineRunner` auto-discovers and starts the detector on next deploy

## 9. Data Quality Framework

Principal-level data architectures require comprehensive data quality validation, observability, and remediation patterns.

### 9.1 Quality Dimensions

| Dimension | Validation Rule | Action on Failure |
|---|---|---|
| **Completeness** | Required fields not null: `event_id`, `symbol`, `price`, `quantity`, `timestamp` | Route to DLQ |
| **Validity** | `price > 0`, `quantity > 0`, `symbol` in allowed list | Route to DLQ |
| **Timeliness** | `timestamp` within 5 minutes of processing time | Flag as late, still process |
| **Consistency** | `quote_volume ≈ price × quantity` (±0.1% tolerance) | Log warning, still process |
| **Uniqueness** | No duplicate `event_id` within 1-hour window | Deduplicate, keep first |

### 9.2 Quality Check Pipeline

```
Raw Record
    │
    ▼
┌─────────────────┐
│ Schema Validation│ ──fail──▶ [DLQ: malformed]
└────────┬────────┘
         │ pass
         ▼
┌─────────────────┐
│ Null Checks     │ ──fail──▶ [DLQ: incomplete]
└────────┬────────┘
         │ pass
         ▼
┌─────────────────┐
│ Range Validation│ ──fail──▶ [DLQ: invalid]
└────────┬────────┘
         │ pass
         ▼
┌─────────────────┐
│ Deduplication   │ ──dup───▶ [Dropped, logged]
└────────┬────────┘
         │ unique
         ▼
┌─────────────────┐
│ Timeliness Check│ ──late──▶ [Flagged, processed]
└────────┬────────┘
         │
         ▼
    Valid Record
```

### 9.3 Quality Metrics (CloudWatch)

| Metric | Namespace | Description |
|---|---|---|
| `RecordsProcessed` | CryptoPulse/Quality | Total records entering quality pipeline |
| `RecordsPassed` | CryptoPulse/Quality | Records passing all checks |
| `RecordsFailed` | CryptoPulse/Quality | Records routed to DLQ |
| `RecordsLate` | CryptoPulse/Quality | Records with stale timestamps |
| `RecordsDuplicate` | CryptoPulse/Quality | Duplicate records dropped |
| `QualityScore` | CryptoPulse/Quality | `RecordsPassed / RecordsProcessed × 100` |
| `FailureRate` | CryptoPulse/Quality | `RecordsFailed / RecordsProcessed × 100` |

**Alarm:** `QualityScore < 95%` for 5 minutes → Alert

### 9.4 Dead Letter Queue Strategy

**S3 DLQ Structure:**
```
s3://crypto-pulse-dev-raw-{account}/dlq/
├── malformed/          # JSON parse failures
│   └── dt=2025-02-05/
├── incomplete/         # Missing required fields
│   └── dt=2025-02-05/
├── invalid/            # Failed range/business rules
│   └── dt=2025-02-05/
└── _metadata/
    └── dlq_summary.json  # Daily aggregates for monitoring
```

**Retention:** 7 days (enough to investigate and replay)

### 9.5 Quality Dashboard Widgets

- Gauge: Current quality score (target: >99%)
- Time series: Pass/fail rates over 24 hours
- Bar chart: Failure breakdown by reason
- Table: Recent DLQ samples with failure reasons

---

## 10. Batch Processing & Reprocessing

Production data platforms require batch capabilities for historical loads, backfills, and reprocessing.

### 10.1 Batch Job: Historical Loader

**Purpose:** Backfill historical trade data from exchange REST APIs into the raw zone.

**Input:** Binance REST API (`GET /api/v3/aggTrades`) with time range parameters

**Process:**
1. Paginate through historical trades (max 1000 per request)
2. Normalize to unified schema
3. Write to S3 raw zone as Parquet, partitioned by `date` and `symbol`
4. Register in Glue catalog

**Trigger:** Manual or Step Functions (for initial load)

**Output:** `s3://raw-bucket/historical/symbol={}/date={}/`

### 10.2 Batch Job: Reprocess Anomalies

**Purpose:** Recompute anomalies from raw Iceberg tables after algorithm changes or bug fixes.

**Input:** Iceberg table `raw_trades` with time-travel capability

**Process:**
1. Read from Iceberg at specific snapshot (or time range)
2. Apply updated anomaly detection logic
3. Write to `anomalies_reprocessed` table
4. Compare with original `anomalies` table for validation
5. Optionally swap tables if validation passes

**Trigger:** Step Functions (on-demand)

**Iceberg Time-Travel Query:**
```sql
-- Read data as of a specific snapshot
SELECT * FROM glue_catalog.crypto_pulse.raw_trades
VERSION AS OF 123456789;

-- Read data as of a specific timestamp
SELECT * FROM glue_catalog.crypto_pulse.raw_trades
TIMESTAMP AS OF '2025-02-01 00:00:00';
```

### 10.3 Schema Evolution Example

Demonstrate Iceberg's schema evolution by adding a field without table rewrite:

```sql
-- Add a new column (instant metadata operation)
ALTER TABLE glue_catalog.crypto_pulse.volume_aggregates
ADD COLUMN market_cap_rank INT;

-- Old data returns NULL for new column
-- New data populates the field
-- No rewrite of existing Parquet files required
```

**Why this matters:** Shows understanding of Iceberg's value proposition vs. plain Parquet.

---

## 11. Orchestration (Step Functions)

### 11.1 Batch Workflow State Machine

```
                    ┌─────────────────┐
                    │   EventBridge   │
                    │  (Daily 02:00)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Historical Load │
                    │   (Lambda)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Submit Spark    │
                    │ Batch Job       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
              ┌─────│ Wait for Job    │─────┐
              │     │ Completion      │     │
              │     └─────────────────┘     │
              │                             │
         succeeded                      failed
              │                             │
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ Run Data Quality│          │  Send Alert     │
    │ Validation      │          │  (SNS)          │
    └────────┬────────┘          └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │ Update Glue     │
    │ Table Stats     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Publish Success │
    │ Metrics         │
    └─────────────────┘
```

### 11.2 Step Functions Definition (Summary)

| State | Type | Action |
|---|---|---|
| `HistoricalLoad` | Task (Lambda) | Fetch yesterday's data from REST API |
| `SubmitSparkJob` | Task (EMR Serverless) | Submit reprocessing job |
| `WaitForJob` | Wait + Poll | Check job status every 60s |
| `RunQualityChecks` | Task (Lambda) | Validate output counts and schema |
| `UpdateCatalog` | Task (Lambda) | Refresh Glue table statistics |
| `SendAlert` | Task (SNS) | Notify on failure |
| `PublishMetrics` | Task (Lambda) | Push execution metrics to CloudWatch |

### 11.3 EventBridge Schedule

```json
{
  "ScheduleExpression": "cron(0 2 * * ? *)",
  "Description": "Daily batch processing at 02:00 UTC"
}
```

---

## 12. Data Governance (Lake Formation)

### 12.1 Governance Model

| Principal | Database Access | Table Access | Column Access |
|---|---|---|---|
| `emr-execution-role` | crypto_pulse_lakehouse | All tables | All columns |
| `lambda-api-role` | crypto_pulse_lakehouse | alerts, metrics | All columns |
| `analyst-role` | crypto_pulse_lakehouse | All tables | Exclude: `raw_event_payload` |
| `data-scientist-role` | crypto_pulse_lakehouse | All tables | All columns |

### 12.2 Lake Formation Setup

```hcl
# Register S3 location with Lake Formation
resource "aws_lakeformation_resource" "lakehouse" {
  arn = aws_s3_bucket.processed.arn
}

# Grant database permissions
resource "aws_lakeformation_permissions" "emr_database" {
  principal   = aws_iam_role.emr_execution.arn
  permissions = ["ALL"]
  
  database {
    name = aws_glue_catalog_database.crypto_pulse.name
  }
}
```

### 12.3 Why Lake Formation Matters

- **Centralized permissions:** Single pane of glass vs. scattered IAM policies
- **Column-level security:** Restrict sensitive fields (not needed here, but shows awareness)
- **Audit logging:** CloudTrail integration for compliance
- **Cross-account sharing:** Enable data mesh patterns (future)

---

## 13. Architecture Decision Records

### ADR-001: Kinesis vs MSK for Stream Ingestion

**Status:** Accepted

**Context:** Need a managed streaming service for real-time trade data ingestion.

**Options Considered:**

| Criteria | Kinesis Data Streams | MSK Serverless | MSK Provisioned |
|---|---|---|---|
| Setup complexity | Low (on-demand) | Medium | High |
| Cost at low volume | ~$0.04/hr minimum | ~$0.75/hr minimum | ~$2.50/hr minimum |
| Kafka compatibility | No | Yes | Yes |
| Spark integration | Native | Native | Native |
| Scale-to-zero | Partial (on-demand) | No | No |
| Client ecosystem | AWS SDK | Kafka clients | Kafka clients |

**Decision:** Kinesis Data Streams (on-demand mode)

**Rationale:**
1. **Cost:** Portfolio project with low volume; Kinesis on-demand is 10-60x cheaper at our scale
2. **Simplicity:** No broker management, instant provisioning
3. **Sufficient for demo:** EMR Serverless + Kinesis is a valid production pattern used by AWS customers
4. **Migration path:** PySpark jobs are connector-agnostic; switching to MSK requires only config changes

**Trade-offs Accepted:**
- No Kafka ecosystem compatibility (acceptable for this project)
- Limited to AWS (acceptable for AWS-focused portfolio)

**Production Recommendation:** For Caylent clients with existing Kafka ecosystems or multi-cloud requirements, recommend MSK Serverless. The PySpark jobs in this project would require only these changes:
```python
# Kinesis source (current)
df = spark.readStream.format("kinesis").option("streamName", ...).load()

# Kafka/MSK source (production alternative)
df = spark.readStream.format("kafka").option("kafka.bootstrap.servers", ...).load()
```

---



### GET /alerts

Returns recent anomaly alerts.

**Query Parameters:**
- `type` (optional): `volume_spike | whale | spread` — filter by alert type
- `symbol` (optional): `BTC-USDT` — filter by symbol
- `limit` (optional, default 50, max 200): number of results
- `since` (optional): ISO timestamp — alerts after this time

**Response:**
```json
{
  "alerts": [
    {
      "alert_id": "uuid",
      "type": "volume_spike",
      "symbol": "BTC-USDT",
      "exchange": "binance",
      "severity": "high",
      "z_score": 3.2,
      "window_volume": 1500000,
      "rolling_mean": 450000,
      "detected_at": "2025-02-05T10:30:00Z",
      "message": "BTC-USDT volume 3.3x above 1h average on Binance"
    }
  ],
  "count": 1,
  "has_more": false
}
```

### GET /metrics/{symbol}

Returns current streaming metrics for a symbol.

**Response:**
```json
{
  "symbol": "BTC-USDT",
  "current_price": {"binance": 67432.50, "coinbase": 67445.00},
  "spread_pct": 0.019,
  "volume_1h": {"binance": 2500000, "coinbase": 1800000},
  "anomaly_count_24h": 7,
  "last_whale": {"price": 67400, "quantity": 2.5, "side": "buy", "timestamp": "..."},
  "updated_at": "2025-02-05T10:30:00Z"
}
```

---

## 10. Dashboard Requirements

### 10.1 Single-Page Layout

| Section | Content |
|---|---|
| **Header** | Project title, live/paused indicator, last updated timestamp |
| **Alert Feed** | Scrolling list of recent anomalies with severity badges |
| **Volume Chart** | Real-time bar chart per symbol (60s windows) with anomaly markers |
| **Spread Tracker** | Line chart showing cross-exchange spread % over time |
| **Whale Log** | Table of whale transactions with exchange, size, side |
| **System Health** | Kinesis lag, Spark job status, record count |

### 10.2 Tech Stack

- React (Vite scaffold)
- Recharts for visualizations
- TailwindCSS for styling
- API polling every 10 seconds (simple, no WebSocket needed for dashboard)
- Deployed on S3 + CloudFront (or Amplify for simplicity)

---

## 11. AI Safety & Responsible Design

### 11.1 Data Ethics

- **Public data only:** All market data is publicly available, no user PII
- **No financial advice:** Dashboard explicitly disclaims: "For educational and analytical purposes only. Not financial advice."
- **Data lineage:** Every record traceable from source exchange → Kinesis → Spark → storage
- **No trading automation:** System detects signals but does not execute trades

### 11.2 AI-Assisted Development Safety

- **Human-in-the-loop:** All agent-generated specs reviewed by Frank and Mike before implementation
- **Code review gates:** Claude Code PRs require human approval
- **Prompt transparency:** All agent prompts versioned in `/agents` directory
- **Bias awareness:** Anomaly thresholds are configurable, not hard-coded, to avoid false signal bias

### 11.3 Model Guardrails (Future ML Extension)

- If ML scoring is added, document model cards, training data provenance, and accuracy metrics
- No user-facing predictions without confidence intervals
- Rate-limit API to prevent abuse

---

## 12. Cost Model — Per-Tier Breakdown

### 12.1 Small Tier (CEX Detection)

| Service | Config | Est. Cost/Hour |
|---|---|---|
| Kinesis Data Streams (on-demand, ~1K rec/s) | 1 shard equivalent | ~$0.50 |
| EMR Serverless (4 vCPU, 8GB) | Spark 3.4, 3 detectors | ~$0.30 |
| DynamoDB (PAY_PER_REQUEST) | Low write volume | ~$0.01 |
| Lambda (low invocation) | 128-512 MB | ~$0.01 |
| **Total Small tier** | | **~$0.82/hour** |

### 12.2 Medium Tier (Identity + Conviction)

| Service | Config | Est. Cost/Hour |
|---|---|---|
| Small tier baseline | All Small services | ~$0.82 |
| EMR Serverless (+2 vCPU, +4GB) | 7 detectors, stateful scoring | +$0.20 |
| Additional Kinesis throughput | Wallet scoring writes | +$0.13 |
| DynamoDB (higher write volume) | More alert types | +$0.05 |
| External API calls (label datasets) | Periodic refresh | +$0.20 |
| **Total Medium tier** | | **~$1.40/hour** |

### 12.3 Large Tier (On-Chain + Predictive)

| Service | Config | Est. Cost/Hour |
|---|---|---|
| Medium tier baseline | All Medium services | ~$1.40 |
| EMR Serverless (+2 vCPU, +4GB) | 11 detectors, block parsing | +$0.35 |
| RPC node costs (Alchemy/Helius) | Ethereum + Solana WebSocket | +$0.50 |
| Additional S3 throughput | On-chain event volume | +$0.10 |
| Batch compute (backtester) | 1-2 runs/day | +$0.15 |
| **Total Large tier** | | **~$2.50/hour** |

### 12.4 Idle Mode (All Tiers — streaming off)

| Service | Cost/Day |
|---|---|
| S3 storage (< 1GB) | < $0.01 |
| Everything else | $0.00 (serverless, scale-to-zero) |
| **Total idle** | **< $0.01/day** |

### 12.5 Cost Safety Controls

- CloudWatch billing alarm at $25 and $50
- Start/stop shell scripts for streaming components
- DynamoDB TTL (24h) to auto-purge old alerts
- S3 lifecycle policy: transition to IA after 30 days, delete after 90
- Feature tier selection controls blast radius — start Small, upgrade when ready
- Per-module cost tracked in `docs/MODULE_REGISTRY.md`

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Exchange API changes/downtime | Medium | Medium | Abstract exchange connectors, graceful degradation |
| EMR Serverless cold start latency | Medium | Low | Pre-warm with scheduled trigger, document in demo prep |
| Cost overrun from runaway streams | Low | High | Billing alarms, auto-stop Lambda if spend > threshold |
| Weekend time constraints | Medium | High | Strict scope control, defer enhancements to backlog |
| Kinesis throttling at high volume | Low | Medium | On-demand mode, error handling with exponential backoff |

---

## 14. Definition of Done

The weekend MVP is complete when:

- [ ] Binance trade stream ingested into Kinesis for BTC/ETH/SOL
- [ ] PySpark streaming job running on EMR Serverless detecting anomalies
- [ ] Data landing in S3 Iceberg tables, queryable via Athena
- [ ] Alerts in DynamoDB, accessible via Lambda API
- [ ] Dashboard displaying live alerts and charts
- [ ] `terraform apply` deploys full stack from scratch
- [ ] `scripts/start.sh` and `scripts/stop.sh` toggle streaming on/off
- [ ] README with architecture diagram, setup instructions, cost analysis
- [ ] Well-Architected review document completed
- [ ] Both Frank and Mike have commits in the repo
- [ ] LinkedIn posts drafted with architecture diagram and key learnings

---

## Appendix A: Repository Structure

```
crypto-pulse-analytics/
├── README.md
├── docs/
│   ├── PRD.md                    # This document
│   ├── ARCHITECTURE.md           # Detailed architecture with diagrams
│   ├── WELL-ARCHITECTED.md       # WAF pillar review
│   └── RUNBOOK.md                # Weekend execution runbook
├── agents/
│   ├── README.md                 # BMAD method explanation
│   ├── ba-agent.md               # Business Analyst agent prompt
│   ├── architect-agent.md        # Architect agent prompt
│   ├── data-engineer-agent.md    # Data Engineer agent prompt
│   ├── security-agent.md         # Security agent prompt
│   ├── devops-agent.md           # DevOps agent prompt
│   └── qa-agent.md               # QA agent prompt
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── backend.tf
│   └── modules/
│       ├── kinesis/
│       ├── s3-lakehouse/
│       ├── emr-serverless/
│       ├── iam/
│       ├── glue/
│       └── monitoring/
├── src/
│   ├── producer/                 # Python Kinesis producer
│   ├── spark-jobs/               # PySpark streaming jobs
│   ├── api/                      # Lambda API handlers
│   └── dashboard/                # React dashboard
├── scripts/
│   ├── start.sh                  # Start streaming components
│   ├── stop.sh                   # Stop streaming components
│   └── demo-prep.sh              # Pre-demo checklist
├── .github/
│   └── workflows/
│       ├── ci.yml                # Lint, test, validate
│       └── deploy.yml            # Terraform plan/apply
└── .gitignore
```

---

## Appendix B: Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Stream broker | Kinesis (not MSK) | Simpler, cheaper at low scale, native EMR integration, no cluster management |
| Compute | EMR Serverless (not Glue Streaming) | More control over Spark config, better for portfolio demonstration, true PySpark |
| Table format | Iceberg (not Delta/Hudi) | AWS-native Glue Catalog support, ACID, time-travel, open standard |
| IaC | Terraform (not CDK/CF) | Multi-cloud portable, Caylent standard, better state management |
| Dashboard | React + S3 (not Grafana) | Custom portfolio piece, lightweight, no server cost |
| Alert store | DynamoDB (not RDS) | Serverless pricing, TTL cleanup, fast reads, schema flexibility |
