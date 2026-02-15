# Epics & Stories: Coat Tail Capital

> Mapping PRD goals to implementation tasks for the weekend sprint

## Document Control

| Field | Value |
|---|---|
| **Source** | `docs/PRD.md` v1.0, `docs/ARCHITECTURE.md` v1.0, `docs/MODULE_REGISTRY.md` v1.0 |
| **BMAD Workflow** | `/create-epics-and-stories` |
| **Sprint Scope** | Weekend MVP — Small Tier (Day 2: ~6-8 hours) |
| **Prioritization** | Framework first, then modules, then serving layer |
| **Architecture** | Generic Connector → Detector → Sink pipeline (ADR-007) |

---

## Epic 1: Plugin Framework

**PRD Goals:** P1 (PySpark mastery), P2 (architecture demonstration)
**Design Principle:** Framework first, then modules (ARCHITECTURE.md Section 13.4)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **1.1** Build BaseConnector | `src/spark-jobs/framework/base_connector.py` — abstract base class with `connect()`, `normalize()`, `health_check()`, `shutdown()` interface | ABC defined with type hints; importable; docstrings for public methods | Data Engineer | 0.25h |
| **1.2** Build BaseDetector | `src/spark-jobs/framework/base_detector.py` — abstract base with `module_id`, `module_name`, `configure()`, `process(df) → DataFrame`, `alert_types()`, `output_table()` | ABC defined; enforces module contract from MODULE_REGISTRY.md; testable with mock DataFrame | Data Engineer | 0.25h |
| **1.3** Build AlertRouter | `src/spark-jobs/framework/alert_router.py` — routes alerts conforming to base alert schema to DynamoDB + Iceberg `anomaly_alerts` table | Writes to DynamoDB with TTL; writes to Iceberg via Glue Catalog; handles `details` JSON field; idempotent on `alert_id` | Data Engineer | 0.5h |
| **1.4** Build ConfigLoader | `src/spark-jobs/framework/config_loader.py` — reads `config/features.yaml` + SSM parameters; resolves active tier and enabled modules | Loads Small tier config; reads SSM for runtime params (bucket names, stream name); returns typed config object | Data Engineer | 0.25h |
| **1.5** Build ModuleRegistry | `src/spark-jobs/framework/module_registry.py` — discovers and instantiates BaseDetector subclasses based on active config | Given Small tier config, discovers and returns MOD-001, MOD-002, MOD-003 instances; skips disabled modules | Data Engineer | 0.25h |
| **1.6** Build PipelineRunner | `src/spark-jobs/framework/pipeline_runner.py` — orchestrates: Kinesis source → DQ module → fan-out to active detectors → AlertRouter sinks | Single Spark application reads Kinesis, validates, fans out to N detectors, routes all alerts; checkpointing works | Data Engineer | 0.5h |

**Party Mode Opportunity:** Story 1.6 (PipelineRunner) should use Architect + Data Engineer + Security to validate the full pipeline wiring, checkpoint strategy, and input validation.

**Definition of Done:** Framework classes importable, type-checked, and unit-testable with mock DataFrames. `PipelineRunner` can wire up detectors from config without hardcoded module references.

---

## Epic 2: Data Ingestion (Connectors)

**PRD Goals:** G1 (real-time trade data from 2+ exchanges)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **2.1** Build BinanceConnector | `src/connectors/binance_connector.py` — subclass of BaseConnector; connects to Binance `@trade` WS for BTC/ETH/SOL; normalizes to unified trade schema | Binance trades flowing into Kinesis for 3 symbols; unified schema validated; reconnect on disconnect | Data Engineer | 0.75h |
| **2.2** Build CoinbaseConnector | `src/connectors/coinbase_connector.py` — subclass of BaseConnector; connects to Coinbase matches channel; normalizes to same unified schema | Coinbase trades interleaved with Binance in Kinesis; `exchange` field distinguishes source | Data Engineer | 0.5h |
| **2.3** Build ConnectorManager (Producer) | `src/producer/main.py` — reads `config/features.yaml` `required_connectors`, instantiates active connectors, manages lifecycle and Kinesis writes | Reads Small tier config; starts Binance + Coinbase connectors; exponential backoff on disconnect; CloudWatch metrics for records sent/failed | Data Engineer | 0.5h |

**Definition of Done:** PRD checklist item "Binance trade stream ingested into Kinesis for BTC/ETH/SOL". Connectors registered in `config/features.yaml`.

---

## Epic 3: Small Tier Detectors

