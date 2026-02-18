# Architecture Decision Records

> Coat Tail Capital — Riding smart money so you don't have to think 🐋

This document captures key architectural decisions made during the design of Coat Tail Capital. Each ADR follows the format: Context → Options → Decision → Consequences.

---

## ADR-001: Stream Processing Engine — Kinesis vs MSK

**Status:** Accepted  
**Date:** 2025-02-05  
**Deciders:** Frank, Mike Veksler

### Context

We need a managed streaming service to ingest real-time cryptocurrency trade data from exchange WebSocket feeds. The stream processor must integrate with PySpark Structured Streaming on EMR Serverless and support our cost constraints (~$5/hour active, ~$0/day idle).

### Options Considered

| Criteria | Kinesis Data Streams | MSK Serverless | MSK Provisioned |
|---|---|---|---|
| **Setup complexity** | Low (on-demand, instant) | Medium (cluster creation) | High (broker config) |
| **Minimum cost** | ~$0.04/hr (on-demand) | ~$0.75/hr | ~$2.50/hr |
| **Scale to zero** | Partial (on-demand mode) | No | No |
| **Kafka compatibility** | No | Yes | Yes |
| **Spark integration** | Native (spark-sql-kinesis) | Native (spark-sql-kafka) | Native |
| **Retention** | 24h-365d | 7d (default), unlimited | Configurable |
| **Multi-AZ by default** | Yes | Yes | Manual config |
| **AWS ecosystem integration** | Deep (Lambda, Firehose, Analytics) | Limited | Limited |

### Decision

**Kinesis Data Streams with on-demand capacity mode.**

### Rationale

1. **Cost:** At our volume (~1K records/sec during demo), Kinesis on-demand is 10-60x cheaper than MSK options. The minimum MSK Serverless cost would dominate our budget even when idle.

2. **Simplicity:** On-demand Kinesis requires no capacity planning. No shard management, no broker configuration, instant provisioning.

3. **Portfolio validity:** Kinesis + EMR Serverless is a legitimate production pattern used by AWS customers. It demonstrates AWS streaming skills without artificial complexity.

4. **Migration path clear:** PySpark Structured Streaming jobs are connector-agnostic. Switching to Kafka/MSK requires only configuration changes:

```python
# Current (Kinesis)
df = spark.readStream.format("kinesis") \
    .option("streamName", "crypto-pulse-trades") \
    .option("region", "us-west-2") \
    .load()

# Alternative (Kafka/MSK)
df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "broker:9092") \
    .option("subscribe", "crypto-pulse-trades") \
    .load()
```

### Consequences

**Positive:**
- Lower cost for portfolio project
- Faster setup (deploy in minutes vs hours)
- Simpler operations (no broker management)

**Negative:**
- No Kafka ecosystem compatibility (Schema Registry, Connect, etc.)
- Limited to AWS (no multi-cloud portability)
- Some Caylent clients may specifically need Kafka experience

**Mitigation:**
- Document the MSK migration path explicitly
- Note in portfolio that Kafka/MSK is the recommendation for clients with existing Kafka ecosystems
- Add a section showing the connector swap for credibility

---

## ADR-002: Table Format — Iceberg vs Delta Lake vs Hudi

**Status:** Accepted  
**Date:** 2025-02-05

### Context

We need an open table format for our S3 lakehouse that supports ACID transactions, schema evolution, and time-travel queries. The format must integrate with Glue Data Catalog and be queryable via Athena.

### Options Considered

| Criteria | Apache Iceberg | Delta Lake | Apache Hudi |
|---|---|---|---|
| **AWS native support** | Glue, Athena, EMR native | EMR, limited Athena | EMR, Athena via connector |
| **Glue Catalog integration** | Native catalog impl | Requires Unity or workarounds | Hive Metastore sync |
| **Time-travel** | Yes (snapshots + timestamps) | Yes (versions) | Yes (timeline) |
| **Schema evolution** | Excellent (add/rename/reorder) | Good (add columns) | Good |
| **Partition evolution** | Yes (no rewrite) | No | No |
| **Hidden partitioning** | Yes | No | No |
| **Community momentum** | High (Netflix, Apple, AWS) | High (Databricks ecosystem) | Medium |
| **Vendor lock-in risk** | Low (open standard) | Medium (Databricks-centric) | Low |

