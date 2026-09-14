from __future__ import annotations

import numpy as np
import pandas as pd

from .execution import shift_decisions_to_next_open


def rebalance_mask(index: pd.DatetimeIndex, frequency: str) -> pd.Series:
    if frequency == "weekly":
        periods = pd.Series(index.to_period("W-SUN"), index=index)
        return periods.ne(periods.shift(1))
    if frequency == "monthly":
        periods = pd.Series(index.to_period("M"), index=index)
        return periods.ne(periods.shift(1))
    if frequency == "bimonthly":
        periods = pd.Series(index.to_period("M"), index=index)
        first_of_month = periods.ne(periods.shift(1))
        return first_of_month & index.month.isin((1, 3, 5, 7, 9, 11))
    if frequency == "quarterly":
        periods = pd.Series(index.to_period("Q"), index=index)
        return periods.ne(periods.shift(1))
    raise ValueError("frequency must be weekly, monthly, bimonthly, or quarterly")


def ma_trend_decision(adjusted_close: pd.Series, lookback: int = 200) -> pd.Series:
    if lookback < 1:
        raise ValueError("lookback must be positive")
    price = pd.to_numeric(adjusted_close, errors="coerce")
    if price.isna().any() or (price <= 0).any():
        raise ValueError("adjusted close must be positive and complete")
    moving_average = price.rolling(lookback, min_periods=lookback).mean()
    return price.gt(moving_average).fillna(False).astype(float)


def scheduled_target_next_open(decisions_at_close: pd.Series, frequency: str) -> pd.Series:
    """Apply a completed close decision on the next eligible scheduled open."""
    decisions = pd.to_numeric(decisions_at_close, errors="coerce")
    if decisions.isna().any() or not decisions.isin((0.0, 1.0)).all():
        raise ValueError("decisions must be complete and binary")
    available_at_open = shift_decisions_to_next_open(decisions)
    index = decisions.index
    scheduled = rebalance_mask(index, frequency)
    targets = pd.Series(float("nan"), index=index)
    targets.loc[scheduled] = available_at_open.loc[scheduled]
    return targets.ffill().fillna(0.0)


def trend_target_next_open(adjusted_close: pd.Series, frequency: str, lookback: int = 200) -> pd.Series:
    """Return the MA position target applied at each open, using only prior closes."""
    return scheduled_target_next_open(ma_trend_decision(adjusted_close, lookback), frequency)


def absolute_momentum_decision(adjusted_close: pd.Series, lookback: int) -> pd.Series:
    if lookback not in {126, 189, 252}:
        raise ValueError("absolute momentum lookback must be 126, 189, or 252")
    price = pd.to_numeric(adjusted_close, errors="coerce")
    if price.isna().any() or (price <= 0).any():
        raise ValueError("adjusted close must be positive and complete")
    momentum = price / price.shift(lookback) - 1.0
    return momentum.gt(0.0).fillna(False).astype(float)


def absolute_momentum_target_next_open(adjusted_close: pd.Series, frequency: str, lookback: int) -> pd.Series:
    return scheduled_target_next_open(absolute_momentum_decision(adjusted_close, lookback), frequency)


def relative_momentum_decision(spy_adjusted_close: pd.Series, qqq_adjusted_close: pd.Series, lookback: int) -> pd.DataFrame:
    if lookback not in {126, 189, 252}:
        raise ValueError("relative momentum lookback must be 126, 189, or 252")
    if not spy_adjusted_close.index.equals(qqq_adjusted_close.index):
        raise ValueError("SPY and QQQ signal series must have identical sessions")
    spy = pd.to_numeric(spy_adjusted_close, errors="coerce")
    qqq = pd.to_numeric(qqq_adjusted_close, errors="coerce")
    if spy.isna().any() or qqq.isna().any() or (spy <= 0).any() or (qqq <= 0).any():
        raise ValueError("signal prices must be positive and complete")
    spy_momentum = spy / spy.shift(lookback) - 1.0
    qqq_momentum = qqq / qqq.shift(lookback) - 1.0
    both_off = (spy_momentum <= 0.0) & (qqq_momentum <= 0.0)
    ready = spy_momentum.notna() & qqq_momentum.notna()
    # Deterministic tie rule: SPY wins an exact positive tie.
    choose_spy = ready & ~both_off & (spy_momentum >= qqq_momentum)
    choose_qqq = ready & ~both_off & ~choose_spy
    return pd.DataFrame({"SPY": choose_spy.astype(float), "QQQ": choose_qqq.astype(float)}, index=spy.index)


def scheduled_weights_next_open(decisions_at_close: pd.DataFrame, frequency: str) -> pd.DataFrame:
    values = decisions_at_close.astype(float)
    if values.isna().any().any() or (values < 0).any().any() or (values.sum(axis=1) > 1.0 + 1e-12).any():
        raise ValueError("decision weights must be finite, nonnegative, and sum to at most one")
    available = values.shift(1).fillna(0.0)
    scheduled = rebalance_mask(values.index, frequency)
    targets = pd.DataFrame(float("nan"), index=values.index, columns=values.columns)
    targets.loc[scheduled] = available.loc[scheduled]
    return targets.ffill().fillna(0.0)


def relative_momentum_target_next_open(
    spy_adjusted_close: pd.Series, qqq_adjusted_close: pd.Series, frequency: str, lookback: int
) -> pd.DataFrame:
    return scheduled_weights_next_open(relative_momentum_decision(spy_adjusted_close, qqq_adjusted_close, lookback), frequency)


