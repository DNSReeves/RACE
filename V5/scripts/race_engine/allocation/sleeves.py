"""Sleeve definitions and baseline ETF classification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    sleeve: str
    inception_date: date
    effective_date: date
    rationale: str
    q1_review_required: bool = True


BASELINE_UNIVERSE: tuple[UniverseEntry, ...] = (
    UniverseEntry("SPY", "us_equity_core", date(1993, 1, 29), date(2026, 1, 1), "US large-cap core"),
    UniverseEntry("IVV", "us_equity_core", date(2000, 5, 15), date(2026, 1, 1), "US large-cap core"),
    UniverseEntry("VOO", "us_equity_core", date(2010, 9, 7), date(2026, 1, 1), "US large-cap core"),
    UniverseEntry("VTI", "us_equity_core", date(2001, 5, 24), date(2026, 1, 1), "US total-market core"),
    UniverseEntry("RPV", "us_equity_factor", date(2006, 3, 1), date(2026, 1, 1), "Value factor"),
    UniverseEntry("SPHQ", "us_equity_factor", date(2005, 12, 6), date(2026, 1, 1), "Quality factor"),
    UniverseEntry("MTUM", "us_equity_factor", date(2013, 4, 16), date(2026, 1, 1), "Momentum factor"),
    UniverseEntry("QUAL", "us_equity_factor", date(2013, 7, 16), date(2026, 1, 1), "Quality factor"),
    UniverseEntry("USMV", "us_equity_factor", date(2011, 10, 18), date(2026, 1, 1), "Minimum volatility factor"),
    UniverseEntry("VXUS", "intl_equity", date(2011, 1, 26), date(2026, 1, 1), "International total market"),
    UniverseEntry("EFA", "intl_equity", date(2001, 8, 14), date(2026, 1, 1), "Developed international"),
    UniverseEntry("EEM", "intl_equity", date(2003, 4, 7), date(2026, 1, 1), "Emerging markets"),
    UniverseEntry("IEFA", "intl_equity", date(2012, 10, 18), date(2026, 1, 1), "Developed international core"),
    UniverseEntry("IEF", "fixed_income", date(2002, 7, 22), date(2026, 1, 1), "Intermediate Treasury"),
    UniverseEntry("TLT", "fixed_income", date(2002, 7, 22), date(2026, 1, 1), "Long Treasury"),
    UniverseEntry("AGG", "fixed_income", date(2003, 9, 22), date(2026, 1, 1), "Aggregate bonds"),
    UniverseEntry("BND", "fixed_income", date(2007, 4, 3), date(2026, 1, 1), "Total bond market"),
    UniverseEntry("TIP", "fixed_income", date(2003, 12, 4), date(2026, 1, 1), "TIPS fixed-income classification"),
    UniverseEntry("VTIP", "fixed_income", date(2012, 10, 12), date(2026, 1, 1), "Short TIPS fixed-income classification"),
    UniverseEntry("LQD", "fixed_income", date(2002, 7, 22), date(2026, 1, 1), "Investment-grade credit"),
    UniverseEntry("HYG", "fixed_income", date(2007, 4, 4), date(2026, 1, 1), "High-yield credit"),
    UniverseEntry("GLD", "real_assets", date(2004, 11, 18), date(2026, 1, 1), "Gold"),
    UniverseEntry("DBC", "real_assets", date(2006, 2, 3), date(2026, 1, 1), "Broad commodities"),
    UniverseEntry("PDBC", "real_assets", date(2014, 11, 7), date(2026, 1, 1), "Broad commodities"),
    UniverseEntry("VNQ", "real_assets", date(2004, 9, 23), date(2026, 1, 1), "Listed real estate"),
    UniverseEntry("DBMF", "crisis_alpha", date(2019, 5, 8), date(2026, 1, 1), "Managed futures"),
    UniverseEntry("KMLM", "crisis_alpha", date(2020, 12, 2), date(2026, 1, 1), "Managed futures"),
    UniverseEntry("BTAL", "crisis_alpha", date(2011, 9, 13), date(2026, 1, 1), "Anti-beta equity hedge"),
    UniverseEntry("BIL", "cash", date(2007, 5, 25), date(2026, 1, 1), "T-bill cash sleeve"),
    UniverseEntry("SHV", "cash", date(2007, 1, 5), date(2026, 1, 1), "Short Treasury cash fallback"),
    UniverseEntry("SGOV", "cash", date(2020, 5, 26), date(2026, 1, 1), "T-bill cash sleeve"),
)


SISTER_SLEEVES: dict[str, tuple[str, ...]] = {
    "us_equity_factor": ("us_equity_core",),
    "intl_equity": ("us_equity_core",),
    "real_assets": ("fixed_income", "cash"),
    "crisis_alpha": ("fixed_income", "cash"),
    "fixed_income": ("cash",),
    "us_equity_core": ("cash",),
    "cash": (),
}

