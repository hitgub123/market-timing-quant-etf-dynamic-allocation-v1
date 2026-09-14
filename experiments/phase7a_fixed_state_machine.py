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
from market_timing_quant.metrics import completed_holding_periods, drawdown_series, performance_metrics
from market_timing_quant.portfolio import buy_and_hold, cash_hold, dynamic_allocation_backtest, single_asset_timed_backtest
from market_timing_quant.signals import phase7_state_decisions, phase7_targets_next_open, rebalance_mask, trend_target_next_open
from market_timing_quant.walk_forward import expanding_calendar_year_folds, fold_table


def _benchmark_table(prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex, config: dict) -> pd.DataFrame:
    capital = float(config["initial_capital"])
    rows = []
    for asset in ("SPY", "QQQ", "SSO", "QLD", "CASH"):
        if asset == "CASH":
            ledger, _, trades = cash_hold(index, capital)
        else:
            ledger, _, trades = buy_and_hold(
                prices[asset].loc[index], initial_capital=capital,
                commission_bps=float(config["execution"]["commission_bps"]),
                slippage_bps=float(config["execution"]["slippage_bps"]),
            )
        pre = performance_metrics(
            ledger, trades, capital,
            terminal_tax_rate=float(config["tax"]["capital_gains_rate"]),
            terminal_cost_rate=(float(config["execution"]["commission_bps"]) + float(config["execution"]["slippage_bps"])) / 10_000,
        )
        # Tax-paid-to-date is unchanged because no actual terminal sale occurs.
        rows.append({"asset": asset, "cagr": pre["cagr"], "max_drawdown": pre["max_drawdown"],
                     "calmar": pre["calmar"], "sortino": pre["sortino"],
                     "after_tax_tax_paid_to_date": pre["after_tax_tax_paid_to_date"],
                     "after_tax_terminal_liquidation": pre["after_tax_terminal_liquidation"],
                     "after_tax_cagr_tax_paid_to_date": pre["cagr"],
                     "after_tax_cagr_terminal_liquidation": pre["terminal_liquidation_cagr"],
                     "turnover": pre["annual_turnover"], "gross_traded_notional": pre["gross_traded_notional"],
                     "recovery_trading_days": pre["recovery_trading_days"]})
    return pd.DataFrame(rows)


def _qld_ma200_table(prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex, config: dict) -> pd.DataFrame:
    """Recompute the accepted simple QLD/MA200 rule on the exact Phase 7A OOS index."""
    capital = float(config["initial_capital"])
    cost_rate = (float(config["execution"]["commission_bps"]) + float(config["execution"]["slippage_bps"])) / 10_000
    rows = []
    for frequency in FREQUENCIES:
        targets = trend_target_next_open(
            prices["QQQ"].adjusted_close, frequency, lookback=200,
        ).reindex(index)
        if targets.isna().any():
            raise ValueError("QLD/MA200 signal and Phase 7A OOS calendars are not aligned")
        for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
            ledger, _, trades, _ = single_asset_timed_backtest(
                prices["QLD"].reindex(index), targets, initial_capital=capital,
                commission_bps=float(config["execution"]["commission_bps"]),
                slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
            )
            metric = performance_metrics(
                ledger, trades, capital,
                terminal_tax_rate=float(config["tax"]["capital_gains_rate"]) if mode == "after_tax" else None,
                terminal_cost_rate=cost_rate,
            )
            metric.update({
                "strategy": f"QQQ_MA200_QLD_{frequency}", "frequency": frequency,
                "period": "chronological_oos", "tax_mode": mode, "fixed_rule": True,
            })
            rows.append(metric)
    return pd.DataFrame(rows)


