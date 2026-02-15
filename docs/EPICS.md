# Epics & Stories: Coat Tail Capital

> Mapping PRD goals to implementation tasks for the weekend sprint

## Document Control

| Field | Value |
|---|---|
| **Source** | `docs/PRD.md` v1.0, `docs/ARCHITECTURE.md` v1.0 |
| **BMAD Workflow** | `/create-epics-and-stories` |
| **Sprint Scope** | Weekend MVP (Day 2: ~6-8 hours) |
| **Prioritization** | Critical path first, then parallelizable work |

---

## Epic 1: Data Ingestion

**PRD Goals:** G1 (real-time trade data from 2+ exchanges)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **1.1** Build Binance WebSocket producer | Connect to Binance `@trade` stream for BTC/ETH/SOL, normalize to unified schema, write to Kinesis | Binance trades flowing into Kinesis for 3 symbols; unified schema validated; reconnect on disconnect | Data Engineer | 1h |
| **1.2** Add Coinbase WebSocket producer | Connect to Coinbase matches channel, normalize to same unified schema, write to same Kinesis stream | Coinbase trades interleaved with Binance in Kinesis; `exchange` field distinguishes source | Data Engineer | 0.5h |
| **1.3** Producer error handling & metrics | Exponential backoff on disconnect, CloudWatch metrics for records sent/failed, graceful shutdown | Producer recovers from 30s disconnect; metrics visible in CloudWatch | Data Engineer | 0.25h |

**Definition of Done:** PRD checklist item "Binance trade stream ingested into Kinesis for BTC/ETH/SOL"

---

## Epic 2: Stream Processing

**PRD Goals:** G2 (volume anomalies), G3 (whale detection), G4 (spread calculation), P1 (PySpark mastery)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **2.1** Build shared data quality module | `src/spark-jobs/common/quality.py` — schema validation, null checks, range validation, dedup, timeliness; publish CloudWatch metrics | DQ module passes unit tests; publishes `QualityScore` metric; routes failures to S3 DLQ by category | Data Engineer | 0.5h |
| **2.2** Build volume anomaly streaming job | 60s tumbling window, rolling 1h mean/stddev, z-score calculation, flag if \|z\| > 2.5 | Z-score alerts fire within 90s of volume spike; alerts land in DynamoDB + Iceberg; severity classification works | Data Engineer | 1h |
| **2.3** Build whale detection streaming job | Per-record threshold filter (`quote_volume > $100K`), severity tiers ($100K/$500K/$1M) | 95%+ detection rate on test data; whale alerts in DynamoDB with full trade context | Data Engineer | 0.5h |
| **2.4** Build cross-exchange spread job | 30s tumbling window, VWAP per exchange, spread calculation, flag if \|spread\| > 0.5% | Spread calculations within 30s window; alerts fire on divergence; both exchanges present in output | Data Engineer | 0.5h |
| **2.5** Shared Spark config & Iceberg sinks | `src/spark-jobs/common/config.py` and `sink.py` — reusable Kinesis source, Iceberg writer, DynamoDB writer, CloudWatch publisher | All 3 jobs share common I/O modules; Iceberg tables registered in Glue Catalog; checkpointing works | Data Engineer | 0.5h |

**Party Mode Opportunity:** Story 2.2 (first streaming job) should use Architect + Data Engineer + Security in Party Mode to establish patterns for 2.3 and 2.4.

**Definition of Done:** PRD checklist items "PySpark streaming job running on EMR Serverless detecting anomalies" + "Data landing in S3 Iceberg tables, queryable via Athena"

---

## Epic 3: Batch Processing

**PRD Goals:** G5 (historical data in lakehouse), P1 (PySpark mastery)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **3.1** Build historical data loader | Lambda that paginates Binance REST API (`/api/v3/aggTrades`), normalizes to unified schema, writes Parquet to S3 raw zone | Historical data for BTC/ETH/SOL lands in S3 partitioned by date/symbol; registered in Glue | Data Engineer | 0.5h |
| **3.2** Build reprocessing batch job | PySpark batch job that reads from Iceberg `raw_trades` (with time-travel), applies anomaly logic, writes to `anomalies_reprocessed` | Reprocessing produces consistent results with streaming; Iceberg time-travel query works | Data Engineer | 0.25h |

**Definition of Done:** Step Functions workflow executes end-to-end (historical load → Spark batch → quality check → catalog update)

---

## Epic 4: API & Serving Layer

**PRD Goals:** G6 (dashboard + API, <500ms response, <3s load)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **4.1** Build GET /alerts Lambda handler | Query DynamoDB (base table or GSIs based on filters), return JSON response with pagination | Responds <500ms; filters by type, symbol, since; returns max 200 results | Data Engineer | 0.5h |
| **4.2** Build GET /metrics/{symbol} handler | Aggregate latest volume, spread, anomaly count, last whale from DynamoDB | Responds <500ms; returns current state for any tracked symbol | Data Engineer | 0.25h |
| **4.3** Configure API Gateway | REST API with two routes, CORS enabled, throttling (100 req/s) | API accessible from browser; CORS headers present; throttling configured | DevOps | 0.25h |