### Decision

**Apache Iceberg with Glue Catalog as the metastore.**

### Rationale

1. **AWS-native:** Iceberg is the strategic table format for AWS. Glue has native Iceberg catalog implementation, Athena queries Iceberg directly, EMR has first-class support.

2. **Partition evolution:** Iceberg allows changing partition schemes without rewriting data. This is critical for evolving schemas in streaming workloads.

3. **Hidden partitioning:** Users query without knowing partition structure. `SELECT * FROM trades WHERE timestamp > '2025-02-01'` works without explicit partition predicates.

4. **Open standard:** Iceberg is governed by Apache Foundation, reducing vendor lock-in risk compared to Delta Lake's Databricks association.

5. **Caylent alignment:** Iceberg is increasingly recommended for AWS-centric clients. Demonstrating Iceberg proficiency is strategically valuable.

### Consequences

**Positive:**
- Seamless Athena integration
- Schema and partition evolution without rewrites
- Time-travel for reprocessing and debugging
- Strong AWS roadmap alignment

**Negative:**
- Smaller ecosystem than Delta Lake (fewer tools, tutorials)
- Databricks-heavy clients may prefer Delta Lake

---

## ADR-003: Compute — EMR Serverless vs Glue Streaming vs EKS

**Status:** Accepted  
**Date:** 2025-02-05

### Context

We need a compute platform to run PySpark Structured Streaming jobs. Requirements: serverless pricing model, PySpark 3.4+ support, Kinesis and Iceberg integration, minimal operational overhead.

### Options Considered

| Criteria | EMR Serverless | Glue Streaming | EKS + Spark Operator |
|---|---|---|---|
| **Pricing model** | Per-second (vCPU + memory) | Per-DPU-second | Per-node (EC2) |
| **Idle cost** | Zero | Zero | Node minimum |
| **PySpark control** | Full (configs, packages) | Limited (Glue abstractions) | Full |
| **Startup time** | 30-90s (cold), instant (warm) | 60-120s | Minutes (pod scheduling) |
| **Spark version** | 3.4 (EMR 7.0) | 3.3 (Glue 4.0) | Any |
| **Operational overhead** | Low | Lowest | High |
| **Custom dependencies** | Yes (--packages, --py-files) | Limited | Yes |
| **Streaming checkpoints** | S3 | S3 | S3 or HDFS |

### Decision

**EMR Serverless with Spark 3.4 runtime.**

### Rationale

1. **Full PySpark control:** Unlike Glue, EMR Serverless runs standard Spark. We can use any Spark configuration, add packages, tune memory—essential for a portfolio demonstrating Spark expertise.

2. **Pay-per-second:** True serverless billing. When streaming is stopped, cost is zero. Aligns with our cost constraints.

3. **Portfolio differentiation:** "PySpark on EMR Serverless" is more impressive on a resume than "Glue Streaming ETL job." It shows hands-on Spark skills, not just managed ETL.

4. **Modern Spark version:** EMR 7.0 includes Spark 3.4 with the latest Structured Streaming features (rate source improvements, better watermark handling).

### Consequences

**Positive:**
- Demonstrates real Spark skills
- Full control over job configuration
- Excellent cost model for intermittent workloads

**Negative:**
- Slightly more complex than Glue (explicit job submission)
- Cold start latency (30-90s) vs always-warm clusters

---

## ADR-004: Orchestration — Step Functions vs MWAA (Airflow) vs EventBridge

**Status:** Accepted  
**Date:** 2025-02-05

### Context

We need an orchestration layer for batch workflows: historical data loading, reprocessing jobs, quality validation, and catalog updates. The orchestrator must integrate with EMR Serverless job submission and Lambda functions.

### Options Considered

