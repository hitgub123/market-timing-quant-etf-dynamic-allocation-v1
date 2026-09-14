from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import drawdown_series, performance_metrics
from market_timing_quant.portfolio import buy_and_hold, single_asset_timed_backtest
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open

FREQUENCIES = ("weekly", "monthly", "bimonthly", "quarterly")
STRATEGIES = {
    "QQQ_MA200_QQQ": ("QQQ", "QQQ"),
    "QQQ_MA200_QLD": ("QQQ", "QLD"),
    "SPY_MA200_SSO": ("SPY", "SSO"),
}
TURNOVER_AUDIT_KEYS = {
    ("QQQ_MA200_QQQ", "weekly"),
    ("QQQ_MA200_QQQ", "monthly"),
    ("QQQ_MA200_QLD", "weekly"),
    ("SPY_MA200_SSO", "monthly"),
}


def _add_pretrade_equity(
    ledger: pd.DataFrame, prices: pd.DataFrame, initial_capital: float,
) -> pd.DataFrame:
    """Attach the open-before-trade equity used by the turnover definition.

    The shared execution function deliberately returns the economic ledger
    without this reporting-only field. Reconstructing it here keeps the shared
    Phase 3--7 execution code untouched while making Phase 2 denominators
    explicit and auditable.
    """
    if not ledger.index.equals(prices.index):
        raise ValueError("ledger and prices must share the evaluation calendar")
    result = ledger.copy()
    result["pretrade_equity"] = (
        ledger.cash.shift(1) + ledger.shares.shift(1) * prices["open"].astype(float)
    ).fillna(float(initial_capital))
    return result


def _turnover_audit(ledger: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    """Return the frozen turnover components for one strategy ledger."""
    years = max((ledger.index[-1] - ledger.index[0]).days / 365.25, 1 / 365.25)
    if not len(trades):
        return {
            "included_normalized_turnover": 0.0,
            "years": years,
            "annual_turnover": 0.0,
            "nonzero_trade_dates": 0,
            "nonzero_trade_rebalances": 0,
            "gross_traded_notional": 0.0,
            "number_of_trades": 0,
        }
    dates = pd.to_datetime(trades["date"])
    initial_date = dates.min()
    include = ~(dates.eq(initial_date) & trades["side"].eq("BUY")).to_numpy()
    denominators = ledger["pretrade_equity"].reindex(dates).to_numpy(dtype=float)
    normalized = float(
        (trades.loc[include, "notional"].abs().to_numpy(dtype=float) / denominators[include]).sum()
    )
    included_dates = dates.loc[include]
    return {
        "included_normalized_turnover": normalized,
        "years": years,
        "annual_turnover": normalized / years,
        "nonzero_trade_dates": int(included_dates.nunique()),
        "nonzero_trade_rebalances": int(included_dates.nunique()),
        "gross_traded_notional": float(trades["notional"].abs().sum()),
        "number_of_trades": int(len(trades)),
    }


def _write_plots(
    curves: pd.DataFrame,
    drawdowns: pd.DataFrame,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    output: Path,
) -> None:
    pre = curves[curves.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], label=name, alpha=.75)
    plt.yscale("log")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "equity_curve.png", dpi=150)
    plt.close()

    pre_dd = drawdowns[drawdowns.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, label=name, alpha=.75)
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "drawdown.png", dpi=150)
    plt.close()

    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for name, part in pre.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(
                lambda x: (x / x.cummax() - 1).min()
                if is_dd else x.iloc[-1] / x.iloc[0] - 1,
            )
            plt.plot(values.index, values, label=name, alpha=.75)
        plt.legend(fontsize=7, ncol=2)
        plt.tight_layout()
        plt.savefig(output / filename, dpi=150)
        plt.close()

    plt.figure(figsize=(9, 7))
    points = metrics[metrics.tax_mode == "pre_tax"]
    plt.scatter(points.max_drawdown.abs(), points.cagr, label="MA200 strategies")
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows():
        plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown")
    plt.ylabel("CAGR")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150)
    plt.close()


