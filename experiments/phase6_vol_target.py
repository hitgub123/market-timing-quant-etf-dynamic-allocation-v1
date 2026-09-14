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
from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import drawdown_series, performance_metrics
from market_timing_quant.portfolio import buy_and_hold, continuous_weight_backtest
from market_timing_quant.signals import rebalance_mask, volatility_target_next_open

VOL_WINDOWS = (20, 40, 60)
TARGET_VOLS = (0.10, 0.15, 0.20, 0.25, 0.30)
ASSETS = ("SPY", "QQQ", "SSO", "QLD")


def parameter_grid() -> tuple[tuple[int, float], ...]:
    return tuple((window, target) for window in VOL_WINDOWS for target in TARGET_VOLS)


def _plots(curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame, benchmarks: pd.DataFrame, output: Path) -> None:
    names = set(metrics[(metrics.tax_mode == "pre_tax") & (metrics.frequency == "monthly") & (metrics.target_vol == .15)].strategy)
    pre = curves[(curves.tax_mode == "pre_tax") & curves.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in pre.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.7, label=name)
    plt.yscale("log"); plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    pre_dd = drawdowns[(drawdowns.tax_mode == "pre_tax") & drawdowns.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in pre_dd.groupby("strategy"): plt.plot(part.date, part.drawdown, alpha=.7, label=name)
    plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for _, part in pre.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_dd else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values, alpha=.7)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    points = metrics[metrics.tax_mode == "pre_tax"]
    plt.figure(figsize=(9, 7)); plt.scatter(points.max_drawdown.abs(), points.cagr, c=points.target_vol, cmap="viridis", alpha=.55)
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows(): plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR"); plt.colorbar(label="Target volatility"); plt.legend()
    plt.tight_layout(); plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase6_vol_target"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ASSETS}
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    capital = float(config["initial_capital"])
    rows, curves, drawdowns, positions, trades, taxes = [], [], [], [], [], []
    for asset in ASSETS:
        held_prices = prices[asset].loc[start:end]
        for frequency in FREQUENCIES:
            schedule = rebalance_mask(held_prices.index, frequency)
            for window, target_vol in parameter_grid():
                target = volatility_target_next_open(prices[asset].adjusted_close, frequency, window, target_vol).reindex(held_prices.index)
                if target.isna().any(): raise ValueError("volatility target and held-asset calendars are not aligned")
                for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                    strategy = f"{asset}_VOL{window}_TARGET{int(target_vol*100):02d}_{frequency}"
                    ledger, position, trade, tax = continuous_weight_backtest(
                        held_prices, target, schedule, initial_capital=capital,
                        commission_bps=float(config["execution"]["commission_bps"]),
                        slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                    )
                    metric = performance_metrics(ledger, trade, capital)
                    metric.update({"strategy": strategy, "asset": asset, "frequency": frequency,
                                   "vol_window": window, "target_vol": target_vol, "tax_mode": mode})
                    rows.append(metric)
                    curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                    drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, tax_mode=mode).reset_index(names="date"))
                    positions.append(position.assign(strategy=strategy, tax_mode=mode))
                    if len(trade): trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                    if len(tax): taxes.append(tax.assign(strategy=strategy, tax_mode=mode))
    metrics = pd.DataFrame(rows)
    metrics[metrics.tax_mode == "pre_tax"].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode == "after_tax"].to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "vol_parameter_surface.csv", index=False)
    metrics.to_csv(output / "parameter_results.csv", index=False)
    curve_table = pd.concat(curves, ignore_index=True); curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table = pd.concat(drawdowns, ignore_index=True); dd_table.to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    pd.concat(taxes, ignore_index=True).to_csv(output / "tax_ledger.csv", index=False)
    benchmarks = []
    for asset in ASSETS:
        ledger, _, trade = buy_and_hold(prices[asset].loc[start:end], initial_capital=capital,
                                        commission_bps=float(config["execution"]["commission_bps"]),
                                        slippage_bps=float(config["execution"]["slippage_bps"]))
        benchmarks.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    _plots(curve_table, dd_table, metrics, pd.DataFrame(benchmarks), output)
    pre = metrics[metrics.tax_mode == "pre_tax"]
    lines = [
        "# Phase 6 — Volatility Targeting", "",
        "Frozen realized-volatility windows: 20, 40, 60 sessions. Frozen targets: 10%, 15%, 20%, 25%, 30%.",
        "Risk weight is clipped to [0, 1]; remaining capital is USD cash at 0%; no external margin is used.",
        "Because the frozen section does not name an asset subset, this run applies each asset's own realized volatility separately to SPY, QQQ, SSO, and QLD. TQQQ remains locked.",
        "", "| Asset | Frequency | Best full-sample CAGR | Associated MaxDD | Window | Target |", "|---|---|---:|---:|---:|---:|",
    ]
    for (asset, frequency), group in pre.groupby(["asset", "frequency"], sort=False):
        row = group.loc[group.cagr.idxmax()]
        lines.append(f"| {asset} | {frequency} | {row.cagr:.2%} | {row.max_drawdown:.2%} | {row.vol_window} | {row.target_vol:.0%} |")
    lines += ["", "The table is descriptive only. It does not select parameters or establish OOS performance."]
    (output / "phase6_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 6 volatility targeting")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

