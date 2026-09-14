from __future__ import annotations

import argparse
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from market_timing_quant.configuration import load_config
from market_timing_quant.data import run_data_audit
from market_timing_quant.metrics import add_rolling_metrics, drawdown_series, performance_metrics, period_returns
from market_timing_quant.portfolio import cash_hold, static_allocation_backtest

PAIRS = (
    ("SPY", "SSO"), ("SPY", "QLD"), ("QQQ", "SSO"), ("QQQ", "QLD"),
    ("SSO", "QLD"), ("QQQ", "CASH"), ("QLD", "CASH"), ("SSO", "CASH"),
)
TRIPLES = (
    ("SPY", "QQQ", "SSO"), ("SPY", "QQQ", "QLD"), ("QQQ", "SSO", "QLD"),
    ("QQQ", "QLD", "CASH"), ("SPY", "SSO", "CASH"),
)
FREQUENCIES = ("monthly", "quarterly")


def candidate_allocations() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for assets in PAIRS:
        for units in range(21):
            weights = (units / 20, 1 - units / 20)
            rows.append({"kind": "pair", "assets": assets, "weights": dict(zip(assets, weights, strict=True))})
    for assets in TRIPLES:
        for first in range(11):
            for second in range(11 - first):
                third = 10 - first - second
                weights = (first / 10, second / 10, third / 10)
                rows.append({"kind": "triple", "assets": assets, "weights": dict(zip(assets, weights, strict=True))})
    return rows


def strategy_name(frequency: str, kind: str, assets: tuple[str, ...], weights: dict[str, float]) -> str:
    allocation = "_".join(f"{asset}{int(round(weights[asset] * 100)):03d}" for asset in assets)
    return f"{frequency}_{kind}_{allocation}"


def mark_pareto(frame: pd.DataFrame) -> pd.Series:
    result = pd.Series(False, index=frame.index)
    ordered = frame.assign(risk=frame["max_drawdown"].abs()).sort_values(["risk", "cagr"], ascending=[True, False])
    best = -np.inf
    for index, row in ordered.iterrows():
        if row["cagr"] > best + 1e-12:
            result.loc[index] = True
            best = row["cagr"]
    return result


def _plot_frontier(frame: pd.DataFrame, path: Path, title: str) -> None:
    plt.figure(figsize=(10, 7))
    plt.scatter(frame["max_drawdown"].abs(), frame["cagr"], s=9, alpha=0.25)
    pareto = frame[frame["pareto"]].sort_values("max_drawdown", key=lambda x: x.abs())
    plt.plot(pareto["max_drawdown"].abs(), pareto["cagr"], color="black", linewidth=1.2, label="Pareto frontier")
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        point = frame[(frame["benchmark_asset"] == asset) & (frame["frequency"] == "monthly")].iloc[0]
        plt.scatter(abs(point.max_drawdown), point.cagr, s=45)
        plt.annotate(asset, (abs(point.max_drawdown), point.cagr))
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR"); plt.title(title); plt.legend()
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def _unique_benchmarks(metrics: pd.DataFrame) -> pd.DataFrame:
    pieces = [metrics]
    # All-cash and pure-asset endpoints occur in several mandated scans. Keep every
    # experiment row, but identify one canonical row per benchmark for chart labels.
    metrics["benchmark_asset"] = None
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        for frequency in FREQUENCIES:
            matches = metrics[(metrics["frequency"] == frequency) & (metrics[f"weight_{asset}"] == 1.0)]
            if len(matches):
                metrics.loc[matches.index[0], "benchmark_asset"] = asset
    return metrics