def _warmup_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows = []
    for asset in ("QQQ", "SPY"):
        frame = prices[asset]
        decision = ma_trend_decision(frame["adjusted_close"], lookback=200)
        before = frame.loc[frame.index < start]
        through_start = frame.loc[:start]
        lookback = through_start.tail(200)
        rows.append({
            "signal_asset": asset,
            "evaluation_start": start.date().isoformat(),
            "evaluation_end": end.date().isoformat(),
            "signal_rows_full": int(len(frame)),
            "pre_start_warmup_rows": int(len(before)),
            "lookback_observations_at_start": int(len(lookback)),
            "lookback_start_at_start": str(lookback.index[0].date()) if len(lookback) else None,
            "lookback_end_at_start": str(lookback.index[-1].date()) if len(lookback) else None,
            "first_valid_ma200_date": str(decision.index[199].date()),
            "first_evaluation_signal_date": str(frame.loc[start:].index[0].date()),
        })
    return rows


def _alignment_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows = []
    for rule, (signal_asset, held_asset) in STRATEGIES.items():
        signal_index = prices[signal_asset].loc[start:end].index
        held_index = prices[held_asset].loc[start:end].index
        common = signal_index.intersection(held_index)
        rows.append({
            "rule": rule,
            "signal_asset": signal_asset,
            "held_asset": held_asset,
            "signal_calendar_rows": int(len(signal_index)),
            "held_calendar_rows": int(len(held_index)),
            "common_evaluation_rows": int(len(common)),
            "missing_targets_after_reindex": int(len(held_index.difference(signal_index))),
        })
    return rows


