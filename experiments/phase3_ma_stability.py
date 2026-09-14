from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.phase2_ma200 import (  # noqa: E402
    FREQUENCIES,
    STRATEGIES,
    _add_pretrade_equity,
    _turnover_audit,
)
from market_timing_quant.configuration import load_config  # noqa: E402
from market_timing_quant.data import run_data_audit  # noqa: E402
from market_timing_quant.metrics import drawdown_series, performance_metrics  # noqa: E402
from market_timing_quant.portfolio import buy_and_hold, single_asset_timed_backtest  # noqa: E402
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open  # noqa: E402

MA_WINDOWS = (150, 175, 200, 225, 250)
RULE_FAMILIES = {
    "QQQ_MA200_QQQ": "QQQ_MA_QQQ",
    "QQQ_MA200_QLD": "QQQ_MA_QLD",
    "SPY_MA200_SSO": "SPY_MA_SSO",
}
TURNOVER_AUDIT_KEYS = {
    ("QQQ_MA200_QQQ", "weekly"),
    ("QQQ_MA200_QQQ", "monthly"),
    ("QQQ_MA200_QLD", "weekly"),
    ("SPY_MA200_SSO", "monthly"),
}
METRIC_FIELDS = (
    "start", "end", "ending_value", "total_return", "cagr", "max_drawdown", "sharpe", "sortino",
    "calmar", "ulcer_index", "number_of_trades", "annual_turnover", "mean_holding_period_days",
    "median_holding_period_days", "max_holding_period_days", "transaction_costs", "tax_paid",
)
TERMINAL_FIELDS = (
    "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
    "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
)


def parameter_grid() -> tuple[int, ...]:
    """The intentionally evaluated, frozen Phase 3 stability grid."""
    return MA_WINDOWS


def rule_family(legacy_rule: str) -> str:
    return RULE_FAMILIES[legacy_rule]


def strategy_identifier(legacy_rule: str, frequency: str, ma_window: int) -> str:
    return f"{rule_family(legacy_rule)}_{frequency}_MA{ma_window}"


def _warmup_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows = []
    for window in MA_WINDOWS:
        for asset in ("QQQ", "SPY"):
            frame = prices[asset]
            decision = ma_trend_decision(frame["adjusted_close"], lookback=window)
            lookback = frame.loc[:start].tail(window)
            held = "QQQ" if asset == "QQQ" else "SSO"
            signal_index = frame.loc[start:end].index
            held_index = prices[held].loc[start:end].index
            rows.append({
                "signal_asset": asset,
                "ma_window": window,
                "signal_rows_full": int(len(frame)),
                "pre_start_warmup_rows": int((frame.index < start).sum()),
                "lookback_observations_at_start": int(len(lookback)),
                "lookback_start_at_evaluation": str(lookback.index[0].date()),
                "lookback_end_at_evaluation": str(lookback.index[-1].date()),
                "first_valid_ma_date": str(decision.index[window - 1].date()),
                "evaluation_start": str(start.date()),
                "evaluation_end": str(end.date()),
                "missing_aligned_targets": int(len(held_index.difference(signal_index))),
            })
    return rows


def _alignment_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows = []
    for legacy_rule, (signal_asset, held_asset) in STRATEGIES.items():
        signal_index = prices[signal_asset].loc[start:end].index
        held_index = prices[held_asset].loc[start:end].index
        rows.append({
            "rule_family": rule_family(legacy_rule),
            "signal_asset": signal_asset,
            "held_asset": held_asset,
            "signal_calendar_rows": int(len(signal_index)),
            "held_calendar_rows": int(len(held_index)),
            "common_evaluation_rows": int(len(signal_index.intersection(held_index))),
            "missing_targets_after_reindex": int(len(held_index.difference(signal_index))),
        })
    return rows


