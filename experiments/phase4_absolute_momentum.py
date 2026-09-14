from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.phase2_ma200 import (  # noqa: E402
    FREQUENCIES,
    _add_pretrade_equity,
    _turnover_audit,
)
from market_timing_quant.configuration import load_config  # noqa: E402
from market_timing_quant.data import run_data_audit  # noqa: E402
from market_timing_quant.metrics import drawdown_series, performance_metrics  # noqa: E402
from market_timing_quant.portfolio import buy_and_hold, single_asset_timed_backtest  # noqa: E402
from market_timing_quant.signals import (  # noqa: E402
    absolute_momentum_decision,
    absolute_momentum_target_next_open,
)

MOMENTUM_WINDOWS = (126, 189, 252)
STRATEGIES = {
    "SPY_ABS_MOM_SSO": ("SPY", "SSO"),
    "QQQ_ABS_MOM_QLD": ("QQQ", "QLD"),
}


def parameter_grid() -> tuple[int, ...]:
    """The intentionally evaluated, frozen Phase 4 momentum grid."""
    return MOMENTUM_WINDOWS


def strategy_identifier(rule: str, frequency: str, momentum_window: int) -> str:
    return f"{rule}_{frequency}_{momentum_window}D"


def _warmup_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows = []
    for window in MOMENTUM_WINDOWS:
        for asset in ("SPY", "QQQ"):
            frame = prices[asset]
            decision = absolute_momentum_decision(frame["adjusted_close"], lookback=window)
            through_start = frame.loc[:start]
            lookback = through_start.tail(window + 1)
            signal_index = frame.loc[start:end].index
            held_asset = "SSO" if asset == "SPY" else "QLD"
            held_index = prices[held_asset].loc[start:end].index
            rows.append({
                "signal_asset": asset,
                "momentum_window": window,
                "signal_rows_full": int(len(frame)),
                "pre_start_warmup_rows": int((frame.index < start).sum()),
                "required_lookback_sessions": window,
                "lookback_observations_at_evaluation_start": int(len(lookback)),
                "lookback_start_at_evaluation": str(lookback.index[0].date()),
                "lookback_end_at_evaluation": str(lookback.index[-1].date()),
                "first_valid_momentum_date": str(decision.index[window].date()),
                "evaluation_start": str(start.date()),
                "evaluation_end": str(end.date()),
                "missing_aligned_targets": int(len(held_index.difference(signal_index))),
            })
    return rows


def _alignment_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows = []
    for rule, (signal_asset, held_asset) in STRATEGIES.items():
        signal_index = prices[signal_asset].loc[start:end].index
        held_index = prices[held_asset].loc[start:end].index
        rows.append({
            "rule": rule,
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
        index=["rule", "frequency"], columns="momentum_window", values="cagr",
    )
    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(table.to_numpy(), aspect="auto", cmap="viridis")
    axis.set_xticks(range(len(table.columns)), labels=table.columns)
    axis.set_yticks(
        range(len(table.index)),
        labels=[f"{rule} / {frequency}" for rule, frequency in table.index],
        fontsize=8,
    )
    axis.set_xlabel("Absolute-momentum lookback (trading sessions)")
    axis.set_title(f"Absolute-momentum CAGR — {mode.replace('_', ' ')}")
    figure.colorbar(image, ax=axis, label="CAGR")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _standard_plots(
    curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame,
    benchmarks: pd.DataFrame, output: Path,
) -> None:
    selected_metrics = metrics[metrics.tax_mode.eq("pre_tax") & metrics.frequency.eq("monthly")]
    names = set(selected_metrics.strategy)
    selected = curves[curves.tax_mode.eq("pre_tax") & curves.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.65, label=name)
    plt.yscale("log")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "equity_curve.png", dpi=150)
    plt.close()

    selected_dd = drawdowns[drawdowns.tax_mode.eq("pre_tax") & drawdowns.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.65, label=name)
    plt.legend(fontsize=7, ncol=2)
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
    plt.scatter(pre.max_drawdown.abs(), pre.cagr, c=pre.momentum_window, cmap="viridis", alpha=.7)
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows():
        plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown")
    plt.ylabel("CAGR")
    plt.colorbar(label="Momentum window")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150)
    plt.close()


