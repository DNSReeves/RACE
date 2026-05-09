# RACE Release Candidate

Schema version: `race.audit.v1`

## Dry-Run Status

Current status: **WARN for dry-run use**.

The implementation scaffolding, deterministic modules, audit/report outputs, and standalone dry-run CLI are present. RACE is not production-trading-ready. It must remain diagnostic-only until recorded out-of-sample validation artifacts, ablation results, sensitivity sweeps, and 8-12 weeks of dry-run audit consistency support promotion.

RACE is standalone. `add_trim_sell_hold.py` is not part of the core strategy; it is only an optional ATSH compatibility bridge. Any ATSH handoff is downstream of the core RACE run.

## Implementation Coverage

- Configuration schema and immutable defaults: complete.
- Data readiness and degraded-mode rules: complete.
- Regime signals, persistence, blending, and recovery exception: complete.
- Universe, substitution, fallbacks, ETF ranking, risk gates, construction, risk budget, and trade quality: complete.
- Backtest, sensitivity, ablation, validation, audit, reports, and dry-run CLI: complete.
- Optional ATSH bridge: isolated from the standalone validation path.

## Validation And Falsification

Release evidence must include:

- OOS validation pass versus SPY and 60/40.
- Sharpe delta versus SPY of at least +0.20.
- Max drawdown at least 10 percentage points lower than SPY.
- Calmar above SPY.
- Positive excess return in at least four of five regimes.
- Non-negative ablation contribution from major engines.
- Sensitivity results that are not fragile.

## Promotion Gates

Execution behavior is not authorized unless all gates pass:

- OOS validation PASS.
- Ablation contribution non-negative.
- Sensitivity robust across required sweeps.
- Trade-quality counterfactual positive or turnover-beneficial.
- 8-12 weeks of dry-run audit consistency.
- No standalone schema or validation failures.

## Rollback Rules

Rollback to diagnostic-only on:

- Validation FAIL.
- Unexplained `WEIGHT_SUM_ERROR`.
- Tier 1 data failure.
- Stale data warnings above threshold.
- Unexpected turnover spike.
- Manual operator veto.

## Unresolved Limitations

- Numeric sleeve min/max and drift defaults are encoded locally because the markdown task package does not provide all underlying specification values.
- Dry-run order output is generated for manual review only and is never transmitted to a broker.
- `dbloader.py` remains a general-purpose database loader and is not modified by RACE.
- `summary_dict_debug.json` is ATSH-specific and is checked only by the optional ATSH bridge validation script.

## Dry-Run Command Examples

```powershell
python -m race_engine.execution.cli --race-engine-enable --race-current-positions-csv positions.csv --race-output-folder out\race --race-validation-status FAIL
python -m race_engine.execution.cli --race-engine-enable --race-current-positions-csv positions.csv --race-output-folder out\race --race-validation-status WARN --race-allow-warn-dry-run
python scripts\run_race_full_validation.py
python scripts\run_race_atsh_bridge_validation.py
```
