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
from market_timing_quant.portfolio import buy_and_hold, cash_hold, single_asset_timed_backtest
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open

FREQUENCIES = ("weekly", "monthly", "bimonthly", "quarterly")
STRATEGIES = {
    "QQQ_MA200_QQQ": ("QQQ", "QQQ"),
    "QQQ_MA200_QLD": ("QQQ", "QLD"),
    "SPY_MA200_SSO": ("SPY", "SSO"),
}


def _write_plots(curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame, benchmarks: pd.DataFrame, output: Path) -> None:
    pre = curves[curves.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], label=name, alpha=.75)
    plt.yscale("log"); plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    pre_dd = drawdowns[drawdowns.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, label=name, alpha=.75)
    plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for name, part in pre.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_dd else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values, label=name, alpha=.75)
        plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    plt.figure(figsize=(9, 7))
    points = metrics[metrics.tax_mode == "pre_tax"]
    plt.scatter(points.max_drawdown.abs(), points.cagr, label="MA200 strategies")
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows():
        plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR"); plt.legend(); plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase2_ma200"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD")}
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    capital = float(config["initial_capital"])
    rows, curves, drawdowns, positions, trades, taxes, parameters = [], [], [], [], [], [], []
    for name, (signal_asset, held_asset) in STRATEGIES.items():
        for frequency in FREQUENCIES:
            full_target = trend_target_next_open(prices[signal_asset].adjusted_close, frequency, lookback=200)
            held_prices = prices[held_asset].loc[start:end]
            targets = full_target.reindex(held_prices.index)
            if targets.isna().any():
                raise ValueError("signal and held-asset calendars are not aligned")
            for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                strategy = f"{name}_{frequency}"
                ledger, position, trade, tax = single_asset_timed_backtest(
                    held_prices, targets, initial_capital=capital,
                    commission_bps=float(config["execution"]["commission_bps"]),
                    slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                )
                metric = performance_metrics(ledger, trade, capital)
                metric.update({"strategy": strategy, "rule": name, "signal_asset": signal_asset,
                               "held_asset": held_asset, "frequency": frequency, "ma_window": 200,
                               "tax_mode": mode})
                rows.append(metric)
                curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, tax_mode=mode).reset_index(names="date"))
                positions.append(position.assign(strategy=strategy, tax_mode=mode))
                if len(trade): trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                if len(tax): taxes.append(tax.assign(strategy=strategy, tax_mode=mode))
            parameters.append({"strategy": name, "frequency": frequency, "ma_window": 200, "searched": False})
    metrics = pd.DataFrame(rows)
    metrics[metrics.tax_mode == "pre_tax"].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode == "after_tax"].to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "ma200_results.csv", index=False)
    pd.concat(curves, ignore_index=True).to_csv(output / "equity_curve.csv", index=False)
    pd.concat(drawdowns, ignore_index=True).to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    (pd.concat(taxes, ignore_index=True) if taxes else pd.DataFrame(columns=["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid", "strategy", "tax_mode"])).to_csv(output / "tax_ledger.csv", index=False)
    pd.DataFrame(parameters).to_csv(output / "parameter_results.csv", index=False)
    benchmark_rows = []
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        ledger, _, trade = buy_and_hold(prices[asset].loc[start:end], initial_capital=capital,
                                        commission_bps=float(config["execution"]["commission_bps"]),
                                        slippage_bps=float(config["execution"]["slippage_bps"]))
        benchmark_rows.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    benchmarks = pd.DataFrame(benchmark_rows)
    _write_plots(pd.concat(curves, ignore_index=True), pd.concat(drawdowns, ignore_index=True), metrics, benchmarks, output)
    lines = [
        "# Phase 2 — MA200 Simple Trend", "",
        "Signal price: adjusted close of the unleveraged underlying. Signal at close t; execution no earlier than open t+1.",
        "The MA window is frozen at 200 trading sessions. No neighboring MA values were searched.",
        "Bi-monthly is anchored to the first trading day of Jan/Mar/May/Jul/Sep/Nov.",
        "", "| Rule | Frequency | Pre-tax CAGR | Pre-tax MaxDD | After-tax CAGR | After-tax MaxDD |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name in STRATEGIES:
        for frequency in FREQUENCIES:
            strategy = f"{name}_{frequency}"
            a = metrics[(metrics.strategy == strategy) & (metrics.tax_mode == "pre_tax")].iloc[0]
            b = metrics[(metrics.strategy == strategy) & (metrics.tax_mode == "after_tax")].iloc[0]
            lines.append(f"| {name} | {frequency} | {a.cagr:.2%} | {a.max_drawdown:.2%} | {b.cagr:.2%} | {b.max_drawdown:.2%} |")
    lines += ["", "No parameter selection or OOS claim is made in Phase 2."]
    (output / "phase2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
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