def _stability_rows(metrics: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for (rule, frequency), group in metrics.groupby(["rule", "frequency"], sort=False):
        pre = group[group.tax_mode.eq("pre_tax")].sort_values("momentum_window")
        after = group[group.tax_mode.eq("after_tax")].sort_values("momentum_window")
        rows.append({
            "rule": rule,
            "frequency": frequency,
            "pre_tax_cagr_min": float(pre.cagr.min()),
            "pre_tax_cagr_max": float(pre.cagr.max()),
            "cagr_spread": float(pre.cagr.max() - pre.cagr.min()),
            "min_abs_maxdd": float(pre.max_drawdown.abs().min()),
            "max_abs_maxdd": float(pre.max_drawdown.abs().max()),
            "maxdd_spread": float(pre.max_drawdown.abs().max() - pre.max_drawdown.abs().min()),
            "calmar_min": float(pre.calmar.min()),
            "calmar_max": float(pre.calmar.max()),
            "after_tax_cagr_min": float(after.cagr.min()),
            "after_tax_cagr_max": float(after.cagr.max()),
            "terminal_cagr_min": float(after.terminal_liquidation_cagr.min()),
            "terminal_cagr_max": float(after.terminal_liquidation_cagr.max()),
            "turnover_min": float(pre.annual_turnover.min()),
            "turnover_max": float(pre.annual_turnover.max()),
            "descriptive_min_cagr_window": int(pre.loc[pre.cagr.idxmin(), "momentum_window"]),
            "descriptive_max_cagr_window": int(pre.loc[pre.cagr.idxmax(), "momentum_window"]),
        })
    return rows


def _format(value: object, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.4%}" if percent else f"{float(value):,.6f}"


def _write_phase4_report(
    output: Path,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    warmups: list[dict[str, object]],
    alignments: list[dict[str, object]],
    stability: list[dict[str, object]],
    turnover_audits: list[dict[str, object]],
    first_executions: dict[str, str | None],
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution_rate: float,
) -> None:
    lines = [
        "# Phase 4 — Absolute Momentum",
        "",
        "## Frozen specification and common sample",
        "",
        f"The full-sample evaluation period is **{start.date()} through {end.date()}** (inclusive). "
        "The exact frozen momentum grid is `(126, 189, 252)` trading sessions across two rules and four "
        "frequencies: 24 economic combinations per tax mode and 48 rows in `absolute_momentum_results.csv`.",
        "",
        "SPY adjusted-close absolute momentum signals map only to SSO/CASH. QQQ adjusted-close absolute "
        "momentum signals map only to QLD/CASH. The mathematical definition is `momentum_t = "
        "adjusted_close_t / adjusted_close_(t-L) - 1`; Risk-On is strictly `momentum_t > 0`, while exact "
        "zero and negative momentum are Risk-Off.",
        "",
        "The signal is observed at close *t*. Execution is at the held ETF open no earlier than the next "
        "available session (*t+1*); no same-day-close execution is used. Weekly, monthly, bi-monthly, and "
        "quarterly schedules use the first available trading session of the period (odd months Jan/Mar/May/"
        "Jul/Sep/Nov for bi-monthly). CASH earns exactly 0%.",
        "",
        "The three frozen lookbacks were evaluated as a descriptive full-sample grid, but no lookback was "
        "selected for deployment. Extrema below are in-sample descriptive observations, not selection evidence. "
        "Phase 4 makes no OOS or Walk-Forward claim; Walk-Forward parameter selection remains deferred to the "
        "frozen later phase.",
        "",
        "## Warm-up and calendar audit",
        "",
        "Pre-evaluation history is used only as legitimate warm-up. For momentum window L, the first valid "
        "calculation is the date at position L because it requires the current close and the close L sessions "
        "earlier. Warm-up creates no pre-evaluation equity, positions, or trades. Missing targets after final "
        "signal-to-held calendar alignment are zero.",
        "",
        "| Signal | Window | Full rows | Pre-start rows | Required L | Observations at evaluation start | Lookback start | First valid momentum date | Missing targets |",
        "|---|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for row in warmups:
        lines.append(
            f"| {row['signal_asset']} | {row['momentum_window']} | {row['signal_rows_full']} | "
            f"{row['pre_start_warmup_rows']} | {row['required_lookback_sessions']} | "
            f"{row['lookback_observations_at_evaluation_start']} | {row['lookback_start_at_evaluation']} | "
            f"{row['first_valid_momentum_date']} | {row['missing_aligned_targets']} |",
        )
    lines += [
        "",
        "| Rule | Signal | Held | Signal rows | Held rows | Common rows | Missing targets |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in alignments:
        lines.append(
            f"| {row['rule']} | {row['signal_asset']} | {row['held_asset']} | "
            f"{row['signal_calendar_rows']} | {row['held_calendar_rows']} | "
            f"{row['common_evaluation_rows']} | {row['missing_targets_after_reindex']} |",
        )
    lines += [
        "",
        "| Rule | Frequency | Window | First actual execution date |",
        "|---|---|---:|---|",
    ]
    for rule in STRATEGIES:
        for frequency in FREQUENCIES:
            for window in MOMENTUM_WINDOWS:
                name = strategy_identifier(rule, frequency, window)
                lines.append(
                    f"| {rule} | {frequency} | {window} | {first_executions.get(name) or 'N/A'} |",
                )

    lines += [
        "",
        "## Stability ranges (descriptive only)",
        "",
        "`CAGR spread = max(CAGR) − min(CAGR)` and `MaxDD spread = max(abs(MaxDD)) − min(abs(MaxDD))`. "
        "Lookback labels in the final two columns identify descriptive extrema only; none is optimal, "
        "selected, recommended, or a winner.",
        "",
        "| Rule | Frequency | Pre-tax CAGR min–max | CAGR spread | Abs MaxDD min–max | MaxDD spread | Calmar min–max | After-tax CAGR min–max | Terminal CAGR min–max | Turnover min–max | Descriptive min-CAGR L | Descriptive max-CAGR L |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in stability:
        lines.append(
            f"| {row['rule']} | {row['frequency']} | {_format(row['pre_tax_cagr_min'], percent=True)}–{_format(row['pre_tax_cagr_max'], percent=True)} | "
            f"{_format(row['cagr_spread'], percent=True)} | {_format(row['min_abs_maxdd'], percent=True)}–{_format(row['max_abs_maxdd'], percent=True)} | "
            f"{_format(row['maxdd_spread'], percent=True)} | {_format(row['calmar_min'])}–{_format(row['calmar_max'])} | "
            f"{_format(row['after_tax_cagr_min'], percent=True)}–{_format(row['after_tax_cagr_max'], percent=True)} | "
            f"{_format(row['terminal_cagr_min'], percent=True)}–{_format(row['terminal_cagr_max'], percent=True)} | "
            f"{_format(row['turnover_min'])}–{_format(row['turnover_max'])} | "
            f"{row['descriptive_min_cagr_window']} | {row['descriptive_max_cagr_window']} |",
        )

    lines += [
        "",
        "## Complete metric surface",
        "",
        "All 48 metric rows are retained. Holding periods are completed position episodes measured in trading "
        "sessions; an open terminal position is not fabricated into an episode. After-tax wealth and CAGR are "
        "wealth after realized tax paid to date. Terminal liquidation fields are hypothetical diagnostics only "
        "and do not add a SELL, change turnover/holding statistics, or mutate the tax ledger.",
        "",
        "| Rule | Frequency | L | Tax mode | CAGR | MaxDD | Calmar | Annual turnover | Mean hold | Median hold | Max hold | Trades | Costs | Realized tax | Terminal CAGR |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics.sort_values(["rule", "frequency", "momentum_window", "tax_mode"]).iterrows():
        lines.append(
            f"| {row.rule} | {row.frequency} | {int(row.momentum_window)} | {row.tax_mode} | "
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
        f"{execution_rate:.8f} (0 commission bps + 5 slippage bps). The same audited Phase 2/3 helpers are "
        "used for every Phase 4 row.",
        "",
        "| Rule | Frequency | L | Included normalized turnover | Calendar years | Annual turnover | Included trade dates | Gross notional | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in turnover_audits:
        lines.append(
            f"| {row['rule']} | {row['frequency']} | {row['momentum_window']} | "
            f"{row['included_normalized_turnover']:.9f} | {row['years']:.9f} | "
            f"{row['annual_turnover']:.9f} | {row['nonzero_trade_dates']} | "
            f"${row['gross_traded_notional']:,.2f} | {row['number_of_trades']} |",
        )

    lines += [
        "",
        "## Common-sample benchmarks",
        "",
        "SPY, QQQ, SSO, and QLD buy-and-hold endpoints use the same common evaluation sample and audited "
        "benchmark turnover convention; they are descriptive benchmarks, not predictive evidence.",
        "",
        "| Benchmark | Start | End | CAGR | MaxDD | Calmar | Annual turnover |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for _, row in benchmarks.iterrows():
        lines.append(
            f"| {row.asset} | {row.start} | {row.end} | {_format(row.cagr, percent=True)} | "
            f"{_format(row.max_drawdown, percent=True)} | {_format(row.calmar)} | {_format(row.annual_turnover)} |",
        )
    lines += [
        "",
        "Tax convention: Simplified Japan taxable mode uses average cost, immediate payment, and loss-pool "
        "treatment at realized sales. Unrealized appreciation is not taxed merely for increasing in value. "
        "Cumulative realized tax paid is retained in `cumulative_realized_tax_paid`; terminal liquidation is "
        "non-mutating and diagnostic only.",
        "",
        "`absolute_momentum_results.csv` is the complete 48-row tax-mode metric surface. `parameter_results.csv` "
        "is the 24-row unique economic grid with `searched_for_selection=False` and `selection_performed=False`; "
        "the frozen windows were evaluated for stability, not selected for deployment.",
        "",
        "Phase 4 is a full-sample parameter study only. It makes no OOS or Walk-Forward claim. Walk-Forward "
        "parameter selection remains deferred to the frozen later phase.",
    ]
    (output / "phase4_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase4_absolute_momentum"))
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

    for rule, (signal_asset, held_asset) in STRATEGIES.items():
        signal_prices = prices[signal_asset]["adjusted_close"]
        held_prices = prices[held_asset].loc[start:end]
        for frequency in FREQUENCIES:
            for window in MOMENTUM_WINDOWS:
                target = absolute_momentum_target_next_open(
                    signal_prices, frequency, window,
                ).reindex(held_prices.index)
                if target.isna().any() or not target.index.equals(held_prices.index):
                    raise ValueError("signal and held-asset calendars are not aligned")
                strategy = strategy_identifier(rule, frequency, window)
                for mode, mode_tax_rate in (("pre_tax", None), ("after_tax", tax_rate)):
                    ledger, position, trade, tax = single_asset_timed_backtest(
                        held_prices,
                        target,
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
                        "rule": rule,
                        "rule_family": rule,
                        "legacy_rule": rule,
                        "legacy_strategy": strategy,
                        "signal_asset": signal_asset,
                        "held_asset": held_asset,
                        "frequency": frequency,
                        "momentum_window": window,
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
                    if mode == "pre_tax":
                        turnover_audits.append({
                            "rule": rule,
                            "frequency": frequency,
                            "momentum_window": window,
                            **_turnover_audit(ledger, trade),
                        })
                parameters.append({
                    "rule": rule,
                    "rule_family": rule,
                    "legacy_rule": rule,
                    "signal_asset": signal_asset,
                    "held_asset": held_asset,
                    "frequency": frequency,
                    "momentum_window": window,
                    "searched_for_selection": False,
                    "selection_performed": False,
                })

    metrics = pd.DataFrame(rows)
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].reset_index(drop=True)
    after = metrics.loc[metrics.tax_mode.eq("after_tax")].reset_index(drop=True)
    combined = pd.concat([pre, after], ignore_index=True)
    if len(pre) != 24 or len(after) != 24 or len(parameters) != 24:
        raise AssertionError("Phase 4 must produce 24 rows per tax mode and 24 parameter combinations")
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    combined.to_csv(output / "absolute_momentum_results.csv", index=False)
    pd.DataFrame(parameters).to_csv(output / "parameter_results.csv", index=False)

    curve_table = pd.concat(curves, ignore_index=True)
    dd_table = pd.concat(drawdowns, ignore_index=True)
    position_table = pd.concat(positions, ignore_index=True)
    trade_table = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
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
    _heatmap(metrics, "pre_tax", output / "absolute_momentum_heatmap.png")
    _heatmap(metrics, "after_tax", output / "absolute_momentum_heatmap_after_tax.png")
    _standard_plots(curve_table, dd_table, metrics, benchmark_table, output)
    _write_phase4_report(
        output,
        combined,
        benchmark_table,
        warmups,
        alignments,
        _stability_rows(combined),
        turnover_audits,
        first_executions,
        start=start,
        end=end,
        execution_rate=execution_rate,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 4 absolute momentum")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
