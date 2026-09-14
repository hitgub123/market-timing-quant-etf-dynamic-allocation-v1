from __future__ import annotations

import numpy as np
import pandas as pd

from .tax import SimplifiedJapanTax


def drawdown_series(equity: pd.Series, initial_capital: float) -> pd.Series:
    augmented = _equity_with_initial_capital(equity, initial_capital)
    return (augmented / augmented.cummax() - 1.0).iloc[1:]


def _equity_with_initial_capital(equity: pd.Series, initial_capital: float) -> pd.Series:
    """Prepend the capital available immediately before the first ledger session."""
    initial_date = equity.index[0] - pd.Timedelta(days=1)
    return pd.concat([pd.Series([initial_capital], index=[initial_date], dtype=float), equity.astype(float)])


def _drawdown_episode(
    equity: pd.Series, initial_capital: float,
) -> tuple[pd.Series, pd.Timestamp | None, pd.Timestamp | None, pd.Timestamp | None, int | None]:
    """Derive peak, trough and recovery from the same augmented running-peak path."""
    augmented = _equity_with_initial_capital(equity, initial_capital)
    running_peak = augmented.cummax()
    augmented_drawdown = augmented / running_peak - 1.0
    drawdown = augmented_drawdown.iloc[1:]
    trough = drawdown.idxmin()
    if float(drawdown.loc[trough]) >= 0:
        return drawdown, None, None, None, None
    peak_value = float(running_peak.loc[trough])
    peak_candidates = augmented.loc[:trough]
    peak = peak_candidates.index[peak_candidates.eq(peak_value)][0]
    recovery_candidates = augmented.loc[trough:][augmented.loc[trough:] >= peak_value]
    recovery = recovery_candidates.index[0] if len(recovery_candidates) else None
    recovery_trading_days = int(len(equity.loc[trough:recovery]) - 1) if recovery is not None else None
    return drawdown, peak, trough, recovery, recovery_trading_days


def _period_returns(equity: pd.Series, frequency: str, initial_capital: float) -> pd.Series:
    values = equity.resample(frequency).last()
    result = values.pct_change()
    if len(result):
        result.iloc[0] = values.iloc[0] / initial_capital - 1.0
    return result


def period_returns(ledger: pd.DataFrame, initial_capital: float) -> tuple[pd.Series, pd.Series]:
    return (
        _period_returns(ledger["equity"].astype(float), "YE", initial_capital),
        _period_returns(ledger["equity"].astype(float), "ME", initial_capital),
    )


def completed_holding_periods(ledger: pd.DataFrame) -> pd.DataFrame:
    """Return only completed zero-to-positive-to-zero position episodes."""
    share_columns = [column for column in ledger if column.endswith("_shares")]
    if share_columns:
        holdings = ledger[share_columns].rename(columns=lambda value: value.removesuffix("_shares"))
    elif "shares" in ledger:
        holdings = ledger[["shares"]].rename(columns={"shares": "POSITION"})
    else:
        return pd.DataFrame(columns=["asset", "entry_date", "exit_date", "trading_days", "calendar_days"])
    episodes = []
    for asset in holdings:
        invested = holdings[asset].to_numpy(dtype=float) > 1e-10
        start = None
        for i, active in enumerate(invested):
            if active and start is None:
                start = i
            if not active and start is not None:
                entry, exit_date = ledger.index[start], ledger.index[i]
                episodes.append({"asset": asset, "entry_date": entry, "exit_date": exit_date,
                                 "trading_days": i - start, "calendar_days": (exit_date - entry).days})
                start = None
        # An open terminal holding is deliberately not a completed episode.
    return pd.DataFrame(episodes, columns=["asset", "entry_date", "exit_date", "trading_days", "calendar_days"])


