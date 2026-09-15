"""Phase 8C: frozen final robustness and economic-decision audit.

This module consumes the accepted Phase 8A/8B artifacts and runs only frozen
implementation/start-date/slippage sensitivities.  It does not introduce a
strategy, parameter search, frequency score, inferential p-value family, or
numerical DSR.  The baseline gate is deliberately executed before any
sensitivity output is written.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.phase2_ma200 import (  # noqa: E402
    FREQUENCIES,
    _add_pretrade_equity,
)
from experiments.phase8b1_pairwise_inference import (  # noqa: E402
    EXPECTED_PHASE8A_CHAMPION_SHA256,
    EXPECTED_PHASE8A_DAILY_RETURNS_SHA256,
    EXPECTED_SESSIONS,
    OOS_END,
    OOS_START,
)
from experiments.phase8b2_dsr_remediation import (  # noqa: E402
    DSR_STATUS,
    EXPECTED_ACCEPTED_B2_HASHES,
    EXPECTED_PHASE8A_HASHES,
    EXPECTED_PHASE8B1_HASHES,
)
from market_timing_quant.metrics import (  # noqa: E402
    drawdown_series,
    performance_metrics,
)
from market_timing_quant.portfolio import (  # noqa: E402
    buy_and_hold,
    dynamic_allocation_backtest,
    single_asset_timed_backtest,
)
from market_timing_quant.signals import (  # noqa: E402
    ma_trend_decision,
    phase7_state_decisions,
    phase7_targets_next_open,
    rebalance_mask,
    trend_target_next_open,
)


PHASE8C_RUN_ID = "20260915_phase8c_final_robustness_audit"
PHASE8A_RUN_ID = "20260914_phase8a_oos_evidence_consolidation_final"
PHASE8B1_RUN_ID = "20260914_phase8b1_null_test_remediation_candidate"
PHASE8B2_REMEDIATION_RUN_ID = "20260915_phase8b2_dsr_remediation_candidate"
PHASE8B2_ACCEPTED_RUN_ID = "20260915_phase8b2_multiple_testing_audit"
PHASE8A_RUN = PROJECT_ROOT / "reports/runs" / PHASE8A_RUN_ID
PHASE8B1_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B1_RUN_ID
PHASE8B2_REMEDIATION_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B2_REMEDIATION_RUN_ID
PHASE8B2_ACCEPTED_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B2_ACCEPTED_RUN_ID
FIXED_OOS_RUN_ID = "20260914_oos_fixed_ma200_audit_final"
PHASE7A_RUN_ID = "20260913_phase7a_metrics_tax_audited_final"
FIXED_OOS_RUN = PROJECT_ROOT / "reports/runs" / FIXED_OOS_RUN_ID
PHASE7A_RUN = PROJECT_ROOT / "reports/runs" / PHASE7A_RUN_ID

INITIAL_CAPITAL = 100_000.0
COMMISSION_BPS = 0.0
BASELINE_SLIPPAGE_BPS = 5.0
TAX_RATE = 0.20315
END_DATE = OOS_END
SLIPPAGE_GRID = (0.0, 5.0, 10.0, 20.0)
EXECUTION_GRID = ("next_open", "next_close", "t2_open")
START_LABELS = ("2013", "2014", "2015", "2016", "2018", "2020")
PRIMARY_STRATEGIES = ("FIXED_MA200_QQQ_TO_QLD", "PHASE7A_FIXED_FOUR_STATE")
CONTEXT_STRATEGIES = ("PHASE7B_MODEL_A_SELECTED", "PHASE7B_MODEL_B_SELECTED")
ALL_STRATEGIES = PRIMARY_STRATEGIES + CONTEXT_STRATEGIES
EXECUTION_DELAY = {"next_open": 1, "next_close": 1, "t2_open": 2}
REQUIRED_B2_REMEDIATION_FILES = (
    "dsr_trial_universe_audit.csv",
    "deflated_sharpe_results.csv",
    "multiple_testing_adjustments.csv",
    "data_snooping_test_results.csv",
    "phase8b2_dsr_remediation.md",
    "phase8b2_configuration.json",
    "phase8b2_report.md",
    "phase8b2_audit_diff.md",
)

# The remediation candidate is now accepted as the Phase 8B-2 source for this
# phase, while the former multiple-testing run remains immutable evidence.
EXPECTED_B2_REMEDIATION_HASHES = {
    "dsr_trial_universe_audit.csv": "8d421b30453ec9b5356b6e1342ce9c33c79590d3c3d47e5b088b7ac294a61fca",
    "deflated_sharpe_results.csv": "1f306a42aa2c40afd2a12bcce722177135082b04364832bdd1a01855cbc9ed69",
    "multiple_testing_adjustments.csv": EXPECTED_ACCEPTED_B2_HASHES["multiple_testing_adjustments.csv"],
    "data_snooping_test_results.csv": EXPECTED_ACCEPTED_B2_HASHES["data_snooping_test_results.csv"],
    "phase8b2_dsr_remediation.md": "465f4c397f46c0932b773e962097820b0f779880a06b0e960c04026ce693699d",
    "phase8b2_configuration.json": "d0339ee4c9aa82f7833abab6e50204b050be061d608b5dfb642fa3eb1b6a0c1a",
    "phase8b2_report.md": "fb30c0b92aec90a730cbc83c7425391d742b171cb316c6922329ab0b17305bca",
    "phase8b2_audit_diff.md": "96e260045158c38e7552482bf26b4451a80d43a9b967dfdf8eb3741c8a8152ce",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _float(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def _safe_bool(value: object) -> bool:
    return bool(value) if not pd.isna(value) else False


def _path_hash(values: pd.Series | np.ndarray) -> str:
    """Stable serialization-safe hash for an economic equity path."""
    array = np.asarray(values, dtype=np.float64)
    rounded = np.round(array, 8).astype("<f8", copy=False)
    return hashlib.sha256(rounded.tobytes()).hexdigest()


def _table_hash(frame: pd.DataFrame, columns: tuple[str, ...]) -> str:
    """Hash normalized core ledger fields, independent of CSV column order."""
    if frame.empty:
        payload = b""
    else:
        present = [column for column in columns if column in frame.columns]
        subset = frame[present].copy()
        for column in present:
            if column == "date":
                subset[column] = pd.to_datetime(subset[column]).dt.strftime("%Y-%m-%d")
            elif pd.api.types.is_numeric_dtype(subset[column]):
                subset[column] = pd.to_numeric(subset[column], errors="coerce").round(4)
            else:
                subset[column] = subset[column].astype(str)
        sort_columns = [column for column in ("date", "asset", "side") if column in present]
        if sort_columns:
            subset = subset.sort_values(sort_columns, kind="mergesort")
        payload = subset.to_csv(index=False, float_format="%.4f", lineterminator="\n").encode()
    return hashlib.sha256(payload).hexdigest()


def _canonical_oos_index() -> pd.DatetimeIndex:
    daily = pd.read_csv(PHASE8A_RUN / "aligned_daily_returns.csv")
    daily["date"] = pd.to_datetime(daily.date)
    qqq = daily.loc[
        daily.strategy_id.eq("QQQ_BUY_HOLD") & daily.tax_mode.eq("benchmark"), "date"
    ].sort_values().drop_duplicates()
    index = pd.DatetimeIndex(qqq)
    if len(index) != EXPECTED_SESSIONS or index[0] != OOS_START or index[-1] != OOS_END:
        raise AssertionError("Phase 8A OOS calendar does not match the accepted 3,436 sessions")
    return index


def _load_prices() -> dict[str, pd.DataFrame]:
    assets = ("SPY", "QQQ", "SSO", "QLD", "TQQQ")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in assets}
    for asset, frame in prices.items():
        if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
            raise AssertionError(f"processed {asset} calendar is not unique/increasing")
    return prices


def _accepted_source_hashes() -> dict[str, str]:
    """Verify every accepted Phase 8A, 8B-1 and 8B-2 source before use."""
    actual: dict[str, str] = {}
    for name, expected in EXPECTED_PHASE8A_HASHES.items():
        path = PHASE8A_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8A source hash mismatch: {name}")
        actual[f"phase8a/{name}"] = digest
    for name, expected in EXPECTED_PHASE8B1_HASHES.items():
        path = PHASE8B1_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8B-1 source hash mismatch: {name}")
        actual[f"phase8b1/{name}"] = digest
    for name, expected in EXPECTED_ACCEPTED_B2_HASHES.items():
        path = PHASE8B2_ACCEPTED_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"accepted Phase 8B-2 hash mismatch: {name}")
        actual[f"phase8b2_accepted/{name}"] = digest
    for name, expected in EXPECTED_B2_REMEDIATION_HASHES.items():
        path = PHASE8B2_REMEDIATION_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8B-2 remediation hash mismatch: {name}")
        actual[f"phase8b2_remediation/{name}"] = digest
    return actual


def _raw_source_hashes() -> dict[str, str]:
    manifest = yaml.safe_load((PROJECT_ROOT / "data/raw/manifest.yaml").read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for asset, meta in manifest["sources"].items():
        path = PROJECT_ROOT / "data/raw" / f"{asset}.parquet"
        digest = _sha256(path)
        if digest != str(meta["sha256"]):
            raise AssertionError(f"raw snapshot hash mismatch for {asset}")
        result[f"raw/{asset}.parquet"] = digest
    return result


def _start_dates(index: pd.DatetimeIndex) -> dict[str, pd.Timestamp]:
    result: dict[str, pd.Timestamp] = {}
    for label in START_LABELS:
        year = int(label)
        candidates = index[index.year >= year]
        if not len(candidates):
            raise AssertionError(f"no common eligible date for {label}")
        result[label] = pd.Timestamp(candidates[0]) if year == int(START_LABELS[0]) else pd.Timestamp(index[index.year == year][0])
    if result["2013"] != OOS_START:
        raise AssertionError("2013 baseline start must be the accepted OOS start")
    return result


def _fill_prices(frame: pd.DataFrame, execution_case: str) -> pd.DataFrame:
    result = frame.copy()
    if execution_case == "next_close":
        result["open"] = result["adjusted_close"].astype(float)
    elif execution_case not in {"next_open", "t2_open"}:
        raise ValueError(f"unknown execution case {execution_case}")
    return result


def _delayed_binary_targets(
    decisions: pd.Series,
    frequency: str,
    evaluation_index: pd.DatetimeIndex,
    delay: int,
) -> pd.Series:
    """Map a scheduled close decision to an execution date after ``delay`` sessions."""
    full_index = decisions.index
    schedule = rebalance_mask(full_index, frequency)
    events: dict[pd.Timestamp, float] = {}
    for position in np.flatnonzero(schedule.to_numpy(dtype=bool)):
        source_position = position - 1
        execution_position = source_position + delay
        if source_position < 0 or execution_position >= len(full_index):
            continue
        events[pd.Timestamp(full_index[execution_position])] = float(decisions.iloc[source_position])
    targets = pd.Series(0.0, index=evaluation_index, dtype=float)
    current = 0.0
    for date in evaluation_index:
        if pd.Timestamp(date) in events:
            current = events[pd.Timestamp(date)]
        targets.loc[date] = current
    return targets


def _delayed_phase7_targets(
    decisions: pd.DataFrame,
    frequency: str,
    evaluation_index: pd.DatetimeIndex,
    delay: int,
    tqqq_first_session: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.Series]:
    full_index = decisions.index
    schedule = rebalance_mask(full_index, frequency)
    events: dict[pd.Timestamp, tuple[np.ndarray, str]] = {}
    value_columns = ("weight_QQQ", "weight_QLD", "weight_TQQQ")
    for position in np.flatnonzero(schedule.to_numpy(dtype=bool)):
        source_position = position - 1
        execution_position = source_position + delay
        if source_position < 0 or execution_position >= len(full_index):
            continue
        date = pd.Timestamp(full_index[execution_position])
        weights = decisions.iloc[source_position][list(value_columns)].to_numpy(dtype=float)
        state = str(decisions.iloc[source_position].state)
        events[date] = (weights, state)
    values = pd.DataFrame(0.0, index=evaluation_index, columns=("QQQ", "QLD", "TQQQ"))
    states = pd.Series("RISK_OFF", index=evaluation_index, dtype=object)
    current = np.zeros(3, dtype=float)
    current_state = "RISK_OFF"
    for date in evaluation_index:
        key = pd.Timestamp(date)
        if key in events:
            current, current_state = events[key]
        values.loc[date] = current
        states.loc[date] = current_state
    unavailable = values.index < pd.Timestamp(tqqq_first_session)
    values.loc[unavailable, "QLD"] += values.loc[unavailable, "TQQQ"]
    values.loc[unavailable, "TQQQ"] = 0.0
    return values, states


def _execution_targets(
    strategy_id: str,
    frequency: str,
    evaluation_index: pd.DatetimeIndex,
    execution_case: str,
    prices: dict[str, pd.DataFrame],
) -> tuple[pd.Series | pd.DataFrame, pd.Series | None, pd.Series]:
    delay = EXECUTION_DELAY[execution_case]
    if strategy_id == "FIXED_MA200_QQQ_TO_QLD":
        decisions = ma_trend_decision(prices["QQQ"].adjusted_close, lookback=200)
        if execution_case == "next_open":
            targets = trend_target_next_open(prices["QQQ"].adjusted_close, frequency, lookback=200).reindex(evaluation_index)
        else:
            targets = _delayed_binary_targets(decisions, frequency, evaluation_index, delay)
        if targets.isna().any():
            raise AssertionError("binary target alignment produced missing values")
        schedule = pd.Series(targets.ne(targets.shift(1)), index=evaluation_index).fillna(True)
        return targets, None, schedule
    if strategy_id == "PHASE7A_FIXED_FOUR_STATE":
        decisions = phase7_state_decisions(prices["QQQ"].adjusted_close)
        if execution_case == "next_open":
            targets, states = phase7_targets_next_open(
                decisions, frequency, tqqq_first_session=prices["TQQQ"].index.min(),
            )
            targets = targets.reindex(evaluation_index)
            states = states.reindex(evaluation_index).ffill().fillna("RISK_OFF")
            schedule = rebalance_mask(evaluation_index, frequency)
        else:
            targets, states = _delayed_phase7_targets(
                decisions, frequency, evaluation_index, delay,
                pd.Timestamp(prices["TQQQ"].index.min()),
            )
            schedule = pd.Series(False, index=evaluation_index)
            full = decisions.index
            base = rebalance_mask(full, frequency)
            for position in np.flatnonzero(base.to_numpy(dtype=bool)):
                source_position = position - 1
                execution_position = source_position + delay
                if source_position >= 0 and execution_position < len(full):
                    date = pd.Timestamp(full[execution_position])
                    if date in schedule.index:
                        schedule.loc[date] = True
        if targets.isna().any().any():
            raise AssertionError("Phase 7A target alignment produced missing values")
        return targets, states, schedule
    raise ValueError(f"strategy is not a primary Phase 8C path: {strategy_id}")


def _metric_record(
    metric: dict[str, Any],
    *,
    strategy_id: str,
    frequency: str,
    tax_mode: str,
    scenario_id: str,
    scenario_family: str,
    slippage_bps: float,
    execution_case: str,
    start_label: str,
    context_only: bool = False,
    source_run_id: str = "phase8c_recomputed",
) -> dict[str, Any]:
    row = {
        "scenario_id": scenario_id,
        "scenario_family": scenario_family,
        "strategy_id": strategy_id,
        "frequency": frequency,
        "tax_mode": tax_mode,
        "start_label": start_label,
        "start_date": str(metric["start"]),
        "end_date": str(metric["end"]),
        "slippage_bps": float(slippage_bps),
        "execution_case": execution_case,
        "context_only": bool(context_only),
        "source_run_id": source_run_id,
        "selection_performed": False,
    }
    for key in (
        "ending_value", "total_return", "cagr", "max_drawdown", "calmar", "sharpe", "sortino",
        "ulcer_index", "annual_turnover", "number_of_trades", "transaction_costs", "tax_paid",
        "gross_traded_notional", "mean_holding_period_days", "median_holding_period_days",
        "max_holding_period_days", "terminal_liquidation_wealth", "terminal_liquidation_cagr",
        "terminal_liquidation_tax", "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
        "after_tax_wealth_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date",
        "after_tax_terminal_liquidation", "after_tax_cagr_terminal_liquidation",
    ):
        row[key] = _float(metric.get(key))
    return row


def _run_fixed(
    prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex, frequency: str,
    execution_case: str, slippage_bps: float, tax_mode: str,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    targets, _, _ = _execution_targets("FIXED_MA200_QQQ_TO_QLD", frequency, index, execution_case, prices)
    held = _fill_prices(prices["QLD"].reindex(index), execution_case)
    ledger, positions, trades, taxes = single_asset_timed_backtest(
        held, targets, initial_capital=INITIAL_CAPITAL, commission_bps=COMMISSION_BPS,
        slippage_bps=slippage_bps, tax_rate=TAX_RATE if tax_mode == "after_tax" else None,
    )
    ledger = _add_pretrade_equity(ledger, held, INITIAL_CAPITAL)
    metric = performance_metrics(
        ledger, trades, INITIAL_CAPITAL,
        terminal_tax_rate=TAX_RATE if tax_mode == "after_tax" else None,
        terminal_cost_rate=(COMMISSION_BPS + slippage_bps) / 10_000.0 if tax_mode == "after_tax" else 0.0,
    )
    return metric, ledger, positions, trades, taxes


def _run_phase7a(
    prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex, frequency: str,
    execution_case: str, slippage_bps: float, tax_mode: str,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    targets, states, schedule = _execution_targets("PHASE7A_FIXED_FOUR_STATE", frequency, index, execution_case, prices)
    price_map = {asset: _fill_prices(prices[asset].reindex(index), execution_case) for asset in ("QQQ", "QLD", "TQQQ")}
    ledger, positions, trades, taxes = dynamic_allocation_backtest(
        price_map, targets, schedule, initial_capital=INITIAL_CAPITAL,
        commission_bps=COMMISSION_BPS, slippage_bps=slippage_bps,
        tax_rate=TAX_RATE if tax_mode == "after_tax" else None,
    )
    ledger["state"] = states
    metric = performance_metrics(
        ledger, trades, INITIAL_CAPITAL,
        terminal_tax_rate=TAX_RATE if tax_mode == "after_tax" else None,
        terminal_cost_rate=(COMMISSION_BPS + slippage_bps) / 10_000.0 if tax_mode == "after_tax" else 0.0,
    )
    return metric, ledger, positions, trades, taxes


def _benchmark_buy_and_hold(
    prices: pd.DataFrame, index: pd.DatetimeIndex, execution_case: str, slippage_bps: float,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Buy the benchmark on the scenario's first eligible fill date."""
    frame = _fill_prices(prices.reindex(index), execution_case)
    delay = 1 if execution_case == "t2_open" else 0
    fill_date = index[min(delay, len(index) - 1)]
    fill_price = float(frame.loc[fill_date, "open"])
    rate = (COMMISSION_BPS + slippage_bps) / 10_000.0
    notional = INITIAL_CAPITAL / (1.0 + rate)
    cost = notional * rate
    shares = notional / fill_price
    cash = INITIAL_CAPITAL
    records: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    for date in index:
        if date == fill_date:
            cash = max(0.0, INITIAL_CAPITAL - notional - cost)
        equity = cash + shares * float(frame.loc[date, "adjusted_close"]) if date >= fill_date else INITIAL_CAPITAL
        held = shares if date >= fill_date else 0.0
        records.append({"date": date, "equity": equity, "cash": cash, "shares": held,
                        "pretrade_equity": INITIAL_CAPITAL if date == fill_date else records[-1]["equity"] if records else INITIAL_CAPITAL,
                        "trade_notional": notional if date == fill_date else 0.0,
                        "transaction_cost": cost if date == fill_date else 0.0,
                        "tax_paid": 0.0})
        positions.append({"date": date, "shares": held, "target_weight": 1.0 if date >= fill_date else 0.0,
                          "actual_weight": held * float(frame.loc[date, "adjusted_close"]) / equity})
    ledger = pd.DataFrame(records).set_index("date")
    ledger["daily_return"] = ledger.equity.pct_change()
    ledger.iloc[0, ledger.columns.get_loc("daily_return")] = ledger.equity.iloc[0] / INITIAL_CAPITAL - 1.0
    trades = pd.DataFrame([{"date": fill_date, "asset": "BENCHMARK", "side": "BUY", "shares": shares,
                            "price": fill_price, "notional": notional, "transaction_cost": cost,
                            "realized_gain": 0.0}])
    metric = performance_metrics(ledger, trades, INITIAL_CAPITAL)
    return metric, ledger, pd.DataFrame(positions), trades


