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

from experiments.phase2_ma200 import FREQUENCIES, STRATEGIES
from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import drawdown_series, performance_metrics
from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.signals import trend_target_next_open

MA_WINDOWS = (150, 175, 200, 225, 250)


def parameter_grid() -> tuple[int, ...]:
    return MA_WINDOWS


def _heatmap(metrics: pd.DataFrame, mode: str, output: Path) -> None:
    table = metrics[metrics.tax_mode == mode].pivot(index=["rule", "frequency"], columns="ma_window", values="cagr")
    figure, axis = plt.subplots(figsize=(8, 8))
    image = axis.imshow(table.to_numpy(), aspect="auto", cmap="viridis")
    axis.set_xticks(range(len(table.columns)), labels=table.columns)
    axis.set_yticks(range(len(table.index)), labels=[f"{rule} / {frequency}" for rule, frequency in table.index], fontsize=8)
    axis.set_xlabel("Moving-average window"); axis.set_title(f"MA stability CAGR — {mode.replace('_', ' ')}")
    figure.colorbar(image, ax=axis, label="CAGR")
    figure.tight_layout(); figure.savefig(output, dpi=150); plt.close(figure)


def _standard_plots(curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame, output: Path) -> None:
    # Show only monthly lines in generic time-series figures; all 120 results
    # remain in the CSV artifacts and both heatmaps.
    selected_metrics = metrics[(metrics.tax_mode == "pre_tax") & (metrics.frequency == "monthly")]
    names = set(selected_metrics.strategy)
    selected = curves[(curves.tax_mode == "pre_tax") & curves.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.65, label=name)
    plt.yscale("log"); plt.legend(fontsize=6, ncol=3); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    selected_dd = drawdowns[(drawdowns.tax_mode == "pre_tax") & drawdowns.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.65, label=name)
    plt.legend(fontsize=6, ncol=3); plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for name, part in selected.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_dd else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values, alpha=.65)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    pre = metrics[metrics.tax_mode == "pre_tax"]
    plt.figure(figsize=(9, 7)); plt.scatter(pre.max_drawdown.abs(), pre.cagr, c=pre.ma_window, cmap="viridis", alpha=.7)
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR"); plt.colorbar(label="MA window")
    plt.tight_layout(); plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase3_ma_stability"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD")}
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    capital = float(config["initial_capital"])
    rows, curves, drawdowns, positions, trades, taxes = [], [], [], [], [], []
    for name, (signal_asset, held_asset) in STRATEGIES.items():
        held_prices = prices[held_asset].loc[start:end]
        for frequency in FREQUENCIES:
            for window in MA_WINDOWS:
                targets = trend_target_next_open(prices[signal_asset].adjusted_close, frequency, lookback=window).reindex(held_prices.index)
                if targets.isna().any():
                    raise ValueError("signal and held-asset calendars are not aligned")
                for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                    strategy = f"{name}_{frequency}_MA{window}"
                    ledger, position, trade, tax = single_asset_timed_backtest(
                        held_prices, targets, initial_capital=capital,
                        commission_bps=float(config["execution"]["commission_bps"]),
                        slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                    )
                    metric = performance_metrics(ledger, trade, capital)
                    metric.update({"strategy": strategy, "rule": name, "signal_asset": signal_asset,
                                   "held_asset": held_asset, "frequency": frequency,
                                   "ma_window": window, "tax_mode": mode})
                    rows.append(metric)
                    curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                    drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, tax_mode=mode).reset_index(names="date"))
                    positions.append(position.assign(strategy=strategy, tax_mode=mode))
                    if len(trade): trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                    if len(tax): taxes.append(tax.assign(strategy=strategy, tax_mode=mode))
    metrics = pd.DataFrame(rows)
    metrics[metrics.tax_mode == "pre_tax"].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode == "after_tax"].to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "ma_parameter_surface.csv", index=False)
    metrics.to_csv(output / "parameter_results.csv", index=False)
    curve_table = pd.concat(curves, ignore_index=True); curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table = pd.concat(drawdowns, ignore_index=True); dd_table.to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    pd.concat(taxes, ignore_index=True).to_csv(output / "tax_ledger.csv", index=False)
    _heatmap(metrics, "pre_tax", output / "ma_stability_heatmap.png")
    _heatmap(metrics, "after_tax", output / "ma_stability_heatmap_after_tax.png")
    _standard_plots(curve_table, dd_table, metrics, output)
    pre = metrics[metrics.tax_mode == "pre_tax"]
    lines = [
        "# Phase 3 — MA Parameter Stability", "",
        "Frozen MA windows: 150, 175, 200, 225, 250. No other lookback was evaluated.",
        "Results are full-sample stability descriptions, not parameter selection and not OOS evidence.",
        "", "| Rule | Frequency | CAGR range | MaxDD range | Best-minus-worst CAGR |", "|---|---|---:|---:|---:|",
    ]
    for (rule, frequency), group in pre.groupby(["rule", "frequency"], sort=False):
        lines.append(
            f"| {rule} | {frequency} | {group.cagr.min():.2%}–{group.cagr.max():.2%} | "
            f"{group.max_drawdown.min():.2%}–{group.max_drawdown.max():.2%} | {(group.cagr.max()-group.cagr.min()):.2%} |"
        )
    lines += ["", "No isolated best window is promoted. Walk-forward/OOS selection remains deferred to the frozen later stage."]
    (output / "phase3_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
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