| Criteria | Step Functions | MWAA (Airflow) | EventBridge + Lambda |
|---|---|---|---|
| **Pricing** | Per state transition | Per environment-hour | Per event + Lambda |
| **Minimum cost** | ~$0 (pay per use) | ~$300/month minimum | ~$0 |
| **Visual workflow** | Yes (built-in) | Yes (Airflow UI) | No (custom) |
| **EMR integration** | Native (SDK integration) | Via operators | Custom Lambda |
| **Error handling** | Built-in retry, catch, fallback | Task-level retries | Custom |
| **Learning curve** | Low (JSON/YAML DSL) | Medium (Python DAGs) | Low |
| **State management** | Built-in | External (Airflow DB) | Custom |

### Decision

**AWS Step Functions with EventBridge scheduling.**

### Rationale

1. **Serverless cost model:** No minimum monthly cost. For a portfolio project with infrequent batch runs, Step Functions costs pennies vs $300+/month for MWAA.

2. **Native EMR integration:** Step Functions has built-in optimized integrations for EMR Serverless job submission, including `.sync` patterns that wait for completion.

3. **Visual workflow:** The Step Functions console provides a visual workflow editor and execution history—useful for demos and debugging.

4. **Appropriate complexity:** MWAA (Airflow) is overkill for our 5-step batch workflow. It's designed for complex, multi-DAG environments with dozens of pipelines.

### Consequences

**Positive:**
- Zero idle cost
- Visual workflow editor for demos
- Native AWS integrations

**Negative:**
- Less portable than Airflow (AWS-specific)
- Some Caylent clients may use Airflow and want that experience demonstrated

**Mitigation:**
- Note in portfolio that MWAA/Airflow is recommended for complex multi-pipeline orchestration
- The workflow patterns (retry, error handling, conditional logic) transfer to any orchestrator

---

## ADR-005: Data Governance — Lake Formation vs IAM-Only

**Status:** Accepted  
**Date:** 2025-02-05

### Context

We need to control access to our lakehouse data. Options range from pure IAM policies on S3/Glue to AWS Lake Formation's centralized governance model.

### Decision

**Lake Formation for database/table-level permissions, hybrid with IAM for service access.**

### Rationale

1. **Principal-level demonstration:** Lake Formation is expected knowledge for a Principal Data Architect. Including it shows governance awareness beyond basic IAM.

2. **Simplified table permissions:** Lake Formation abstracts away the complex IAM policies needed for Glue + S3 + Athena access patterns.

3. **Future-ready:** Lake Formation enables column-level security, row-level filtering, and LF-Tags—features increasingly requested by enterprise clients.

4. **Hybrid approach:** We use Lake Formation for data access (SELECT on tables) and IAM for service access (Lambda execution, EMR submission). This is the recommended pattern.

### Consequences

**Positive:**
- Demonstrates governance maturity
- Simplifies analyst onboarding
- Enables future column/row security

**Negative:**
- Additional complexity for a portfolio project
- Lake Formation permissions can conflict with IAM if not configured carefully

---

## ADR-006: Data Quality — Custom Framework vs Great Expectations vs Deequ

**Status:** Accepted  
**Date:** 2025-02-05

### Context

We need data quality validation in our streaming pipeline. Options include building a custom PySpark quality module, using Great Expectations, or using AWS Deequ.

### Decision

**Custom PySpark quality module with CloudWatch metrics integration.**

### Rationale

1. **Streaming-native:** Great Expectations and Deequ are primarily batch-oriented. While they can work with streaming, a custom module gives us more control over the streaming integration.

2. **Lightweight:** For a weekend project with 5-10 quality checks, a full framework is overkill. A focused module demonstrates the concepts without dependency overhead.

3. **Portfolio demonstration:** Writing a quality framework from scratch demonstrates understanding of data quality principles, not just tool usage.

4. **CloudWatch integration:** We can publish quality metrics directly to CloudWatch for dashboarding and alerting—tighter AWS integration than external tools.

### Consequences

**Positive:**
- Shows fundamental understanding of DQ patterns
- Lightweight, no additional dependencies
- Tight CloudWatch integration

**Negative:**
- Less feature-rich than mature frameworks
- Not reusable across projects without extraction

**Production recommendation:** For enterprise deployments, recommend Great Expectations or AWS Glue Data Quality for more comprehensive rule management and reporting.

---

## ADR-007: Modular Feature Architecture — Phases vs Modules

**Status:** Accepted
**Date:** 2025-02-14
**Deciders:** Frank, Mike Veksler

