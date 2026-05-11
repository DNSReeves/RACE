@echo off
setlocal

rem RACE V5 periodic dry-run report workflow.
rem Run from: C:\Users\david\Development\Python\RACE\V5\scripts
rem This script does not place trades or call broker APIs.

cd /d "%~dp0"

set "MARKET_DB=C:\Users\david\Development\Python\ta_optimizer.dir\etf_trading\etf_trading_system\databases\etf_market_data.db"
set "REGISTRY_DB=C:\Users\david\Development\Python\ta_optimizer.dir\etf_trading\etf_trading_system\databases\etf_registry.db"
set "REGISTRY_SCHEMA=C:\Users\david\Development\Python\ta_optimizer.dir\etf_trading\etf_trading_system\databases\etf_registry_schema.sql"

set "FRED_KEY_FILE=api_keys\fred_api_key.txt"
set "EODHD_KEY_FILE=api_keys\eodhd_api_key.txt"
set "FMP_KEY_FILE=api_keys\fmp_api_key.txt"

set "OUT_DIR=race_engine_out"
set "MACRO_CSV=%OUT_DIR%\race_macro.csv"
set "VIX_CSV=%OUT_DIR%\vix.csv"
set "CACHE_DB=%OUT_DIR%\race_market_cache.sqlite"
set "ORDER_JSON=%OUT_DIR%\race_order_list.json"
set "ORDER_HTML=%OUT_DIR%\race_order_report.html"

rem Optional: set this to a CSV with columns ticker,current_weight.
set "CURRENT_POSITIONS_CSV=C:\Users\david\Development\Python\RACE\V5\scripts\DNSR-IRA-Positions-2026-05-11-172715.csv"

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo [1/4] Fetching local FRED macro and VIX CSV inputs...
if exist "%FMP_KEY_FILE%" (
  python scripts\load_race_macro_cache.py ^
    --fred-api-key-file "%FRED_KEY_FILE%" ^
    --eodhd-api-key-file "%EODHD_KEY_FILE%" ^
    --fmp-api-key-file "%FMP_KEY_FILE%"
) else (
  python scripts\load_race_macro_cache.py ^
    --fred-api-key-file "%FRED_KEY_FILE%" ^
    --eodhd-api-key-file "%EODHD_KEY_FILE%"
)
if errorlevel 1 (
  if exist "%MACRO_CSV%" if exist "%VIX_CSV%" (
    echo WARN: Macro/VIX refresh failed; reusing existing CSV files.
  ) else (
    goto fail
  )
)

echo [2/4] Building RACE market cache...
python scripts\build_race_market_cache.py ^
  --source-db "%MARKET_DB%" ^
  --source-registry-db "%REGISTRY_DB%" ^
  --registry-schema-file "%REGISTRY_SCHEMA%" ^
  --macro-csv "%MACRO_CSV%" ^
  --vix-csv "%VIX_CSV%" ^
  --output-db "%CACHE_DB%"
if errorlevel 1 goto fail

echo [3/4] Running standalone RACE dry-run engine...
if defined CURRENT_POSITIONS_CSV (
  python -m race_engine.execution.cli ^
    --race-engine-enable ^
    --race-market-data-cache "%CACHE_DB%" ^
    --race-current-positions-csv "%CURRENT_POSITIONS_CSV%" ^
    --race-validation-status PASS
) else (
  python -m race_engine.execution.cli ^
    --race-engine-enable ^
    --race-market-data-cache "%CACHE_DB%" ^
    --race-validation-status PASS
)
if errorlevel 1 goto fail

echo [4/4] Rendering HTML report...
python scripts\render_race_order_report.py ^
  --input-json "%ORDER_JSON%" ^
  --output-html "%ORDER_HTML%"
if errorlevel 1 goto fail

echo.
echo RACE periodic report complete:
echo   %ORDER_HTML%
exit /b 0

:fail
echo.
echo RACE periodic report failed. Review the error above.
exit /b 1