def terminal_liquidation(
    ledger: pd.DataFrame,
    trades: pd.DataFrame,
    *,
    tax_rate: float,
    transaction_cost_rate: float,
) -> dict[str, float]:
    """Hypothetically sell terminal holdings without changing the actual ledger."""
    tax = SimplifiedJapanTax(rate=tax_rate)
    if len(trades) and "realized_gain" in trades:
        sales = trades.loc[trades["side"].eq("SELL")].copy()
        if len(sales):
            for _, group in sales.groupby(pd.to_datetime(sales["date"]), sort=True):
                tax.realize(float(group["realized_gain"].sum()))
    remaining_basis: dict[str, float] = {}
    remaining_shares: dict[str, float] = {}
    if len(trades):
        for row in trades.sort_values("date").itertuples(index=False):
            asset = str(row.asset) if hasattr(row, "asset") else "POSITION"
            shares = float(row.shares)
            remaining_basis.setdefault(asset, 0.0); remaining_shares.setdefault(asset, 0.0)
            if row.side == "BUY":
                remaining_shares[asset] += shares
                remaining_basis[asset] += float(row.notional) + float(row.transaction_cost)
            elif row.side == "SELL" and remaining_shares[asset] > 0:
                fraction = min(1.0, shares / remaining_shares[asset])
                remaining_basis[asset] *= 1.0 - fraction
                remaining_shares[asset] = max(0.0, remaining_shares[asset] - shares)
    terminal_equity = float(ledger["equity"].iloc[-1])
    terminal_cash = float(ledger["cash"].iloc[-1]) if "cash" in ledger else 0.0
    market_value = max(0.0, terminal_equity - terminal_cash)
    sale_cost = market_value * transaction_cost_rate
    liquidation_gain = market_value - sale_cost - sum(remaining_basis.values())
    liquidation_tax = tax.preview(liquidation_gain)
    return {
        "terminal_liquidation_wealth": terminal_equity - sale_cost - liquidation_tax,
        "terminal_liquidation_tax": liquidation_tax,
        "terminal_liquidation_cost": sale_cost,
        "terminal_unrealized_gain_after_cost": liquidation_gain,
        "terminal_loss_pool_before_liquidation": tax.loss_pool,
    }


