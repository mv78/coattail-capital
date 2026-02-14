# Module Registry: Coat Tail Capital

> Single source of truth for all feature modules

## Document Control

| Field | Value |
|---|---|
| **Project** | Coat Tail Capital (CTC) |
| **Version** | 1.0 |
| **Authors** | Mike Veksler, Frank D'Avanzo |
| **Referenced By** | `docs/PRD.md`, `docs/ARCHITECTURE.md`, `agents/data-engineer-agent.md` |

---

## Module Contract

Every feature module conforms to this standard interface:

| Field | Description |
|---|---|
| **Module ID** | Unique identifier (MOD-XXX) |
| **Name** | Machine-readable name (kebab-case) |
| **Tier** | Small, Medium, or Large |
| **Description** | What the module detects/computes |
| **Data Sources** | Required connectors (e.g., `binance-ws`, `ethereum-rpc`) |
| **Dependencies** | Other modules that must be active |
| **Processing** | Algorithm summary (window type, logic) |
| **Output Table** | Iceberg table name and partition strategy |
| **Alert Types** | Alert type strings emitted (open enum) |
| **Cost Impact** | Incremental cost per hour when active |

---

## Tier Summary

| Tier | Theme | Modules | Incremental Cost | Total Cost |
|---|---|---|---|---|
| **Small** | Detect CEX activity | MOD-001, MOD-002, MOD-003 | — | ~$0.82/hr |
| **Medium** | Track who smart money IS | +MOD-004, MOD-005, MOD-006, MOD-007 | +$0.58/hr | ~$1.40/hr |
| **Large** | Predict where it's going | +MOD-008, MOD-009, MOD-010, MOD-011 | +$1.10/hr | ~$2.50/hr |

Each tier is a superset of the previous. Medium includes all Small modules. Large includes all Medium modules.

---

## Small Tier Modules

### MOD-001: volume-anomaly

| Field | Value |
|---|---|
| **Module ID** | MOD-001 |
| **Name** | `volume-anomaly` |
| **Tier** | Small |
| **Description** | Detects statistically significant volume spikes using z-score analysis over tumbling windows. Identifies when trading activity for a symbol deviates meaningfully from its rolling baseline. |
| **Data Sources** | `binance-ws`, `coinbase-ws` |
| **Dependencies** | None |
| **Processing** | 60-second tumbling window aggregation per `(symbol, exchange)`. Maintains rolling 1-hour mean and stddev per symbol via stateful processing. Calculates z-score: `z = (window_volume - rolling_mean) / rolling_stddev`. Flags anomaly if `|z| > 2.5`. Severity: `>2.5` medium, `>3.5` high. |
| **Output Table** | `volume_aggregates` — partitioned by `date(window_start), symbol` |
| **Alert Types** | `volume_spike` |
| **Cost Impact** | Included in base EMR compute (~$0.10/hr share) |

---

### MOD-002: whale-detector

| Field | Value |
|---|---|
| **Module ID** | MOD-002 |
| **Name** | `whale-detector` |
| **Tier** | Small |
| **Description** | Identifies large single trades (whale activity) by filtering on quote volume thresholds. Enriches with exchange context and severity classification. |
| **Data Sources** | `binance-ws`, `coinbase-ws` |
| **Dependencies** | None |
| **Processing** | Per-record evaluation (no windowing). Filter trades where `quote_volume > $100,000`. Severity tiers: `>$100K` medium, `>$500K` high, `>$1M` critical. |
| **Output Table** | `whale_trades` — partitioned by `date(detected_at), symbol` |
| **Alert Types** | `whale_trade` |
| **Cost Impact** | Included in base EMR compute (~$0.05/hr share) |

---

### MOD-003: spread-calculator

| Field | Value |
|---|---|
| **Module ID** | MOD-003 |
| **Name** | `spread-calculator` |
| **Tier** | Small |
| **Description** | Calculates cross-exchange price divergence by comparing VWAP across exchanges within tumbling windows. Flags arbitrage-relevant spreads. |
| **Data Sources** | `binance-ws`, `coinbase-ws` |
| **Dependencies** | None |
| **Processing** | 30-second tumbling window. VWAP per `(symbol, exchange)` per window. Spread = `(exchange_a_vwap - exchange_b_vwap) / exchange_b_vwap * 100`. Flag if `|spread| > 0.5%`. |
| **Output Table** | `exchange_spreads` — partitioned by `date(window_start), symbol` |
| **Alert Types** | `spread_divergence` |
| **Cost Impact** | Included in base EMR compute (~$0.15/hr share) |

