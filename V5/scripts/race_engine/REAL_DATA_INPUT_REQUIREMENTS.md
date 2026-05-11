# RACE Real Data Input Requirements

RACE is standalone. It does not import or modify `dbloader.py`.

The data flow is:

```text
dbloader.py -> generic ETF database -> RACE cache builder -> race_market_cache.sqlite -> RACE pipeline
```

## Required RACE Cache

Build the cache with:

```powershell
python scripts\build_race_market_cache.py --source-db path\to\generic_etf_database.sqlite
```

Default output:

```text
race_engine_out/race_market_cache.sqlite
```

## Required Tables

The RACE pipeline reads these cache tables:

- `prices`
- `etf_metrics`
- `macro_observations`

The `prices` table must include:

```sql
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adjusted_close REAL NOT NULL,
    volume REAL,
    PRIMARY KEY (ticker, date)
);
```

`etf_metrics` must include `ticker`, `as_of`, `aum`, `expense_ratio`, and `bid_ask_spread`.

`macro_observations` must include `series_name`, `date`, and `value`.

## VIX And Macro Population

The standalone RACE pipeline requires VIX as a price-like series in `prices`, plus these macro series in `macro_observations`:

- `T10Y2Y`
- `T10YIE`
- `BAMLH0A0HYM2`

Create local CSV inputs with:

```powershell
python scripts\load_race_macro_cache.py
```

Default outputs:

```text
race_engine_out\race_macro.csv
race_engine_out\vix.csv
```

The utility uses FRED for `T10Y2Y`, `T10YIE`, and `BAMLH0A0HYM2`. It uses EODHD first for VIX when `EODHD_API_KEY` or `--eodhd-api-key-file` is available, then FMP when `FMP_API_KEY` or `--fmp-api-key-file` is available. API keys are never hardcoded and should remain in environment variables or local key files outside source control.

Then build the RACE market cache with:

```powershell
python scripts\build_race_market_cache.py --source-db generic.sqlite --macro-csv race_engine_out\race_macro.csv --vix-csv race_engine_out\vix.csv
```

Never commit generated CSV files or API key files.

If VIX is not present in the generic market database, provide a local VIX CSV:

```powershell
python scripts\build_race_market_cache.py --source-db generic.sqlite --vix-csv vix.csv
```

The VIX CSV must include `date` and one of `adjusted_close`, `close`, or `value`. Optional columns are `open`, `high`, `low`, and `volume`.

Macro observations can be loaded from a local CSV:

```powershell
python scripts\build_race_market_cache.py --source-db generic.sqlite --macro-csv macro.csv
```

The macro CSV must contain:

```text
series_name,date,value
T10Y2Y,2026-01-01,0.50
T10YIE,2026-01-01,2.10
BAMLH0A0HYM2,2026-01-01,300
```

Macro observations can also be loaded from a local SQLite source:

```powershell
python scripts\build_race_market_cache.py --source-db generic.sqlite --macro-source-db macro.sqlite
```

The macro SQLite source must contain a `macro_observations` table with `series_name`, `date`, and `value`.

## Required Series

Price history is required for the baseline RACE universe and Tier 1 price series:

- `SPY`, `QQQ`, `VIX`, `IEF`, `HYG`, `LQD`, `DBC`, `GLD`
- All ETFs listed in `race_engine/allocation/sleeves.py`

Macro observations are required for:

- `T10Y2Y`
- `T10YIE`
- `BAMLH0A0HYM2`

The current pipeline readiness check requires at least 800 price rows per required ticker and at least 21 `T10YIE` observations.

## Schema Translation

If the generic database uses different table names, pass:

```powershell
python scripts\build_race_market_cache.py --source-db generic.sqlite --price-table market_prices --metrics-table etf_registry --macro-table macro_observations
```

If adjusted close uses a different column name:

```powershell
python scripts\build_race_market_cache.py --source-db generic.sqlite --adjusted-close-column adj_close
```

The source database is opened read-only. The builder writes only the RACE-specific cache.

## Registry Database Metadata

Registry-side ETF metadata is described by:

```text
C:\Users\david\Development\Python\ta_optimizer.dir\etf_trading\etf_trading_system\databases\etf_registry_schema.sql
```

Use that SQL file as the authoritative registry schema when building from a separate registry database:

```powershell
python scripts\build_race_market_cache.py --source-db path\to\market.sqlite --source-registry-db path\to\registry.sqlite --registry-schema-file C:\Users\david\Development\Python\ta_optimizer.dir\etf_trading\etf_trading_system\databases\etf_registry_schema.sql
```

Important registry tables currently include:

- `etf_registry`
- `etf_metrics`
- `etf_sectors`
- `loading_history`
- `loading_sessions`

The RACE cache builder uses registry `etf_metrics.ticker`, `etf_metrics.aum`, `etf_metrics.expense_ratio`, and `etf_metrics.last_updated`. Registry `last_updated` is translated into RACE cache `etf_metrics.as_of`.

The documented registry schema does not include a bid-ask spread field. When the registry database is used as the metrics source, RACE cache `etf_metrics.bid_ask_spread` is left null unless a future schema adds an explicit source column.
