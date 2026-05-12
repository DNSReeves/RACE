from datetime import date

from race_engine.universe.substitution import pre_inception_substitution
from race_engine.universe.universe import baseline_universe, eligible_entries, sleeve_for_ticker


def test_every_baseline_etf_maps_to_exactly_one_sleeve() -> None:
    entries = baseline_universe()
    tickers = [entry.ticker for entry in entries]

    assert len(tickers) == len(set(tickers))
    assert sleeve_for_ticker("TIP") == "fixed_income"
    assert sleeve_for_ticker("VTIP") == "fixed_income"
    assert sleeve_for_ticker("BCI") == "real_assets"


def test_bci_is_real_assets_candidate_not_forced_selection() -> None:
    entries = {entry.ticker: entry for entry in baseline_universe()}

    assert entries["BCI"].sleeve == "real_assets"
    assert "original RACE article" in entries["BCI"].rationale


def test_etf_not_selectable_before_252_days_of_history() -> None:
    entries = eligible_entries(date(2026, 5, 9), {"SPY": 251, "IVV": 252})
    tickers = {entry.ticker for entry in entries}

    assert "SPY" not in tickers
    assert "IVV" in tickers


def test_crisis_alpha_substitution_is_backtest_only() -> None:
    substitution = pre_inception_substitution(
        "crisis_alpha",
        date(2019, 1, 1),
        {"IEF", "GLD"},
        live_mode=False,
    )

    assert substitution is not None
    assert substitution.replacements == (("IEF", 0.5), ("GLD", 0.5))
    assert substitution.backtest_only is True
    assert pre_inception_substitution("crisis_alpha", date(2019, 1, 1), {"IEF", "GLD"}, live_mode=True) is None


def test_cash_pre_bil_uses_proxy() -> None:
    substitution = pre_inception_substitution("cash", date(2006, 1, 1), set())

    assert substitution is not None
    assert substitution.replacements == (("DGS3MO", 1.0),)