def _comparison_table(metrics: pd.DataFrame, simple: pd.DataFrame) -> pd.DataFrame:
    """Compare rules without granting a complexity bonus.

    Material improvement requires strict gains in CAGR, Calmar, and terminal-
    liquidation after-tax CAGR, no deeper MaxDD, and no higher turnover.
    """
    phase_pre = metrics[(metrics.period == "chronological_oos") & (metrics.tax_mode == "pre_tax")].set_index("frequency")
    phase_after = metrics[(metrics.period == "chronological_oos") & (metrics.tax_mode == "after_tax")].set_index("frequency")
    simple_pre = simple[simple.tax_mode == "pre_tax"].set_index("frequency")
    simple_after = simple[simple.tax_mode == "after_tax"].set_index("frequency")
    rows = []
    for frequency in FREQUENCIES:
        phase, base = phase_pre.loc[frequency], simple_pre.loc[frequency]
        phase_tax, base_tax = phase_after.loc[frequency], simple_after.loc[frequency]
        differences = {
            "cagr_difference": phase.cagr - base.cagr,
            "max_drawdown_difference": phase.max_drawdown - base.max_drawdown,
            "calmar_difference": phase.calmar - base.calmar,
            "after_tax_cagr_tax_paid_to_date_difference": (
                phase_tax.after_tax_cagr_tax_paid_to_date - base_tax.after_tax_cagr_tax_paid_to_date
            ),
            "after_tax_cagr_terminal_liquidation_difference": (
                phase_tax.after_tax_cagr_terminal_liquidation - base_tax.after_tax_cagr_terminal_liquidation
            ),
            "turnover_difference": phase.annual_turnover - base.annual_turnover,
        }
        materially_improves = (
            differences["cagr_difference"] > 0
            and differences["max_drawdown_difference"] >= 0
            and differences["calmar_difference"] > 0
            and differences["after_tax_cagr_terminal_liquidation_difference"] > 0
            and differences["turnover_difference"] <= 0
        )
        rows.append({
            "frequency": frequency, **differences,
            "material_improvement": materially_improves,
            "criterion": "CAGR>0; MaxDD_diff>=0; Calmar>0; terminal_after_tax_CAGR>0; turnover_diff<=0",
        })
    return pd.DataFrame(rows)