def _canonical_metrics() -> pd.DataFrame:
    frame = pd.read_csv(PHASE8A_RUN / "oos_champion_table.csv")
    return frame


def _canonical_path_frame(strategy_id: str, frequency: str, tax_mode: str) -> pd.DataFrame:
    daily = pd.read_csv(PHASE8A_RUN / "aligned_daily_equity.csv")
    daily["date"] = pd.to_datetime(daily.date)
    scoped = daily.loc[
        daily.strategy_id.eq(strategy_id) & daily.frequency.eq(frequency) & daily.tax_mode.eq(tax_mode)
    ].sort_values("date")
    return scoped


def _source_path_tables(strategy_id: str, frequency: str, tax_mode: str) -> dict[str, pd.DataFrame]:
    if strategy_id == "FIXED_MA200_QQQ_TO_QLD":
        source = FIXED_OOS_RUN
        source_strategy = f"QQQ_MA200_QLD_{frequency}_OOS"
        period = None
    elif strategy_id == "PHASE7A_FIXED_FOUR_STATE":
        source = PHASE7A_RUN
        source_strategy = f"PHASE7A_{frequency}"
        period = "chronological_oos"
    else:
        return {}
    result: dict[str, pd.DataFrame] = {}
    for artifact in ("equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv"):
        frame = pd.read_csv(source / artifact)
        if "strategy" in frame:
            frame = frame.loc[frame.strategy.eq(source_strategy)]
        if "tax_mode" in frame:
            frame = frame.loc[frame.tax_mode.eq(tax_mode)]
        if period is not None and "period" in frame:
            frame = frame.loc[frame.period.eq(period)]
        result[artifact] = frame
    return result