**PRD Goals:** G2 (volume anomalies), G3 (whale detection), G4 (spread calculation), P1 (PySpark mastery)
**Modules:** MOD-001, MOD-002, MOD-003 per `docs/MODULE_REGISTRY.md`

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **3.1** Build config-driven data quality module | `src/spark-jobs/common/quality.py` — schema validation, null checks, range validation, dedup, timeliness; rules loaded from config; publishes CloudWatch metrics | DQ module passes unit tests; publishes `QualityScore` metric; routes failures to S3 DLQ by category; extensible via config | Data Engineer | 0.5h |
| **3.2** Build VolumeAnomalyDetector (MOD-001) | `src/detectors/volume_anomaly_detector.py` — subclass of BaseDetector; 60s tumbling window, rolling 1h mean/stddev, z-score, severity tiers | Z-score alerts fire within 90s of volume spike; alerts conform to base alert schema with `details` JSON; writes to `volume_aggregates` + `anomaly_alerts` + DynamoDB | Data Engineer | 0.75h |
| **3.3** Build WhaleDetector (MOD-002) | `src/detectors/whale_detector.py` — subclass of BaseDetector; per-record threshold filter, severity tiers ($100K/$500K/$1M) | 95%+ detection rate on test data; alerts use `alert_type: whale_trade` with correct `details` payload | Data Engineer | 0.5h |
| **3.4** Build SpreadCalculatorDetector (MOD-003) | `src/detectors/spread_calculator_detector.py` — subclass of BaseDetector; 30s tumbling window, VWAP per exchange, spread calculation | Spread calculations within 30s window; alerts fire on divergence >0.5%; both exchanges present in `details` | Data Engineer | 0.5h |

**Party Mode Opportunity:** Story 3.2 (first detector) should use Architect + Data Engineer + Security — establishes the BaseDetector implementation pattern for 3.3 and 3.4.

**Definition of Done:** PRD checklist items "PySpark streaming job running on EMR Serverless detecting anomalies" + "Data landing in S3 Iceberg tables, queryable via Athena". All 3 detectors auto-discovered by ModuleRegistry from Small tier config.

---

## Epic 4: Batch Processing

**PRD Goals:** G5 (historical data in lakehouse), P1 (PySpark mastery)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **4.1** Build historical data loader | Lambda that paginates Binance REST API (`/api/v3/aggTrades`), normalizes to unified schema, writes Parquet to S3 raw zone | Historical data for BTC/ETH/SOL lands in S3 partitioned by date/symbol; registered in Glue | Data Engineer | 0.5h |
| **4.2** Build reprocessing batch job | PySpark batch job that reads from Iceberg `raw_trades` (with time-travel), runs through PipelineRunner with active detectors, writes to reprocessed tables | Reprocessing produces consistent results with streaming; Iceberg time-travel query works; PipelineRunner reused for batch | Data Engineer | 0.25h |

**Definition of Done:** Step Functions workflow executes end-to-end (historical load → Spark batch → quality check → catalog update)

---

## Epic 5: API & Serving Layer

**PRD Goals:** G6 (dashboard + API, <500ms response, <3s load)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **5.1** Build GET /alerts Lambda handler | Query DynamoDB (base table or GSIs); filter by any registered `alert_type` from MODULE_REGISTRY; return JSON with pagination | Responds <500ms; filters by type, symbol, since; handles open alert_type enum; returns max 200 results | Data Engineer | 0.5h |
| **5.2** Build GET /metrics/{symbol} handler | Aggregate latest volume, spread, anomaly count, last whale from DynamoDB | Responds <500ms; returns current state for any tracked symbol | Data Engineer | 0.25h |
| **5.3** Configure API Gateway | REST API with two routes, CORS enabled, throttling (100 req/s) | API accessible from browser; CORS headers present; throttling configured | DevOps | 0.25h |

**Definition of Done:** PRD checklist item "Alerts in DynamoDB, accessible via Lambda API"

---

## Epic 6: Dashboard

**PRD Goals:** G6 (dashboard loads <3s)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **6.1** Scaffold React dashboard | Vite + React + TailwindCSS + Recharts; layout with header, alert feed, volume chart, spread tracker, whale log, system health | App builds and runs locally; all 6 layout sections visible | Data Engineer | 0.5h |
| **6.2** Wire API polling & live data | Poll GET /alerts and GET /metrics every 10s; render data in charts and tables | Dashboard updates every 10s; shows real alerts from DynamoDB; loads <3s | Data Engineer | 0.5h |
| **6.3** Add disclaimer & polish | "Not financial advice" disclaimer, live/paused indicator, last-updated timestamp | Disclaimer visible; indicator reflects API connectivity | Data Engineer | 0.15h |

**Definition of Done:** PRD checklist item "Dashboard displaying live alerts and charts"

---

## Epic 7: Testing