def _heatmap(metrics: pd.DataFrame, mode: str, output: Path) -> None:
    table = metrics[metrics.tax_mode.eq(mode)].pivot(
        index=["rule_family", "frequency"], columns="ma_window", values="cagr",
    )
    figure, axis = plt.subplots(figsize=(8, 8))
    image = axis.imshow(table.to_numpy(), aspect="auto", cmap="viridis")
    axis.set_xticks(range(len(table.columns)), labels=table.columns)
    axis.set_yticks(
        range(len(table.index)),
        labels=[f"{rule} / {frequency}" for rule, frequency in table.index],
        fontsize=8,
    )
    axis.set_xlabel("Moving-average window")
    axis.set_title(f"MA stability CAGR — {mode.replace('_', ' ')}")
    figure.colorbar(image, ax=axis, label="CAGR")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _standard_plots(
    curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame,
    benchmarks: pd.DataFrame, output: Path,
) -> None:
    # Keep generic time-series figures readable while the two heatmaps retain
    # the complete five-window surface.
    selected_metrics = metrics[metrics.tax_mode.eq("pre_tax") & metrics.frequency.eq("monthly")]
    names = set(selected_metrics.strategy)
    selected = curves[curves.tax_mode.eq("pre_tax") & curves.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.65, label=name)
    plt.yscale("log")
    plt.legend(fontsize=6, ncol=3)
    plt.tight_layout()
    plt.savefig(output / "equity_curve.png", dpi=150)
    plt.close()

    selected_dd = drawdowns[drawdowns.tax_mode.eq("pre_tax") & drawdowns.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.65, label=name)
    plt.legend(fontsize=6, ncol=3)
    plt.tight_layout()
    plt.savefig(output / "drawdown.png", dpi=150)
    plt.close()

    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for name, part in selected.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(
                lambda x: (x / x.cummax() - 1).min()
                if is_dd else x.iloc[-1] / x.iloc[0] - 1,
            )
            plt.plot(values.index, values, alpha=.65)
        plt.tight_layout()
        plt.savefig(output / filename, dpi=150)
        plt.close()

    pre = metrics[metrics.tax_mode.eq("pre_tax")]
    plt.figure(figsize=(9, 7))
    plt.scatter(pre.max_drawdown.abs(), pre.cagr, c=pre.ma_window, cmap="viridis", alpha=.7)
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows():
        plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown")
    plt.ylabel("CAGR")
    plt.colorbar(label="MA window")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150)
    plt.close()