def performance_metrics(
    ledger: pd.DataFrame,
    trades: pd.DataFrame,
    initial_capital: float,
    *,
    terminal_tax_rate: float | None = None,
    terminal_cost_rate: float = 0.0,
) -> dict[str, object]:
    equity = ledger["equity"].astype(float)
    daily = ledger["daily_return"].astype(float)
    calendar_days = (equity.index[-1] - equity.index[0]).days
    cagr = (equity.iloc[-1] / initial_capital) ** (365.25 / calendar_days) - 1 if calendar_days else None
    dd, peak, trough, recovery, recovery_trading_days = _drawdown_episode(equity, initial_capital)
    max_dd = float(dd.min())
    std = daily.std(ddof=1)
    downside = daily[daily < 0].std(ddof=1)
    sharpe = float(np.sqrt(252) * daily.mean() / std) if std > 0 else None
    sortino = float(np.sqrt(252) * daily.mean() / downside) if downside > 0 else None
    annual = _period_returns(equity, "YE", initial_capital)
    monthly = _period_returns(equity, "ME", initial_capital)
    weekly = _period_returns(equity, "W-FRI", initial_capital)
    years = max(calendar_days / 365.25, 1 / 365.25)
    total_cost = float(trades["transaction_cost"].sum()) if len(trades) else 0.0
    notional = float(trades["notional"].abs().sum()) if len(trades) else 0.0
    normalized_turnover = 0.0
    if len(trades):
        trade_dates = pd.to_datetime(trades["date"])
        denominator_series = ledger["pretrade_equity"] if "pretrade_equity" in ledger else equity
        denominators = denominator_series.reindex(trade_dates).to_numpy(dtype=float)
        initial_deployment_date = trade_dates.min()
        include = ~(trade_dates.eq(initial_deployment_date) & trades["side"].eq("BUY").to_numpy())
        normalized_turnover = float((trades.loc[include, "notional"].abs().to_numpy(dtype=float) / denominators[include]).sum())
    completed = trades.loc[trades.get("side", pd.Series(index=trades.index, dtype=object)).eq("SELL")] if len(trades) else trades
    win_rate = float((completed["realized_gain"] > 0).mean()) if len(completed) and "realized_gain" in completed else None
    episodes = completed_holding_periods(ledger)
    result = {
        "start": str(equity.index[0].date()), "end": str(equity.index[-1].date()),
        "ending_value": float(equity.iloc[-1]), "total_return": float(equity.iloc[-1] / initial_capital - 1),
        "cagr": cagr, "annualized_volatility": float(std * np.sqrt(252)), "max_drawdown": max_dd,
        "worst_day": float(daily.min()), "worst_week": float(weekly.min()), "worst_month": float(monthly.min()),
        "worst_calendar_year": float(annual.min()), "sharpe": sharpe, "sortino": sortino,
        "calmar": cagr / abs(max_dd) if cagr is not None and max_dd < 0 else None,
        "ulcer_index": float(np.sqrt(np.mean(np.square(dd)))),
        "max_drawdown_start": str(peak.date()) if peak is not None else None,
        "max_drawdown_trough": str(trough.date()) if max_dd < 0 else None,
        "recovery_date": str(recovery.date()) if recovery is not None else None,
        "recovery_trading_days": recovery_trading_days,
        "time_under_water_days": int((dd < 0).sum()), "number_of_trades": int(len(trades)),
        "annual_turnover": normalized_turnover / years,
        "gross_traded_notional": notional,
        # Primary holding-period fields use trading sessions everywhere.
        "average_holding_period_days": float(episodes.trading_days.mean()) if len(episodes) else None,
        "mean_holding_period_days": float(episodes.trading_days.mean()) if len(episodes) else None,
        "median_holding_period_days": float(episodes.trading_days.median()) if len(episodes) else None,
        "max_holding_period_days": int(episodes.trading_days.max()) if len(episodes) else None,
        "mean_holding_trading_days": float(episodes.trading_days.mean()) if len(episodes) else None,
        "median_holding_trading_days": float(episodes.trading_days.median()) if len(episodes) else None,
        "max_holding_trading_days": int(episodes.trading_days.max()) if len(episodes) else None,
        "mean_holding_calendar_days": float(episodes.calendar_days.mean()) if len(episodes) else None,
        "median_holding_calendar_days": float(episodes.calendar_days.median()) if len(episodes) else None,
        "max_holding_calendar_days": int(episodes.calendar_days.max()) if len(episodes) else None,
        "mean_holding_days": float(episodes.trading_days.mean()) if len(episodes) else None,
        "median_holding_days": float(episodes.trading_days.median()) if len(episodes) else None,
        "max_holding_days": int(episodes.trading_days.max()) if len(episodes) else None,
        "win_rate": win_rate, "tax_paid": float(ledger["tax_paid"].sum()) if "tax_paid" in ledger else 0.0,
        "transaction_costs": total_cost,
    }
    if terminal_tax_rate is not None:
        liquidation = terminal_liquidation(
            ledger, trades, tax_rate=terminal_tax_rate, transaction_cost_rate=terminal_cost_rate,
        )
        result.update(liquidation)
        result["terminal_liquidation_cagr"] = (
            (liquidation["terminal_liquidation_wealth"] / initial_capital) ** (365.25 / calendar_days) - 1
            if calendar_days else None
        )
        result["after_tax_wealth_tax_paid_to_date"] = float(equity.iloc[-1])
        # Deprecated compatibility alias used by existing Phase 7 report code.  Despite
        # its historical name, this is wealth after realized taxes paid to date, not tax paid.
        result["after_tax_tax_paid_to_date"] = result["after_tax_wealth_tax_paid_to_date"]
        result["after_tax_terminal_liquidation"] = liquidation["terminal_liquidation_wealth"]
        result["after_tax_cagr_tax_paid_to_date"] = float(cagr) if cagr is not None else None
        result["after_tax_cagr_terminal_liquidation"] = result["terminal_liquidation_cagr"]
    else:
        result.update({
            "terminal_liquidation_wealth": None, "terminal_liquidation_tax": None,
            "terminal_liquidation_cost": None, "terminal_unrealized_gain_after_cost": None,
            "terminal_loss_pool_before_liquidation": None, "terminal_liquidation_cagr": None,
            "after_tax_wealth_tax_paid_to_date": None, "after_tax_tax_paid_to_date": None,
            "after_tax_terminal_liquidation": None,
            "after_tax_cagr_tax_paid_to_date": None, "after_tax_cagr_terminal_liquidation": None,
        })
    return result


def add_rolling_metrics(ledger: pd.DataFrame) -> pd.DataFrame:
    output = ledger.copy()
    eq = output["equity"]
    for years, sessions in ((1, 252), (3, 756), (5, 1260), (10, 2520)):
        output[f"rolling_{years}y_return"] = eq.pct_change(sessions)
        if years > 1:
            output[f"rolling_{years}y_cagr"] = (eq / eq.shift(sessions)) ** (1 / years) - 1
    output["rolling_1y_maxdd"] = eq.rolling(252).apply(lambda x: np.min(x / np.maximum.accumulate(x) - 1), raw=True)
    return output