**PRD Goals:** NF2 (reproducible), P1 (mastery)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **7.1** Unit tests for framework base classes | Test BaseDetector contract enforcement, ModuleRegistry discovery, ConfigLoader tier resolution, AlertRouter schema compliance | Framework contracts verified; `pytest tests/unit/test_framework.py` passes | QA | 0.25h |
| **7.2** Unit tests for data quality module | Test each validation rule (schema, nulls, range, dedup, timeliness) with pass/fail cases | All DQ rules covered; `pytest tests/unit/test_quality.py` passes | QA | 0.25h |
| **7.3** Unit tests for detectors | Test VolumeAnomalyDetector z-score, WhaleDetector threshold, SpreadCalculatorDetector VWAP with mock DataFrames | Core business logic covered per detector; each detector testable in isolation | QA | 0.25h |
| **7.4** Unit tests for Lambda handlers | Test API response format, GSI query routing, open alert_type handling, edge cases | All API paths covered; `pytest tests/unit/test_api.py` passes | QA | 0.15h |

**Definition of Done:** `pytest tests/unit/ -v` passes, CI pipeline green

---

## Epic 8: Documentation & Portfolio Polish

**PRD Goals:** P2 (architecture), P3 (BMAD), P4 (collaboration), P5 (Well-Architected)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **8.1** Final README polish | Update CLAUDE.md with completed state, verify all links, add demo instructions | README accurately reflects deployed project; quick-start works | Coach | 0.15h |
| **8.2** LinkedIn post drafts | Architecture diagram screenshot, modular framework callout, 3-5 key learnings, BMAD method showcase | Two posts drafted (one per contributor) | Coach | 0.25h |

**Definition of Done:** PRD checklist items "README with architecture diagram" + "LinkedIn posts drafted"

---

## Sprint Plan: Recommended Execution Order

| Order | Story | Dependencies | Parallelizable |
|---|---|---|---|
| 1 | 1.1 — BaseConnector | None | Yes (with 1.2) |
| 2 | 1.2 — BaseDetector | None | Yes (with 1.1) |
| 3 | 1.3 — AlertRouter | 1.2 (alert schema) | No |
| 4 | 1.4 — ConfigLoader | None | Yes (with 1.3) |
| 5 | 1.5 — ModuleRegistry | 1.2, 1.4 | No |
| 6 | 1.6 — PipelineRunner (Party Mode) | 1.2, 1.3, 1.4, 1.5 | No (wires everything) |
| 7 | 3.1 — Data quality module | 1.6 | Yes (with 2.1) |
| 8 | 2.1 — BinanceConnector | 1.1 | Yes (with 3.1) |
| 9 | 3.2 — VolumeAnomalyDetector (Party Mode) | 1.2, 1.6, 3.1 | No (sets patterns) |
| 10 | 2.2 — CoinbaseConnector | 1.1, patterns from 2.1 | Yes (with 3.3) |
| 11 | 3.3 — WhaleDetector | 1.2, patterns from 3.2 | Yes (with 2.2) |
| 12 | 3.4 — SpreadCalculatorDetector | 1.2, 2.2, patterns from 3.2 | Yes (with 7.1) |
| 13 | 2.3 — ConnectorManager (Producer) | 2.1, 2.2, 1.4 | Yes (with 3.4) |
| 14 | 7.1 — Framework unit tests | 1.1-1.6 | Yes (with 3.4) |
| 15 | 7.2 — DQ unit tests | 3.1 | Yes (with 7.3) |
| 16 | 7.3 — Detector unit tests | 3.2, 3.3, 3.4 | Yes (with 5.1) |
| 17 | 5.1 — GET /alerts handler | DynamoDB populated | Yes (with 7.3) |
| 18 | 5.2 — GET /metrics handler | 5.1 | No |
| 19 | 5.3 — API Gateway config | 5.1, 5.2 | No |
| 20 | 4.1 — Historical loader | S3 raw zone ready | Yes (with 6.1) |
| 21 | 4.2 — Reprocessing batch job | 4.1, 1.6 (reuses PipelineRunner) | No |
| 22 | 6.1 — Scaffold dashboard | None | Yes (with 4.1) |
| 23 | 6.2 — Wire API polling | 6.1, 5.3 | No |
| 24 | 6.3 — Disclaimer & polish | 6.2 | No |
| 25 | 7.4 — Lambda handler tests | 5.1, 5.2 | Yes (with 6.3) |
| 26 | 8.1 — README polish | All code done | No |
| 27 | 8.2 — LinkedIn drafts | 8.1 | No |

**Critical Path:** 1.1/1.2 → 1.3 → 1.5 → 1.6 (Party Mode) → 3.1 → 3.2 (Party Mode) → 3.3/3.4 → 5.1 → 5.2 → 5.3 → 6.1 → 6.2 → 8.1

**Total Estimated Effort:** ~8.5 hours (tight for Day 2's 6-8 hour target — the framework adds ~1h but pays back in detector velocity and portfolio demonstration)
