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

from experiments.phase2_ma200 import FREQUENCIES, STRATEGIES
from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import drawdown_series, performance_metrics
from market_timing_quant.portfolio import buy_and_hold, single_asset_timed_backtest
from market_timing_quant.signals import trend_target_next_open
from market_timing_quant.walk_forward import expanding_calendar_year_folds, fold_table


def _segment_metrics(ledger: pd.DataFrame, trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                     prior_equity: float, strategy: str, mode: str, year: int) -> dict[str, object]:
    segment = ledger.loc[start:end].copy()
    segment.iloc[0, segment.columns.get_loc("daily_return")] = segment.equity.iloc[0] / prior_equity - 1.0
    segment_trades = trades[(trades.date >= start) & (trades.date <= end)] if len(trades) else trades
    result = performance_metrics(segment, segment_trades, prior_equity)
    result.update({"strategy": strategy, "tax_mode": mode, "test_year": year})
    return result


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_walk_forward_fixed_ma200"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD")}
    end = min(frame.index.max() for frame in prices.values())
    folds = expanding_calendar_year_folds(prices["SSO"].loc[:end].index)
    oos_start = folds[0].test_start
    capital = float(config["initial_capital"])
    rows, fold_rows, curves, drawdowns, positions, trades, taxes = [], [], [], [], [], [], []
    for rule, (signal_asset, held_asset) in STRATEGIES.items():
        held_prices = prices[held_asset].loc[oos_start:end]
        for frequency in FREQUENCIES:
            target = trend_target_next_open(prices[signal_asset].adjusted_close, frequency, 200).reindex(held_prices.index)
            for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                strategy = f"{rule}_{frequency}_OOS"
                ledger, position, trade, tax = single_asset_timed_backtest(
                    held_prices, target, initial_capital=capital,
                    commission_bps=float(config["execution"]["commission_bps"]),
                    slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                )
                metric = performance_metrics(ledger, trade, capital)
                metric.update({"strategy": strategy, "rule": rule, "frequency": frequency,
                               "ma_window": 200, "tax_mode": mode, "result_type": "stitched_OOS"})
                rows.append(metric)
                for fold in folds:
                    prior = capital if fold.test_year == folds[0].test_year else float(ledger.loc[ledger.index < fold.test_start, "equity"].iloc[-1])
                    fold_rows.append(_segment_metrics(ledger, trade, fold.test_start, fold.test_end,
                                                      prior, strategy, mode, fold.test_year))
                curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, tax_mode=mode).reset_index(names="date"))
                positions.append(position.assign(strategy=strategy, tax_mode=mode))
                if len(trade): trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                if len(tax): taxes.append(tax.assign(strategy=strategy, tax_mode=mode))
    metrics = pd.DataFrame(rows)
    metrics[metrics.tax_mode == "pre_tax"].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode == "after_tax"].to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "oos_results.csv", index=False)
    pd.DataFrame(fold_rows).to_csv(output / "oos_fold_metrics.csv", index=False)
    fold_table(folds).to_csv(output / "walk_forward_folds.csv", index=False)
    pd.DataFrame([{"ma_window": 200, "selected": False, "selection_reason": "fixed baseline; no optimization"}]).to_csv(output / "parameter_results.csv", index=False)
    curve_table = pd.concat(curves, ignore_index=True); curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table = pd.concat(drawdowns, ignore_index=True); dd_table.to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    pd.concat(taxes, ignore_index=True).to_csv(output / "tax_ledger.csv", index=False)
    pre_curves = curve_table[curve_table.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre_curves.groupby("strategy"):
        plt.plot(part.date, part.equity / capital, label=name, alpha=.7)
    plt.yscale("log"); plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    pre_dd = dd_table[dd_table.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name, part in pre_dd.groupby("strategy"): plt.plot(part.date, part.drawdown, alpha=.7)
    plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for _, part in pre_curves.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_dd else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values, alpha=.7)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    pre = metrics[metrics.tax_mode == "pre_tax"]
    plt.figure(figsize=(9, 7)); plt.scatter(pre.max_drawdown.abs(), pre.cagr)
    for _, row in pre.iterrows(): plt.annotate(row.strategy.replace("_OOS", ""), (abs(row.max_drawdown), row.cagr), fontsize=6)
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("OOS CAGR"); plt.tight_layout(); plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()
    lines = [
        "# Fixed-Rule Chronological OOS — MA200", "",
        "Frozen initial training interval: 2006-06-21 through 2012-12-31. Annual test folds run from 2013 through the latest 2026 YTD session.",
        "MA200 is the already-frozen baseline, so no parameter is fitted or selected in any fold. The continuous OOS ledger concatenates all test years without resetting holdings, taxes, or loss pools.",
        "", "| Rule | Frequency | OOS pre-tax CAGR | OOS MaxDD | OOS after-tax CAGR |", "|---|---|---:|---:|---:|",
    ]
    for _, row in pre.sort_values(["rule", "frequency"]).iterrows():
        after = metrics[(metrics.strategy == row.strategy) & (metrics.tax_mode == "after_tax")].iloc[0]
        lines.append(f"| {row.rule} | {row.frequency} | {row.cagr:.2%} | {row.max_drawdown:.2%} | {after.cagr:.2%} |")
    lines += [
        "", "Parameter selection remains disabled: the frozen specification does not provide numeric minimum-CAGR and maximum-MaxDD constraints required by Section 24.",
        "This run validates only fixed MA200 behavior and does not authorize an unspecified Phase 7 state machine.",
    ]
    (output / "oos_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Fixed MA200 expanding-window OOS prerequisite")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
