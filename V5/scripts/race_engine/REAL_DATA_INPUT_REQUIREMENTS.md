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