def _format_value(value: object, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if percent:
        return f"{float(value):.4%}"
    if isinstance(value, (float, int)):
        return f"{float(value):,.6f}"
    return str(value)


def _write_phase2_report(
    output: Path,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    warmups: list[dict[str, object]],
    alignments: list[dict[str, object]],
    turnover_audits: list[dict[str, object]],
    first_executions: dict[str, str | None],
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution_rate: float,
) -> None:
    lines = [
        "# Phase 2 — MA200 Simple Trend",
        "",
        "## Frozen specification and common sample",
        "",
        f"The common evaluation sample is **{start.date()} through {end.date()}** (inclusive), "
        "the intersection of each signal/held ETF calendar. The three frozen rules are "
        "QQQ MA200 → QQQ/CASH, QQQ MA200 → QLD/CASH, and SPY MA200 → SSO/CASH. "
        "The MA window is exactly 200 trading sessions and was not selected through a parameter search; "
        "no neighboring windows were evaluated. Phase 2 makes no OOS or Walk-Forward claim.",
        "",
        "Signal uses the adjusted close of the unleveraged underlying at close *t*. "
        "A completed decision can first affect the next available session's open (*t+1*); "
        "the held ETF's open is the execution price. No same-day-close execution is used.",
        "",
        "Rebalance dates are the first available trading session of each period: weekly (first session "
        "of the Sunday-ending week), monthly (first session of the calendar month), bi-monthly "
        "(first session of odd months Jan/Mar/May/Jul/Sep/Nov), and quarterly (first session of "
        "Jan/Apr/Jul/Oct). A signal change on a non-rebalance day is held until the next scheduled "
        "decision/execution sequence.",
        "",
        "## MA200 warm-up audit",
        "",
        "Pre-start observations are used only to form the legitimate 200-session moving average. "
        "They create no pre-evaluation equity or trades. The first evaluation-day target is read from "
        "the already-available prior close and is executed, if scheduled, at the evaluation-day open.",
        "",
        "| Signal asset | Full signal rows | Pre-start warm-up rows | 200-observation lookback at evaluation start | Lookback start | First valid MA200 date | First evaluation date |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in warmups:
        lines.append(
            f"| {row['signal_asset']} | {row['signal_rows_full']} | {row['pre_start_warmup_rows']} | "
            f"{row['lookback_observations_at_start']} | {row['lookback_start_at_start']} | "
            f"{row['first_valid_ma200_date']} | {row['first_evaluation_signal_date']} |",
        )
    lines += [
        "",
        "## Signal/held-calendar alignment",
        "",
        "The full signal is computed on the signal asset, then reindexed to the held ETF calendar. "
        "No unexplained forward-fill is used for missing dates; every final reindex below has zero missing targets.",
        "",
        "| Rule | Signal calendar rows | Held-asset calendar rows | Common evaluation rows | Missing targets after reindex |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in alignments:
        lines.append(
            f"| {row['rule']} ({row['signal_asset']} → {row['held_asset']}) | "
            f"{row['signal_calendar_rows']} | {row['held_calendar_rows']} | "
            f"{row['common_evaluation_rows']} | {row['missing_targets_after_reindex']} |",
        )

    lines += [
        "",
        "## First execution dates",
        "",
        "The first execution date below is the first actual BUY or SELL in the pre-tax strategy ledger; "
        "there is no trade or equity before the common evaluation start.",
        "",
        "| Rule | Frequency | First evaluation date | First strategy execution date |",
        "|---|---|---|---|",
    ]
    for rule in STRATEGIES:
        for frequency in FREQUENCIES:
            strategy = f"{rule}_{frequency}"
            lines.append(
                f"| {rule} | {frequency} | {start.date()} | {first_executions.get(strategy) or 'N/A'} |",
            )

    lines += [
        "",
        "## Strategy results",
        "",
        "Primary after-tax wealth and CAGR mean wealth after realized tax paid to date. "
        "`terminal_liquidation_*` values are non-mutating diagnostics that hypothetically sell the "
        "remaining terminal position, deduct the same transaction-cost rate, apply the frozen tax/loss-pool "
        "rules, and do not add a trade, change turnover, or change holding-period statistics.",
        "",
        "| Rule | Frequency | Tax mode | Ending value | CAGR | MaxDD | Calmar | Annual turnover | Mean hold (sessions) | Median hold (sessions) | Max hold (sessions) | Trades | Costs | Realized tax | Terminal wealth | Terminal CAGR |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics.iterrows():
        lines.append(
            f"| {row.rule} | {row.frequency} | {row.tax_mode} | "
            f"${row.ending_value:,.2f} | {_format_value(row.cagr, percent=True)} | "
            f"{_format_value(row.max_drawdown, percent=True)} | {_format_value(row.calmar)} | "
            f"{_format_value(row.annual_turnover)} | {_format_value(row.mean_holding_period_days)} | "
            f"{_format_value(row.median_holding_period_days)} | {_format_value(row.max_holding_period_days)} | "
            f"{int(row.number_of_trades)} | ${row.transaction_costs:,.2f} | ${row.tax_paid:,.2f} | "
            f"{_format_value(row.terminal_liquidation_wealth)} | "
            f"{_format_value(row.terminal_liquidation_cagr, percent=True)} |",
        )

    lines += [
        "",
        "## Turnover audit",
        "",
        f"The execution-cost rate is {execution_rate:.8f} (0 commission bps + 5 slippage bps). "
        "Annual turnover is the sum of `abs(trade_notional) / contemporaneous pretrade_equity` for "
        "included trades, excluding initial portfolio deployment and any hypothetical terminal liquidation, "
        "divided by calendar backtest years. Nonzero trade dates are the included rebalance dates; gross "
        "notional and trade counts are reported from the actual trade ledger.",
        "",
        "| Strategy | Frequency | Included normalized turnover | Calendar years | Annual turnover | Included trade dates/rebalances | Gross traded notional | Number of trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in turnover_audits:
        lines.append(
            f"| {row['strategy']} | {row['frequency']} | {row['included_normalized_turnover']:.9f} | "
            f"{row['years']:.9f} | {row['annual_turnover']:.9f} | {row['nonzero_trade_dates']} | "
            f"${row['gross_traded_notional']:,.2f} | {row['number_of_trades']} |",
        )

    lines += [
        "",
        "## Common-sample benchmarks",
        "",
        "The buy-and-hold SPY, QQQ, SSO, and QLD endpoints use the same common evaluation sample "
        "and frozen 5 bps execution cost for their initial deployment. They are descriptive benchmarks, "
        "not predictive evidence.",
        "",
        "| Benchmark | Start | End | CAGR | MaxDD | Calmar |",
        "|---|---|---|---:|---:|---:|",
    ]
    for _, row in benchmarks.iterrows():
        lines.append(
            f"| {row.asset} | {row.start} | {row.end} | {_format_value(row.cagr, percent=True)} | "
            f"{_format_value(row.max_drawdown, percent=True)} | {_format_value(row.calmar)} |",
        )
    lines += [
        "",
        "Tax semantics: `tax_paid` and `cumulative_realized_tax_paid` are realized taxes paid immediately "
        "under frozen average-cost/loss-pool accounting; unrealized appreciation is not taxed until a sale "
        "or the separate terminal diagnostic. CASH earns exactly 0%.",
        "",
        "MA=200 remains frozen, no parameter alternatives were searched, and this Phase 2 report makes no "
        "out-of-sample or Walk-Forward claim.",
    ]
    (output / "phase2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase2_ma200"))
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

    for name, (signal_asset, held_asset) in STRATEGIES.items():
        signal_prices = prices[signal_asset]["adjusted_close"]
        held_prices = prices[held_asset].loc[start:end]
        signal_eval = signal_prices.loc[start:end]
        for frequency in FREQUENCIES:
            # This is the frozen strategy path: full-history MA200 signal,
            # scheduled at the selected frozen frequency, then final
            # evaluation-calendar reindex to the held ETF.
            full_target = trend_target_next_open(signal_prices, frequency, lookback=200)
            targets = full_target.reindex(held_prices.index)
            if targets.isna().any():
                raise ValueError("signal and held-asset calendars are not aligned")
            if not signal_eval.index.equals(held_prices.index):
                raise ValueError("signal and held-asset evaluation calendars are not aligned")
            for mode, mode_tax_rate in (("pre_tax", None), ("after_tax", tax_rate)):
                strategy = f"{name}_{frequency}"
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
                    "rule": name,
                    "signal_asset": signal_asset,
                    "held_asset": held_asset,
                    "frequency": frequency,
                    "ma_window": 200,
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
                if mode == "pre_tax" and (name, frequency) in TURNOVER_AUDIT_KEYS:
                    turnover_audits.append({
                        "strategy": name,
                        "frequency": frequency,
                        **_turnover_audit(ledger, trade),
                    })
            parameters.append({"strategy": name, "frequency": frequency, "ma_window": 200, "searched": False})

    metrics = pd.DataFrame(rows)
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].reset_index(drop=True)
    after = metrics.loc[metrics.tax_mode.eq("after_tax")].reset_index(drop=True)
    if len(pre) != 12 or len(after) != 12:
        raise AssertionError("Phase 2 must produce 12 rows per tax mode")
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "ma200_results.csv", index=False)
    pd.concat(curves, ignore_index=True).to_csv(output / "equity_curve.csv", index=False)
    pd.concat(drawdowns, ignore_index=True).to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    tax_frame = (
        pd.concat(taxes, ignore_index=True)
        if taxes else pd.DataFrame(columns=["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid", "strategy", "tax_mode"])
    )
    tax_frame.to_csv(output / "tax_ledger.csv", index=False)
    pd.DataFrame(parameters).to_csv(output / "parameter_results.csv", index=False)

    benchmark_rows = []
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        benchmark_prices = prices[asset].loc[start:end]
        ledger, _, trade = buy_and_hold(
            benchmark_prices,
            initial_capital=capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        benchmark_rows.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    benchmarks = pd.DataFrame(benchmark_rows)
    _write_plots(
        pd.concat(curves, ignore_index=True),
        pd.concat(drawdowns, ignore_index=True),
        metrics,
        benchmarks,
        output,
    )
    _write_phase2_report(
        output,
        metrics,
        benchmarks,
        warmups,
        alignments,
        turnover_audits,
        first_executions,
        start=start,
        end=end,
        execution_rate=execution_rate,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 2 MA200 trend")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