def _plots(curves: pd.DataFrame, drawdowns: pd.DataFrame, metrics: pd.DataFrame, benchmarks: pd.DataFrame, output: Path) -> None:
    names = set(metrics[(metrics.period == "chronological_oos") & (metrics.tax_mode == "pre_tax")].strategy)
    selected = curves[(curves.period == "chronological_oos") & (curves.tax_mode == "pre_tax")]
    plt.figure(figsize=(11, 6))
    for name, part in selected.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], label=name)
    plt.yscale("log"); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(output / "equity_curve.png", dpi=150); plt.close()
    selected_dd = drawdowns[(drawdowns.period == "chronological_oos") & (drawdowns.tax_mode == "pre_tax")]
    plt.figure(figsize=(11, 6))
    for name, part in selected_dd.groupby("strategy"): plt.plot(part.date, part.drawdown, label=name)
    plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(output / "drawdown.png", dpi=150); plt.close()
    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for _, part in selected.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(lambda x: (x / x.cummax() - 1).min() if is_dd else x.iloc[-1] / x.iloc[0] - 1)
            plt.plot(values.index, values)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()
    points = metrics[(metrics.period == "chronological_oos") & (metrics.tax_mode == "pre_tax")]
    plt.figure(figsize=(9, 7)); plt.scatter(points.max_drawdown.abs(), points.cagr, label="Phase 7A")
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Benchmarks")
    for _, row in benchmarks.iterrows(): plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("CAGR"); plt.legend(); plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase7a_fixed_state"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD", "TQQQ")}
    full_index = prices["QLD"].index.intersection(prices["SSO"].index)
    full_index = full_index[full_index >= pd.Timestamp(config["backtest"]["live_start"])]
    end = min(prices[a].index.max() for a in ("SPY", "QQQ", "SSO", "QLD", "TQQQ"))
    full_index = full_index[full_index <= end]
    tqqq_first = prices["TQQQ"].index.min()
    qqq_decisions = phase7_state_decisions(prices["QQQ"].adjusted_close)
    qqq_decisions.to_csv(output / "state_decisions.csv", index_label="decision_date")
    oos_start = expanding_calendar_year_folds(full_index)[0].test_start
    periods = {"full_sample": full_index, "chronological_oos": full_index[full_index >= oos_start]}
    capital = float(config["initial_capital"])
    rows, curves, drawdowns, positions, trades, taxes, target_tables, holding_episodes = [], [], [], [], [], [], [], []
    for frequency in FREQUENCIES:
        all_targets, all_states = phase7_targets_next_open(qqq_decisions, frequency, tqqq_first_session=tqqq_first)
        for period, index in periods.items():
            targets = all_targets.reindex(index)
            states = all_states.reindex(index)
            schedule = rebalance_mask(index, frequency)
            price_map = {
                "QQQ": prices["QQQ"].reindex(index), "QLD": prices["QLD"].reindex(index),
                "TQQQ": prices["TQQQ"].reindex(index),
            }
            target_tables.append(targets.assign(state=states, frequency=frequency, period=period).reset_index(names="execution_date"))
            for mode, tax_rate in (("pre_tax", None), ("after_tax", float(config["tax"]["capital_gains_rate"]))):
                strategy = f"PHASE7A_{frequency}"
                ledger, position, trade, tax = dynamic_allocation_backtest(
                    price_map, targets, schedule, initial_capital=capital,
                    commission_bps=float(config["execution"]["commission_bps"]),
                    slippage_bps=float(config["execution"]["slippage_bps"]), tax_rate=tax_rate,
                )
                ledger["state"] = states
                metric = performance_metrics(
                    ledger, trade, capital,
                    terminal_tax_rate=float(config["tax"]["capital_gains_rate"]) if mode == "after_tax" else None,
                    terminal_cost_rate=(float(config["execution"]["commission_bps"]) + float(config["execution"]["slippage_bps"])) / 10_000,
                )
                metric.update({"strategy": strategy, "frequency": frequency, "period": period,
                               "tax_mode": mode, "fixed_rule": True})
                metric["after_tax_cagr_tax_paid_to_date"] = metric["cagr"] if mode == "after_tax" else None
                metric["after_tax_cagr_terminal_liquidation"] = metric["terminal_liquidation_cagr"] if mode == "after_tax" else None
                rows.append(metric)
                curves.append(ledger[["equity", "state"]].assign(strategy=strategy, tax_mode=mode, period=period).reset_index())
                drawdowns.append(drawdown_series(ledger.equity, capital).rename("drawdown").to_frame().assign(strategy=strategy, tax_mode=mode, period=period).reset_index(names="date"))
                positions.append(position.assign(strategy=strategy, tax_mode=mode, period=period))
                episodes = completed_holding_periods(ledger)
                if len(episodes):
                    holding_episodes.append(episodes.assign(strategy=strategy, tax_mode=mode, period=period))
                if len(trade): trades.append(trade.assign(strategy=strategy, tax_mode=mode, period=period))
                if len(tax): taxes.append(tax.assign(strategy=strategy, tax_mode=mode, period=period))
    metrics = pd.DataFrame(rows)
    oos_index = periods["chronological_oos"]
    benchmarks = _benchmark_table(prices, oos_index, config)
    simple_ma200 = _qld_ma200_table(prices, oos_index, config)
    comparison = _comparison_table(metrics, simple_ma200)
    qqq = benchmarks.set_index("asset").loc["QQQ"]
    oos_pre = (metrics.period == "chronological_oos") & (metrics.tax_mode == "pre_tax")
    metrics["qqq_dominance"] = False
    metrics.loc[oos_pre, "qqq_dominance"] = (
        (metrics.loc[oos_pre, "cagr"] > qqq.cagr)
        & (metrics.loc[oos_pre, "max_drawdown"] >= qqq.max_drawdown)
        & (metrics.loc[oos_pre, "calmar"] > qqq.calmar)
    )
    metrics[metrics.tax_mode == "pre_tax"].to_csv(output / "metrics_pre_tax.csv", index=False)
    metrics[metrics.tax_mode == "after_tax"].to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "phase7a_results.csv", index=False)
    pd.DataFrame([{"phase": "7A", "ma_days": 200, "momentum_days": 252,
                   "low_vol_quantile": .33, "parameters_selected": False}]).to_csv(output / "parameter_results.csv", index=False)
    curve_table = pd.concat(curves, ignore_index=True); curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table = pd.concat(drawdowns, ignore_index=True); dd_table.to_csv(output / "drawdown.csv", index=False)
    pd.concat(positions, ignore_index=True).to_csv(output / "positions.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(output / "trades.csv", index=False)
    pd.concat(taxes, ignore_index=True).to_csv(output / "tax_ledger.csv", index=False)
    pd.concat(target_tables, ignore_index=True).to_csv(output / "execution_targets.csv", index=False)
    pd.concat(holding_episodes, ignore_index=True).to_csv(output / "holding_episodes.csv", index=False)
    benchmarks.to_csv(output / "oos_benchmarks.csv", index=False)
    simple_ma200.to_csv(output / "qld_ma200_oos_results.csv", index=False)
    comparison.to_csv(output / "phase7a_vs_qld_ma200.csv", index=False)
    fold_table(expanding_calendar_year_folds(full_index)).to_csv(output / "walk_forward_folds.csv", index=False)
    _plots(curve_table, dd_table, metrics, benchmarks, output)
    after = metrics[(metrics.period == "chronological_oos") & (metrics.tax_mode == "after_tax")].set_index("strategy")
    lines = [
        "# Phase 7A — Fixed Four-State Machine", "",
        "All signals use QQQ adjusted-close history only. RV20 q33 is expanding and shifted one session, so date t excludes RV20(t).",
        "This is a Fixed-Rule Chronological OOS result, not parameter-selection Walk-Forward.",
        "", "## Same-period OOS benchmarks", "",
        "| Asset | CAGR | MaxDD | Calmar | Sortino | Tax-paid-to-date CAGR | Terminal-liquidation CAGR | Turnover | Gross traded | Recovery sessions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in benchmarks.iterrows():
        calmar = f"{row.calmar:.3f}" if pd.notna(row.calmar) else "N/A"
        sortino = f"{row.sortino:.3f}" if pd.notna(row.sortino) else "N/A"
        lines.append(f"| {row.asset} | {row.cagr:.2%} | {row.max_drawdown:.2%} | {calmar} | {sortino} | {row.after_tax_cagr_tax_paid_to_date:.2%} | {row.after_tax_cagr_terminal_liquidation:.2%} | {row.turnover:.3f} | ${row.gross_traded_notional:,.0f} | {row.recovery_trading_days if pd.notna(row.recovery_trading_days) else 'N/A'} |")
    lines += ["", "## Phase 7A OOS", "", "| Frequency | CAGR | MaxDD | Calmar | Sortino | Tax-paid-to-date CAGR | Terminal-liquidation CAGR | Turnover | Mean/median/max holding sessions | Recovery sessions | QQQ_DOMINANCE |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, row in metrics[oos_pre].sort_values("frequency").iterrows():
        tax_row = after.loc[row.strategy]
        holding = f"{row.mean_holding_trading_days:.1f}/{row.median_holding_trading_days:.1f}/{int(row.max_holding_trading_days)}" if pd.notna(row.mean_holding_trading_days) else "N/A"
        lines.append(f"| {row.frequency} | {row.cagr:.2%} | {row.max_drawdown:.2%} | {row.calmar:.3f} | {row.sortino:.3f} | {tax_row.cagr:.2%} | {tax_row.terminal_liquidation_cagr:.2%} | {row.annual_turnover:.3f} | {holding} | {row.recovery_trading_days if pd.notna(row.recovery_trading_days) else 'N/A'} | {str(bool(row.qqq_dominance)).upper()} |")
    lines += [
        "", "Dominance uses the frozen three-part QQQ condition with negative MaxDD comparison.",
        "", "## Phase 7A versus simple QLD/MA200 OOS", "",
        "Positive MaxDD difference means Phase 7A has a shallower (better) drawdown. Material improvement requires higher CAGR, no deeper MaxDD, higher Calmar, higher terminal-liquidation after-tax CAGR, and no higher turnover.",
        "", "| Frequency | CAGR diff | MaxDD diff | Calmar diff | Tax-paid CAGR diff | Terminal-liquidation CAGR diff | Turnover diff | Material improvement |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row.frequency} | {row.cagr_difference:+.2%} | {row.max_drawdown_difference:+.2%} | "
            f"{row.calmar_difference:+.3f} | {row.after_tax_cagr_tax_paid_to_date_difference:+.2%} | "
            f"{row.after_tax_cagr_terminal_liquidation_difference:+.2%} | {row.turnover_difference:+.3f} | "
            f"{str(bool(row.material_improvement)).upper()} |"
        )
    lines += [
        "", "Conclusion: Phase 7A materially improves on simple QLD/MA200 only where the complete conservative criterion above is TRUE; added state complexity receives no independent credit.",
        "", "## Metric definitions", "",
        "- Holding-period days are trading sessions in completed zero-to-positive-to-zero position episodes; open terminal episodes are excluded. Calendar-day episode diagnostics are also exported.",
        "- Annual turnover excludes initial deployment and excludes the hypothetical terminal liquidation. Gross traded notional includes actual orders, including initial deployment.",
        "- Tax-paid-to-date reflects only taxes actually realized in the historical ledger. Terminal liquidation is a report-only endpoint using the existing loss pool and frozen tax rate; it does not alter the equity curve or decisions.",
    ]
    (output / "phase7a_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen Phase 7A fixed state machine")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
