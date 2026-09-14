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
from market_timing_quant.data import ASSETS, run_data_audit
from market_timing_quant.metrics import add_rolling_metrics, drawdown_series, performance_metrics, period_returns
from market_timing_quant.portfolio import buy_and_hold, cash_hold


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase0_buy_hold")


def _plot_outputs(equities: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame, output: Path) -> None:
    plt.figure(figsize=(11, 6))
    normalized = equities.apply(lambda series: series / series.dropna().iloc[0])
    normalized.plot(ax=plt.gca(), logy=True)
    plt.ylabel("Growth of $1 (log scale)")
    plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    drawdowns.plot(figsize=(11, 6))
    plt.ylabel("Drawdown")
    plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    rolling = equities.pct_change(252)
    rolling.plot(figsize=(11, 6))
    plt.ylabel("Rolling 1Y return")
    plt.tight_layout(); plt.savefig(output / "rolling_returns.png", dpi=150); plt.close()
    rolling_dd = equities.apply(lambda s: s.rolling(252).apply(lambda x: (x / x.cummax() - 1).min()))
    rolling_dd.plot(figsize=(11, 6))
    plt.ylabel("Rolling 1Y max drawdown")
    plt.tight_layout(); plt.savefig(output / "rolling_maxdd.png", dpi=150); plt.close()
    points = metrics[(metrics["period"] == "main") & metrics["asset"].ne("CASH")]
    plt.figure(figsize=(8, 6))
    plt.scatter(points["max_drawdown"].abs(), points["cagr"])
    for _, row in points.iterrows():
        plt.annotate(row["asset"], (abs(row["max_drawdown"]), row["cagr"]))
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR")
    plt.tight_layout(); plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or _run_id())
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ASSETS}
    live_start = pd.Timestamp(config["backtest"]["live_start"])
    common_start = pd.Timestamp(config["backtest"]["tqqq_common_start"])
    latest = min(frame.index.max() for frame in prices.values())
    capital = float(config["initial_capital"])
    commission = float(config["execution"]["commission_bps"])
    slippage = float(config["execution"]["slippage_bps"])
    cost_rate = (commission + slippage) / 10_000.0
    tax_rate = float(config["tax"]["capital_gains_rate"])
    ledgers: dict[str, pd.DataFrame] = {}
    positions, trades, pre_tax_rows, after_tax_rows = [], [], [], []
    periods = (
        ("main", live_start, ("SPY", "QQQ", "SSO", "QLD", "CASH")),
        ("common_2010", common_start, (*ASSETS, "CASH")),
    )
    for period, start, candidates in periods:
        for asset in candidates:
            actual_start = max(start, prices[asset].index.min()) if asset != "CASH" else start
            index = prices["SPY"].loc[actual_start:latest].index
            if asset == "CASH":
                ledger, position, trade = cash_hold(index, capital)
            else:
                sample = prices[asset].loc[actual_start:latest]
                ledger, position, trade = buy_and_hold(
                    sample, initial_capital=capital, commission_bps=commission, slippage_bps=slippage
                )
            name = f"{period}_{asset}"
            ledgers[name] = add_rolling_metrics(ledger)
            position.insert(0, "strategy", name); positions.append(position)
            trade.insert(0, "strategy", name); trades.append(trade)
            identity = {"strategy": name, "period": period, "asset": asset}
            pre_tax_metric = performance_metrics(ledger, trade, capital)
            pre_tax_metric.update(identity)
            pre_tax_rows.append(pre_tax_metric)
            after_tax_metric = performance_metrics(
                ledger,
                trade,
                capital,
                terminal_tax_rate=tax_rate,
                terminal_cost_rate=cost_rate,
            )
            after_tax_metric.update(identity)
            after_tax_metric["tax_semantics"] = "realized tax paid to date; terminal liquidation is diagnostic"
            after_tax_rows.append(after_tax_metric)

    pre_tax_metrics = pd.DataFrame(pre_tax_rows)
    after_tax_metrics = pd.DataFrame(after_tax_rows)
    pre_tax_metrics.to_csv(output / "metrics_pre_tax.csv", index=False)
    after_tax_metrics.to_csv(output / "metrics_after_tax.csv", index=False)
    equity = pd.concat({name: ledger["equity"] for name, ledger in ledgers.items()}, axis=1)
    equity.index.name = "date"; equity.to_csv(output / "equity_curve.csv")
    drawdowns = pd.concat({name: drawdown_series(ledger["equity"], capital) for name, ledger in ledgers.items()}, axis=1)
    drawdowns.index.name = "date"; drawdowns.to_csv(output / "drawdown.csv")
    annual = pd.concat({name: period_returns(ledger, capital)[0] for name, ledger in ledgers.items()}, axis=1)
    monthly = pd.concat({name: period_returns(ledger, capital)[1] for name, ledger in ledgers.items()}, axis=1)
    annual.index.name = "period_end"; annual.to_csv(output / "annual_returns.csv")
    monthly.index.name = "period_end"; monthly.to_csv(output / "monthly_returns.csv")
    rolling_columns = ("rolling_1y_return", "rolling_3y_cagr", "rolling_5y_cagr", "rolling_10y_cagr", "rolling_1y_maxdd")
    rolling = pd.concat({name: ledger.loc[:, rolling_columns] for name, ledger in ledgers.items()}, axis=1)
    rolling.index.name = "date"; rolling.to_csv(output / "rolling_metrics.csv")
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    trade_table = pd.concat(trades, ignore_index=True)
    trade_table.to_csv(output / "trades.csv", index=False)
    pd.DataFrame(columns=["strategy", "date", "realized_gain", "loss_pool", "tax_paid"]).to_csv(output / "tax_ledger.csv", index=False)
    pd.DataFrame([{"phase": 0, "parameters_searched": False}]).to_csv(output / "parameter_results.csv", index=False)
    _plot_outputs(equity, drawdowns, pre_tax_metrics, output)

    def comparison_table(period: str, assets: tuple[str, ...]) -> list[str]:
        pre = pre_tax_metrics[pre_tax_metrics["period"].eq(period)].set_index("asset")
        after = after_tax_metrics[after_tax_metrics["period"].eq(period)].set_index("asset")
        lines = [
            "| Asset | Start | End | Pre-tax wealth | Pre-tax CAGR | MaxDD | Calmar | Annual turnover | Completed holding mean/median/max |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for asset in assets:
            row = pre.loc[asset]
            calmar = f"{row.calmar:.3f}" if pd.notna(row.calmar) else "N/A"
            holding = (
                f"{row.mean_holding_period_days:g} / {row.median_holding_period_days:g} / {row.max_holding_period_days:g}"
                if pd.notna(row.mean_holding_period_days) else "N/A / N/A / N/A"
            )
            lines.append(
                f"| {asset} | {row.start} | {row.end} | ${row.ending_value:,.2f} | {row.cagr:.2%} | "
                f"{row.max_drawdown:.2%} | {calmar} | {row.annual_turnover:.3f} | {holding} |"
            )
        lines += [
            "",
            "| Asset | Start | End | Wealth after realized tax paid to date | CAGR after realized tax paid to date | "
            "Terminal-liquidation wealth | Terminal-liquidation CAGR | Liquidation tax | Liquidation cost | Unrealized gain after cost |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for asset in assets:
            row = after.loc[asset]
            lines.append(
                f"| {asset} | {row.start} | {row.end} | ${row.after_tax_wealth_tax_paid_to_date:,.2f} | "
                f"{row.after_tax_cagr_tax_paid_to_date:.2%} | ${row.terminal_liquidation_wealth:,.2f} | "
                f"{row.terminal_liquidation_cagr:.2%} | ${row.terminal_liquidation_tax:,.2f} | "
                f"${row.terminal_liquidation_cost:,.2f} | ${row.terminal_unrealized_gain_after_cost:,.2f} |"
            )
        return lines

    report = [
        "# Phase 0 — Buy & Hold Baseline", "",
        f"Evaluation end: `{latest.date()}` (latest common live-ETF session).",
        "Execution uses the first available adjusted open and a one-sided 5 bps slippage cost. CASH return is 0%.",
        "No position is sold at the end, so wealth after realized tax paid to date equals pre-tax wealth; unrealized gains are taxed only in the diagnostic terminal-liquidation columns.",
        "Terminal-liquidation after-tax metrics are diagnostic and do not mutate the strategy ledger.",
        "", "## A. Live Main Period", "",
        "SPY, QQQ, SSO, and QLD are compared from 2006-06-21 through the common ending session. TQQQ is excluded because it was not yet listed.", "",
    ]
    report += comparison_table("main", ("SPY", "QQQ", "SSO", "QLD"))
    report += [
        "", "## B. Common TQQQ Period", "",
        "All five ETFs are compared from 2010-02-11 through the same ending session; no pre-listing TQQQ history is synthesized.", "",
    ]
    report += comparison_table("common_2010", ASSETS)
    cash = pre_tax_metrics[(pre_tax_metrics["period"].eq("main")) & (pre_tax_metrics["asset"].eq("CASH"))].iloc[0]
    report += [
        "", f"CASH diagnostic ({cash.start} through {cash.end}): ending wealth ${cash.ending_value:,.2f}, CAGR {cash.cagr:.2%}, MaxDD {cash.max_drawdown:.2%}.",
        "", "Phase 0 contains no parameter search and makes no dominance claim.",
        "Data source status: point-in-time approximate market-data snapshots; see `data/audit/data_audit_report.md`.",
    ]
    (output / "phase0_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen v1 Phase 0 buy-and-hold baseline")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    output = run(args.config, args.output_root, args.run_id)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