---

## Medium Tier Modules

### MOD-004: wallet-scorer

| Field | Value |
|---|---|
| **Module ID** | MOD-004 |
| **Name** | `wallet-scorer` |
| **Tier** | Medium |
| **Description** | Scores wallet addresses based on historical trading performance — hit rate, average return, timing relative to price movements. Identifies consistently profitable actors. |
| **Data Sources** | `ethereum-rpc`, `solana-rpc` (on-chain transaction data) |
| **Dependencies** | MOD-008 (`onchain-ingester`) for on-chain data, or operates on labeled data from MOD-005 |
| **Processing** | Batch + streaming hybrid. Batch: compute historical alpha scores from labeled wallet trade history. Streaming: update scores incrementally as new trades arrive. Score formula: `alpha = win_rate * avg_return * sqrt(trade_count) / max_drawdown`. Rolling 30-day window. |
| **Output Table** | `wallet_scores` — partitioned by `date(scored_at), blockchain` |
| **Alert Types** | `high_alpha_wallet`, `score_change` |
| **Cost Impact** | ~$0.15/hr (additional compute for scoring) |

---

### MOD-005: labeled-whales

| Field | Value |
|---|---|
| **Module ID** | MOD-005 |
| **Name** | `labeled-whales` |
| **Tier** | Medium |
| **Description** | Maintains a registry of known whale wallets with labels (fund name, entity type, historical behavior). Enriches on-chain transactions with identity context. |
| **Data Sources** | Static label dataset (CSV/JSON), community APIs (Arkham, Nansen-style) |
| **Dependencies** | None |
| **Processing** | Batch load of labeled wallet addresses into a lookup table. Streaming enrichment: join incoming transactions against label registry. Periodic refresh of label dataset (daily batch). |
| **Output Table** | `labeled_wallets` — unpartitioned (small reference table) |
| **Alert Types** | `known_whale_activity` |
| **Cost Impact** | ~$0.08/hr (lookup table maintenance, join overhead) |

---

### MOD-006: flow-direction

| Field | Value |
|---|---|
| **Module ID** | MOD-006 |
| **Name** | `flow-direction` |
| **Tier** | Medium |
| **Description** | Tracks net flow direction of assets — are whales accumulating or distributing? Aggregates buy/sell volume from whale-sized trades to determine smart money conviction. |
| **Data Sources** | `binance-ws`, `coinbase-ws` |
| **Dependencies** | MOD-002 (`whale-detector`) for whale trade identification |
| **Processing** | 5-minute tumbling window. Aggregate whale trades (from MOD-002 output) by side. Net flow = `buy_volume - sell_volume`. Flow ratio = `buy_volume / (buy_volume + sell_volume)`. Signal: ratio > 0.7 = accumulation, ratio < 0.3 = distribution. |
| **Output Table** | `flow_direction` — partitioned by `date(window_start), symbol` |
| **Alert Types** | `accumulation_signal`, `distribution_signal` |
| **Cost Impact** | ~$0.10/hr (aggregation on whale trade stream) |

---

### MOD-007: consensus

| Field | Value |
|---|---|
| **Module ID** | MOD-007 |
| **Name** | `consensus` |
| **Tier** | Medium |
| **Description** | Combines signals from multiple modules into a unified conviction score. When volume spikes, whale activity, and flow direction all align, the consensus score increases — indicating higher-confidence smart money signals. |
| **Data Sources** | Internal (outputs from MOD-001, MOD-002, MOD-006) |
| **Dependencies** | MOD-001 (`volume-anomaly`), MOD-002 (`whale-detector`), MOD-006 (`flow-direction`) |
| **Processing** | 5-minute tumbling window. Reads recent alerts from dependent modules. Weighted scoring: volume_spike (0.3) + whale_trade (0.3) + flow_signal (0.4). Consensus score 0-100. Threshold: score > 70 = strong signal. |
| **Output Table** | `consensus_signals` — partitioned by `date(window_start), symbol` |
| **Alert Types** | `consensus_bullish`, `consensus_bearish` |
| **Cost Impact** | ~$0.25/hr (multi-stream joins and scoring) |

