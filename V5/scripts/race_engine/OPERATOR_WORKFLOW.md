# RACE Operator Workflow

## Routine Cycle

1. Refresh market, ETF, and macro data daily.
2. Run the standalone RACE evaluation after Friday close or before Monday open.
3. Review the JSON summary, audit ledger, markdown report, and HTML report.
4. Review the RACE Engine Dry Run output separately from any downstream ATSH bridge output.
5. Review the proposed order list manually.

## No-Action Conditions

Do not act on RACE output when:

- Validation status is `FAIL`.
- Required Tier 1 data is missing or stale without an approved fallback.
- The order list is marked `diagnostic_only=true`.
- There is an unexplained `WEIGHT_SUM_ERROR`.
- Turnover spikes unexpectedly.
- The operator vetoes the run.

## Manual Review Boundary

Actionable manual order review is allowed only for dry-run artifacts that are not diagnostic-only and only after validation status is `PASS`, or `WARN` with explicit operator approval. Broker execution remains unauthorized.

`add_trim_sell_hold.py` is not part of the core RACE strategy. ATSH integration is optional and downstream; run `scripts\run_race_atsh_bridge_validation.py` only when validating that bridge. `summary_dict_debug.json` is ATSH-specific and is not required for standalone RACE validation.

## Promotion Criteria

Promotion toward controlled portfolio-construction behavior requires OOS validation PASS, non-negative ablation results, robust sensitivity sweeps, positive trade-quality counterfactuals or turnover benefit, 8-12 weeks of consistent dry-run audit records, and clean standalone schema/validation checks.