### Context

The original PRD defined capabilities in three rigid scope phases: Weekend MVP, Principal-Level Additions, and Future Enhancements. Adding new "smart money" features — wallet scoring, on-chain tracking, predictive signals — required rewriting multiple documents and refactoring code that assumed a fixed set of three streaming jobs.

As the project vision expanded from "detect CEX anomalies" to "find what smart money is doing and predict where it's going," we needed an architecture that could grow without constant restructuring.

### Options Considered

| Criteria | Phase-Based Scoping | Module-Based Composition |
|---|---|---|
| **Adding a new feature** | Rewrite PRD scope, update architecture, modify pipeline code | New module class + config entry |
| **Cost control** | All-or-nothing per phase | Per-module cost tracking, tier-based sizing |
| **Independent deployment** | No — phases are monolithic | Yes — enable/disable individual modules |
| **Complexity** | Low upfront, high over time | Higher upfront (framework), low ongoing |
| **Testing** | Coupled test suites | Isolated module tests + integration |
| **Extensibility signal** | Shows scope management | Shows plugin architecture (Principal-level skill) |

### Decision

**Module-based composition with config-driven feature toggles.**

Replace the phase-based scope with a **Module-Tier System**:

- **11 feature modules** (MOD-001 through MOD-011) cataloged in `docs/MODULE_REGISTRY.md`
- **3 tiers** (Small, Medium, Large) — each a superset of the previous
- **Standard module contract** — every module implements `BaseDetector` with consistent interface
- **YAML configuration** — modules activated via `config/features.yaml`, tier definitions in `config/tiers/`
- **Terraform integration** — `feature_tier` variable controls EMR sizing and SSM parameters
- **Single Spark application** — all detectors share one EMR cluster (one bill, simpler ops)

### Rationale

1. **Extensibility IS a Principal-level skill.** A plugin architecture demonstrates more architectural maturity than a rigid three-phase plan. Portfolio reviewers see composable design, not just task completion.

2. **Per-module cost control.** Each module documents its cost impact. Operators choose a tier that matches their budget. Small tier runs on 4 vCPU; Large needs 8 vCPU. No surprises.

3. **Right-sized complexity.** Small tier has the same code quality and patterns as Large — just fewer modules loaded. The framework overhead is minimal (6 base classes), but the extensibility payoff is significant.

4. **New features = new module + config entry.** Adding wallet scoring doesn't touch volume anomaly detection. Adding on-chain ingestion doesn't require rewriting the CEX pipeline. This is the microkernel pattern applied to data processing.

5. **YAML config over database flags.** For a portfolio project, version-controlled YAML is the right choice — reviewers can see the configuration in the repo. SSM parameters handle runtime values that come from Terraform.

### Consequences

**Positive:**
- Adding a feature requires only: new `BaseDetector` subclass, MODULE_REGISTRY entry, config update
- Cost scales predictably with tier selection
- Modules can be tested in isolation
- Architecture diagram shows generic pipeline, not hardcoded jobs
- Demonstrates plugin architecture pattern (valued at Principal level)

**Negative:**
- More upfront design work (base classes, registry, config loader)
- Slightly more indirection when reading code (must follow module → registry → config)
- Risk of over-engineering if the project never grows beyond Small tier

**Mitigation:**
- Framework classes are minimal (< 50 lines each for base classes)
- Small tier works identically to the original 3-job design — the framework is transparent
- MODULE_REGISTRY.md serves as both spec and documentation, not extra overhead

---

## ADR-008: Producer Compute — ECS Fargate vs Lambda vs EC2

**Status:** Accepted
**Date:** 2026-02-18
**Deciders:** Mike Veksler

### Context

The Kinesis producer connects to exchange WebSocket feeds (Binance, Coinbase) and writes normalized trade events to Kinesis. This is a **persistent, long-running process** — WebSocket connections must be maintained continuously while streaming is active. We need to choose a compute platform that supports this workload within our serverless-first, cost-optimized constraints.

### Options Considered

