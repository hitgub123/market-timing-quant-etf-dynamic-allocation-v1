from __future__ import annotations

import argparse
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.phase2_ma200 import (
    FREQUENCIES,
    _add_pretrade_equity as _phase2_add_pretrade_equity,
    _turnover_audit as _phase2_turnover_audit,
)
from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import drawdown_series, performance_metrics
from market_timing_quant.portfolio import (
    buy_and_hold,
    cash_hold,
    dynamic_allocation_backtest,
    single_asset_timed_backtest,
)
from market_timing_quant.signals import (
    phase7_state_decisions,
    phase7_targets_next_open,
    rebalance_mask,
    trend_target_next_open,
)
from market_timing_quant.walk_forward import (
    expanding_calendar_year_folds,
    fold_table,
    select_calmar_candidate,
)


MA_DAYS = (150, 175, 200, 225, 250)
MOMENTUM_DAYS = (126, 189, 252)
LOW_VOL_QUANTILES = (0.25, 0.33, 0.40)
MINIMUM_CAGR = 0.15
MAXIMUM_ABS_MAX_DRAWDOWN = 0.45
DEFAULT_SELECTION_COMPARISON_RUN = "20260913_phase7b_strict_gate_v1_final"


def _cost_rate(config: dict) -> float:
    return (float(config["execution"]["commission_bps"]) + float(config["execution"]["slippage_bps"])) / 10_000


def _add_pretrade_equity(
    ledger: pd.DataFrame,
    prices: pd.DataFrame | dict[str, pd.DataFrame],
    initial_capital: float,
) -> pd.DataFrame:
    """Attach the canonical contemporaneous open-before-trade equity.

    The Phase 7B execution functions intentionally return economic ledgers
    without a reporting denominator for single-asset paths.  Phase 2's
    audited reconstruction is reused for those paths.  Dynamic multi-asset
    ledgers already carry the same field; when given a price map we verify it
    rather than silently accepting a different denominator.
    """
    if isinstance(prices, pd.DataFrame):
        return _phase2_add_pretrade_equity(ledger, prices, initial_capital)
    if not prices:
        raise ValueError("prices must contain at least one asset")
    if not ledger.index.equals(next(iter(prices.values())).index):
        raise ValueError("ledger and prices must share the evaluation calendar")
    if "cash" not in ledger:
        raise ValueError("ledger must contain cash to reconstruct pretrade equity")
    reconstructed = ledger.cash.shift(1)
    share_columns = []
    for asset, frame in prices.items():
        if not frame.index.equals(ledger.index):
            raise ValueError("all prices must share the ledger evaluation calendar")
        column = f"{asset}_shares"
        if column in ledger:
            share_columns.append(column)
            prior_shares = ledger[column].shift(1).fillna(0.0).astype(float)
            opens = frame["open"].astype(float)
            if ((prior_shares > 0.0) & ~np.isfinite(opens)).any():
                raise ValueError(f"open price is missing while {asset} is held")
            # Assets unavailable before their listing contribute zero while
            # unheld; this mirrors the execution engine's availability rule.
            reconstructed = reconstructed + prior_shares * opens.fillna(0.0)
    if not share_columns:
        if "shares" not in ledger or len(prices) != 1:
            raise ValueError("ledger does not expose asset shares for pretrade reconstruction")
        frame = next(iter(prices.values()))
        prior_shares = ledger["shares"].shift(1).fillna(0.0).astype(float)
        opens = frame["open"].astype(float)
        if ((prior_shares > 0.0) & ~np.isfinite(opens)).any():
            raise ValueError("open price is missing while the asset is held")
        reconstructed = reconstructed + prior_shares * opens.fillna(0.0)
    reconstructed = reconstructed.fillna(float(initial_capital)).astype(float)
    result = ledger.copy()
    if "pretrade_equity" in result:
        existing = result["pretrade_equity"].astype(float)
        if not np.allclose(existing.to_numpy(), reconstructed.to_numpy(), rtol=0.0, atol=1e-9):
            raise AssertionError("ledger pretrade_equity is not the canonical open-before-trade value")
    result["pretrade_equity"] = reconstructed
    return result