def _write_phase1_report(output: Path, pre: pd.DataFrame) -> None:
    best_cagr = pre.loc[pre.cagr.idxmax()]
    lowest_risk = pre.loc[pre.max_drawdown.abs().idxmin()]
    report = [
        "# Phase 1 — Static Allocation Efficient Frontier", "",
        "Frozen scans completed: 8 two-asset pairs at 5% steps and 5 three-asset sets at 10% steps, each with monthly and quarterly rebalancing.",
        "Both pre-tax and Simplified Japan Taxable results use 5 bps slippage, 0 bps commission, average cost, and immediate tax payment.",
        "", f"Candidates per tax mode: `{len(pre)}`.",
        f"Highest pre-tax CAGR: `{best_cagr.strategy}` — {best_cagr.cagr:.2%} CAGR, {best_cagr.max_drawdown:.2%} MaxDD.",
        f"Lowest absolute pre-tax drawdown: `{lowest_risk.strategy}` — {lowest_risk.cagr:.2%} CAGR, {lowest_risk.max_drawdown:.2%} MaxDD.",
        "", "This phase reports the frozen grid without selecting or tuning a dynamic strategy.",
    ]
    (output / "phase1_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase1_static_frontier"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD")}
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    prices = {asset: frame.loc[start:end] for asset, frame in prices.items()}
    capital = float(config["initial_capital"])
    candidates = candidate_allocations()
    metrics_by_mode: dict[str, list[dict[str, object]]] = {"pre_tax": [], "after_tax": []}
    curve_tables, drawdown_tables, position_tables, trade_tables, tax_tables = [], [], [], [], []
    for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
        for frequency, candidate in product(FREQUENCIES, candidates):
            assets = candidate["assets"]
            weights = candidate["weights"]
            name = strategy_name(frequency, candidate["kind"], assets, weights)
            risky = {asset: weight for asset, weight in weights.items() if asset != "CASH" and weight > 0}
            if not risky:
                index = prices["SPY"].index
                ledger, positions, trades = cash_hold(index, capital)
                ledger["tax_paid"] = 0.0
                taxes = pd.DataFrame(columns=["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid"])
            else:
                ledger, positions, trades, taxes = static_allocation_backtest(
                    prices, risky, initial_capital=capital,
                    commission_bps=float(config["execution"]["commission_bps"]),
                    slippage_bps=float(config["execution"]["slippage_bps"]),
                    frequency=frequency, tax_rate=tax_rate,
                )
            metric = performance_metrics(ledger, trades, capital)
            metric.update({"strategy": name, "tax_mode": mode, "frequency": frequency, "kind": candidate["kind"]})
            for asset in ("SPY", "QQQ", "SSO", "QLD", "CASH"):
                metric[f"weight_{asset}"] = float(weights.get(asset, 0.0))
            metrics_by_mode[mode].append(metric)
            curve_tables.append(ledger[["equity"]].assign(strategy=name, tax_mode=mode).reset_index())
            drawdown_tables.append(drawdown_series(ledger["equity"], capital).rename("drawdown").to_frame().assign(strategy=name, tax_mode=mode).reset_index(names="date"))
            if len(positions): position_tables.append(positions.assign(strategy=name, tax_mode=mode))
            if len(trades): trade_tables.append(trades.assign(strategy=name, tax_mode=mode))
            if len(taxes): tax_tables.append(taxes.assign(strategy=name, tax_mode=mode))
    pre = _unique_benchmarks(pd.DataFrame(metrics_by_mode["pre_tax"]))
    after = _unique_benchmarks(pd.DataFrame(metrics_by_mode["after_tax"]))
    pre["pareto"] = mark_pareto(pre); after["pareto"] = mark_pareto(after)
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    frontier = pd.concat([pre, after], ignore_index=True)
    frontier.to_csv(output / "static_frontier.csv", index=False)
    frontier.to_csv(output / "parameter_results.csv", index=False)
    pd.concat(curve_tables, ignore_index=True).to_csv(output / "equity_curve.csv", index=False)
    pd.concat(drawdown_tables, ignore_index=True).to_csv(output / "drawdown.csv", index=False)
    pd.concat(position_tables, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trade_tables, ignore_index=True).to_csv(output / "trades.csv", index=False)
    (pd.concat(tax_tables, ignore_index=True) if tax_tables else pd.DataFrame(columns=["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid", "strategy", "tax_mode"])).to_csv(output / "tax_ledger.csv", index=False)
    for mode, table in (("pre_tax", pre), ("after_tax", after)):
        _plot_frontier(table, output / f"static_frontier_{mode}.png", f"Static allocation frontier — {mode.replace('_', ' ')}")
    _plot_frontier(pre, output / "cagr_maxdd_scatter.png", "Static allocation frontier — pre tax")
    # Required generic plots use the Pareto strategies to keep files readable.
    pareto_names = set(pre.loc[pre.pareto, "strategy"])
    curves = pd.concat(curve_tables, ignore_index=True)
    pre_curves = curves[curves.tax_mode == "pre_tax"]
    plt.figure(figsize=(11, 6))
    for name in list(pareto_names)[:20]:
        series = pre_curves.loc[pre_curves.strategy == name, ["date", "equity"]].set_index("date")["equity"]
        if len(series): plt.plot(series.index, series / series.iloc[0], alpha=.7)
    plt.yscale("log"); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    dds = pd.concat(drawdown_tables, ignore_index=True)
    plt.figure(figsize=(11, 6))
    for name in list(pareto_names)[:20]:
        part = dds[(dds.tax_mode == "pre_tax") & (dds.strategy == name)]
        if len(part): plt.plot(part["date"], part["drawdown"], alpha=.7)
    plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    # Rolling plots are derived from the same daily equity records.
    for filename, window, annualize in (("rolling_returns.png", 252, False), ("rolling_maxdd.png", 252, True)):
        plt.figure(figsize=(11, 6))
        for name in list(pareto_names)[:20]:
            series = pre_curves.loc[pre_curves.strategy == name, ["date", "equity"]].set_index("date")["equity"]
            values = series.rolling(window).apply(lambda x: (x.iloc[-1] / x.iloc[0] - 1) if not annualize else (x / x.cummax() - 1).min())
            plt.plot(values.index, values, alpha=.7)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    _write_phase1_report(output, pre)
    return output


def finish_existing_output(output: Path) -> Path:
    """Finish plots/report after an interrupted post-processing step."""
    pre = pd.read_csv(output / "metrics_pre_tax.csv")
    if "pareto" not in pre:
        pre["pareto"] = mark_pareto(pre)
    pareto_names = set(pre.loc[pre.pareto.astype(bool), "strategy"])

    def selected_chunks(path: Path) -> pd.DataFrame:
        kept = []
        for chunk in pd.read_csv(path, chunksize=250_000, parse_dates=[0]):
            if chunk.columns[0] != "date":
                chunk = chunk.rename(columns={chunk.columns[0]: "date"})
            kept.append(chunk[(chunk.tax_mode == "pre_tax") & chunk.strategy.isin(pareto_names)])
        return pd.concat(kept, ignore_index=True)

    curves = selected_chunks(output / "equity_curve.csv")
    dds = selected_chunks(output / "drawdown.csv")
    plt.figure(figsize=(11, 6))
    for name, part in curves.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.7)
    plt.yscale("log"); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    plt.figure(figsize=(11, 6))
    for name, part in dds.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.7)
    plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_drawdown in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for name, part in curves.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_drawdown else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values, alpha=.7)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    _write_phase1_report(output, pre)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 1 static allocation frontier")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--resume-output", type=Path, default=None)
    args = parser.parse_args()
    print(finish_existing_output(args.resume_output) if args.resume_output else run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