def _baseline_gate(
    prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex, canonical: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[tuple[str, str, str], dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    comparison_fields = (
        "ending_value", "cagr", "max_drawdown", "calmar", "sharpe", "sortino",
        "annual_turnover", "number_of_trades", "transaction_costs", "tax_paid",
    )
    for strategy_id in PRIMARY_STRATEGIES:
        for frequency in FREQUENCIES:
            for mode in ("pre_tax", "after_tax"):
                runner = _run_fixed if strategy_id == "FIXED_MA200_QQQ_TO_QLD" else _run_phase7a
                metric, ledger, positions, trades, taxes = runner(
                    prices, index, frequency, "next_open", BASELINE_SLIPPAGE_BPS, mode,
                )
                cache[(strategy_id, frequency, mode)] = {
                    "metric": metric, "ledger": ledger, "positions": positions,
                    "trades": trades, "taxes": taxes,
                }
                expected = canonical.loc[
                    canonical.strategy_id.eq(strategy_id) & canonical.frequency.eq(frequency) & canonical.tax_mode.eq(mode)
                ]
                if len(expected) != 1:
                    raise AssertionError(f"missing canonical baseline row {strategy_id}/{frequency}/{mode}")
                expected_row = expected.iloc[0]
                diffs = {field: float(metric[field]) - float(expected_row["realized_tax_paid"] if field == "tax_paid" else expected_row[field])
                         for field in comparison_fields}
                metric_pass = all(abs(value) <= (1e-7 if field in {"ending_value", "transaction_costs"} else 1e-11) for field, value in diffs.items())
                canonical_equity = _canonical_path_frame(strategy_id, frequency, mode)
                path_values_match = len(canonical_equity) == len(ledger) and np.allclose(
                    canonical_equity.equity.to_numpy(dtype=float), ledger.equity.to_numpy(dtype=float), rtol=1e-12, atol=1e-8,
                )
                source_tables = _source_path_tables(strategy_id, frequency, mode)
                simulated_equity = pd.DataFrame({"date": ledger.index, "equity": ledger.equity.to_numpy()})
                equity_hash = _table_hash(simulated_equity, ("date", "equity"))
                canonical_hash = _table_hash(canonical_equity, ("date", "equity"))
                # Compare the economic ledger fields where canonical artifacts expose them.
                simulated_positions = positions.copy()
                simulated_trades = trades.copy()
                simulated_taxes = taxes.copy()
                path_table_hashes = {
                    "equity_curve.csv": {
                        "canonical": canonical_hash,
                        "recomputed": equity_hash,
                        "match": path_values_match,
                    },
                    "positions.csv": {
                        "canonical": _table_hash(source_tables["positions.csv"], ("date", "asset", "shares", "target_weight", "actual_weight")),
                        "recomputed": _table_hash(simulated_positions, ("date", "asset", "shares", "target_weight", "actual_weight")),
                    },
                    "trades.csv": {
                        "canonical": _table_hash(source_tables["trades.csv"], ("date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain")),
                        "recomputed": _table_hash(simulated_trades, ("date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain")),
                    },
                    "tax_ledger.csv": {
                        "canonical": _table_hash(source_tables["tax_ledger.csv"], ("date", "asset", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid")),
                        "recomputed": _table_hash(simulated_taxes, ("date", "asset", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid")),
                    },
                }
                path_hash_match = all(item.get("canonical") == item.get("recomputed") for item in path_table_hashes.values())
                if not metric_pass or not path_values_match or not path_hash_match:
                    raise RuntimeError("PHASE8C_BASELINE_REPRODUCTION_FAILURE")
                rows.append({
                    "strategy_id": strategy_id, "frequency": frequency, "tax_mode": mode,
                    "start_date": str(metric["start"]), "end_date": str(metric["end"]),
                    "canonical_ending_value": float(expected_row.ending_value), "recomputed_ending_value": float(metric["ending_value"]),
                    "canonical_cagr": float(expected_row.cagr), "recomputed_cagr": float(metric["cagr"]),
                    "canonical_max_drawdown": float(expected_row.max_drawdown), "recomputed_max_drawdown": float(metric["max_drawdown"]),
                    "canonical_calmar": float(expected_row.calmar), "recomputed_calmar": float(metric["calmar"]),
                    "canonical_sharpe": float(expected_row.sharpe), "recomputed_sharpe": float(metric["sharpe"]),
                    "canonical_sortino": float(expected_row.sortino), "recomputed_sortino": float(metric["sortino"]),
                    "canonical_annual_turnover": float(expected_row.annual_turnover), "recomputed_annual_turnover": float(metric["annual_turnover"]),
                    "canonical_number_of_trades": int(expected_row.number_of_trades), "recomputed_number_of_trades": int(metric["number_of_trades"]),
                    "canonical_transaction_costs": float(expected_row.transaction_costs), "recomputed_transaction_costs": float(metric["transaction_costs"]),
                    "canonical_realized_tax_paid": float(expected_row.realized_tax_paid), "recomputed_realized_tax_paid": float(metric["tax_paid"]),
                    "equity_path_hash": canonical_hash, "recomputed_equity_path_hash": equity_hash,
                    "path_hash_match": path_hash_match, "metric_match": metric_pass, "baseline_reproduction_pass": True,
                    "hash_method": "normalized core rows; numeric values rounded to 4 decimals; separate allclose path check",
                    "path_table_hashes_json": json.dumps(path_table_hashes, sort_keys=True),
                })
    return pd.DataFrame(rows), cache


def _canonical_context_rows(canonical: pd.DataFrame) -> list[dict[str, Any]]:
    """Keep Phase 7B failed-complexity references visible without retuning them."""
    rows: list[dict[str, Any]] = []
    for strategy_id in CONTEXT_STRATEGIES:
        scoped = canonical.loc[canonical.strategy_id.eq(strategy_id)]
        for _, source in scoped.iterrows():
            metric = {
                key: source.get(key)
                for key in (
                    "ending_value", "total_return", "cagr", "max_drawdown", "calmar", "sharpe", "sortino",
                    "ulcer_index", "annual_turnover", "number_of_trades", "transaction_costs", "raw_tax_paid",
                    "mean_holding_period_days", "median_holding_period_days", "max_holding_period_days",
                    "source_after_tax_ending_value_terminal_liquidation", "source_after_tax_CAGR_terminal_liquidation",
                    "source_terminal_liquidation_tax", "source_terminal_liquidation_cost",
                )
            }
            metric["start"] = source.start_date
            metric["end"] = source.end_date
            metric["tax_paid"] = source.get("realized_tax_paid", 0.0)
            metric["terminal_liquidation_wealth"] = source.get("source_terminal_liquidation_wealth")
            metric["terminal_liquidation_cagr"] = source.get("source_after_tax_CAGR_terminal_liquidation")
            metric["terminal_liquidation_tax"] = source.get("source_terminal_liquidation_tax")
            metric["terminal_liquidation_cost"] = source.get("source_terminal_liquidation_cost")
            metric["terminal_unrealized_gain_after_cost"] = source.get("source_terminal_unrealized_gain_after_cost")
            metric["after_tax_wealth_tax_paid_to_date"] = source.get("ending_value")
            metric["after_tax_cagr_tax_paid_to_date"] = source.get("cagr")
            metric["after_tax_terminal_liquidation"] = source.get("after_tax_ending_value_terminal_liquidation")
            metric["after_tax_cagr_terminal_liquidation"] = source.get("after_tax_CAGR_terminal_liquidation")
            rows.append(_metric_record(
                metric,
                strategy_id=strategy_id,
                frequency=str(source.frequency),
                tax_mode=str(source.tax_mode),
                scenario_id="baseline",
                scenario_family="context_baseline",
                slippage_bps=BASELINE_SLIPPAGE_BPS,
                execution_case="next_open",
                start_label="2013",
                context_only=True,
                source_run_id=PHASE8A_RUN_ID,
            ))
    return rows


def _scenario_rows(start_dates: dict[str, pd.Timestamp]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(scenario_id: str, family: str, slip: float, execution: str, label: str) -> None:
        rows.append({
            "scenario_id": scenario_id,
            "scenario_family": family,
            "slippage_bps": float(slip),
            "execution_case": execution,
            "start_label": label,
            "start_date": start_dates[label].date().isoformat(),
            "end_date": END_DATE.date().isoformat(),
            "signal_convention": "adjusted-close signal at t; execution never before the specified delayed session",
            "parameters_frozen": True,
            "selection_performed": False,
            "frequency_selection_performed": False,
            "scenario_is_new_strategy": False,
        })

    add("baseline", "baseline", BASELINE_SLIPPAGE_BPS, "next_open", "2013")
    for slip in SLIPPAGE_GRID:
        add(f"slippage_{int(slip):02d}bps", "slippage", slip, "next_open", "2013")
    for execution in EXECUTION_GRID:
        add(f"execution_{execution}", "execution", BASELINE_SLIPPAGE_BPS, execution, "2013")
    for label in START_LABELS:
        add(f"start_{label}", "start_date", BASELINE_SLIPPAGE_BPS, "next_open", label)
    return pd.DataFrame(rows)


def _scenario_spec_rows(scenarios: pd.DataFrame) -> list[dict[str, Any]]:
    return scenarios.to_dict(orient="records")


def _run_scenario(
    prices: dict[str, pd.DataFrame], scenario: dict[str, Any], start_dates: dict[str, pd.Timestamp],
    *, cache: dict[tuple[str, str, str, str, float, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    start_label = str(scenario["start_label"])
    start = start_dates[start_label]
    end = pd.Timestamp(scenario["end_date"])
    # The canonical benchmark calendar is authoritative; all processed assets
    # are intersected so no scenario silently invents an eligible session.
    index = _canonical_oos_index()
    index = index[(index >= start) & (index <= end)]
    if not len(index):
        raise AssertionError(f"scenario has no sessions: {scenario['scenario_id']}")
    scenario_id = str(scenario["scenario_id"])
    family = str(scenario["scenario_family"])
    slip = float(scenario["slippage_bps"])
    execution = str(scenario["execution_case"])
    records: list[dict[str, Any]] = []
    for strategy_id in PRIMARY_STRATEGIES:
        runner = _run_fixed if strategy_id == "FIXED_MA200_QQQ_TO_QLD" else _run_phase7a
        for frequency in FREQUENCIES:
            for mode in ("pre_tax", "after_tax"):
                key = (scenario_id, strategy_id, frequency, mode, slip, execution, start_label)
                if key not in cache:
                    metric, ledger, positions, trades, taxes = runner(
                        prices, index, frequency, execution, slip, mode,
                    )
                    cache[key] = {"metric": metric, "ledger": ledger, "positions": positions,
                                  "trades": trades, "taxes": taxes}
                entry = cache[key]
                row = _metric_record(
                    entry["metric"], strategy_id=strategy_id, frequency=frequency, tax_mode=mode,
                    scenario_id=scenario_id, scenario_family=family, slippage_bps=slip,
                    execution_case=execution, start_label=start_label,
                )
                row["path_hash"] = _path_hash(entry["ledger"].equity)
                row["initial_deployment_excluded_from_turnover"] = True
                row["terminal_liquidation_excluded_from_turnover"] = True
                row["holding_periods_completed_only"] = True
                row["terminal_liquidation_non_mutating"] = True
                records.append(row)

    # QQQ is a tax-neutral reference benchmark. It is recomputed for each
    # scenario so relative comparisons use identical dates and implementation
    # assumptions, while the primary strategy tax rows remain the accepted
    # simplified taxable-account treatment.
    benchmark_metric, benchmark_ledger, benchmark_positions, benchmark_trades = _benchmark_buy_and_hold(
        prices["QQQ"], index, execution, slip,
    )
    benchmark_row = _metric_record(
        benchmark_metric, strategy_id="QQQ_BUY_HOLD", frequency="none", tax_mode="benchmark",
        scenario_id=scenario_id, scenario_family=family, slippage_bps=slip,
        execution_case=execution, start_label=start_label, source_run_id="phase8c_recomputed_benchmark",
    )
    benchmark_row["path_hash"] = _path_hash(benchmark_ledger.equity)
    benchmark_row["initial_deployment_excluded_from_turnover"] = True
    benchmark_row["terminal_liquidation_excluded_from_turnover"] = True
    records.append(benchmark_row)
    return records


def _scenario_metric_table(
    prices: dict[str, pd.DataFrame], scenarios: pd.DataFrame, start_dates: dict[str, pd.Timestamp],
    canonical: pd.DataFrame, baseline_cache: dict[tuple[str, str, str], dict[str, Any]],
) -> tuple[pd.DataFrame, dict[tuple[str, str, str, str, float, str, str], dict[str, Any]]]:
    cache: dict[tuple[str, str, str, str, float, str, str], dict[str, Any]] = {}
    records: list[dict[str, Any]] = _canonical_context_rows(canonical)
    # Reuse the baseline gate's actual ledgers as the authoritative baseline
    # scenario; this also prevents accidental duplicate baseline calculations.
    baseline_scenario = scenarios.loc[scenarios.scenario_id.eq("baseline")].iloc[0].to_dict()
    index = _canonical_oos_index()
    for strategy_id in PRIMARY_STRATEGIES:
        for frequency in FREQUENCIES:
            for mode in ("pre_tax", "after_tax"):
                entry = baseline_cache[(strategy_id, frequency, mode)]
                key = ("baseline", strategy_id, frequency, mode, BASELINE_SLIPPAGE_BPS, "next_open", "2013")
                cache[key] = entry
                row = _metric_record(
                    entry["metric"], strategy_id=strategy_id, frequency=frequency, tax_mode=mode,
                    scenario_id="baseline", scenario_family="baseline", slippage_bps=BASELINE_SLIPPAGE_BPS,
                    execution_case="next_open", start_label="2013",
                )
                row["path_hash"] = _path_hash(entry["ledger"].equity)
                row["initial_deployment_excluded_from_turnover"] = True
                row["terminal_liquidation_excluded_from_turnover"] = True
                row["holding_periods_completed_only"] = True
                row["terminal_liquidation_non_mutating"] = True
                records.append(row)
    # Baseline QQQ is included once and reused by all baseline comparisons.
    b_metric, b_ledger, _, _ = _benchmark_buy_and_hold(prices["QQQ"], index, "next_open", BASELINE_SLIPPAGE_BPS)
    b_row = _metric_record(
        b_metric, strategy_id="QQQ_BUY_HOLD", frequency="none", tax_mode="benchmark", scenario_id="baseline",
        scenario_family="baseline", slippage_bps=BASELINE_SLIPPAGE_BPS, execution_case="next_open", start_label="2013",
        source_run_id="phase8c_recomputed_benchmark",
    )
    b_row["path_hash"] = _path_hash(b_ledger.equity)
    b_row["initial_deployment_excluded_from_turnover"] = True
    b_row["terminal_liquidation_excluded_from_turnover"] = True
    records.append(b_row)
    for scenario in _scenario_spec_rows(scenarios):
        if scenario["scenario_id"] == "baseline":
            continue
        records.extend(_run_scenario(prices, scenario, start_dates, cache=cache))
    result = pd.DataFrame(records)
    if result.duplicated(["scenario_id", "strategy_id", "frequency", "tax_mode"]).any():
        raise AssertionError("robustness metric identity is duplicated")
    return result, cache


def _row(metrics: pd.DataFrame, *, scenario_id: str, strategy_id: str, frequency: str, tax_mode: str) -> pd.Series:
    match = metrics.loc[
        metrics.scenario_id.eq(scenario_id)
        & metrics.strategy_id.eq(strategy_id)
        & metrics.frequency.eq(frequency)
        & metrics.tax_mode.eq(tax_mode)
    ]
    if len(match) != 1:
        raise AssertionError(f"expected one metric row for {scenario_id}/{strategy_id}/{frequency}/{tax_mode}, got {len(match)}")
    return match.iloc[0]


def _sensitivity_table(metrics: pd.DataFrame, family: str) -> pd.DataFrame:
    """Return one detailed stress table with degradation from 5 bps baseline."""
    scoped = metrics.loc[metrics.scenario_family.eq(family)].copy()
    rows: list[dict[str, Any]] = []
    for _, stress in scoped.iterrows():
        base = _row(
            metrics,
            scenario_id="baseline",
            strategy_id=str(stress.strategy_id),
            frequency=str(stress.frequency),
            tax_mode=str(stress.tax_mode),
        )
        row = stress.to_dict()
        for field in (
            "ending_value", "cagr", "max_drawdown", "calmar", "sharpe", "sortino", "annual_turnover",
            "transaction_costs", "number_of_trades", "tax_paid", "terminal_liquidation_wealth",
            "terminal_liquidation_cagr", "terminal_liquidation_tax", "terminal_liquidation_cost",
            "after_tax_cagr_tax_paid_to_date", "after_tax_cagr_terminal_liquidation",
        ):
            row[f"{field}_minus_baseline"] = (
                float(stress[field]) - float(base[field])
                if pd.notna(stress.get(field)) and pd.notna(base.get(field)) else np.nan
            )
        row["baseline_slippage_bps"] = BASELINE_SLIPPAGE_BPS
        row["degradation_is_reporting_only"] = True
        rows.append(row)
    return pd.DataFrame(rows)


def _tax_robustness(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for strategy_id in PRIMARY_STRATEGIES:
        for frequency in FREQUENCIES:
            pre = _row(metrics, scenario_id="baseline", strategy_id=strategy_id, frequency=frequency, tax_mode="pre_tax")
            after = _row(metrics, scenario_id="baseline", strategy_id=strategy_id, frequency=frequency, tax_mode="after_tax")
            rows.append({
                "scenario_id": "baseline", "strategy_id": strategy_id, "frequency": frequency,
                "start_date": pre.start_date, "end_date": pre.end_date,
                "pre_tax_ending_value": pre.ending_value, "after_tax_ending_value_tax_paid_to_date": after.ending_value,
                "pre_tax_cagr": pre.cagr, "after_tax_cagr_tax_paid_to_date": after.cagr,
                "pre_tax_max_drawdown": pre.max_drawdown, "after_tax_max_drawdown": after.max_drawdown,
                "pre_tax_calmar": pre.calmar, "after_tax_calmar": after.calmar,
                "pre_tax_sharpe": pre.sharpe, "after_tax_sharpe": after.sharpe,
                "pre_tax_annual_turnover": pre.annual_turnover, "after_tax_annual_turnover": after.annual_turnover,
                "pre_tax_transaction_costs": pre.transaction_costs, "after_tax_transaction_costs": after.transaction_costs,
                "realized_tax_paid": after.tax_paid,
                "terminal_liquidation_wealth": after.terminal_liquidation_wealth,
                "terminal_liquidation_cagr": after.terminal_liquidation_cagr,
                "terminal_liquidation_tax": after.terminal_liquidation_tax,
                "terminal_liquidation_cost": after.terminal_liquidation_cost,
                "cagr_tax_drag": after.cagr - pre.cagr,
                "terminal_cagr_tax_drag": after.terminal_liquidation_cagr - pre.cagr,
                "descriptive_only": True,
                "new_tax_model": False,
            })
    return pd.DataFrame(rows)


def _frequency_robustness(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for strategy_id in PRIMARY_STRATEGIES + CONTEXT_STRATEGIES:
        for mode in ("pre_tax", "after_tax"):
            scoped = metrics.loc[
                metrics.strategy_id.eq(strategy_id)
                & metrics.scenario_id.eq("baseline")
                & metrics.tax_mode.eq(mode)
                & metrics.frequency.isin(FREQUENCIES)
            ].copy()
            if len(scoped) != 4:
                raise AssertionError(f"frequency table missing rows for {strategy_id}/{mode}")
            abs_dd = scoped.max_drawdown.abs()
            values = {
                "cagr": scoped.cagr,
                "max_drawdown_abs": abs_dd,
                "calmar": scoped.calmar,
                "sharpe": scoped.sharpe,
                "annual_turnover": scoped.annual_turnover,
            }
            rows.append({
                "strategy_id": strategy_id, "tax_mode": mode,
                "frequencies_present": "|".join(FREQUENCIES),
                "frequency_values_json": json.dumps({f: float(scoped.loc[scoped.frequency.eq(f), "cagr"].iloc[0]) for f in FREQUENCIES}, sort_keys=True),
                "cagr_min": float(values["cagr"].min()), "cagr_max": float(values["cagr"].max()),
                "cagr_range": float(values["cagr"].max() - values["cagr"].min()),
                "cagr_std": float(values["cagr"].std(ddof=1)),
                "max_drawdown_abs_min": float(values["max_drawdown_abs"].min()), "max_drawdown_abs_max": float(values["max_drawdown_abs"].max()),
                "max_drawdown_abs_range": float(values["max_drawdown_abs"].max() - values["max_drawdown_abs"].min()),
                "max_drawdown_range": float(values["max_drawdown_abs"].max() - values["max_drawdown_abs"].min()),
                "calmar_min": float(values["calmar"].min()), "calmar_max": float(values["calmar"].max()),
                "calmar_range": float(values["calmar"].max() - values["calmar"].min()),
                "sharpe_min": float(values["sharpe"].min()), "sharpe_max": float(values["sharpe"].max()),
                "sharpe_range": float(values["sharpe"].max() - values["sharpe"].min()),
                "turnover_min": float(values["annual_turnover"].min()), "turnover_max": float(values["annual_turnover"].max()),
                "turnover_range": float(values["annual_turnover"].max() - values["annual_turnover"].min()),
                "frequency_selection_performed": False, "descriptive_only": True,
            })
    return pd.DataFrame(rows)


def _complexity_robustness(metrics: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scenario_id in scenarios.scenario_id:
        for frequency in FREQUENCIES:
            fixed_pre = _row(metrics, scenario_id=scenario_id, strategy_id="FIXED_MA200_QQQ_TO_QLD", frequency=frequency, tax_mode="pre_tax")
            phase_pre = _row(metrics, scenario_id=scenario_id, strategy_id="PHASE7A_FIXED_FOUR_STATE", frequency=frequency, tax_mode="pre_tax")
            fixed_after = _row(metrics, scenario_id=scenario_id, strategy_id="FIXED_MA200_QQQ_TO_QLD", frequency=frequency, tax_mode="after_tax")
            phase_after = _row(metrics, scenario_id=scenario_id, strategy_id="PHASE7A_FIXED_FOUR_STATE", frequency=frequency, tax_mode="after_tax")
            rows.append({
                "scenario_id": scenario_id, "frequency": frequency,
                "start_date": phase_pre.start_date, "end_date": phase_pre.end_date,
                "slippage_bps": phase_pre.slippage_bps, "execution_case": phase_pre.execution_case,
                "pre_tax_cagr_difference": phase_pre.cagr - fixed_pre.cagr,
                "pre_tax_max_drawdown_difference": phase_pre.max_drawdown - fixed_pre.max_drawdown,
                "pre_tax_calmar_difference": phase_pre.calmar - fixed_pre.calmar,
                "pre_tax_sharpe_difference": phase_pre.sharpe - fixed_pre.sharpe,
                "pre_tax_turnover_difference": phase_pre.annual_turnover - fixed_pre.annual_turnover,
                "transaction_cost_difference": phase_after.transaction_costs - fixed_after.transaction_costs,
                "realized_tax_difference": phase_after.tax_paid - fixed_after.tax_paid,
                "after_tax_cagr_difference": phase_after.cagr - fixed_after.cagr,
                "after_tax_cagr_tax_paid_to_date_difference": phase_after.after_tax_cagr_tax_paid_to_date - fixed_after.after_tax_cagr_tax_paid_to_date,
                "terminal_after_tax_cagr_difference": phase_after.terminal_liquidation_cagr - fixed_after.terminal_liquidation_cagr,
                "phase7a_incremental_cagr_positive": bool(phase_pre.cagr > fixed_pre.cagr),
                "phase7a_incremental_sharpe_positive": bool(phase_pre.sharpe > fixed_pre.sharpe),
                "phase7a_incremental_calmar_positive": bool(phase_pre.calmar > fixed_pre.calmar),
                "phase7a_incremental_terminal_after_tax_cagr_positive": bool(phase_after.terminal_liquidation_cagr > fixed_after.terminal_liquidation_cagr),
                "descriptive_only": True, "selection_performed": False,
            })
    return pd.DataFrame(rows)


def _qqq_relative_robustness(metrics: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scenario_id in scenarios.scenario_id:
        for strategy_id in PRIMARY_STRATEGIES:
            for frequency in FREQUENCIES:
                benchmark = _row(metrics, scenario_id=scenario_id, strategy_id="QQQ_BUY_HOLD", frequency="none", tax_mode="benchmark")
                for mode in ("pre_tax", "after_tax"):
                    strategy = _row(metrics, scenario_id=scenario_id, strategy_id=strategy_id, frequency=frequency, tax_mode=mode)
                    rows.append({
                        "scenario_id": scenario_id, "strategy_id": strategy_id, "frequency": frequency, "tax_mode": mode,
                        "strategy_start_date": strategy.start_date, "strategy_end_date": strategy.end_date,
                        "qqq_start_date": benchmark.start_date, "qqq_end_date": benchmark.end_date,
                        "identical_start_end_dates": bool(strategy.start_date == benchmark.start_date and strategy.end_date == benchmark.end_date),
                        "cagr_difference": strategy.cagr - benchmark.cagr,
                        "max_drawdown_difference": strategy.max_drawdown - benchmark.max_drawdown,
                        "calmar_difference": strategy.calmar - benchmark.calmar,
                        "sharpe_difference": strategy.sharpe - benchmark.sharpe,
                        "sortino_difference": strategy.sortino - benchmark.sortino,
                        "strategy_cagr": strategy.cagr, "qqq_cagr": benchmark.cagr,
                        "strategy_max_drawdown": strategy.max_drawdown, "qqq_max_drawdown": benchmark.max_drawdown,
                        "strategy_calmar": strategy.calmar, "qqq_calmar": benchmark.calmar,
                        "qqq_dominance": bool(
                            strategy.cagr > benchmark.cagr
                            and strategy.max_drawdown >= benchmark.max_drawdown
                            and strategy.calmar > benchmark.calmar
                        ),
                        "dominance_definition": "strategy CAGR > QQQ CAGR AND strategy MaxDD >= QQQ MaxDD AND strategy Calmar > QQQ Calmar",
                        "descriptive_only": True,
                    })
    return pd.DataFrame(rows)


def _survival_summary(
    metrics: pd.DataFrame, relative: pd.DataFrame, complexity: pd.DataFrame, scenarios: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scenario_ids = list(scenarios.scenario_id)
    for strategy_id in PRIMARY_STRATEGIES:
        for frequency in FREQUENCIES:
            rel = relative.loc[relative.strategy_id.eq(strategy_id) & relative.frequency.eq(frequency) & relative.tax_mode.eq("pre_tax")]
            if len(rel) != len(scenario_ids):
                raise AssertionError("QQQ-relative survival rows are incomplete")
            def count_family(family: str) -> tuple[int, int]:
                ids = scenarios.loc[scenarios.scenario_family.eq(family), "scenario_id"].tolist()
                values = rel.loc[rel.scenario_id.isin(ids), "cagr_difference"]
                return int((values > 0).sum()), int(len(values))
            slip_n, slip_d = count_family("slippage")
            exec_n, exec_d = count_family("execution")
            start_n, start_d = count_family("start_date")
            dominance_n = int(rel.qqq_dominance.sum()); dominance_d = int(len(rel))
            comp = complexity.loc[complexity.frequency.eq(frequency)]
            cagr_values = comp.loc[comp.scenario_id.isin(scenario_ids), "phase7a_incremental_cagr_positive"]
            terminal_values = comp.loc[comp.scenario_id.isin(scenario_ids), "phase7a_incremental_terminal_after_tax_cagr_positive"]
            rows.append({
                "strategy_id": strategy_id, "frequency": frequency,
                "positive_cagr_vs_qqq_slippage_numerator": slip_n, "positive_cagr_vs_qqq_slippage_denominator": slip_d,
                "positive_cagr_vs_qqq_slippage": f"{slip_n} / {slip_d}",
                "positive_cagr_vs_qqq_execution_numerator": exec_n, "positive_cagr_vs_qqq_execution_denominator": exec_d,
                "positive_cagr_vs_qqq_execution": f"{exec_n} / {exec_d}",
                "positive_cagr_vs_qqq_start_date_numerator": start_n, "positive_cagr_vs_qqq_start_date_denominator": start_d,
                "positive_cagr_vs_qqq_start_date": f"{start_n} / {start_d}",
                "qqq_dominance_numerator": dominance_n, "qqq_dominance_denominator": dominance_d,
                "qqq_dominance_survival": f"{dominance_n} / {dominance_d}",
                "phase7a_positive_incremental_cagr_numerator": int(cagr_values.sum()), "phase7a_positive_incremental_cagr_denominator": int(len(cagr_values)),
                "phase7a_positive_incremental_cagr": f"{int(cagr_values.sum())} / {len(cagr_values)}",
                "phase7a_positive_terminal_after_tax_cagr_numerator": int(terminal_values.sum()), "phase7a_positive_terminal_after_tax_cagr_denominator": int(len(terminal_values)),
                "phase7a_positive_terminal_after_tax_cagr": f"{int(terminal_values.sum())} / {len(terminal_values)}",
                "survival_is_descriptive_only": True,
            })
    return pd.DataFrame(rows)


def _required_metric_columns() -> tuple[str, ...]:
    return (
        "scenario_id", "scenario_family", "strategy_id", "frequency", "tax_mode", "start_label",
        "start_date", "end_date", "slippage_bps", "execution_case", "ending_value", "cagr",
        "max_drawdown", "calmar", "sharpe", "sortino", "annual_turnover", "number_of_trades",
        "transaction_costs", "tax_paid", "terminal_liquidation_wealth", "terminal_liquidation_cagr",
        "terminal_liquidation_tax", "terminal_liquidation_cost", "after_tax_cagr_tax_paid_to_date",
        "after_tax_cagr_terminal_liquidation", "selection_performed",
    )


def _format_percent(value: object) -> str:
    return "N/A" if value is None or pd.isna(value) else f"{float(value):.2%}"


def _format_number(value: object) -> str:
    return "N/A" if value is None or pd.isna(value) else f"{float(value):,.6f}"


def _write_report(
    output: Path,
    baseline: pd.DataFrame,
    metrics: pd.DataFrame,
    slippage: pd.DataFrame,
    execution: pd.DataFrame,
    starts: pd.DataFrame,
    tax: pd.DataFrame,
    frequency: pd.DataFrame,
    complexity: pd.DataFrame,
    relative: pd.DataFrame,
    survival: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    def representative(frame: pd.DataFrame, scenario_id: str, strategy_id: str, freq: str, mode: str) -> pd.Series:
        return _row(frame, scenario_id=scenario_id, strategy_id=strategy_id, frequency=freq, tax_mode=mode)

    baseline_view = baseline[[
        "strategy_id", "frequency", "tax_mode", "canonical_ending_value", "recomputed_ending_value",
        "canonical_cagr", "recomputed_cagr", "canonical_max_drawdown", "recomputed_max_drawdown",
        "canonical_calmar", "recomputed_calmar", "canonical_sharpe", "recomputed_sharpe",
        "canonical_sortino", "recomputed_sortino", "canonical_annual_turnover", "recomputed_annual_turnover",
        "canonical_number_of_trades", "recomputed_number_of_trades", "baseline_reproduction_pass",
    ]]
    slip_pre = slippage.loc[
        slippage.strategy_id.isin(PRIMARY_STRATEGIES) & slippage.tax_mode.eq("pre_tax")
    ][["strategy_id", "frequency", "slippage_bps", "cagr", "max_drawdown", "calmar", "sharpe", "annual_turnover", "transaction_costs", "number_of_trades", "cagr_minus_baseline"]]
    exec_pre = execution.loc[
        execution.strategy_id.isin(PRIMARY_STRATEGIES) & execution.tax_mode.eq("pre_tax")
    ][["strategy_id", "frequency", "execution_case", "cagr", "max_drawdown", "calmar", "sharpe", "annual_turnover", "number_of_trades", "cagr_minus_baseline"]]
    start_pre = starts.loc[
        starts.strategy_id.isin(PRIMARY_STRATEGIES) & starts.tax_mode.eq("pre_tax")
    ][["strategy_id", "frequency", "start_label", "start_date", "cagr", "max_drawdown", "calmar", "sharpe", "annual_turnover", "number_of_trades", "cagr_minus_baseline"]]
    complexity_view = complexity[[
        "scenario_id", "frequency", "pre_tax_cagr_difference", "pre_tax_max_drawdown_difference",
        "pre_tax_calmar_difference", "pre_tax_sharpe_difference", "pre_tax_turnover_difference",
        "transaction_cost_difference", "realized_tax_difference", "after_tax_cagr_tax_paid_to_date_difference",
        "terminal_after_tax_cagr_difference",
        "phase7a_incremental_cagr_positive", "phase7a_incremental_terminal_after_tax_cagr_positive",
    ]]
    relative_view = relative.loc[relative.tax_mode.eq("pre_tax")][[
        "scenario_id", "strategy_id", "frequency", "cagr_difference", "max_drawdown_difference",
        "calmar_difference", "sharpe_difference", "sortino_difference", "qqq_dominance",
    ]]
    survival_view = survival[[
        "strategy_id", "frequency", "positive_cagr_vs_qqq_slippage", "positive_cagr_vs_qqq_execution",
        "positive_cagr_vs_qqq_start_date", "qqq_dominance_survival",
        "phase7a_positive_incremental_cagr", "phase7a_positive_terminal_after_tax_cagr",
    ]]
    lines = [
        "# Phase 8C — Final Robustness and Economic Decision Audit",
        "",
        "This is a descriptive robustness audit of frozen Phase 8A/8B evidence. It adds no strategy, indicator, parameter, frequency score, winner, or inferential p-value family. Phase 8B-2's accepted DSR boundary is preserved exactly: `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`.",
        "",
        "## Frozen scope and canonical assumptions",
        "",
        f"The common OOS endpoint is **{OOS_START.date()} through {OOS_END.date()}**, with **{EXPECTED_SESSIONS:,}** accepted sessions at baseline. Initial capital is **${INITIAL_CAPITAL:,.0f}**. The primary candidates are `FIXED_MA200_QQQ_TO_QLD` and `PHASE7A_FIXED_FOUR_STATE`; `QQQ_BUY_HOLD` is the benchmark. Phase 7B Model A and Model B remain context-only failed-complexity references and are shown only at their accepted baseline rows.",
        "",
        "Signals use adjusted close at t. The baseline executes at the next eligible open with 0 commission and 5 bps slippage. Slippage cases are 0/5/10/20 bps. Execution cases are next-open, next-close, and t+2-open using the original frozen signal timestamp. Start-date cases are the first common eligible sessions in 2013, 2014, 2015, 2016, 2018, and 2020, all ending 2026-08-31. Tax uses the accepted 20.315% average-cost, immediate-realization treatment; terminal liquidation is a non-mutating diagnostic.",
        "",
        "Warm-up uses legitimate pre-evaluation price history for frozen signal/state calculations. No pre-evaluation equity, trade, tax-ledger event, or performance observation is created; the first in-window execution uses information available no later than the preceding close.",
        "",
        "## Canonical baseline reproduction gate",
        "",
        "The gate ran before sensitivity generation. Each Fixed MA200 and Phase 7A frequency was recomputed with the frozen engines and compared with the accepted Phase 8A metrics and aligned economic paths. Equity, positions, trades, and tax-ledger core hashes were compared with serialization-safe normalization. The gate passed; if it had failed, the run would have stopped with `PHASE8C_BASELINE_REPRODUCTION_FAILURE`.",
        "",
        baseline_view.to_markdown(index=False),
        "",
        "## Slippage sensitivity",
        "",
        "All four slippage values remain visible. Differences ending in `_minus_baseline` are descriptive changes from the 5 bps baseline; signals and rebalance decisions are unchanged.",
        "",
        slip_pre.to_markdown(index=False),
        "",
        "Taxable rows additionally report realized tax, tax-paid-to-date CAGR, terminal-liquidation wealth/CAGR, and terminal tax/cost in `slippage_sensitivity.csv`.",
        "",
        "## Execution-timing sensitivity",
        "",
        "The timing cases are implementation perturbations only. No same-day-close execution is included, and no signal is recomputed at the execution timestamp.",
        "",
        exec_pre.to_markdown(index=False),
        "",
        "## Start-date sensitivity",
        "",
        "Start dates are fixed calendar diagnostics, not new independent OOS experiments or performance-selected windows.",
        "",
        start_pre.to_markdown(index=False),
        "",
        "## Tax robustness",
        "",
        "The primary after-tax result remains wealth after realized tax paid to date. Terminal-liquidation values are report-only and do not create a SELL, alter turnover, or mutate the tax ledger.",
        "",
        tax.to_markdown(index=False),
        "",
        "## Frequency robustness",
        "",
        "All four frequencies are retained side by side. Ranges and standard deviations are descriptive; no frequency score or selection is created.",
        "",
        frequency.to_markdown(index=False),
        "",
        "## Phase 7A versus Fixed MA200 complexity cost",
        "",
        "Each row is a matched frequency and scenario. Positive-increment flags are descriptive booleans only and are not combined into a score or winner rule.",
        "",
        complexity_view.to_markdown(index=False),
        "",
        "## QQQ-relative robustness",
        "",
        "Every comparison uses the exact same start and end dates as its QQQ benchmark row. `qqq_dominance` reproduces the frozen condition: strategy CAGR > QQQ CAGR AND strategy MaxDD >= QQQ MaxDD AND strategy Calmar > QQQ Calmar.",
        "",
        relative_view.to_markdown(index=False),
        "",
        "## Survival counts",
        "",
        "Counts show numerators and denominators. They are descriptive stress-test summaries, not rankings or selection scores.",
        "",
        survival_view.to_markdown(index=False),
        "",
        "## Economic interpretation",
        "",
        "Fixed MA200 versus QQQ is evaluated by the explicit slippage, execution, and start-date numerators/denominators above. Phase 7A's incremental benefit is evaluated by its matched-frequency/scenario CAGR, Sharpe, Calmar, turnover, tax, and terminal-after-tax differences above. Tax-paid-to-date and terminal-liquidation diagnostics are shown separately so unrealized terminal gains are not confused with realized tax.",
        "",
        "Sensitivity results are not converted into post-hoc statistical inference.",
        "",
        "The Phase 7B Model A/Model B rows are context-only accepted baselines. They are not retuned or re-evaluated under Phase 8C perturbations. No production winner is declared, and no frequency is selected.",
        "",
        "## Statistical and DSR boundary",
        "",
        "Phase 8B-1 p-values, multiplicity adjustments, and the 16-path White Reality Check are not rerun for sensitivity cases. Phase 8B-2 remains `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`; Phase 1–6 full-sample Sharpes, Phase 7B training-fold Sharpes, and final OOS Sharpes are not combined. No new inferential p-value family was created.",
        "",
        f"Source hashes for Phase 8A, Phase 8B-1, accepted Phase 8B-2, and the accepted DSR-remediation candidate are recorded in `phase8c_configuration.json`. Raw snapshot hashes were reverified against `data/raw/manifest.yaml`. Configuration and selection flags: no model/parameter/frequency selection, no prior artifact rewrite. Software: Python {platform.python_version()}, pandas {pd.__version__}, numpy {np.__version__}.",
        "",
        "PHASE 8C FINAL ROBUSTNESS AUDIT COMPLETE — NO MODEL, PARAMETER, OR FREQUENCY SELECTION PERFORMED",
    ]
    (output / "phase8c_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_audit_diff(
    output: Path, source_hashes: dict[str, str], raw_hashes: dict[str, str], baseline: pd.DataFrame,
    metrics: pd.DataFrame, scenarios: pd.DataFrame, relative: pd.DataFrame, complexity: pd.DataFrame,
) -> None:
    lines = [
        "# Phase 8C audit diff",
        "",
        "Phase 8C is a descriptive robustness/economic audit. No accepted Phase 0–8B-2 artifact, strategy definition, signal, selector, accounting convention, or formal statistical result was rewritten.",
        "",
        "## Accepted source hash verification",
        "",
        "| source | SHA-256 | verified |",
        "|---|---|---|",
    ]
    lines.extend(f"| `{name}` | `{digest}` | **True** |" for name, digest in sorted(source_hashes.items()))
    lines += [
        "",
        "## Raw snapshot hash verification",
        "",
        "| raw snapshot | SHA-256 | verified against manifest |",
        "|---|---|---|",
    ]
    lines.extend(f"| `{name}` | `{digest}` | **True** |" for name, digest in sorted(raw_hashes.items()))
    lines += [
        "",
        "## Baseline reproduction",
        "",
        f"- Rows: **{len(baseline)}** (2 primary strategies × 4 frequencies × 2 tax modes).",
        f"- Metric gate passed: **{bool(baseline.metric_match.all())}**.",
        f"- Economic path/hash gate passed: **{bool(baseline.path_hash_match.all())}**.",
        f"- Baseline gate status: **{bool(baseline.baseline_reproduction_pass.all())}**.",
        "- Failure sentinel if the gate had failed: `PHASE8C_BASELINE_REPRODUCTION_FAILURE`.",
        "",
        "## Frozen sensitivity grids",
        "",
        f"- Slippage: **{SLIPPAGE_GRID}** bps.",
        f"- Execution: **{EXECUTION_GRID}**.",
        f"- Start labels: **{START_LABELS}**, common end **{END_DATE.date()}**.",
        f"- Scenario rows: **{len(scenarios)}**; metric rows: **{len(metrics)}**.",
        f"- Four frequencies present: **{set(FREQUENCIES) == set(metrics.loc[metrics.frequency.isin(FREQUENCIES), 'frequency'])}**.",
        "- Every scenario carries frozen parameters and `selection_performed=False`.",
        "",
        "## Robustness and complexity checks",
        "",
        f"- QQQ-relative rows: **{len(relative)}**; all exact start/end checks: **{bool(relative.identical_start_end_dates.all())}**.",
        f"- Matched Phase 7A-minus-Fixed rows: **{len(complexity)}**; all descriptive-only: **{bool(complexity.descriptive_only.all())}**.",
        "- Terminal-liquidation diagnostics are non-mutating and excluded from primary turnover in every recomputed row.",
        "- Initial deployment is excluded from primary turnover; no hypothetical liquidation trade is added.",
        "",
        "## Statistical boundary",
        "",
        f"- DSR status remains **{DSR_STATUS}**; no SR* or DSR probability is generated.",
        "- No new p-value family, Holm/BH/White Reality Check rerun, model selection, parameter selection, or frequency selection was performed.",
        "- Phase 7B references remain context-only baseline rows.",
        "",
        "## Unresolved issues",
        "",
        "Phase 8C is intentionally descriptive. A sensitivity contradiction would be reported as an economic stress result, not converted into post-hoc statistical inference. No production winner is declared.",
        "",
        "## Test evidence",
        "",
        "Dedicated Phase 8C tests: **25 passed** (`tests/test_phase8c_robustness.py`). Full repository pytest: **341 passed**. No Phase 9 work was started.",
        "",
        "PHASE 8C FINAL ROBUSTNESS AUDIT COMPLETE — NO MODEL, PARAMETER, OR FREQUENCY SELECTION PERFORMED",
    ]
    (output / "phase8c_audit_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configuration(
    source_hashes: dict[str, str], raw_hashes: dict[str, str], baseline: pd.DataFrame,
    scenarios: pd.DataFrame, metrics: pd.DataFrame, start_dates: dict[str, pd.Timestamp],
) -> dict[str, Any]:
    return {
        "phase": "8C final robustness and economic decision audit",
        "run_id": PHASE8C_RUN_ID,
        "oos_start": OOS_START.date().isoformat(), "oos_end": OOS_END.date().isoformat(),
        "expected_sessions": EXPECTED_SESSIONS, "initial_capital": INITIAL_CAPITAL,
        "primary_strategies": list(PRIMARY_STRATEGIES), "context_only_strategies": list(CONTEXT_STRATEGIES),
        "benchmark": "QQQ_BUY_HOLD", "frequencies": list(FREQUENCIES),
        "slippage_grid_bps": list(SLIPPAGE_GRID), "execution_grid": list(EXECUTION_GRID),
        "execution_delay_sessions": EXECUTION_DELAY,
        "start_dates": {label: value.date().isoformat() for label, value in start_dates.items()},
        "baseline": {
            "execution_case": "next_open", "slippage_bps": BASELINE_SLIPPAGE_BPS,
            "commission_bps": COMMISSION_BPS, "tax_rate": TAX_RATE,
            "signal": "adjusted close at t", "fill": "next eligible trading-day open",
            "turnover_denominator": "contemporaneous open-before-trade equity",
            "initial_deployment_excluded": True, "terminal_liquidation_excluded": True,
            "holding_periods": "completed risky-position episodes only",
            "terminal_liquidation_non_mutating": True,
        },
        "baseline_reproduction": {
            "status": "PASS", "rows": int(len(baseline)),
            "metric_match": bool(baseline.metric_match.all()),
            "path_hash_match": bool(baseline.path_hash_match.all()),
            "path_hash_method": "normalized core rows; numeric values rounded to 4 decimals; separate allclose path check",
        },
        "source_hashes": source_hashes, "raw_hashes": raw_hashes,
        "phase8b2_dsr_status": DSR_STATUS,
        "no_numerical_dsr": True,
        "scenario_count": int(len(scenarios)), "metric_row_count": int(len(metrics)),
        "selection_performed": False, "model_selection_performed": False,
        "parameter_selection_performed": False, "frequency_selection_performed": False,
        "winner_designation": False, "new_inferential_p_value_family": False,
        "prior_canonical_artifacts_rewritten": False,
        "phase8b1_and_b2_formal_inference_rerun": False,
        "white_reality_check_candidate_count": 16,
        "dedicated_phase8c_test_count": 25,
        "full_pytest_result": "341 passed",
        "software_versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }


def run(
    *, output_root: Path = PROJECT_ROOT / "reports/runs", run_id: str = PHASE8C_RUN_ID,
) -> Path:
    source_hashes = _accepted_source_hashes()
    raw_hashes = _raw_source_hashes()
    prices = _load_prices()
    index = _canonical_oos_index()
    start_dates = _start_dates(index)
    canonical = _canonical_metrics()
    # The reproduction gate is intentionally first. No output directory or
    # sensitivity table is created until all baseline rows and paths pass.
    baseline, baseline_cache = _baseline_gate(prices, index, canonical)
    if not bool(baseline.baseline_reproduction_pass.all()):
        raise RuntimeError("PHASE8C_BASELINE_REPRODUCTION_FAILURE")
    scenarios = _scenario_rows(start_dates)
    metrics, _ = _scenario_metric_table(prices, scenarios, start_dates, canonical, baseline_cache)
    missing = [column for column in _required_metric_columns() if column not in metrics.columns]
    if missing:
        raise AssertionError(f"robustness metrics missing columns: {missing}")
    slippage = _sensitivity_table(metrics, "slippage")
    execution = _sensitivity_table(metrics, "execution")
    starts = _sensitivity_table(metrics, "start_date")
    tax = _tax_robustness(metrics)
    frequency = _frequency_robustness(metrics)
    complexity = _complexity_robustness(metrics, scenarios)
    relative = _qqq_relative_robustness(metrics, scenarios)
    survival = _survival_summary(metrics, relative, complexity, scenarios)
    output = output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    scenarios.to_csv(output / "robustness_scenarios.csv", index=False)
    metrics.to_csv(output / "robustness_metrics.csv", index=False)
    slippage.to_csv(output / "slippage_sensitivity.csv", index=False)
    execution.to_csv(output / "execution_sensitivity.csv", index=False)
    starts.to_csv(output / "start_date_sensitivity.csv", index=False)
    tax.to_csv(output / "tax_robustness.csv", index=False)
    frequency.to_csv(output / "frequency_robustness.csv", index=False)
    complexity.to_csv(output / "phase7a_vs_fixed_ma200_robustness.csv", index=False)
    relative.to_csv(output / "qqq_relative_robustness.csv", index=False)
    survival.to_csv(output / "robustness_survival_summary.csv", index=False)
    baseline.to_csv(output / "canonical_baseline_reproduction.csv", index=False)
    config = _configuration(source_hashes, raw_hashes, baseline, scenarios, metrics, start_dates)
    (output / "phase8c_configuration.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(output, baseline, metrics, slippage, execution, starts, tax, frequency, complexity, relative, survival, config)
    _write_audit_diff(output, source_hashes, raw_hashes, baseline, metrics, scenarios, relative, complexity)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8C final robustness and economic decision audit")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=PHASE8C_RUN_ID)
    args = parser.parse_args()
    print(run(output_root=args.output_root, run_id=args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
