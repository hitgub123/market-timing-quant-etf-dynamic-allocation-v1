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

from experiments.phase2_ma200 import FREQUENCIES
from experiments.phase4_absolute_momentum import MOMENTUM_WINDOWS
from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import drawdown_series, performance_metrics
from market_timing_quant.portfolio import buy_and_hold, rotation_backtest
from market_timing_quant.signals import relative_momentum_target_next_open

MAPPINGS = {
    "RELATIVE_MOMENTUM_1X": {"SPY": "SPY", "QQQ": "QQQ"},
    "RELATIVE_MOMENTUM_2X": {"SPY": "SSO", "QQQ": "QLD"},
}


def _plots(curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame, benchmarks: pd.DataFrame, output: Path) -> None:
    pre = curves[curves.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.65, label=name)
    plt.yscale("log"); plt.legend(fontsize=6, ncol=3); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    pre_dd = drawdowns[drawdowns.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.65)
    plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for _, part in pre.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_dd else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values, alpha=.65)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    points = metrics[metrics.tax_mode == "pre_tax"]
    plt.figure(figsize=(9, 7)); plt.scatter(points.max_drawdown.abs(), points.cagr, c=points.momentum_window, cmap="viridis", label="Relative momentum")
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows(): plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR"); plt.colorbar(label="Momentum window"); plt.legend()
    plt.tight_layout(); plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase5_relative_momentum"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD")}
    signal_index = prices["SPY"].index.intersection(prices["QQQ"].index)
    signal_spy = prices["SPY"].loc[signal_index, "adjusted_close"]
    signal_qqq = prices["QQQ"].loc[signal_index, "adjusted_close"]
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    evaluation_index = prices["SSO"].loc[start:end].index
    capital = float(config["initial_capital"])
    rows, curves, drawdowns, positions, trades, taxes = [], [], [], [], [], []
    for rule, mapping in MAPPINGS.items():
        held_assets = list(mapping.values())
        held_prices = {asset: prices[asset].loc[evaluation_index] for asset in held_assets}
        for frequency in FREQUENCIES:
            for window in MOMENTUM_WINDOWS:
                underlying = relative_momentum_target_next_open(signal_spy, signal_qqq, frequency, window).reindex(evaluation_index)
                if underlying.isna().any().any(): raise ValueError("signal and held-asset calendars are not aligned")
                targets = pd.DataFrame({mapping["SPY"]: underlying.SPY, mapping["QQQ"]: underlying.QQQ}, index=evaluation_index)
                for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                    strategy = f"{rule}_{frequency}_{window}D"
                    ledger, position, trade, tax = rotation_backtest(
                        held_prices, targets, initial_capital=capital,
                        commission_bps=float(config["execution"]["commission_bps"]),
                        slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                    )
                    metric = performance_metrics(ledger, trade, capital)
                    metric.update({"strategy": strategy, "rule": rule, "frequency": frequency,
                                   "momentum_window": window, "tax_mode": mode})
                    rows.append(metric)
                    curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                    drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, tax_mode=mode).reset_index(names="date"))
                    positions.append(position.assign(strategy=strategy, tax_mode=mode))
                    if len(trade): trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                    if len(tax): taxes.append(tax.assign(strategy=strategy, tax_mode=mode))
    metrics = pd.DataFrame(rows)
    metrics[metrics.tax_mode == "pre_tax"].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode == "after_tax"].to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "relative_momentum_results.csv", index=False)
    metrics.to_csv(output / "parameter_results.csv", index=False)
    curve_table = pd.concat(curves, ignore_index=True); curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table = pd.concat(drawdowns, ignore_index=True); dd_table.to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    pd.concat(taxes, ignore_index=True).to_csv(output / "tax_ledger.csv", index=False)
    benchmarks = []
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        ledger, _, trade = buy_and_hold(prices[asset].loc[evaluation_index], initial_capital=capital,
                                        commission_bps=float(config["execution"]["commission_bps"]),
                                        slippage_bps=float(config["execution"]["slippage_bps"]))
        benchmarks.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    _plots(curve_table, dd_table, metrics, pd.DataFrame(benchmarks), output)
    pre = metrics[metrics.tax_mode == "pre_tax"]
    lines = [
        "# Phase 5 — Relative Momentum", "",
        "Momentum is calculated only from SPY and QQQ adjusted closes. Leveraged ETF momentum is never used for selection.",
        "Both non-positive selects CASH. Exact positive ties deterministically select SPY because the frozen specification does not define a tie-break.",
        "", "| Mapping | Frequency | Window | Pre-tax CAGR | MaxDD | After-tax CAGR |", "|---|---|---:|---:|---:|---:|",
    ]
    for _, a in pre.sort_values(["rule", "frequency", "momentum_window"]).iterrows():
        b = metrics[(metrics.strategy == a.strategy) & (metrics.tax_mode == "after_tax")].iloc[0]
        lines.append(f"| {a.rule} | {a.frequency} | {a.momentum_window} | {a.cagr:.2%} | {a.max_drawdown:.2%} | {b.cagr:.2%} |")
    lines += ["", "These are full-sample descriptions. No lookback or frequency is selected, and no OOS claim is made."]
    (output / "phase5_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 5 relative momentum")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