def _turnover_audit(ledger: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    """Expose the exact audited Phase 2 turnover helper for Phase 7B tests."""
    if len(trades) and "pretrade_equity" not in ledger:
        raise ValueError("canonical turnover requires pretrade_equity on trade dates")
    return _phase2_turnover_audit(ledger, trades)


def _training_metric(ledger: pd.DataFrame, trades: pd.DataFrame, end: pd.Timestamp, capital: float) -> dict:
    prefix_ledger = ledger.loc[:end]
    prefix_trades = trades[pd.to_datetime(trades["date"]) <= end] if len(trades) else trades
    if len(prefix_trades) and "pretrade_equity" not in prefix_ledger:
        raise ValueError("training turnover requires canonical pretrade_equity")
    return performance_metrics(prefix_ledger, prefix_trades, capital)


def _select_training_folds(
    cache: dict[tuple, tuple[pd.DataFrame, pd.DataFrame]],
    parameter_rows: list[dict],
    folds: list,
    *,
    model: str,
    frequency: str,
    capital: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_rows, selection_rows = [], []
    for fold in folds:
        fold_candidates = []
        for parameters in parameter_rows:
            key = tuple(parameters[name] for name in parameters)
            ledger, trades = cache[key]
            metric = _training_metric(ledger, trades, fold.train_end, capital)
            row = {
                "model": model, "frequency": frequency, "test_year": fold.test_year,
                "train_start": str(fold.train_start.date()), "train_end": str(fold.train_end.date()),
                **parameters,
                "cagr": metric["cagr"], "max_drawdown": metric["max_drawdown"],
                "calmar": metric["calmar"], "sharpe": metric["sharpe"],
                "sortino": metric["sortino"], "annual_turnover": metric["annual_turnover"],
            }
            fold_candidates.append(row)
        evaluated = pd.DataFrame(fold_candidates)
        selected, evaluated = select_calmar_candidate(
            evaluated, minimum_cagr=MINIMUM_CAGR,
            maximum_abs_max_drawdown=MAXIMUM_ABS_MAX_DRAWDOWN,
        )
        candidate_rows.extend(evaluated.to_dict("records"))
        eligible_count = int(evaluated["eligible"].sum())
        if selected is None:
            selection_rows.append({
                "model": model, "frequency": frequency, "test_year": fold.test_year,
                "training_start": str(fold.train_start.date()), "training_end": str(fold.train_end.date()),
                "train_start": str(fold.train_start.date()), "train_end": str(fold.train_end.date()),
                "test_start": str(fold.test_start.date()), "test_end": str(fold.test_end.date()),
                "selection_status": "NO_ELIGIBLE_PARAMETER", "candidate_count": len(evaluated),
                "eligible_count": eligible_count, "selected_parameters": None,
                "selected_ma_days": None, "selected_momentum_days": None,
                "selected_low_vol_quantile": None, "selected_training_CAGR": None,
                "selected_training_MaxDD": None, "selected_training_Calmar": None,
                "test_allocation_mode": "CASH_FALLBACK",
            })
        else:
            selected_parameters = {
                name: (selected[name].item() if hasattr(selected[name], "item") else selected[name])
                for name in parameter_rows[0]
            }
            selection_rows.append({
                "model": model, "frequency": frequency, "test_year": fold.test_year,
                "training_start": str(fold.train_start.date()), "training_end": str(fold.train_end.date()),
                "train_start": str(fold.train_start.date()), "train_end": str(fold.train_end.date()),
                "test_start": str(fold.test_start.date()), "test_end": str(fold.test_end.date()),
                "selection_status": "SELECTED", "candidate_count": len(evaluated),
                "eligible_count": eligible_count,
                "selected_parameters": json.dumps(selected_parameters, sort_keys=True),
                "selected_ma_days": selected.get("ma_days"),
                "selected_momentum_days": selected.get("momentum_days"),
                "selected_low_vol_quantile": selected.get("low_vol_quantile"),
                "selected_training_CAGR": selected["cagr"],
                "selected_training_MaxDD": selected["max_drawdown"],
                "selected_training_Calmar": selected["calmar"],
                "test_allocation_mode": "SELECTED_STRATEGY",
                **selected_parameters,
                "training_cagr": selected["cagr"], "training_max_drawdown": selected["max_drawdown"],
                "training_calmar": selected["calmar"], "training_turnover": selected["annual_turnover"],
                "best_eligible_calmar": evaluated.loc[evaluated.eligible, "calmar"].max(),
                "selected_within_5pct_band": bool(selected["within_5pct_of_best_calmar"]),
            })
    return pd.DataFrame(candidate_rows), pd.DataFrame(selection_rows)


def _find_selection_comparison_source(output_root: Path, output: Path) -> Path | None:
    """Find the previously delivered Phase 7B selection table for the audit."""
    preferred = output_root / DEFAULT_SELECTION_COMPARISON_RUN / "selected_parameters_by_fold.csv"
    if preferred.exists() and preferred.parent.resolve() != output.resolve():
        return preferred
    candidates = sorted(
        (path for path in output_root.glob("*phase7b*/selected_parameters_by_fold.csv")
         if path.parent.resolve() != output.resolve()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _selection_old_vs_new(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Compare every frozen model/frequency/fold selection input and result."""
    key = ["model", "frequency", "test_year"]
    if old.duplicated(key).any() or new.duplicated(key).any():
        raise AssertionError("selection comparison requires one row per model/frequency/fold")
    fields = {
        "selection_status": "selection_status",
        "selected_ma_days": "selected_ma_days",
        "selected_momentum_days": "selected_momentum_days",
        "selected_low_vol_quantile": "selected_low_vol_quantile",
        "selected_training_CAGR": "selected_training_CAGR",
        "selected_training_MaxDD": "selected_training_MaxDD",
        "selected_training_Calmar": "selected_training_Calmar",
        "selected_training_turnover": "training_turnover",
    }
    old_part = old[key + list(fields)].rename(columns={value: f"old_{name}" for name, value in fields.items()})
    new_part = new[key + list(fields)].rename(columns={value: f"new_{name}" for name, value in fields.items()})
    merged = old_part.merge(new_part, on=key, how="outer", validate="one_to_one", sort=False)
    if len(merged) != len(new) or len(merged) != 112:
        raise AssertionError(f"expected 112 selection comparisons, got {len(merged)}")

    def same(left: object, right: object) -> bool:
        if pd.isna(left) and pd.isna(right):
            return True
        if isinstance(left, str) or isinstance(right, str):
            return left == right
        try:
            return bool(np.isclose(float(left), float(right), rtol=0.0, atol=1e-12, equal_nan=True))
        except (TypeError, ValueError):
            return left == right

    changed = []
    parameter_fields = [
        ("old_selection_status", "new_selection_status"),
        ("old_selected_ma_days", "new_selected_ma_days"),
        ("old_selected_momentum_days", "new_selected_momentum_days"),
        ("old_selected_low_vol_quantile", "new_selected_low_vol_quantile"),
    ]
    for _, row in merged.iterrows():
        changed.append(any(not same(row[left], row[right]) for left, right in parameter_fields))
    merged["selection_changed"] = changed
    # Keep lower-snake-case aliases for consumers that normalize metric names.
    for name in ("cagr", "max_drawdown", "calmar", "turnover"):
        source = {
            "cagr": "selected_training_CAGR",
            "max_drawdown": "selected_training_MaxDD",
            "calmar": "selected_training_Calmar",
            "turnover": "selected_training_turnover",
        }[name]
        merged[f"old_training_{name}"] = merged[f"old_{source}"]
        merged[f"new_training_{name}"] = merged[f"new_{source}"]
    return merged.sort_values(key).reset_index(drop=True)


def _stitch_series(
    selections: pd.DataFrame,
    folds: list,
    target_cache: dict[tuple, pd.Series],
    index: pd.DatetimeIndex,
    parameter_names: tuple[str, ...],
) -> tuple[pd.Series, pd.Series]:
    result = pd.Series(float("nan"), index=index)
    modes = pd.Series(pd.NA, index=index, dtype=object)
    selected = selections.set_index("test_year")
    for fold in folds:
        row = selected.loc[fold.test_year]
        year_index = index[(index >= fold.test_start) & (index <= fold.test_end)]
        if row.selection_status == "NO_ELIGIBLE_PARAMETER":
            result.loc[year_index] = 0.0
            modes.loc[year_index] = "CASH_FALLBACK"
        else:
            key = tuple(row[name] for name in parameter_names)
            result.loc[year_index] = target_cache[key].reindex(year_index)
            modes.loc[year_index] = "SELECTED_STRATEGY"
    if result.isna().any() or modes.isna().any():
        raise AssertionError("stitched Model A targets are incomplete")
    return result, modes


def _stitch_frame(
    selections: pd.DataFrame,
    folds: list,
    target_cache: dict[tuple, tuple[pd.DataFrame, pd.Series]],
    index: pd.DatetimeIndex,
    parameter_names: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    targets = pd.DataFrame(float("nan"), index=index, columns=["QQQ", "QLD", "TQQQ"])
    states = pd.Series(pd.NA, index=index, dtype=object)
    modes = pd.Series(pd.NA, index=index, dtype=object)
    selected = selections.set_index("test_year")
    for fold in folds:
        row = selected.loc[fold.test_year]
        year_index = index[(index >= fold.test_start) & (index <= fold.test_end)]
        if row.selection_status == "NO_ELIGIBLE_PARAMETER":
            targets.loc[year_index] = 0.0
            states.loc[year_index] = "CASH_FALLBACK"
            modes.loc[year_index] = "CASH_FALLBACK"
        else:
            key = tuple(row[name] for name in parameter_names)
            candidate_targets, candidate_states = target_cache[key]
            targets.loc[year_index] = candidate_targets.reindex(year_index)
            states.loc[year_index] = candidate_states.reindex(year_index)
            modes.loc[year_index] = "SELECTED_STRATEGY"
    if targets.isna().any().any() or states.isna().any() or modes.isna().any():
        raise AssertionError("stitched Model B targets or states are incomplete")
    return targets, states, modes


def _fold_test_audit(
    ledger: pd.DataFrame,
    trades: pd.DataFrame,
    taxes: pd.DataFrame,
    folds: list,
    *,
    initial_capital: float,
) -> pd.DataFrame:
    """Measure each test year from the continuous ledger without resetting it."""
    rows = []
    for fold in folds:
        year_index = ledger.index[(ledger.index >= fold.test_start) & (ledger.index <= fold.test_end)]
        if year_index.empty:
            raise AssertionError(f"missing test sessions for {fold.test_year}")
        prior = ledger.loc[ledger.index < year_index[0], "equity"]
        starting_equity = float(prior.iloc[-1]) if len(prior) else float(initial_capital)
        values = pd.concat([pd.Series([starting_equity], index=[year_index[0] - pd.Timedelta(days=1)]), ledger.loc[year_index, "equity"]])
        dd = values / values.cummax() - 1.0
        year_trades = trades.loc[(pd.to_datetime(trades["date"]) >= fold.test_start) & (pd.to_datetime(trades["date"]) <= fold.test_end)] if len(trades) else trades
        if len(year_trades):
            dates = pd.to_datetime(year_trades["date"])
            if "pretrade_equity" not in ledger:
                raise ValueError("fold turnover requires canonical pretrade_equity")
            denominator_series = ledger["pretrade_equity"]
            denominators = denominator_series.reindex(dates).to_numpy(dtype=float)
            include = np.ones(len(year_trades), dtype=bool)
            first_trade_date = pd.to_datetime(trades["date"]).min() if len(trades) else None
            include &= ~((dates == first_trade_date) & year_trades["side"].eq("BUY").to_numpy())
            turnover = float((year_trades.loc[include, "notional"].abs().to_numpy(dtype=float) / denominators[include]).sum())
        else:
            turnover = 0.0
        year_taxes = taxes.loc[(pd.to_datetime(taxes["date"]) >= fold.test_start) & (pd.to_datetime(taxes["date"]) <= fold.test_end)] if len(taxes) else taxes
        rows.append({
            "test_year": fold.test_year,
            "test_start": str(fold.test_start.date()), "test_end": str(fold.test_end.date()),
            "test_year_return": float(values.iloc[-1] / starting_equity - 1.0),
            "test_year_max_drawdown": float(dd.min()), "test_year_turnover": turnover,
            "test_year_tax_paid": float(year_taxes["tax_paid"].sum()) if len(year_taxes) else 0.0,
            "test_session_count": len(year_index),
        })
    return pd.DataFrame(rows)


def _attach_fold_audit(
    selections: pd.DataFrame,
    *,
    model: str,
    frequency: str,
    pre_ledger: pd.DataFrame,
    pre_trades: pd.DataFrame,
    after_taxes: pd.DataFrame,
    folds: list,
    modes: pd.Series,
    initial_capital: float,
) -> pd.DataFrame:
    audit = _fold_test_audit(pre_ledger, pre_trades, after_taxes, folds, initial_capital=initial_capital)
    audit["test_allocation_mode"] = [
        "CASH_FALLBACK" if selections.loc[selections.test_year.eq(year), "selection_status"].iloc[0] == "NO_ELIGIBLE_PARAMETER" else "SELECTED_STRATEGY"
        for year in audit.test_year
    ]
    subset = selections[(selections.model == model) & (selections.frequency == frequency)].copy()
    return subset.merge(audit, on=["test_year", "test_start", "test_end", "test_allocation_mode"], how="left", validate="one_to_one")


def _metric_row(
    ledger: pd.DataFrame,
    trades: pd.DataFrame,
    config: dict,
    *,
    strategy: str,
    model: str,
    frequency: str,
    tax_mode: str,
    prices: pd.DataFrame | dict[str, pd.DataFrame] | None = None,
) -> dict:
    if prices is not None:
        ledger = _add_pretrade_equity(ledger, prices, float(config["initial_capital"]))
    if len(trades) and "pretrade_equity" not in ledger:
        raise ValueError("final turnover requires canonical pretrade_equity")
    metric = performance_metrics(
        ledger, trades, float(config["initial_capital"]),
        terminal_tax_rate=float(config["tax"]["capital_gains_rate"]) if tax_mode == "after_tax" else None,
        terminal_cost_rate=_cost_rate(config),
    )
    metric.update({
        "strategy": strategy, "model": model, "frequency": frequency,
        "period": "stitched_chronological_oos", "tax_mode": tax_mode,
    })
    if "cash_weight" in ledger:
        invested = ledger["cash_weight"] < 1.0 - 1e-12
    elif "risk_weight" in ledger:
        invested = ledger["risk_weight"] > 1e-12
    elif "shares" in ledger:
        invested = ledger["shares"] > 1e-12
    else:
        invested = pd.Series(False, index=ledger.index)
    metric["invested_session_pct"] = float(invested.mean())
    metric["cash_session_pct"] = float((~invested).mean())
    metric["no_eligible_parameter_folds"] = 0
    return metric


def _buy_hold_rows(prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex, config: dict) -> list[dict]:
    rows = []
    for asset in ("SPY", "QQQ", "SSO", "QLD", "CASH"):
        if asset == "CASH":
            ledger, _, trades = cash_hold(index, float(config["initial_capital"]))
        else:
            ledger, _, trades = buy_and_hold(
                prices[asset].reindex(index), initial_capital=float(config["initial_capital"]),
                commission_bps=float(config["execution"]["commission_bps"]),
                slippage_bps=float(config["execution"]["slippage_bps"]),
            )
        metric = performance_metrics(
            ledger, trades, float(config["initial_capital"]),
            terminal_tax_rate=float(config["tax"]["capital_gains_rate"]), terminal_cost_rate=_cost_rate(config),
        )
        metric.update({
            "strategy": f"{asset}_BUY_HOLD", "model": "benchmark", "frequency": "none",
            "period": "stitched_chronological_oos", "tax_mode": "benchmark",
            "invested_session_pct": 0.0 if asset == "CASH" else 1.0,
            "cash_session_pct": 1.0 if asset == "CASH" else 0.0,
            "no_eligible_parameter_folds": 0,
        })
        rows.append(metric)
    return rows


def _complexity_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    pre = metrics[metrics.tax_mode.eq("pre_tax")].set_index(["model", "frequency"])
    after = metrics[metrics.tax_mode.eq("after_tax")].set_index(["model", "frequency"])
    rows = []
    for frequency in FREQUENCIES:
        a, b = pre.loc[("MODEL_A_QLD_TREND", frequency)], pre.loc[("MODEL_B_FOUR_STATE", frequency)]
        at, bt = after.loc[("MODEL_A_QLD_TREND", frequency)], after.loc[("MODEL_B_FOUR_STATE", frequency)]
        rows.append({
            "frequency": frequency,
            "cagr_difference": b.cagr - a.cagr,
            "max_drawdown_difference": b.max_drawdown - a.max_drawdown,
            "calmar_difference": b.calmar - a.calmar,
            "sortino_difference": b.sortino - a.sortino,
            "terminal_liquidation_cagr_difference": bt.after_tax_cagr_terminal_liquidation - at.after_tax_cagr_terminal_liquidation,
            "turnover_difference": b.annual_turnover - a.annual_turnover,
            "tax_difference": bt.tax_paid - at.tax_paid,
            "realized_tax_paid_difference": bt.tax_paid - at.tax_paid,
            "cash_exposure_difference": b.cash_session_pct - a.cash_session_pct,
            "model_b_no_eligible_folds": int(b.no_eligible_parameter_folds),
            "model_a_no_eligible_folds": int(a.no_eligible_parameter_folds),
            "material_outperformance": bool(
                b.cagr > a.cagr
                and b.max_drawdown >= a.max_drawdown
                and pd.notna(b.calmar) and pd.notna(a.calmar) and b.calmar > a.calmar
                and bt.after_tax_cagr_terminal_liquidation > at.after_tax_cagr_terminal_liquidation
                and b.annual_turnover <= a.annual_turnover
                and bt.tax_paid <= at.tax_paid
            ),
        })
    return pd.DataFrame(rows)


def _report_realized_tax_paid(row: pd.Series, after_row: pd.Series | None) -> float:
    """Return the realized-tax amount on the ledger represented by a report row.

    Performance rows are pre-tax for risk/return comparability, but their
    realized-tax display must come from the matching after-tax ledger. Buy and
    hold benchmark rows have no realized sale and therefore use their own zero
    tax ledger.
    """
    if row.tax_mode == "benchmark":
        return float(row.tax_paid)
    if after_row is None:
        raise ValueError("an after-tax ledger row is required for strategy tax display")
    return float(after_row.tax_paid)


def _write_report(output: Path, metrics: pd.DataFrame, selections: pd.DataFrame, complexity: pd.DataFrame) -> None:
    def fmt(value: object, pattern: str = ".3f") -> str:
        return "N/A" if value is None or pd.isna(value) else format(float(value), pattern)

    def fmt_signed(value: object, pattern: str = "+.3f") -> str:
        return "N/A" if value is None or pd.isna(value) else format(float(value), pattern)

    lines = [
        "# Phase 7B-v1 — Strict Eligibility Gate", "",
        "Model A is the simple QLD trend complexity-control benchmark. Model B is the frozen four-state model.",
        "Parameters are selected from training data only. OOS fold targets are concatenated and executed through one continuous ledger per model, frequency, and tax mode.",
        "", "## Selected parameters by fold", "",
        "| Model | Frequency | Test year | Eligible / candidates | Status | Test allocation | MA | Momentum | Low-vol q | Training CAGR | Training MaxDD | Training Calmar |",
        "|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in selections.sort_values(["model", "frequency", "test_year"]).iterrows():
        momentum = int(row.momentum_days) if pd.notna(row.get("momentum_days")) else "—"
        quantile = f"{row.low_vol_quantile:.2f}" if pd.notna(row.get("low_vol_quantile")) else "—"
        ma = int(row.ma_days) if pd.notna(row.get("ma_days")) else row.selection_status
        tcagr = f"{row.training_cagr:.2%}" if pd.notna(row.get("training_cagr")) else "—"
        tdd = f"{row.training_max_drawdown:.2%}" if pd.notna(row.get("training_max_drawdown")) else "—"
        tcalmar = f"{row.training_calmar:.3f}" if pd.notna(row.get("training_calmar")) else "—"
        lines.append(f"| {row.model} | {row.frequency} | {row.test_year} | {row.eligible_count}/{row.candidate_count} | {row.selection_status} | {row.test_allocation_mode} | {ma} | {momentum} | {quantile} | {tcagr} | {tdd} | {tcalmar} |")
    lines += [
        "", "## Stitched OOS performance", "",
        "Tax-paid CAGR is based on the continuous after-tax ledger. Terminal CAGR additionally applies report-only final liquidation.",
        "", "| Strategy | Frequency | CAGR | MaxDD | Calmar | Sharpe | Sortino | Ulcer | Tax-paid CAGR | Terminal CAGR | Turnover | Costs | Realized tax paid (after-tax ledger) | Invested sessions | CASH sessions | NO_ELIGIBLE folds | Recovery sessions | QQQ dominance |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    pre = metrics[metrics.tax_mode.isin(["pre_tax", "benchmark"])].copy()
    after = metrics[metrics.tax_mode.eq("after_tax")].set_index(["strategy", "frequency"])
    qqq = metrics[metrics.strategy.eq("QQQ_BUY_HOLD")].iloc[0]
    for _, row in pre.sort_values(["model", "frequency"]).iterrows():
        if row.tax_mode == "benchmark":
            tax_paid, terminal = row.cagr, row.after_tax_cagr_terminal_liquidation
            realized_tax_paid = _report_realized_tax_paid(row, None)
        else:
            tax_row = after.loc[(row.strategy, row.frequency)]
            tax_paid = tax_row.after_tax_cagr_tax_paid_to_date
            terminal = tax_row.after_tax_cagr_terminal_liquidation
            realized_tax_paid = _report_realized_tax_paid(row, tax_row)
        dominance = row.cagr > qqq.cagr and row.max_drawdown >= qqq.max_drawdown and row.calmar > qqq.calmar
        lines.append(
            f"| {row.strategy} | {row.frequency} | {fmt(row.cagr, '.2%')} | {fmt(row.max_drawdown, '.2%')} | {fmt(row.calmar)} | "
            f"{fmt(row.sharpe)} | {fmt(row.sortino)} | {fmt(row.ulcer_index)} | {fmt(tax_paid, '.2%')} | {fmt(terminal, '.2%')} | "
            f"{row.annual_turnover:.3f} | ${row.transaction_costs:,.0f} | ${realized_tax_paid:,.0f} | "
            f"{row.invested_session_pct:.1%} | {row.cash_session_pct:.1%} | {int(row.no_eligible_parameter_folds)} | "
            f"{row.recovery_trading_days if pd.notna(row.recovery_trading_days) else 'N/A'} | {str(bool(dominance)).upper()} |"
        )
    lines += [
        "", "## Complexity-control comparison: Model B minus Model A", "",
        "This is the primary Phase 7B complexity test. Positive MaxDD difference is better because MaxDD is negative; positive cash-exposure difference means Model B spent more sessions in CASH.",
        "", "| Frequency | CAGR diff | MaxDD diff | Calmar diff | Sortino diff | Terminal CAGR diff | Turnover diff | Tax paid diff | CASH exposure diff | Model A NO_ELIGIBLE | Model B NO_ELIGIBLE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in complexity.iterrows():
        lines.append(
            f"| {row.frequency} | {fmt_signed(row.cagr_difference, '+.2%')} | {fmt_signed(row.max_drawdown_difference, '+.2%')} | {fmt_signed(row.calmar_difference)} | "
            f"{fmt_signed(row.sortino_difference)} | {fmt_signed(row.terminal_liquidation_cagr_difference, '+.2%')} | {fmt_signed(row.turnover_difference)} | "
            f"${row.tax_difference:+,.0f} | {fmt_signed(row.cash_exposure_difference, '+.1%')} | {int(row.model_a_no_eligible_folds)} | {int(row.model_b_no_eligible_folds)} |"
        )
    lines += [
        "", "The CAGR/risk columns are read from the pre-tax ledger. The `Realized tax paid (after-tax ledger)` column is deliberately read from the matching after-tax ledger; pre-tax ledgers do not model tax payments and therefore show zero in their own `tax_paid` field. Buy-and-hold benchmarks have no realized sale, so their realized tax remains zero.",
        "", "Material outperformance requires higher CAGR, no deeper MaxDD, higher Calmar, higher terminal-liquidation after-tax CAGR, no higher turnover, and no higher realized tax paid.",
        "", "Material outperformance by frequency: " + ", ".join(f"{row.frequency}={str(bool(row.material_outperformance)).upper()}" for _, row in complexity.iterrows()) + ". If no frequency passes, prefer the simpler Model A.",
        "", "## Selection rules", "",
        "Eligibility is training CAGR >= 15% and abs(MaxDD) <= 45%. Candidates within 5% of the best eligible Calmar use the frozen tie-break: lower absolute MaxDD, lower turnover, longer MA, longer momentum, then volatility quantile closest to 0.33.",
        "No test-fold performance enters parameter selection. Any fold without an eligible parameter is recorded as `NO_ELIGIBLE_PARAMETER`; constraints are never relaxed.",
        "Annual turnover is the audited contemporaneous-open definition: sum(abs(trade notional) / open-before-trade pretrade equity) divided by calendar years. The true initial deployment BUY and hypothetical terminal liquidation are excluded.",
        "The frozen selector was rerun after correcting turnover inputs; `selection_old_vs_new.csv` records the fold-by-fold comparison.",
    ]
    (output / "phase7b_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase7b_walk_forward"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (output / "phase7b_parameter_grid.yaml").write_text(yaml.safe_dump({
        "model_a_ma_days": list(MA_DAYS),
        "model_b_ma_days": list(MA_DAYS),
        "model_b_momentum_days": list(MOMENTUM_DAYS),
        "model_b_low_vol_quantile": list(LOW_VOL_QUANTILES),
        "minimum_cagr": MINIMUM_CAGR,
        "maximum_abs_max_drawdown": MAXIMUM_ABS_MAX_DRAWDOWN,
        "objective": "maximize_calmar",
        "fallback": "NO_ELIGIBLE_PARAMETER -> CASH",
    }, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD", "TQQQ")}
    full_index = prices["QLD"].index.intersection(prices["SSO"].index)
    full_index = full_index[full_index >= pd.Timestamp(config["backtest"]["live_start"])]
    end = min(prices[a].index.max() for a in prices)
    full_index = full_index[full_index <= end]
    folds = expanding_calendar_year_folds(full_index)
    oos_index = full_index[full_index >= folds[0].test_start]
    capital = float(config["initial_capital"])
    tqqq_first = prices["TQQQ"].index.min()
    full_price_map = {asset: prices[asset].reindex(full_index) for asset in ("QQQ", "QLD", "TQQQ")}

    all_candidate_tables, all_selections = [], []
    model_a_targets_by_frequency: dict[str, dict[tuple, pd.Series]] = {}
    model_b_targets_by_frequency: dict[str, dict[tuple, tuple[pd.DataFrame, pd.Series]]] = {}
    for frequency in FREQUENCIES:
        a_parameters = [{"ma_days": ma} for ma in MA_DAYS]
        a_cache, a_targets = {}, {}
        for parameters in a_parameters:
            key = (parameters["ma_days"],)
            targets = trend_target_next_open(prices["QQQ"].adjusted_close, frequency, lookback=parameters["ma_days"]).reindex(full_index)
            ledger, _, trades, _ = single_asset_timed_backtest(
                prices["QLD"].reindex(full_index), targets, initial_capital=capital,
                commission_bps=float(config["execution"]["commission_bps"]),
                slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=None,
            )
            ledger = _add_pretrade_equity(ledger, prices["QLD"].reindex(full_index), capital)
            a_cache[key] = (ledger, trades); a_targets[key] = targets
        candidates, selections = _select_training_folds(
            a_cache, a_parameters, folds, model="MODEL_A_QLD_TREND", frequency=frequency, capital=capital,
        )
        all_candidate_tables.append(candidates); all_selections.append(selections)
        model_a_targets_by_frequency[frequency] = a_targets

        b_parameters = [
            {"ma_days": ma, "momentum_days": momentum, "low_vol_quantile": quantile}
            for ma, momentum, quantile in product(MA_DAYS, MOMENTUM_DAYS, LOW_VOL_QUANTILES)
        ]
        b_cache, b_targets = {}, {}
        schedule = rebalance_mask(full_index, frequency)
        for parameters in b_parameters:
            key = (parameters["ma_days"], parameters["momentum_days"], parameters["low_vol_quantile"])
            decisions = phase7_state_decisions(prices["QQQ"].adjusted_close, **parameters)
            targets, states = phase7_targets_next_open(decisions, frequency, tqqq_first_session=tqqq_first)
            targets = targets.reindex(full_index); states = states.reindex(full_index)
            ledger, _, trades, _ = dynamic_allocation_backtest(
                full_price_map, targets, schedule, initial_capital=capital,
                commission_bps=float(config["execution"]["commission_bps"]),
                slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=None,
            )
            ledger = _add_pretrade_equity(ledger, full_price_map, capital)
            b_cache[key] = (ledger, trades); b_targets[key] = (targets, states)
        candidates, selections = _select_training_folds(
            b_cache, b_parameters, folds, model="MODEL_B_FOUR_STATE", frequency=frequency, capital=capital,
        )
        all_candidate_tables.append(candidates); all_selections.append(selections)
        model_b_targets_by_frequency[frequency] = b_targets

    candidate_table = pd.concat(all_candidate_tables, ignore_index=True)
    selections = pd.concat(all_selections, ignore_index=True)
    candidate_table.to_csv(output / "training_candidate_results.csv", index=False)
    fold_table(folds).to_csv(output / "walk_forward_folds.csv", index=False)
    comparison_source = _find_selection_comparison_source(output_root, output)
    if comparison_source is None:
        old_selections = selections.copy()
    else:
        old_selections = pd.read_csv(comparison_source)
    selection_comparison = _selection_old_vs_new(old_selections, selections)
    selection_comparison.to_csv(output / "selection_old_vs_new.csv", index=False)

    metric_rows = _buy_hold_rows(prices, oos_index, config)
    curves, drawdowns, trades_out, taxes_out, positions_out, targets_out = [], [], [], [], [], []
    audited_selections = []
    phase7a_decisions = phase7_state_decisions(prices["QQQ"].adjusted_close)
    for frequency in FREQUENCIES:
        frequency_selection = selections[selections.frequency.eq(frequency)]
        a_selection = frequency_selection[frequency_selection.model.eq("MODEL_A_QLD_TREND")]
        b_selection = frequency_selection[frequency_selection.model.eq("MODEL_B_FOUR_STATE")]
        selected_a, selected_a_modes = _stitch_series(a_selection, folds, model_a_targets_by_frequency[frequency], oos_index, ("ma_days",))
        selected_b, selected_states, selected_b_modes = _stitch_frame(
            b_selection, folds, model_b_targets_by_frequency[frequency], oos_index,
            ("ma_days", "momentum_days", "low_vol_quantile"),
        )
        fixed_target = trend_target_next_open(prices["QQQ"].adjusted_close, frequency, lookback=200).reindex(oos_index)
        phase7a_target, phase7a_states = phase7_targets_next_open(phase7a_decisions, frequency, tqqq_first_session=tqqq_first)
        phase7a_target = phase7a_target.reindex(oos_index); phase7a_states = phase7a_states.reindex(oos_index)
        schedule = rebalance_mask(oos_index, frequency)
        targets_out.append(pd.DataFrame({"date": oos_index, "MODEL_A_target": selected_a, "allocation_mode": selected_a_modes, "frequency": frequency, "model": "MODEL_A_QLD_TREND"}))
        targets_out.append(selected_b.assign(state=selected_states, allocation_mode=selected_b_modes, frequency=frequency, model="MODEL_B_FOUR_STATE").reset_index(names="date"))
        runs = {}
        for strategy, model, target, states in (
            (f"FIXED_QLD_MA200_{frequency}", "FIXED_QLD_MA200", fixed_target, None),
            (f"MODEL_A_QLD_TREND_{frequency}", "MODEL_A_QLD_TREND", selected_a, None),
        ):
            for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                ledger, position, trades, taxes = single_asset_timed_backtest(
                    prices["QLD"].reindex(oos_index), target, initial_capital=capital,
                    commission_bps=float(config["execution"]["commission_bps"]),
                    slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                )
                ledger = _add_pretrade_equity(ledger, prices["QLD"].reindex(oos_index), capital)
                runs[(model, mode)] = (ledger, trades, taxes)
                metric_rows.append(_metric_row(ledger, trades, config, strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
                curves.append(ledger[["equity"]].assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode).reset_index())
                drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode).reset_index(names="date"))
                positions_out.append(position.assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
                if len(trades): trades_out.append(trades.assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
                if len(taxes): taxes_out.append(taxes.assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
        for strategy, model, target, states in (
            (f"PHASE7A_FIXED_{frequency}", "PHASE7A_FIXED", phase7a_target, phase7a_states),
            (f"MODEL_B_FOUR_STATE_{frequency}", "MODEL_B_FOUR_STATE", selected_b, selected_states),
        ):
            for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                ledger, position, trades, taxes = dynamic_allocation_backtest(
                    {asset: prices[asset].reindex(oos_index) for asset in ("QQQ", "QLD", "TQQQ")},
                    target, schedule, initial_capital=capital,
                    commission_bps=float(config["execution"]["commission_bps"]),
                    slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                )
                ledger = _add_pretrade_equity(
                    ledger,
                    {asset: prices[asset].reindex(oos_index) for asset in ("QQQ", "QLD", "TQQQ")},
                    capital,
                )
                ledger["state"] = states
                runs[(model, mode)] = (ledger, trades, taxes)
                metric_rows.append(_metric_row(ledger, trades, config, strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
                curves.append(ledger[["equity", "state"]].assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode).reset_index())
                drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode).reset_index(names="date"))
                positions_out.append(position.assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
                if len(trades): trades_out.append(trades.assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
                if len(taxes): taxes_out.append(taxes.assign(strategy=strategy, model=model, frequency=frequency, tax_mode=mode))
        # Fold audit is attached to each parameter-selected model after its two continuous ledgers exist.
        audited_selections.extend([
            _attach_fold_audit(
                a_selection, model="MODEL_A_QLD_TREND", frequency=frequency,
                pre_ledger=runs[("MODEL_A_QLD_TREND", "pre_tax")][0],
                pre_trades=runs[("MODEL_A_QLD_TREND", "pre_tax")][1],
                after_taxes=runs[("MODEL_A_QLD_TREND", "after_tax")][2], folds=folds,
                modes=selected_a_modes, initial_capital=capital,
            ),
            _attach_fold_audit(
                b_selection, model="MODEL_B_FOUR_STATE", frequency=frequency,
                pre_ledger=runs[("MODEL_B_FOUR_STATE", "pre_tax")][0],
                pre_trades=runs[("MODEL_B_FOUR_STATE", "pre_tax")][1],
                after_taxes=runs[("MODEL_B_FOUR_STATE", "after_tax")][2], folds=folds,
                modes=selected_b_modes, initial_capital=capital,
            ),
        ])

    metrics = pd.DataFrame(metric_rows)
    qqq = metrics[metrics.strategy.eq("QQQ_BUY_HOLD")].iloc[0]
    metrics["qqq_dominance"] = (
        (metrics["cagr"] > qqq.cagr) & (metrics["max_drawdown"] >= qqq.max_drawdown)
        & (metrics["calmar"] > qqq.calmar)
    )
    selection_audit = pd.concat(audited_selections, ignore_index=True)
    for model in ("MODEL_A_QLD_TREND", "MODEL_B_FOUR_STATE"):
        counts = selection_audit[selection_audit.model.eq(model)].groupby("frequency").selection_status.agg(
            no_eligible_parameter_folds=lambda s: int((s == "NO_ELIGIBLE_PARAMETER").sum())
        )
        for frequency, count in counts["no_eligible_parameter_folds"].items():
            metrics.loc[(metrics.model == model) & (metrics.frequency == frequency), "no_eligible_parameter_folds"] = int(count)
    selection_audit.to_csv(output / "selected_parameters_by_fold.csv", index=False)
    metrics.to_csv(output / "phase7b_stitched_oos_results.csv", index=False)
    metrics[metrics.tax_mode.isin(["pre_tax", "benchmark"])].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode.eq("after_tax")].to_csv(output / "metrics_after_tax.csv", index=False)
    pd.concat(curves, ignore_index=True).to_csv(output / "equity_curve.csv", index=False)
    pd.concat(drawdowns, ignore_index=True).to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions_out, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades_out, ignore_index=True).to_csv(output / "trades.csv", index=False)
    (pd.concat(taxes_out, ignore_index=True) if taxes_out else pd.DataFrame()).to_csv(output / "tax_ledger.csv", index=False)
    pd.concat(targets_out, ignore_index=True, sort=False).to_csv(output / "stitched_execution_targets.csv", index=False)
    complexity = _complexity_comparison(metrics)
    complexity.to_csv(output / "model_b_minus_model_a.csv", index=False)
    _write_report(output, metrics, selection_audit, complexity)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen Phase 7B parameter-selection Walk-Forward")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
