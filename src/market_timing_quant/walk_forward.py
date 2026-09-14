from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardFold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    test_year: int


def expanding_calendar_year_folds(
    sessions: pd.DatetimeIndex,
    *,
    train_start: str = "2006-06-21",
    initial_train_end: str = "2012-12-31",
) -> list[WalkForwardFold]:
    if sessions.empty or sessions.has_duplicates or not sessions.is_monotonic_increasing:
        raise ValueError("sessions must be unique and increasing")
    train_start_ts = pd.Timestamp(train_start)
    initial_end = pd.Timestamp(initial_train_end)
    if sessions.min() > train_start_ts or sessions.max() <= initial_end:
        raise ValueError("sessions do not cover the frozen initial train and a test period")
    folds = []
    for year in range(initial_end.year + 1, sessions.max().year + 1):
        test = sessions[(sessions.year == year) & (sessions > initial_end)]
        if test.empty:
            continue
        folds.append(WalkForwardFold(
            train_start=train_start_ts,
            train_end=pd.Timestamp(year=year - 1, month=12, day=31),
            test_start=test[0], test_end=test[-1], test_year=year,
        ))
    return folds


def require_selection_constraints(minimum_cagr: float | None, maximum_maxdd: float | None) -> None:
    """Fail closed rather than invent the missing frozen selection thresholds."""
    if minimum_cagr is None or maximum_maxdd is None:
        raise ValueError("parameter selection requires frozen minimum CAGR and maximum acceptable MaxDD")
    if minimum_cagr < -1 or not 0 <= maximum_maxdd <= 1:
        raise ValueError("invalid parameter-selection constraints")


def select_calmar_candidate(
    candidates: pd.DataFrame,
    *,
    minimum_cagr: float = 0.15,
    maximum_abs_max_drawdown: float = 0.45,
) -> tuple[pd.Series | None, pd.DataFrame]:
    """Apply the frozen eligibility gate, 5% Calmar band, and tie-break order."""
    require_selection_constraints(minimum_cagr, maximum_abs_max_drawdown)
    required = {"cagr", "max_drawdown", "calmar", "annual_turnover", "ma_days"}
    missing = required - set(candidates)
    if missing:
        raise ValueError(f"candidate table missing fields: {sorted(missing)}")
    evaluated = candidates.copy()
    evaluated["eligible"] = (
        (evaluated["cagr"] >= minimum_cagr)
        & (evaluated["max_drawdown"].abs() <= maximum_abs_max_drawdown)
        & evaluated["calmar"].notna()
    )
    evaluated["within_5pct_of_best_calmar"] = False
    eligible = evaluated[evaluated["eligible"]].copy()
    if eligible.empty:
        return None, evaluated
    best_calmar = float(eligible["calmar"].max())
    if best_calmar > 0:
        in_band = eligible["calmar"] >= best_calmar * 0.95
    else:
        # This branch is defensive; the frozen positive-CAGR gate normally makes Calmar positive.
        in_band = (best_calmar - eligible["calmar"]).abs() <= abs(best_calmar) * 0.05
    band = eligible[in_band].copy()
    evaluated.loc[band.index, "within_5pct_of_best_calmar"] = True
    band["abs_max_drawdown"] = band["max_drawdown"].abs()
    band["momentum_sort"] = band.get("momentum_days", pd.Series(0, index=band.index)).fillna(0)
    quantile = band.get("low_vol_quantile", pd.Series(0.33, index=band.index)).fillna(0.33)
    band["quantile_distance"] = (quantile - 0.33).abs()
    ordered = band.sort_values(
        ["abs_max_drawdown", "annual_turnover", "ma_days", "momentum_sort", "quantile_distance", "calmar"],
        ascending=[True, True, False, False, True, False], kind="mergesort",
    )
    return ordered.iloc[0], evaluated


def fold_table(folds: list[WalkForwardFold]) -> pd.DataFrame:
    return pd.DataFrame([{
        "train_start": str(fold.train_start.date()), "train_end": str(fold.train_end.date()),
        "test_start": str(fold.test_start.date()), "test_end": str(fold.test_end.date()),
        "test_year": fold.test_year,
    } for fold in folds])
