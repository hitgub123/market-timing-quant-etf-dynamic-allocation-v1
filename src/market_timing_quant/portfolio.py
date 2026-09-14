from __future__ import annotations

import numpy as np
import pandas as pd

from .execution import transaction_cost
from .tax import SimplifiedJapanTax


def validate_weights(weights: pd.DataFrame, tolerance: float = 1e-12) -> None:
    values = weights.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("weights must be finite and nonnegative")
    if (values.sum(axis=1) > 1.0 + tolerance).any():
        raise ValueError("total portfolio weight exceeds 100%")


def enforce_asset_availability(weights: pd.DataFrame, first_available: dict[str, str | pd.Timestamp]) -> pd.DataFrame:
    result = weights.copy()
    for asset, first_date in first_available.items():
        if asset in result:
            result.loc[result.index < pd.Timestamp(first_date), asset] = 0.0
    validate_weights(result)
    return result


def buy_and_hold(
    prices: pd.DataFrame,
    *,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if prices.empty or not prices.index.is_monotonic_increasing or prices.index.has_duplicates:
        raise ValueError("prices must have unique increasing dates")
    if (prices[["open", "adjusted_close"]] <= 0).any().any():
        raise ValueError("prices must be positive")
    rate = (commission_bps + slippage_bps) / 10_000.0
    notional = initial_capital / (1.0 + rate)
    cost = transaction_cost(notional, commission_bps, slippage_bps)
    shares = notional / float(prices["open"].iloc[0])
    cash = max(0.0, initial_capital - notional - cost)
    equity = shares * prices["adjusted_close"] + cash
    ledger = pd.DataFrame({"equity": equity, "cash": cash, "shares": shares}, index=prices.index)
    ledger["daily_return"] = ledger["equity"].pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger["equity"].iloc[0] / initial_capital - 1.0
    positions = pd.DataFrame({"date": prices.index, "shares": shares, "weight": shares * prices["adjusted_close"] / equity})
    trades = pd.DataFrame([{
        "date": prices.index[0], "side": "BUY", "shares": shares,
        "price": float(prices["open"].iloc[0]), "notional": notional, "transaction_cost": cost,
    }])
    return ledger, positions, trades


def cash_hold(index: pd.DatetimeIndex, initial_capital: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ledger = pd.DataFrame({"equity": initial_capital, "cash": initial_capital, "shares": 0.0, "daily_return": 0.0}, index=index)
    positions = pd.DataFrame({"date": index, "shares": 0.0, "weight": 0.0})
    trades = pd.DataFrame(columns=["date", "side", "shares", "price", "notional", "transaction_cost"])
    return ledger, positions, trades


def rebalance_schedule(index: pd.DatetimeIndex, frequency: str) -> pd.Series:
    if frequency not in {"monthly", "quarterly"}:
        raise ValueError("Phase 1 frequency must be monthly or quarterly")
    periods = pd.Series(index.to_period("M" if frequency == "monthly" else "Q"), index=index)
    schedule = periods.ne(periods.shift(1))
    schedule.iloc[0] = True
    return schedule


def static_allocation_backtest(
    prices: dict[str, pd.DataFrame],
    weights: dict[str, float],
    *,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    frequency: str,
    tax_rate: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Long-only static allocation with average-cost realized-gain accounting."""
    assets = list(weights)
    if not assets or "CASH" in assets:
        raise ValueError("CASH is represented by weights summing below one, not as a price series")
    weight_frame = pd.DataFrame([weights])
    validate_weights(weight_frame)
    target = np.asarray([weights[a] for a in assets], dtype=float)
    indexes = [prices[a].index for a in assets]
    index = indexes[0]
    for other in indexes[1:]:
        index = index.intersection(other)
    if index.empty:
        raise ValueError("assets have no common sessions")
    opens = np.column_stack([prices[a].loc[index, "open"].to_numpy(dtype=float) for a in assets])
    closes = np.column_stack([prices[a].loc[index, "adjusted_close"].to_numpy(dtype=float) for a in assets])
    if not np.isfinite(opens).all() or not np.isfinite(closes).all() or (opens <= 0).any() or (closes <= 0).any():
        raise ValueError("prices must be positive and finite")
    schedule = rebalance_schedule(index, frequency).to_numpy(dtype=bool)
    rate = (commission_bps + slippage_bps) / 10_000.0
    shares = np.zeros(len(assets), dtype=float)
    average_basis = np.zeros(len(assets), dtype=float)
    cash = float(initial_capital)
    tax = SimplifiedJapanTax(rate=tax_rate) if tax_rate is not None else None
    records, position_rows, trade_rows, tax_rows = [], [], [], []
    for i, date in enumerate(index):
        op = opens[i]
        before_values = shares * op
        before_equity = float(cash + before_values.sum())
        signed = np.zeros(len(assets), dtype=float)
        costs = np.zeros(len(assets), dtype=float)
        realized_by_asset = np.zeros(len(assets), dtype=float)
        tax_paid = 0.0
        if schedule[i]:
            def proposal(after_equity: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
                desired = target * after_equity
                proposed = desired - before_values
                proposed_costs = np.abs(proposed) * rate
                realized = np.zeros(len(assets), dtype=float)
                sells = proposed < 0
                realized[sells] = (-proposed[sells] / op[sells]) * (op[sells] - average_basis[sells]) - proposed_costs[sells]
                preview_tax = tax.preview(float(realized.sum())) if tax is not None else 0.0
                return proposed, proposed_costs, realized, preview_tax

            lo, hi = 0.0, before_equity
            for _ in range(64):
                mid = (lo + hi) / 2.0
                proposed, proposed_costs, realized, preview_tax = proposal(mid)
                residual = mid + float(proposed_costs.sum()) + preview_tax - before_equity
                if residual > 0:
                    hi = mid
                else:
                    lo = mid
            after = (lo + hi) / 2.0
            signed, costs, realized_by_asset, _ = proposal(after)
            signed[np.abs(signed) < before_equity * 1e-12] = 0.0
            costs[np.abs(signed) == 0] = 0.0
            realized_by_asset[np.abs(signed) == 0] = 0.0
            for j, asset in enumerate(assets):
                amount = float(signed[j])
                if amount > 0:
                    bought_shares = amount / op[j]
                    total_basis = shares[j] * average_basis[j] + amount + costs[j]
                    shares[j] += bought_shares
                    average_basis[j] = total_basis / shares[j]
                elif amount < 0:
                    shares[j] -= (-amount) / op[j]
                    if shares[j] < 1e-10:
                        shares[j] = 0.0
                        average_basis[j] = 0.0
                if amount != 0:
                    trade_rows.append({
                        "date": date, "asset": asset, "side": "BUY" if amount > 0 else "SELL",
                        "shares": abs(amount) / op[j], "price": op[j], "notional": abs(amount),
                        "transaction_cost": costs[j], "realized_gain": realized_by_asset[j],
                    })
            cash -= float(signed.sum() + costs.sum())
            net_realized = float(realized_by_asset.sum())
            if tax is not None and net_realized != 0:
                tax_paid = tax.realize(net_realized)
                cash -= tax_paid
                tax_rows.append({
                    "date": date, "realized_gain": net_realized, "loss_pool": tax.loss_pool,
                    "tax_paid": tax_paid, "cumulative_tax_paid": tax.tax_paid,
                })
        if cash < -1e-6 or (shares < -1e-10).any():
            raise AssertionError("static ledger produced negative cash or shares")
        cash = max(cash, 0.0)
        values = shares * closes[i]
        equity = float(cash + values.sum())
        row = {"date": date, "equity": equity, "pretrade_equity": before_equity,
               "cash": cash, "shares": float(shares.sum()),
               "trade_notional": float(np.abs(signed).sum()), "transaction_cost": float(costs.sum()),
               "tax_paid": tax_paid}
        for j, asset in enumerate(assets):
            row[f"{asset}_value"] = values[j]
            row[f"{asset}_weight"] = values[j] / equity
            if schedule[i]:
                position_rows.append({"date": date, "asset": asset, "shares": shares[j], "weight": values[j] / equity})
        row["cash_weight"] = cash / equity
        records.append(row)
    ledger = pd.DataFrame(records).set_index("date")
    ledger["daily_return"] = ledger["equity"].pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger["equity"].iloc[0] / initial_capital - 1.0
    trades = pd.DataFrame(trade_rows, columns=("date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain"))
    positions = pd.DataFrame(position_rows, columns=("date", "asset", "shares", "weight"))
    taxes = pd.DataFrame(tax_rows, columns=("date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid"))
    return ledger, positions, trades, taxes


def single_asset_timed_backtest(
    prices: pd.DataFrame,
    targets_at_open: pd.Series,
    *,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    tax_rate: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute binary 0/100% targets at the open with average-cost tax accounting."""
    targets = pd.Series(targets_at_open, dtype=float).reindex(prices.index)
    if targets.isna().any() or not targets.isin((0.0, 1.0)).all():
        raise ValueError("Phase 2 targets must be complete and binary")
    if (prices[["open", "adjusted_close"]] <= 0).any().any():
        raise ValueError("prices must be positive")
    rate = (commission_bps + slippage_bps) / 10_000.0
    tax = SimplifiedJapanTax(rate=tax_rate) if tax_rate is not None else None
    shares = 0.0
    average_basis = 0.0
    cash = float(initial_capital)
    records, positions, trades, taxes = [], [], [], []
    for date, row in prices.iterrows():
        price = float(row.open)
        target = float(targets.loc[date])
        trade_notional = cost = tax_paid = realized_gain = 0.0
        if target == 1.0 and shares == 0.0:
            trade_notional = cash / (1.0 + rate)
            cost = trade_notional * rate
            shares = trade_notional / price
            average_basis = (trade_notional + cost) / shares
            cash = max(0.0, cash - trade_notional - cost)
            trades.append({"date": date, "asset": "RISK", "side": "BUY", "shares": shares,
                           "price": price, "notional": trade_notional, "transaction_cost": cost,
                           "realized_gain": 0.0})
        elif target == 0.0 and shares > 0.0:
            sold_shares = shares
            trade_notional = sold_shares * price
            cost = trade_notional * rate
            realized_gain = trade_notional - cost - sold_shares * average_basis
            if tax is not None:
                tax_paid = tax.realize(realized_gain)
                taxes.append({"date": date, "realized_gain": realized_gain, "loss_pool": tax.loss_pool,
                              "tax_paid": tax_paid, "cumulative_tax_paid": tax.tax_paid})
            cash += trade_notional - cost - tax_paid
            shares = 0.0
            average_basis = 0.0
            trades.append({"date": date, "asset": "RISK", "side": "SELL", "shares": sold_shares,
                           "price": price, "notional": trade_notional, "transaction_cost": cost,
                           "realized_gain": realized_gain})
        equity = cash + shares * float(row.adjusted_close)
        records.append({"date": date, "equity": equity, "cash": cash, "shares": shares,
                        "target_weight": target, "risk_weight": shares * float(row.adjusted_close) / equity,
                        "trade_notional": trade_notional, "transaction_cost": cost, "tax_paid": tax_paid})
        positions.append({"date": date, "shares": shares, "target_weight": target,
                          "actual_weight": shares * float(row.adjusted_close) / equity})
    ledger = pd.DataFrame(records).set_index("date")
    ledger["daily_return"] = ledger.equity.pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger.equity.iloc[0] / initial_capital - 1.0
    return (
        ledger,
        pd.DataFrame(positions),
        pd.DataFrame(trades, columns=("date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain")),
        pd.DataFrame(taxes, columns=("date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid")),
    )


def rotation_backtest(
    prices: dict[str, pd.DataFrame],
    targets_at_open: pd.DataFrame,
    *,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    tax_rate: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute one-hot relative-momentum rotations, including the all-cash state."""
    assets = list(targets_at_open.columns)
    if not assets or set(assets) != set(prices):
        raise ValueError("price assets must exactly match target columns")
    index = targets_at_open.index
    if any(not prices[a].index.equals(index) for a in assets):
        raise ValueError("all rotation prices and targets must share sessions")
    targets = targets_at_open.astype(float)
    if targets.isna().any().any() or not targets.isin((0.0, 1.0)).all().all() or (targets.sum(axis=1) > 1.0).any():
        raise ValueError("rotation targets must be complete one-hot or all cash")
    rate = (commission_bps + slippage_bps) / 10_000.0
    tax = SimplifiedJapanTax(rate=tax_rate) if tax_rate is not None else None
    shares = {asset: 0.0 for asset in assets}
    basis = {asset: 0.0 for asset in assets}
    cash = float(initial_capital)
    records, positions, trades, taxes = [], [], [], []
    for date in index:
        target_asset = next((asset for asset in assets if targets.loc[date, asset] == 1.0), None)
        current_asset = next((asset for asset in assets if shares[asset] > 0.0), None)
        day_cost = day_tax = day_notional = 0.0
        if current_asset != target_asset:
            if current_asset is not None:
                price = float(prices[current_asset].loc[date, "open"])
                sold_shares = shares[current_asset]
                notional = sold_shares * price
                cost = notional * rate
                gain = notional - cost - sold_shares * basis[current_asset]
                paid = tax.realize(gain) if tax is not None else 0.0
                cash += notional - cost - paid
                shares[current_asset] = 0.0; basis[current_asset] = 0.0
                day_cost += cost; day_tax += paid; day_notional += notional
                trades.append({"date": date, "asset": current_asset, "side": "SELL", "shares": sold_shares,
                               "price": price, "notional": notional, "transaction_cost": cost, "realized_gain": gain})
                if tax is not None:
                    taxes.append({"date": date, "asset": current_asset, "realized_gain": gain,
                                  "loss_pool": tax.loss_pool, "tax_paid": paid, "cumulative_tax_paid": tax.tax_paid})
            if target_asset is not None:
                price = float(prices[target_asset].loc[date, "open"])
                notional = cash / (1.0 + rate)
                cost = notional * rate
                bought = notional / price
                shares[target_asset] = bought
                basis[target_asset] = (notional + cost) / bought
                cash = max(0.0, cash - notional - cost)
                day_cost += cost; day_notional += notional
                trades.append({"date": date, "asset": target_asset, "side": "BUY", "shares": bought,
                               "price": price, "notional": notional, "transaction_cost": cost, "realized_gain": 0.0})
        close_values = {asset: shares[asset] * float(prices[asset].loc[date, "adjusted_close"]) for asset in assets}
        equity = cash + sum(close_values.values())
        record = {"date": date, "equity": equity, "cash": cash, "shares": sum(shares.values()),
                  "trade_notional": day_notional, "transaction_cost": day_cost, "tax_paid": day_tax,
                  "cash_weight": cash / equity}
        for asset in assets:
            record[f"{asset}_shares"] = shares[asset]
            record[f"{asset}_weight"] = close_values[asset] / equity
            positions.append({"date": date, "asset": asset, "shares": shares[asset],
                              "target_weight": float(targets.loc[date, asset]), "actual_weight": close_values[asset] / equity})
        records.append(record)
    ledger = pd.DataFrame(records).set_index("date")
    ledger["daily_return"] = ledger.equity.pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger.equity.iloc[0] / initial_capital - 1.0
    return (
        ledger, pd.DataFrame(positions),
        pd.DataFrame(trades, columns=("date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain")),
        pd.DataFrame(taxes, columns=("date", "asset", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid")),
    )


def continuous_weight_backtest(
    prices: pd.DataFrame,
    targets_at_open: pd.Series,
    rebalance: pd.Series,
    *,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    tax_rate: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Single-asset fractional-weight ledger for volatility targeting."""
    targets = pd.Series(targets_at_open, dtype=float).reindex(prices.index)
    if targets.isna().any() or (targets < 0).any() or (targets > 1).any():
        raise ValueError("targets must be complete and between zero and one")
    schedule = pd.Series(rebalance, dtype=bool).reindex(prices.index)
    if schedule.isna().any():
        raise ValueError("rebalance schedule must be complete")
    values = prices[["open", "adjusted_close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("prices must be positive and finite")
    rate = (commission_bps + slippage_bps) / 10_000.0
    tax = SimplifiedJapanTax(rate=tax_rate) if tax_rate is not None else None
    shares = average_basis = 0.0
    cash = float(initial_capital)
    records, positions, trades, taxes = [], [], [], []
    for date, target, scheduled, (open_price, close_price) in zip(prices.index, targets.to_numpy(), schedule.to_numpy(), values, strict=True):
        current = shares * open_price
        before_equity = cash + current

        def proposal(after_equity: float) -> tuple[float, float, float, float]:
            signed = target * after_equity - current
            cost = abs(signed) * rate
            realized = (-signed / open_price) * (open_price - average_basis) - cost if signed < 0 else 0.0
            preview_tax = tax.preview(realized) if tax is not None else 0.0
            return signed, cost, realized, preview_tax

        signed = cost = realized = 0.0
        if scheduled:
            lo, hi = 0.0, before_equity
            for _ in range(64):
                mid = (lo + hi) / 2.0
                signed, cost, realized, preview_tax = proposal(mid)
                if mid + cost + preview_tax > before_equity:
                    hi = mid
                else:
                    lo = mid
            signed, cost, realized, _ = proposal((lo + hi) / 2.0)
            if abs(signed) < before_equity * 1e-12:
                signed = cost = realized = 0.0
        tax_paid = 0.0
        if signed > 0:
            bought = signed / open_price
            total_basis = shares * average_basis + signed + cost
            shares += bought
            average_basis = total_basis / shares
        elif signed < 0:
            sold = -signed / open_price
            shares -= sold
            if tax is not None:
                tax_paid = tax.realize(realized)
                taxes.append({"date": date, "realized_gain": realized, "loss_pool": tax.loss_pool,
                              "tax_paid": tax_paid, "cumulative_tax_paid": tax.tax_paid})
            if shares < 1e-10:
                shares = average_basis = 0.0
        cash -= signed + cost + tax_paid
        if cash < -1e-6 or shares < -1e-10:
            raise AssertionError("continuous ledger produced negative cash or shares")
        cash = max(cash, 0.0)
        equity = cash + shares * close_price
        records.append({"date": date, "equity": equity, "cash": cash, "shares": shares,
                        "target_weight": target, "risk_weight": shares * close_price / equity,
                        "scheduled_rebalance": bool(scheduled), "trade_notional": abs(signed),
                        "transaction_cost": cost, "tax_paid": tax_paid})
        positions.append({"date": date, "shares": shares, "target_weight": target,
                          "actual_weight": shares * close_price / equity})
        if signed != 0:
            trades.append({"date": date, "asset": "RISK", "side": "BUY" if signed > 0 else "SELL",
                           "shares": abs(signed) / open_price, "price": open_price, "notional": abs(signed),
                           "transaction_cost": cost, "realized_gain": realized})
    ledger = pd.DataFrame(records).set_index("date")
    ledger["daily_return"] = ledger.equity.pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger.equity.iloc[0] / initial_capital - 1.0
    return (
        ledger, pd.DataFrame(positions),
        pd.DataFrame(trades, columns=("date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain")),
        pd.DataFrame(taxes, columns=("date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid")),
    )


def dynamic_allocation_backtest(
    prices: dict[str, pd.DataFrame],
    targets_at_open: pd.DataFrame,
    rebalance: pd.Series,
    *,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    tax_rate: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Multi-asset fractional ledger supporting pre-listing unavailable assets."""
    assets = list(targets_at_open.columns)
    index = targets_at_open.index
    if set(assets) != set(prices):
        raise ValueError("price assets must exactly match target columns")
    targets = targets_at_open.astype(float)
    if targets.isna().any().any() or (targets < 0).any().any() or (targets.sum(axis=1) > 1 + 1e-12).any():
        raise ValueError("invalid dynamic target weights")
    schedule = pd.Series(rebalance, dtype=bool).reindex(index)
    if schedule.isna().any() or any(not prices[a].index.equals(index) for a in assets):
        raise ValueError("prices, targets, and schedule must share complete sessions")
    rate = (commission_bps + slippage_bps) / 10_000.0
    tax = SimplifiedJapanTax(rate=tax_rate) if tax_rate is not None else None
    shares = np.zeros(len(assets)); basis = np.zeros(len(assets)); cash = float(initial_capital)
    records, positions, trades, taxes = [], [], [], []
    for date in index:
        op = np.array([prices[a].loc[date, "open"] for a in assets], dtype=float)
        cp = np.array([prices[a].loc[date, "adjusted_close"] for a in assets], dtype=float)
        requested = targets.loc[date].to_numpy(dtype=float)
        needed = (shares > 0) | (requested > 0)
        if (not np.isfinite(op[needed]).all()) or (op[needed] <= 0).any() or (not np.isfinite(cp[shares > 0]).all()) or (cp[shares > 0] <= 0).any():
            raise ValueError("target or held asset unavailable at execution/valuation")
        current = np.where(shares > 0, shares * op, 0.0)
        before_equity = cash + float(current.sum())
        signed = costs = realized = np.zeros(len(assets), dtype=float)
        tax_paid = 0.0
        if bool(schedule.loc[date]):
            def proposal(after_equity: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
                signed_trade = requested * after_equity - current
                trade_cost = np.abs(signed_trade) * rate
                gain = np.zeros(len(assets))
                sells = signed_trade < 0
                gain[sells] = (-signed_trade[sells] / op[sells]) * (op[sells] - basis[sells]) - trade_cost[sells]
                preview_tax = tax.preview(float(gain.sum())) if tax is not None else 0.0
                return signed_trade, trade_cost, gain, preview_tax
            lo, hi = 0.0, before_equity
            for _ in range(64):
                mid = (lo + hi) / 2
                proposed, proposed_costs, gains, preview = proposal(mid)
                if mid + float(proposed_costs.sum()) + preview > before_equity: hi = mid
                else: lo = mid
            signed, costs, realized, _ = proposal((lo + hi) / 2)
            signed[np.abs(signed) < before_equity * 1e-12] = 0.0
            costs[signed == 0] = 0.0; realized[signed == 0] = 0.0
            for j, asset in enumerate(assets):
                if signed[j] > 0:
                    bought = signed[j] / op[j]
                    total_basis = shares[j] * basis[j] + signed[j] + costs[j]
                    shares[j] += bought; basis[j] = total_basis / shares[j]
                elif signed[j] < 0:
                    shares[j] -= -signed[j] / op[j]
                    if shares[j] < 1e-10: shares[j] = 0.0; basis[j] = 0.0
                if signed[j] != 0:
                    trades.append({"date": date, "asset": asset, "side": "BUY" if signed[j] > 0 else "SELL",
                                   "shares": abs(signed[j]) / op[j], "price": op[j], "notional": abs(signed[j]),
                                   "transaction_cost": costs[j], "realized_gain": realized[j]})
            net_gain = float(realized.sum())
            if tax is not None and net_gain != 0:
                tax_paid = tax.realize(net_gain)
                taxes.append({"date": date, "realized_gain": net_gain, "loss_pool": tax.loss_pool,
                              "tax_paid": tax_paid, "cumulative_tax_paid": tax.tax_paid})
            cash -= float(signed.sum() + costs.sum()) + tax_paid
        if cash < -1e-6 or (shares < -1e-10).any():
            raise AssertionError("dynamic ledger produced negative cash or shares")
        cash = max(cash, 0.0)
        close_values = np.where(shares > 0, shares * cp, 0.0)
        equity = cash + float(close_values.sum())
        row = {"date": date, "equity": equity, "pretrade_equity": before_equity,
               "cash": cash, "shares": float(shares.sum()), "cash_weight": cash / equity,
               "trade_notional": float(np.abs(signed).sum()),
               "transaction_cost": float(costs.sum()), "tax_paid": tax_paid,
               "scheduled_rebalance": bool(schedule.loc[date])}
        for j, asset in enumerate(assets):
            row[f"{asset}_shares"] = shares[j]; row[f"{asset}_weight"] = close_values[j] / equity
            positions.append({"date": date, "asset": asset, "shares": shares[j],
                              "target_weight": requested[j], "actual_weight": close_values[j] / equity})
        records.append(row)
    ledger = pd.DataFrame(records).set_index("date")
    ledger["daily_return"] = ledger.equity.pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger.equity.iloc[0] / initial_capital - 1.0
    return ledger, pd.DataFrame(positions), pd.DataFrame(trades), pd.DataFrame(taxes)
