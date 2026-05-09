"""Walk-forward backtest period generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class WalkForwardPeriod:
    training_start: date
    training_end: date
    oos_start: date
    oos_end: date
    substitution_period: bool = False


def quarterly_walk_forward_periods(
    backtest_start: date,
    backtest_end: date,
    initial_training_years: int = 5,
    step_weeks: int = 13,
    first_oos_start: date = date(2010, 1, 1),
    substitution_cutoff: date | None = None,
) -> tuple[WalkForwardPeriod, ...]:
    periods = []
    oos_start = first_oos_start
    while oos_start <= backtest_end:
        oos_end = min(backtest_end, oos_start + timedelta(weeks=step_weeks) - timedelta(days=1))
        training_end = oos_start - timedelta(days=1)
        training_start = max(backtest_start, date(training_end.year - initial_training_years, training_end.month, training_end.day))
        periods.append(
            WalkForwardPeriod(
                training_start,
                training_end,
                oos_start,
                oos_end,
                substitution_period=bool(substitution_cutoff and oos_start < substitution_cutoff),
            )
        )
        oos_start = oos_start + timedelta(weeks=step_weeks)
    return tuple(periods)