def _stability_rows(metrics: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for (rule, frequency), group in metrics.groupby(["rule_family", "frequency"], sort=False):
        pre = group[group.tax_mode.eq("pre_tax")].sort_values("ma_window")
        after = group[group.tax_mode.eq("after_tax")].sort_values("ma_window")
        rows.append({
            "rule_family": rule,
            "frequency": frequency,
            "min_cagr": float(pre.cagr.min()),
            "max_cagr": float(pre.cagr.max()),
            "cagr_range": float(pre.cagr.max() - pre.cagr.min()),
            "min_abs_maxdd": float(pre.max_drawdown.abs().min()),
            "max_abs_maxdd": float(pre.max_drawdown.abs().max()),
            "maxdd_spread": float(pre.max_drawdown.abs().max() - pre.max_drawdown.abs().min()),
            "calmar_min": float(pre.calmar.min()),
            "calmar_max": float(pre.calmar.max()),
            "after_tax_cagr_min": float(after.cagr.min()),
            "after_tax_cagr_max": float(after.cagr.max()),
            "after_tax_cagr_range": float(after.cagr.max() - after.cagr.min()),
            "terminal_cagr_min": float(after.terminal_liquidation_cagr.min()),
            "terminal_cagr_max": float(after.terminal_liquidation_cagr.max()),
            "terminal_cagr_range": float(after.terminal_liquidation_cagr.max() - after.terminal_liquidation_cagr.min()),
            "turnover_min": float(pre.annual_turnover.min()),
            "turnover_max": float(pre.annual_turnover.max()),
            "descriptive_min_cagr_window": int(pre.loc[pre.cagr.idxmin(), "ma_window"]),
            "descriptive_max_cagr_window": int(pre.loc[pre.cagr.idxmax(), "ma_window"]),
        })
    return rows


def _verify_phase2_ma200(
    output: Path,
    metrics: pd.DataFrame,
    curve_table: pd.DataFrame,
    positions: pd.DataFrame,
    trades: pd.DataFrame,
    taxes: pd.DataFrame,
) -> dict[str, object]:
    """Compare every Phase 3 MA200 row/path with canonical audited Phase 2."""
    phase2_root = PROJECT_ROOT / "reports/runs/20260914_phase2_audit_final"
    if not phase2_root.exists():
        raise FileNotFoundError(f"canonical Phase 2 run is required: {phase2_root}")
    p2_pre = pd.read_csv(phase2_root / "metrics_pre_tax.csv")
    p2_after = pd.read_csv(phase2_root / "metrics_after_tax.csv")
    p2_curve = pd.read_csv(phase2_root / "equity_curve.csv", parse_dates=["date"])
    p2_positions = pd.read_csv(phase2_root / "positions.csv", parse_dates=["date"])
    p2_trades = pd.read_csv(phase2_root / "trades.csv", parse_dates=["date"])
    p2_taxes = pd.read_csv(phase2_root / "tax_ledger.csv", parse_dates=["date"])
    p2_metrics = pd.concat([p2_pre, p2_after], ignore_index=True)
    strategy_by_pair = {
        (signal, held): legacy
        for legacy, (signal, held) in STRATEGIES.items()
    }
    comparisons = 0
    for mode in ("pre_tax", "after_tax"):
        for _, p2_row in p2_metrics[p2_metrics.tax_mode.eq(mode)].iterrows():
            phase3_row = metrics[
                metrics.tax_mode.eq(mode)
                & metrics.ma_window.eq(200)
                & metrics.frequency.eq(p2_row.frequency)
                & metrics.signal_asset.eq(p2_row.signal_asset)
                & metrics.held_asset.eq(p2_row.held_asset)
            ]
            if len(phase3_row) != 1:
                raise AssertionError(f"missing unique Phase 3 MA200 row for {p2_row.strategy} {mode}")
            phase3_row = phase3_row.iloc[0]
            for field in METRIC_FIELDS:
                if field in {"start", "end"}:
                    if str(phase3_row[field]) != str(p2_row[field]):
                        raise AssertionError(f"Phase 2/3 MA200 mismatch in {field}: {p2_row.strategy}")
                elif not np.isclose(float(phase3_row[field]), float(p2_row[field]), rtol=0, atol=1e-10):
                    raise AssertionError(f"Phase 2/3 MA200 mismatch in {field}: {p2_row.strategy}")
            if mode == "after_tax":
                for field in TERMINAL_FIELDS:
                    if not np.isclose(float(phase3_row[field]), float(p2_row[field]), rtol=0, atol=1e-10):
                        raise AssertionError(f"Phase 2/3 MA200 mismatch in {field}: {p2_row.strategy}")
            p3_name = phase3_row.strategy
            p2_name = p2_row.strategy
            for frame3, frame2, fields in (
                (curve_table, p2_curve, ["date", "equity", "tax_mode"]),
                (positions, p2_positions, ["date", "shares", "target_weight", "actual_weight", "tax_mode"]),
                (trades, p2_trades, ["date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain", "tax_mode"]),
                (taxes, p2_taxes, ["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid", "tax_mode"]),
            ):
                left = frame3[frame3.strategy.eq(p3_name) & frame3.tax_mode.eq(mode)].copy()
                right = frame2[frame2.strategy.eq(p2_name) & frame2.tax_mode.eq(mode)].copy()
                if len(left) != len(right):
                    raise AssertionError(f"Phase 2/3 MA200 path length mismatch: {p2_name} {mode}")
                if not left.empty:
                    left = left[fields].reset_index(drop=True)
                    right = right[fields].reset_index(drop=True)
                    for field in fields:
                        if field == "date" or field in {"tax_mode", "asset", "side"}:
                            if left[field].astype(str).tolist() != right[field].astype(str).tolist():
                                raise AssertionError(f"Phase 2/3 MA200 path mismatch: {p2_name} {mode} {field}")
                        elif not np.allclose(left[field].to_numpy(float), right[field].to_numpy(float), rtol=0, atol=1e-10):
                            raise AssertionError(f"Phase 2/3 MA200 path mismatch: {p2_name} {mode} {field}")
            comparisons += 1
    return {"comparisons": comparisons, "phase2_root": str(phase2_root)}


def _format(value: object, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.4%}" if percent else f"{float(value):,.6f}"


def _write_phase3_report(
    output: Path,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    warmups: list[dict[str, object]],
    alignments: list[dict[str, object]],
    stability: list[dict[str, object]],
    turnover_audits: list[dict[str, object]],
    first_executions: dict[str, str | None],
    phase2_equivalence: dict[str, object],
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution_rate: float,
) -> None:
    lines = [
        "# Phase 3 — MA Parameter Stability",
        "",
        "## Frozen grid and common sample",
        "",
        f"The full-sample evaluation sample is **{start.date()} through {end.date()}** (inclusive). "
        "The intentionally evaluated frozen MA grid is exactly `(150, 175, 200, 225, 250)` trading sessions "
        "across three rule families and four frequencies: 60 economic combinations per tax mode and 120 rows "
        "in `ma_parameter_surface.csv`.",
        "",
        "The signal is adjusted close of the unleveraged underlying at close *t*. Execution is at the held ETF "
        "open no earlier than the next available session (*t+1*); no same-day-close execution is used. "
        "Weekly, monthly, bi-monthly, and quarterly schedules use the first available trading session of the "
        "period (odd months Jan/Mar/May/Jul/Sep/Nov for bi-monthly).",
        "",
        "The five windows were evaluated as a descriptive stability grid, but no window was selected for deployment "
        "from Phase 3 results. Extrema below are full-sample observations, not parameter-selection evidence. "
        "Phase 3 is not OOS evidence; Walk-Forward parameter selection remains deferred to the frozen later phase.",
        "",
        "## Phase 2 MA200 equivalence",
        "",
        f"All {phase2_equivalence['comparisons']} (rule, frequency, tax-mode) comparisons against "
        "canonical audited Phase 2 passed for metrics and actual equity/position/trade/tax-ledger paths. "
        "The MA200 row is therefore the Phase 2 regression oracle for this stability surface.",
        "",
        "## Warm-up and calendar audit",
        "",
        "Pre-evaluation history is used only as legitimate MA warm-up. It creates no pre-evaluation equity or "
        "trade. A window's first valid MA date is the first date with the required number of observations; the "
        "evaluation-day target uses only previously available closes. Missing targets after final signal-to-held "
        "calendar alignment are zero.",
        "",
        "| Signal | MA window | Full signal rows | Pre-start rows | Lookback observations at evaluation start | Lookback start | First valid MA date | Missing aligned targets |",
        "|---|---:|---:|---:|---:|---|---|---:|",
    ]
    for row in warmups:
        lines.append(
            f"| {row['signal_asset']} | {row['ma_window']} | {row['signal_rows_full']} | "
            f"{row['pre_start_warmup_rows']} | {row['lookback_observations_at_start']} | "
            f"{row['lookback_start_at_evaluation']} | {row['first_valid_ma_date']} | "
            f"{row['missing_aligned_targets']} |",
        )
    lines += [
        "",
        "| Rule family | Signal | Held | Signal rows | Held rows | Common rows | Missing targets |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in alignments:
        lines.append(
            f"| {row['rule_family']} | {row['signal_asset']} | {row['held_asset']} | "
            f"{row['signal_calendar_rows']} | {row['held_calendar_rows']} | "
            f"{row['common_evaluation_rows']} | {row['missing_targets_after_reindex']} |",
        )
    lines += [
        "",
        "| Rule family | Frequency | MA window | First actual execution date |",
        "|---|---|---:|---|",
    ]
    for legacy_rule, _ in STRATEGIES.items():
        for frequency in FREQUENCIES:
            name = strategy_identifier(legacy_rule, frequency, 200)
            lines.append(
                f"| {rule_family(legacy_rule)} | {frequency} | 200 | {first_executions.get(name) or 'N/A'} |",
            )

    lines += [
        "",
        "## Stability ranges (descriptive only)",
        "",
        "`CAGR spread = max(CAGR) − min(CAGR)` and `MaxDD spread = max(abs(MaxDD)) − min(abs(MaxDD))`. "
        "The window labels in the final two columns are descriptive extrema only; none is optimal, selected, "
        "recommended, or promoted.",
        "",
        "| Rule family | Frequency | Pre-tax CAGR min–max | CAGR spread | Pre-tax abs MaxDD min–max | MaxDD spread | Calmar min–max | After-tax CAGR min–max | Terminal CAGR min–max | Turnover min–max | Descriptive min-CAGR MA | Descriptive max-CAGR MA |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in stability:
        lines.append(
            f"| {row['rule_family']} | {row['frequency']} | {_format(row['min_cagr'], percent=True)}–{_format(row['max_cagr'], percent=True)} | "
            f"{_format(row['cagr_range'], percent=True)} | {_format(row['min_abs_maxdd'], percent=True)}–{_format(row['max_abs_maxdd'], percent=True)} | "
            f"{_format(row['maxdd_spread'], percent=True)} | {_format(row['calmar_min'])}–{_format(row['calmar_max'])} | "
            f"{_format(row['after_tax_cagr_min'], percent=True)}–{_format(row['after_tax_cagr_max'], percent=True)} | "
            f"{_format(row['terminal_cagr_min'], percent=True)}–{_format(row['terminal_cagr_max'], percent=True)} | "
            f"{_format(row['turnover_min'])}–{_format(row['turnover_max'])} | {row['descriptive_min_cagr_window']} | {row['descriptive_max_cagr_window']} |",
        )

    lines += [
        "",
        "## Complete metric surface",
        "",
        "Each of the 120 rows is retained in the CSV surface. Holding periods are completed position episodes "
        "measured in trading sessions; an open terminal position is not fabricated into an episode. After-tax "
        "wealth and CAGR are wealth after realized tax paid to date. Terminal liquidation fields are hypothetical "
        "diagnostics only and do not add a SELL, change turnover/holding statistics, or mutate the tax ledger.",
        "",
        "| Rule family | Frequency | MA | Tax mode | CAGR | MaxDD | Calmar | Annual turnover | Mean hold | Median hold | Max hold | Trades | Costs | Realized tax | Terminal CAGR |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics.sort_values(["rule_family", "frequency", "ma_window", "tax_mode"]).iterrows():
        lines.append(
            f"| {row.rule_family} | {row.frequency} | {int(row.ma_window)} | {row.tax_mode} | "
            f"{_format(row.cagr, percent=True)} | {_format(row.max_drawdown, percent=True)} | {_format(row.calmar)} | "
            f"{_format(row.annual_turnover)} | {_format(row.mean_holding_period_days)} | "
            f"{_format(row.median_holding_period_days)} | {_format(row.max_holding_period_days)} | "
            f"{int(row.number_of_trades)} | ${row.transaction_costs:,.2f} | ${row.tax_paid:,.2f} | "
            f"{_format(row.terminal_liquidation_cagr, percent=True)} |",
        )

    lines += [
        "",
        "## Turnover audit",
        "",
        f"Annual turnover uses `sum(abs(trade_notional) / contemporaneous_pretrade_equity) / calendar_years`, "
        f"with initial deployment and hypothetical terminal liquidation excluded. The execution cost rate is "
        f"{execution_rate:.8f} (0 commission bps + 5 slippage bps).",
        "",
        "| Legacy rule | Frequency | Included normalized turnover | Calendar years | Annual turnover | Included trade dates/rebalances | Gross traded notional | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in turnover_audits:
        lines.append(
            f"| {row['legacy_rule']} | {row['frequency']} | {row['included_normalized_turnover']:.9f} | "
            f"{row['years']:.9f} | {row['annual_turnover']:.9f} | {row['nonzero_trade_dates']} | "
            f"${row['gross_traded_notional']:,.2f} | {row['number_of_trades']} |",
        )

    lines += [
        "",
        "## Common-sample benchmarks",
        "",
        "SPY, QQQ, SSO, and QLD buy-and-hold endpoints use the same common evaluation sample and are descriptive "
        "benchmarks, not predictive evidence.",
        "",
        "| Benchmark | Start | End | CAGR | MaxDD | Calmar |",
        "|---|---|---|---:|---:|---:|",
    ]
    for _, row in benchmarks.iterrows():
        lines.append(
            f"| {row.asset} | {row.start} | {row.end} | {_format(row.cagr, percent=True)} | "
            f"{_format(row.max_drawdown, percent=True)} | {_format(row.calmar)} |",
        )
    lines += [
        "",
        "Tax convention: Simplified Japan taxable mode uses average cost, immediate payment, and loss-pool "
        "treatment at realized sales. Unrealized appreciation is not taxed merely for increasing in value. "
        "CASH earns exactly 0%.",
        "",
        "The legacy `QQQ_MA200_*` labels appear only in compatibility/audit columns; Phase 3 canonical rule-family "
        "and strategy identifiers are `QQQ_MA_QQQ`, `QQQ_MA_QLD`, `SPY_MA_SSO` plus explicit `_MA<window>` suffixes. "
        "No best window is selected, and no OOS/Walk-Forward claim is made.",
    ]
    (output / "phase3_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase3_ma_stability"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {
        asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    capital = float(config["initial_capital"])
    commission_bps = float(config["execution"]["commission_bps"])
    slippage_bps = float(config["execution"]["slippage_bps"])
    execution_rate = (commission_bps + slippage_bps) / 10_000.0
    tax_rate = float(config["tax"]["capital_gains_rate"])
    rows, curves, drawdowns, positions, trades, taxes, parameters = [], [], [], [], [], [], []
    warmups = _warmup_rows(prices, start, end)
    alignments = _alignment_rows(prices, start, end)
    turnover_audits: list[dict[str, object]] = []
    first_executions: dict[str, str | None] = {}

    for legacy_rule, (signal_asset, held_asset) in STRATEGIES.items():
        signal_prices = prices[signal_asset]["adjusted_close"]
        held_prices = prices[held_asset].loc[start:end]
        signal_eval = signal_prices.loc[start:end]
        for frequency in FREQUENCIES:
            for window in MA_WINDOWS:
                targets = trend_target_next_open(signal_prices, frequency, lookback=window).reindex(held_prices.index)
                if targets.isna().any() or not signal_eval.index.equals(held_prices.index):
                    raise ValueError("signal and held-asset calendars are not aligned")
                canonical_rule = rule_family(legacy_rule)
                strategy = strategy_identifier(legacy_rule, frequency, window)
                for mode, mode_tax_rate in (("pre_tax", None), ("after_tax", tax_rate)):
                    ledger, position, trade, tax = single_asset_timed_backtest(
                        held_prices,
                        targets,
                        initial_capital=capital,
                        commission_bps=commission_bps,
                        slippage_bps=slippage_bps,
                        tax_rate=mode_tax_rate,
                    )
                    ledger = _add_pretrade_equity(ledger, held_prices, capital)
                    metric = performance_metrics(
                        ledger,
                        trade,
                        capital,
                        terminal_tax_rate=mode_tax_rate,
                        terminal_cost_rate=execution_rate if mode_tax_rate is not None else 0.0,
                    )
                    metric.update({
                        "strategy": strategy,
                        "rule": canonical_rule,
                        "rule_family": canonical_rule,
                        "legacy_rule": legacy_rule,
                        "legacy_strategy": f"{legacy_rule}_{frequency}_MA{window}",
                        "signal_asset": signal_asset,
                        "held_asset": held_asset,
                        "frequency": frequency,
                        "ma_window": window,
                        "tax_mode": mode,
                        "cumulative_realized_tax_paid": float(metric["tax_paid"]),
                        "tax_semantics": (
                            "realized tax paid to date; terminal liquidation is diagnostic"
                            if mode == "after_tax" else "pre-tax; no realized tax is charged"
                        ),
                    })
                    rows.append(metric)
                    curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                    drawdowns.append(
                        drawdown_series(ledger.equity, capital).rename("drawdown").to_frame()
                        .assign(strategy=strategy, tax_mode=mode).reset_index(names="date")
                    )
                    positions.append(position.assign(strategy=strategy, tax_mode=mode))
                    if len(trade):
                        trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                        if mode == "pre_tax":
                            first_executions[strategy] = str(pd.to_datetime(trade["date"]).min().date())
                    elif mode == "pre_tax":
                        first_executions[strategy] = None
                    if len(tax):
                        taxes.append(tax.assign(strategy=strategy, tax_mode=mode))
                    if mode == "pre_tax" and (legacy_rule, frequency) in TURNOVER_AUDIT_KEYS:
                        turnover_audits.append({
                            "legacy_rule": legacy_rule,
                            "rule_family": canonical_rule,
                            "frequency": frequency,
                            **_turnover_audit(ledger, trade),
                        })
                parameters.append({
                    "rule": canonical_rule,
                    "rule_family": canonical_rule,
                    "legacy_rule": legacy_rule,
                    "signal_asset": signal_asset,
                    "held_asset": held_asset,
                    "frequency": frequency,
                    "ma_window": window,
                    "searched_for_selection": False,
                    "selection_performed": False,
                })

    metrics = pd.DataFrame(rows)
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].reset_index(drop=True)
    after = metrics.loc[metrics.tax_mode.eq("after_tax")].reset_index(drop=True)
    if len(pre) != 60 or len(after) != 60 or len(parameters) != 60:
        raise AssertionError("Phase 3 must produce 60 rows per tax mode and 60 parameter combinations")
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "ma_parameter_surface.csv", index=False)
    pd.DataFrame(parameters).to_csv(output / "parameter_results.csv", index=False)
    curve_table = pd.concat(curves, ignore_index=True)
    dd_table = pd.concat(drawdowns, ignore_index=True)
    position_table = pd.concat(positions, ignore_index=True)
    trade_table = pd.concat(trades, ignore_index=True)
    tax_table = (
        pd.concat(taxes, ignore_index=True)
        if taxes else pd.DataFrame(columns=["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid", "strategy", "tax_mode"])
    )
    curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table.to_csv(output / "drawdown.csv", index=False)
    position_table.to_csv(output / "positions.csv", index=False)
    trade_table.to_csv(output / "trades.csv", index=False)
    tax_table.to_csv(output / "tax_ledger.csv", index=False)
    benchmarks = []
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        ledger, _, trade = buy_and_hold(
            prices[asset].loc[start:end],
            initial_capital=capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        benchmarks.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    benchmark_table = pd.DataFrame(benchmarks)
    _heatmap(metrics, "pre_tax", output / "ma_stability_heatmap.png")
    _heatmap(metrics, "after_tax", output / "ma_stability_heatmap_after_tax.png")
    _standard_plots(curve_table, dd_table, metrics, benchmark_table, output)
    phase2_equivalence = _verify_phase2_ma200(
        output, metrics, curve_table, position_table, trade_table, tax_table,
    )
    _write_phase3_report(
        output,
        metrics,
        benchmark_table,
        warmups,
        alignments,
        _stability_rows(metrics),
        turnover_audits,
        first_executions,
        phase2_equivalence,
        start=start,
        end=end,
        execution_rate=execution_rate,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 3 MA stability")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
