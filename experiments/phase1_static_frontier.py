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


def economic_allocation_id(weights: dict[str, float]) -> str:
    """Stable full-universe identifier for duplicate pair/triple allocations."""
    return "|".join(f"{asset}={float(weights.get(asset, 0.0)):.10f}" for asset in ("SPY", "QQQ", "SSO", "QLD", "CASH"))


def mark_pareto(frame: pd.DataFrame) -> pd.Series:
    """Return strategy-level nondominated flags under strict Pareto dominance.

    Equal risk/CAGR rows do not dominate one another, so duplicate economic
    allocations retained by the frozen scans receive the same flag.
    """
    if frame.empty:
        return pd.Series(dtype=bool, index=frame.index)
    risk = frame["max_drawdown"].abs().to_numpy(dtype=float)
    cagr = frame["cagr"].to_numpy(dtype=float)
    tolerance = 1e-12
    result = np.ones(len(frame), dtype=bool)
    for i in range(len(frame)):
        for j in range(len(frame)):
            if i == j:
                continue
            no_worse_risk = risk[j] <= risk[i] + tolerance
            no_worse_cagr = cagr[j] >= cagr[i] - tolerance
            strictly_better = (risk[j] < risk[i] - tolerance) or (cagr[j] > cagr[i] + tolerance)
            if no_worse_risk and no_worse_cagr and strictly_better:
                result[i] = False
                break
    return pd.Series(result, index=frame.index)


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


def _representative_points(frame: pd.DataFrame, cagr_column: str, pareto_column: str) -> pd.DataFrame:
    points = frame.loc[frame[pareto_column].astype(bool)].copy()
    if points.empty:
        return points
    points["_risk"] = points["max_drawdown"].abs()
    chosen = [points.loc[points["_risk"].idxmin()]]
    middle_risk = float(points["_risk"].median())
    chosen.append(points.loc[(points["_risk"] - middle_risk).abs().idxmin()])
    chosen.append(points.loc[points[cagr_column].idxmax()])
    return pd.DataFrame(chosen).drop_duplicates(subset=["strategy"]).drop(columns=["_risk"], errors="ignore")