| Criteria | AWS Lambda | ECS Fargate | EC2 (spot) |
|---|---|---|---|
| **Max runtime** | 15 minutes (hard limit) | Unlimited | Unlimited |
| **WebSocket support** | No — timeout kills connection | Yes | Yes |
| **Idle cost** | ~$0 | ~$0 (stopped task) | Minimum instance cost |
| **Active cost** | N/A (disqualified) | ~$0.004/hr (Spot, 0.25vCPU/0.5GB) | ~$0.005/hr (t3.nano Spot) |
| **Serverless** | Yes | Yes (Fargate = serverless containers) | No |
| **Horizontal scale** | N/A | ECS Service scaling + env var symbol partitioning | Manual |
| **Operational overhead** | None | Low (ECS task definition) | High (AMI, patching) |
| **IAM integration** | Native task role | Native task role (ecs-tasks.amazonaws.com) | Instance profile |

### Decision

**ECS Fargate with Fargate Spot capacity, using environment variable-based symbol partitioning for horizontal scale.**

### Rationale

1. **Lambda is disqualified.** The 15-minute hard timeout cannot hold a persistent Binance or Coinbase WebSocket connection. The producer must stream continuously for hours or days. Lambda is architecturally incompatible with this requirement.

2. **ECS Fargate is serverless containers.** There are no servers to manage. The IAM producer role already trusts `ecs-tasks.amazonaws.com` (`infra/modules/iam/main.tf`). No infrastructure changes needed.

3. **Fargate Spot reduces cost ~70%.** At 0.25 vCPU / 0.5 GB, the producer costs ~$0.004/hr on Spot vs ~$0.012/hr on-demand. The reconnection logic built into each connector handles graceful Spot reclamation — the WebSocket reconnects with exponential backoff within seconds.

4. **Horizontal scaling via symbol partitioning.** Each Fargate task is assigned a non-overlapping symbol subset via the `SYMBOLS` environment variable (e.g., Task A: `btcusdt,ethusdt`, Task B: `solusdt`). This allows independent scaling without duplicating data in Kinesis. The full symbol list is stored in SSM (`/{prefix}/features/symbols`); per-task overrides are set in the ECS task environment.

5. **Async-native connector design.** The `BinanceConnector` and `CoinbaseConnector` expose an `async stream(queue)` coroutine. The ConnectorManager (Story 2.3) owns the event loop and runs all connectors concurrently via `asyncio.gather()`. This eliminates thread overhead and is idiomatic for I/O-bound streaming workloads.

### Connector Interface (Updated)

```python
class BaseConnector(ABC):
    def connect(self) -> None: ...         # Setup only — validate config, build URLs, no I/O
    def normalize(self, raw: dict) -> dict: ... # Normalize vendor format → unified schema
    def health_check(self) -> bool: ...    # True if message received within last 30s
    def shutdown(self) -> None: ...        # Signal stream() to exit

    # Implemented by each connector subclass:
    async def stream(self, queue: asyncio.Queue) -> None: ...  # Streaming coroutine with reconnect loop
```

### ConnectorManager Execution Model

```python
# ECS Fargate container entry point (Story 2.3)
async def main():
    queue = asyncio.Queue()
    await asyncio.gather(
        binance.stream(queue),
        coinbase.stream(queue),
        kinesis_writer.drain(queue),   # batches put_records() up to 500/call
    )

asyncio.run(main())
```

### Consequences

**Positive:**
- True serverless — no EC2 instances to manage or patch
- Fargate Spot keeps producer cost negligible (~$0.004/hr)
- Symbol partitioning enables horizontal scale without architecture changes
- Async coroutine model is memory-efficient and CI-friendly (deterministic tests with `pytest-asyncio`)
- Reconnection logic handles Spot reclamation transparently

**Negative:**
- ECS task definition Terraform must be added in Story 2.3 (not provisioned yet)
- Fargate Spot reclamation causes 30-60s reconnect gap — acceptable for trade data (Kinesis buffers)
- Symbol partitioning requires operational discipline to keep assignments non-overlapping

**Production Recommendation:** For high-availability production deployments, run a mix of Fargate on-demand (one task per exchange for reliability) and Fargate Spot (additional symbol-partitioned tasks for scale). Use ECS Service with desired count 2+ for automatic task replacement on Spot reclamation.