def realized_volatility(adjusted_close: pd.Series, window: int) -> pd.Series:
    if window not in {20, 40, 60}:
        raise ValueError("realized-volatility window must be 20, 40, or 60")
    price = pd.to_numeric(adjusted_close, errors="coerce")
    if price.isna().any() or (price <= 0).any():
        raise ValueError("adjusted close must be positive and complete")
    daily_return = price / price.shift(1) - 1.0
    return daily_return.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(252.0)


def volatility_target_decision(adjusted_close: pd.Series, window: int, target_vol: float) -> pd.Series:
    if target_vol not in {0.10, 0.15, 0.20, 0.25, 0.30}:
        raise ValueError("target volatility must be 10%, 15%, 20%, 25%, or 30%")
    volatility = realized_volatility(adjusted_close, window)
    weight = (target_vol / volatility).clip(lower=0.0, upper=1.0)
    return weight.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def scheduled_continuous_target_next_open(decisions_at_close: pd.Series, frequency: str) -> pd.Series:
    decision = pd.to_numeric(decisions_at_close, errors="coerce")
    if decision.isna().any() or (decision < 0).any() or (decision > 1).any():
        raise ValueError("continuous decision weights must be complete and between zero and one")
    available = decision.shift(1).fillna(0.0)
    scheduled = rebalance_mask(decision.index, frequency)
    target = pd.Series(float("nan"), index=decision.index)
    target.loc[scheduled] = available.loc[scheduled]
    return target.ffill().fillna(0.0)


def volatility_target_next_open(adjusted_close: pd.Series, frequency: str, window: int, target_vol: float) -> pd.Series:
    return scheduled_continuous_target_next_open(volatility_target_decision(adjusted_close, window, target_vol), frequency)


def phase7_state_decisions(
    qqq_adjusted_close: pd.Series,
    *,
    ma_days: int = 200,
    momentum_days: int = 252,
    low_vol_quantile: float = 0.33,
) -> pd.DataFrame:
    """Close-time state decisions; expanding quantile is strictly prior-only."""
    price = pd.to_numeric(qqq_adjusted_close, errors="coerce")
    if price.isna().any() or (price <= 0).any():
        raise ValueError("QQQ adjusted close must be positive and complete")
    ma = price.rolling(ma_days, min_periods=ma_days).mean()
    momentum = price / price.shift(momentum_days) - 1.0
    rv20 = (price / price.shift(1) - 1.0).rolling(20, min_periods=20).std(ddof=1) * np.sqrt(252.0)
    rv_quantile = rv20.expanding(min_periods=1).quantile(low_vol_quantile).shift(1)
    ready = ma.notna() & momentum.notna() & rv20.notna() & rv_quantile.notna()
    state = pd.Series("RISK_OFF", index=price.index, dtype=object)
    trend = price > ma
    state.loc[ready & trend & (momentum <= 0.0)] = "NORMAL"
    state.loc[ready & trend & (momentum > 0.0) & (rv20 > rv_quantile)] = "LEVERAGED"
    state.loc[ready & trend & (momentum > 0.0) & (rv20 <= rv_quantile)] = "AGGRESSIVE"
    weights = pd.DataFrame(0.0, index=price.index, columns=["QQQ", "QLD", "TQQQ", "CASH"])
    weights.loc[state == "RISK_OFF", "CASH"] = 1.0
    weights.loc[state == "NORMAL", "QQQ"] = 1.0
    weights.loc[state == "LEVERAGED", "QLD"] = 1.0
    weights.loc[state == "AGGRESSIVE", ["QLD", "TQQQ"]] = (0.80, 0.20)
    return pd.concat([
        pd.DataFrame({"adjusted_close": price, "ma": ma, "momentum": momentum,
                      "rv20": rv20, "rv_quantile": rv_quantile, "state": state}),
        weights.add_prefix("weight_"),
    ], axis=1)


def phase7_targets_next_open(
    decisions: pd.DataFrame,
    frequency: str,
    *,
    tqqq_first_session: str | pd.Timestamp,
) -> tuple[pd.DataFrame, pd.Series]:
    columns = ["weight_QQQ", "weight_QLD", "weight_TQQQ"]
    if set(columns + ["state"]) - set(decisions):
        raise ValueError("incomplete Phase 7 decision table")
    available = decisions[columns].shift(1).fillna(0.0)
    available.columns = ["QQQ", "QLD", "TQQQ"]
    available_state = decisions["state"].shift(1).fillna("RISK_OFF")
    schedule = rebalance_mask(decisions.index, frequency)
    targets = pd.DataFrame(float("nan"), index=decisions.index, columns=available.columns)
    states = pd.Series(pd.NA, index=decisions.index, dtype=object)
    targets.loc[schedule] = available.loc[schedule]
    states.loc[schedule] = available_state.loc[schedule]
    targets = targets.ffill().fillna(0.0)
    states = states.ffill().fillna("RISK_OFF")
    unavailable = targets.index < pd.Timestamp(tqqq_first_session)
    targets.loc[unavailable, "QLD"] += targets.loc[unavailable, "TQQQ"]
    targets.loc[unavailable, "TQQQ"] = 0.0
    if (targets.sum(axis=1) > 1.0 + 1e-12).any():
        raise AssertionError("Phase 7 weights exceed 100%")
    return targets, states