---

## Large Tier Modules

### MOD-008: onchain-ingester

| Field | Value |
|---|---|
| **Module ID** | MOD-008 |
| **Name** | `onchain-ingester` |
| **Tier** | Large |
| **Description** | Ingests on-chain transaction data from Ethereum and Solana blockchains. Normalizes DEX swaps, token transfers, and whale wallet movements into a unified on-chain event schema. |
| **Data Sources** | `ethereum-rpc` (Alchemy/Infura), `solana-rpc` (Helius/QuickNode) |
| **Dependencies** | None |
| **Processing** | Streaming ingestion via WebSocket subscriptions to new blocks/transactions. Filter for: DEX router contracts (Uniswap, Jupiter), large token transfers (>$50K), known whale wallet activity. Normalize to unified on-chain event schema. |
| **Output Table** | `onchain_events` — partitioned by `date(block_timestamp), blockchain` |
| **Alert Types** | `large_transfer`, `dex_swap` |
| **Cost Impact** | ~$0.35/hr (RPC node costs + compute for block parsing) |

---

### MOD-009: dex-tracker

| Field | Value |
|---|---|
| **Module ID** | MOD-009 |
| **Name** | `dex-tracker` |
| **Tier** | Large |
| **Description** | Tracks DEX trading activity — swap volumes, liquidity changes, and price impact of large orders on decentralized exchanges. Complements CEX data with DeFi activity. |
| **Data Sources** | `ethereum-rpc`, `solana-rpc` (via MOD-008) |
| **Dependencies** | MOD-008 (`onchain-ingester`) |
| **Processing** | Filter on-chain events for DEX swap transactions. Decode swap parameters (token pair, amount in/out, price impact). Aggregate by token pair and DEX protocol. 60-second windows for volume tracking. Flag large swaps (>$100K) with price impact analysis. |
| **Output Table** | `dex_trades` — partitioned by `date(swap_timestamp), blockchain, protocol` |
| **Alert Types** | `large_dex_swap`, `liquidity_change` |
| **Cost Impact** | ~$0.20/hr (swap decoding compute) |

---

### MOD-010: predictive-scorer

| Field | Value |
|---|---|
| **Module ID** | MOD-010 |
| **Name** | `predictive-scorer` |
| **Tier** | Large |
| **Description** | Generates forward-looking probability scores for price movements based on historical patterns of whale behavior, volume anomalies, and flow direction. Uses statistical models (not ML in v1) to score the likelihood of significant price moves within 1-4 hour windows. |
| **Data Sources** | Internal (outputs from MOD-001, MOD-002, MOD-004, MOD-006, MOD-007) |
| **Dependencies** | MOD-004 (`wallet-scorer`), MOD-007 (`consensus`) |
| **Processing** | 15-minute evaluation windows. Feature vector: consensus score, wallet alpha percentile, volume z-score, flow ratio, historical accuracy at similar conditions. Logistic regression on pre-computed coefficients (no real-time training). Output: probability of >2% move within 1h, 2h, 4h. |
| **Output Table** | `predictive_scores` — partitioned by `date(scored_at), symbol` |
| **Alert Types** | `high_probability_move`, `score_update` |
| **Cost Impact** | ~$0.30/hr (multi-source aggregation + scoring compute) |

---

### MOD-011: backtester