**Definition of Done:** PRD checklist item "Alerts in DynamoDB, accessible via Lambda API"

---

## Epic 5: Dashboard

**PRD Goals:** G6 (dashboard loads <3s)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **5.1** Scaffold React dashboard | Vite + React + TailwindCSS + Recharts; layout with header, alert feed, volume chart, spread tracker, whale log, system health | App builds and runs locally; all 6 layout sections visible | Data Engineer | 0.5h |
| **5.2** Wire API polling & live data | Poll GET /alerts and GET /metrics every 10s; render data in charts and tables | Dashboard updates every 10s; shows real alerts from DynamoDB; loads <3s | Data Engineer | 0.5h |
| **5.3** Add disclaimer & polish | "Not financial advice" disclaimer, live/paused indicator, last-updated timestamp | Disclaimer visible; indicator reflects API connectivity | Data Engineer | 0.15h |

**Definition of Done:** PRD checklist item "Dashboard displaying live alerts and charts"

---

## Epic 6: Testing

**PRD Goals:** NF2 (reproducible), P1 (mastery)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **6.1** Unit tests for data quality module | Test each validation rule (schema, nulls, range, dedup, timeliness) with pass/fail cases | All DQ rules covered; `pytest tests/unit/test_quality.py` passes | QA | 0.25h |
| **6.2** Unit tests for streaming logic | Test z-score calculation, whale threshold, spread calculation with mock data | Core business logic covered; `pytest tests/unit/` passes | QA | 0.25h |
| **6.3** Unit tests for Lambda handlers | Test API response format, GSI query routing, edge cases (no results, max limit) | All API paths covered; `pytest tests/unit/test_api.py` passes | QA | 0.15h |

**Definition of Done:** `pytest tests/unit/ -v` passes, CI pipeline green

---

## Epic 7: Documentation & Portfolio Polish

**PRD Goals:** P2 (architecture), P3 (BMAD), P4 (collaboration), P5 (Well-Architected)

| Story | Description | Acceptance Criteria | Agent | Est. |
|---|---|---|---|---|
| **7.1** Final README polish | Update CLAUDE.md with completed state, verify all links, add demo instructions | README accurately reflects deployed project; quick-start works | Coach | 0.15h |
| **7.2** LinkedIn post drafts | Architecture diagram screenshot, 3-5 key learnings, BMAD method callout | Two posts drafted (one per contributor) | Coach | 0.25h |

**Definition of Done:** PRD checklist items "README with architecture diagram" + "LinkedIn posts drafted"

---

## Sprint Plan: Recommended Execution Order

| Order | Story | Dependencies | Parallelizable |
|---|---|---|---|
| 1 | 2.5 — Shared Spark config & sinks | None | No (foundation) |
| 2 | 2.1 — Data quality module | None | Yes (with 1.1) |
| 3 | 1.1 — Binance producer | None | Yes (with 2.1) |
| 4 | 2.2 — Volume anomaly job (Party Mode) | 2.5, 2.1 | No (sets patterns) |
| 5 | 1.2 — Coinbase producer | 1.1 | Yes (with 2.3) |
| 6 | 2.3 — Whale detection job | 2.5, 2.1, patterns from 2.2 | Yes (with 1.2) |
| 7 | 2.4 — Spread calculator job | 2.5, 2.1, 1.2 | Yes (with 6.1) |
| 8 | 1.3 — Producer error handling | 1.1, 1.2 | Yes (with 2.4) |
| 9 | 6.1 — DQ unit tests | 2.1 | Yes (with 2.4) |
| 10 | 6.2 — Streaming logic tests | 2.2, 2.3, 2.4 | Yes (with 4.1) |
| 11 | 4.1 — GET /alerts handler | DynamoDB populated | Yes (with 6.2) |
| 12 | 4.2 — GET /metrics handler | 4.1 | No |
| 13 | 4.3 — API Gateway config | 4.1, 4.2 | No |
| 14 | 3.1 — Historical loader | S3 raw zone ready | Yes (with 5.1) |
| 15 | 3.2 — Reprocessing job | 3.1, Iceberg tables populated | No |
| 16 | 5.1 — Scaffold dashboard | None | Yes (with 3.1) |
| 17 | 5.2 — Wire API polling | 5.1, 4.3 | No |
| 18 | 5.3 — Disclaimer & polish | 5.2 | No |
| 19 | 6.3 — Lambda handler tests | 4.1, 4.2 | Yes (with 5.3) |
| 20 | 7.1 — README polish | All code done | No |
| 21 | 7.2 — LinkedIn drafts | 7.1 | No |

**Critical Path:** 2.5 → 2.1 → 2.2 (Party Mode) → 2.3/2.4 → 4.1 → 4.2 → 4.3 → 5.1 → 5.2 → 7.1

**Total Estimated Effort:** ~7.5 hours (fits within Day 2's 6-8 hour target)