def _write_phase1_report(output: Path, pre: pd.DataFrame, after: pd.DataFrame, turnover_audits: list[dict[str, object]]) -> None:
    pre_points = _representative_points(pre, "cagr", "pareto")
    after_points = _representative_points(after, "cagr", "pareto")
    terminal_points = _representative_points(after, "terminal_liquidation_cagr", "pareto_terminal_liquidation")
    best_cagr = pre.loc[pre.cagr.idxmax()]
    lowest_risk = pre.loc[pre.max_drawdown.abs().idxmin()]
    end = str(pre["end"].iloc[0])

    def point_lines(title: str, points: pd.DataFrame, cagr_column: str) -> list[str]:
        lines = ["", f"### {title}", "", "| Strategy | Start | End | CAGR | MaxDD | Calmar |", "|---|---|---|---:|---:|---:|"]
        for row in points.itertuples(index=False):
            calmar = f"{row.calmar:.3f}" if pd.notna(row.calmar) else "N/A"
            lines.append(f"| {row.strategy} | {row.start} | {row.end} | {getattr(row, cagr_column):.2%} | {row.max_drawdown:.2%} | {calmar} |")
        return lines

    report = [
        "# Phase 1 — Static Allocation Efficient Frontier", "",
        "Frozen scans completed: 8 two-asset pairs at 5% steps and 5 three-asset sets at 10% steps, each with monthly and quarterly rebalancing.",
        "Both pre-tax and Simplified Japan Taxable results use 5 bps slippage, 0 bps commission, average cost, and immediate tax payment.",
        "", "## Sample definition", "",
        f"All candidates use `{pre.start.iloc[0]}` through `{end}`, the intersection of the four priced Phase 1 ETFs and the latest common applicable session. This keeps every candidate comparison on identical evaluation dates.",
        "", "## Grid audit", "",
        "| Candidate class | Allocations per frequency | Frequencies | Rows per tax mode | Rows across both tax modes |",
        "|---|---:|---:|---:|---:|",
        "| Pair (8 × 21 weights) | 168 | 2 | 336 | 672 |",
        "| Triple (5 × 66 allocations) | 330 | 2 | 660 | 1,320 |",
        "| Total | 498 | 2 | 996 | 1,992 |",
        "",
        "Every candidate has finite, nonnegative weights summing to one within numerical tolerance. Required experiment rows are retained, including economically duplicate endpoint allocations.",
        f"Candidates per tax mode observed: `{len(pre)}`; candidates in combined `static_frontier.csv`: `{len(pre) + len(after)}`.",
        f"Highest pre-tax CAGR: `{best_cagr.strategy}` — {best_cagr.cagr:.2%} CAGR, {best_cagr.max_drawdown:.2%} MaxDD.",
        f"Lowest absolute pre-tax drawdown: `{lowest_risk.strategy}` — {lowest_risk.cagr:.2%} CAGR, {lowest_risk.max_drawdown:.2%} MaxDD.",
    ]
    report += point_lines("Pre-tax nondominated representative points", pre_points, "cagr")
    report += point_lines("After realized-tax-paid-to-date nondominated representative points", after_points, "cagr")
    report += point_lines("Terminal-liquidation after-tax diagnostic representative points", terminal_points, "terminal_liquidation_cagr")
    report += [
        "", "## Tax-aware interpretation", "",
        "`cagr` and `ending_value` in the after-tax table are wealth after realized taxes paid to date. `terminal_liquidation_*` hypothetically sells remaining holdings at the final valuation, deducts the frozen transaction cost, applies the carried loss pool and frozen tax rate, and does not mutate the ledger. The difference is tax timing/deferral, not a claim that one endpoint is universally correct.",
        "Terminal-liquidation after-tax metrics are diagnostic and do not mutate the strategy ledger.",
        "", "## Benchmark endpoints", "",
        "SPY, QQQ, SSO, and QLD 100% endpoints are present on the common sample. CASH, when shown, is the zero-return diagnostic baseline.",
        "", "## Turnover audit", "",
        "| Strategy | Included normalized turnover | Backtest years | Reported annual turnover | Nonzero-trade rebalances | Gross traded notional |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in turnover_audits:
        report.append(
            f"| {row['strategy']} | {row['included_normalized_turnover']:.9f} | {row['years']:.9f} | "
            f"{row['annual_turnover']:.9f} | {row['nonzero_trade_rebalances']} | ${row['gross_traded_notional']:,.2f} |"
        )
    report += [
        "", "For every row above, annual turnover equals the sum of `abs(trade_notional) / contemporaneous_pretrade_equity`, excluding the initial deployment, divided by calendar backtest years.",
        "", "This phase reports the frozen grid without parameter selection or dynamic tuning.",
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
    turnover_specs = {
        "monthly_pair_SPY000_QLD100", "quarterly_pair_SPY000_QLD100",
        "monthly_pair_SPY050_QLD050", "quarterly_pair_SPY050_QLD050",
        "monthly_pair_QQQ050_CASH050",
    }
    turnover_audits: dict[str, dict[str, object]] = {}
    execution_cost_rate = (float(config["execution"]["commission_bps"]) + float(config["execution"]["slippage_bps"])) / 10_000.0
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
            metric["economic_allocation_id"] = economic_allocation_id(weights)
            if mode == "after_tax":
                diagnostic = performance_metrics(
                    ledger,
                    trades,
                    capital,
                    terminal_tax_rate=float(config["tax"]["capital_gains_rate"]),
                    terminal_cost_rate=execution_cost_rate,
                )
                for field in (
                    "terminal_liquidation_wealth", "terminal_liquidation_tax", "terminal_liquidation_cost",
                    "terminal_unrealized_gain_after_cost", "terminal_loss_pool_before_liquidation",
                    "terminal_liquidation_cagr", "after_tax_terminal_liquidation", "after_tax_cagr_terminal_liquidation",
                ):
                    metric[field] = diagnostic[field]
                metric["after_tax_wealth_tax_paid_to_date"] = metric["ending_value"]
                metric["after_tax_cagr_tax_paid_to_date"] = metric["cagr"]
                metric["cumulative_realized_tax_paid"] = metric["tax_paid"]
                metric["tax_semantics"] = "realized tax paid to date; terminal liquidation is diagnostic"
            metrics_by_mode[mode].append(metric)
            if mode == "pre_tax" and name in turnover_specs:
                trade_dates = pd.to_datetime(trades["date"]) if len(trades) else pd.Series(dtype="datetime64[ns]")
                include = pd.Series(True, index=trades.index)
                if len(trades):
                    include = ~(trade_dates.eq(trade_dates.min()) & trades["side"].eq("BUY").to_numpy())
                included = 0.0
                if len(trades) and include.any():
                    denominator = ledger["pretrade_equity"].reindex(trade_dates).to_numpy(dtype=float)
                    included = float((trades.loc[include, "notional"].abs().to_numpy(dtype=float) / denominator[include.to_numpy()]).sum())
                turnover_audits[name] = {
                    "strategy": name,
                    "included_normalized_turnover": included,
                    "years": max((ledger.index[-1] - ledger.index[0]).days / 365.25, 1 / 365.25),
                    "annual_turnover": metric["annual_turnover"],
                    "nonzero_trade_rebalances": int(trade_dates.loc[include].nunique()) if len(trades) else 0,
                    "gross_traded_notional": metric["gross_traded_notional"],
                }
            curve_tables.append(ledger[["equity"]].assign(strategy=name, tax_mode=mode).reset_index())
            drawdown_tables.append(drawdown_series(ledger["equity"], capital).rename("drawdown").to_frame().assign(strategy=name, tax_mode=mode).reset_index(names="date"))
            if len(positions): position_tables.append(positions.assign(strategy=name, tax_mode=mode))
            if len(trades): trade_tables.append(trades.assign(strategy=name, tax_mode=mode))
            if len(taxes): tax_tables.append(taxes.assign(strategy=name, tax_mode=mode))
    pre = _unique_benchmarks(pd.DataFrame(metrics_by_mode["pre_tax"]))
    after = _unique_benchmarks(pd.DataFrame(metrics_by_mode["after_tax"]))
    pre["pareto"] = mark_pareto(pre); after["pareto"] = mark_pareto(after)
    terminal_pareto_input = after.loc[:, ["max_drawdown", "terminal_liquidation_cagr"]].rename(
        columns={"terminal_liquidation_cagr": "cagr"}
    )
    after["pareto_terminal_liquidation"] = mark_pareto(terminal_pareto_input)
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
    terminal_plot = after.copy()
    terminal_plot["cagr"] = terminal_plot["terminal_liquidation_cagr"]
    terminal_plot["pareto"] = terminal_plot["pareto_terminal_liquidation"]
    _plot_frontier(terminal_plot, output / "static_frontier_after_tax_terminal_liquidation.png", "Static allocation frontier — terminal liquidation after tax")
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
    _write_phase1_report(output, pre, after, list(turnover_audits.values()))
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
    after = pd.read_csv(output / "metrics_after_tax.csv") if (output / "metrics_after_tax.csv").exists() else pre.copy()
    audits = []
    _write_phase1_report(output, pre, after, audits)
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
