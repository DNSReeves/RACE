# RACE Engine

RACE is a rules-based, multi-sleeve ETF rotation strategy. It is designed around seven allocation sleeves and five market regimes, with deterministic configuration, auditable validation, regime classification, allocation, ranking, risk controls, portfolio construction, and dry-run order-list generation.

This package is not validated for production trading until the backtest, sensitivity, ablation, and dry-run gates pass. Live broker execution is not authorized by this package.

## Architectural Boundary

`dbloader.py` is an external, general-purpose ETF database loader. RACE must not add strategy-specific constants, sleeve mappings, regime logic, validation rules, imports, or execution hooks to `dbloader.py`.

RACE consumes populated databases through read-only adapter modules under `race_engine/data/`.

