"""Pre-inception backtest substitutions for RACE sleeves."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Substitution:
    sleeve: str
    replacements: tuple[tuple[str, float], ...]
    reason: str
    backtest_only: bool


def pre_inception_substitution(
    sleeve: str,
    evaluation_date: date,
    available_tickers: set[str],
    live_mode: bool = False,
) -> Substitution | None:
    if live_mode:
        return None
    if sleeve == "us_equity_factor":
        replacements = tuple((ticker, 0.5) for ticker in ("RPV", "SPHQ") if ticker in available_tickers)
        if len(replacements) == 2:
            return Substitution(sleeve, replacements, "factor_pre_inception_rpv_sphq", True)
        if "SPY" in available_tickers:
            return Substitution(sleeve, (("SPY", 1.0),), "factor_pre_inception_us_core", True)
    if sleeve == "crisis_alpha":
        if evaluation_date < date(2020, 5, 1):
            return Substitution(sleeve, (("IEF", 0.5), ("GLD", 0.5)), "crisis_alpha_pre_2020_proxy", True)
        if evaluation_date <= date(2021, 12, 31) and "DBMF" in available_tickers:
            return Substitution(sleeve, (("DBMF", 1.0),), "crisis_alpha_dbmf_only", True)
    if sleeve == "cash" and evaluation_date < date(2007, 5, 25):
        if "SHV" in available_tickers:
            return Substitution(sleeve, (("SHV", 1.0),), "cash_pre_bil_shv", True)
        return Substitution(sleeve, (("DGS3MO", 1.0),), "cash_pre_bil_dgs3mo_proxy", True)
    return None