| Field | Value |
|---|---|
| **Module ID** | MOD-011 |
| **Name** | `backtester` |
| **Tier** | Large |
| **Description** | Validates signal quality by back-testing alerts against subsequent price action. Measures hit rate, average return, and Sharpe ratio for each module's signals. Provides feedback loop for threshold tuning. |
| **Data Sources** | Internal (Iceberg time-travel on all alert and price tables) |
| **Dependencies** | MOD-001, MOD-002, MOD-003 (minimum — validates any module's alerts) |
| **Processing** | Batch job (triggered daily or on-demand). For each alert in the last 24h, look forward 1h/4h/24h at actual price movement. Compute: hit rate (did price move in predicted direction?), average return, max drawdown. Aggregate by module, symbol, and time horizon. Iceberg time-travel for consistent point-in-time reads. |
| **Output Table** | `backtest_results` — partitioned by `date(backtest_date), module_id` |
| **Alert Types** | `backtest_complete`, `signal_degradation` |
| **Cost Impact** | ~$0.25/hr (batch compute, runs 1-2x daily) |

---

## Module Dependency Graph

```
Small Tier (standalone):
  MOD-001 volume-anomaly
  MOD-002 whale-detector
  MOD-003 spread-calculator

Medium Tier (builds on Small):
  MOD-004 wallet-scorer ──────► MOD-005 labeled-whales (optional enrichment)
  MOD-005 labeled-whales
  MOD-006 flow-direction ─────► MOD-002 whale-detector
  MOD-007 consensus ──────────► MOD-001, MOD-002, MOD-006

Large Tier (builds on Medium):
  MOD-008 onchain-ingester
  MOD-009 dex-tracker ────────► MOD-008 onchain-ingester
  MOD-010 predictive-scorer ──► MOD-004, MOD-007
  MOD-011 backtester ─────────► MOD-001, MOD-002, MOD-003 (validates any)
```

---

## Alert Type Registry

| Alert Type | Module | Severity Levels |
|---|---|---|
| `volume_spike` | MOD-001 | medium, high |
| `whale_trade` | MOD-002 | medium, high, critical |
| `spread_divergence` | MOD-003 | medium, high |
| `high_alpha_wallet` | MOD-004 | medium, high |
| `score_change` | MOD-004 | low |
| `known_whale_activity` | MOD-005 | medium, high |
| `accumulation_signal` | MOD-006 | medium, high |
| `distribution_signal` | MOD-006 | medium, high |
| `consensus_bullish` | MOD-007 | medium, high |
| `consensus_bearish` | MOD-007 | medium, high |
| `large_transfer` | MOD-008 | medium, high |
| `dex_swap` | MOD-008 | low, medium |
| `large_dex_swap` | MOD-009 | medium, high |
| `liquidity_change` | MOD-009 | medium, high |
| `high_probability_move` | MOD-010 | high |
| `score_update` | MOD-010 | low |
| `backtest_complete` | MOD-011 | low |
| `signal_degradation` | MOD-011 | high |

The `alert_type` field is an open string — new modules register new types without schema changes.

---

## Iceberg Table Registry

### Core Tables (always present)

| Table | Owner | Partition Strategy |
|---|---|---|
| `raw_trades` | Platform (ingestion) | `date(timestamp), symbol` |
| `anomaly_alerts` | Platform (all modules write) | `date(detected_at), alert_type` |

### Module-Created Tables

| Table | Owner Module | Partition Strategy |
|---|---|---|
| `volume_aggregates` | MOD-001 | `date(window_start), symbol` |
| `whale_trades` | MOD-002 | `date(detected_at), symbol` |
| `exchange_spreads` | MOD-003 | `date(window_start), symbol` |
| `wallet_scores` | MOD-004 | `date(scored_at), blockchain` |
| `labeled_wallets` | MOD-005 | Unpartitioned |
| `flow_direction` | MOD-006 | `date(window_start), symbol` |
| `consensus_signals` | MOD-007 | `date(window_start), symbol` |
| `onchain_events` | MOD-008 | `date(block_timestamp), blockchain` |
| `dex_trades` | MOD-009 | `date(swap_timestamp), blockchain, protocol` |
| `predictive_scores` | MOD-010 | `date(scored_at), symbol` |
| `backtest_results` | MOD-011 | `date(backtest_date), module_id` |

Tables are created by the module's detector on first run. Disabled modules = no table created.

---

## Adding a New Module

1. Assign the next `MOD-XXX` ID
2. Add the module spec to this registry following the standard contract
3. Assign to a tier (or create a new tier)
4. Implement as a `BaseDetector` subclass (see `agents/data-engineer-agent.md`)
5. Add module ID to the appropriate tier YAML in `config/tiers/`
6. If new data source needed, implement as a `BaseConnector` subclass
7. Run `terraform apply` to update SSM parameters with new active modules
