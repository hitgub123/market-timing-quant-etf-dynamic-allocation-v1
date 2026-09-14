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

from experiments.phase2_ma200 import (  # noqa: E402
    FREQUENCIES,
    STRATEGIES,
    _add_pretrade_equity as _phase2_add_pretrade_equity,
    _turnover_audit as _phase2_turnover_audit,
)
from market_timing_quant.configuration import load_config  # noqa: E402
from market_timing_quant.data import run_data_audit  # noqa: E402
from market_timing_quant.metrics import (  # noqa: E402
    completed_holding_periods,
    drawdown_series,
    performance_metrics,
)
from market_timing_quant.portfolio import single_asset_timed_backtest  # noqa: E402
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open  # noqa: E402
from market_timing_quant.walk_forward import expanding_calendar_year_folds, fold_table  # noqa: E402


MA_WINDOW = 200
TAX_SEMANTICS_PRE = "pre-tax; no realized tax is charged"
TAX_SEMANTICS_AFTER = "realized tax paid to date; terminal liquidation is diagnostic"


def _add_pretrade_equity(
    ledger: pd.DataFrame, prices: pd.DataFrame, initial_capital: float,
) -> pd.DataFrame:
    """Use the same reporting-only pretrade reconstruction as audited Phase 2."""
    return _phase2_add_pretrade_equity(ledger, prices, initial_capital)


def _turnover_audit(ledger: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    """Expose the canonical Phase 2 turnover helper for cross-phase regression tests."""
    return _phase2_turnover_audit(ledger, trades)


def _holding_stats(episodes: pd.DataFrame) -> dict[str, object]:
    """Summarize completed episodes, returning nulls when none are complete."""
    if episodes.empty:
        return {
            "average_holding_period_days": None,
            "mean_holding_period_days": None,
            "median_holding_period_days": None,
            "max_holding_period_days": None,
            "mean_holding_trading_days": None,
            "median_holding_trading_days": None,
            "max_holding_trading_days": None,
            "mean_holding_calendar_days": None,
            "median_holding_calendar_days": None,
            "max_holding_calendar_days": None,
            "mean_holding_days": None,
            "median_holding_days": None,
            "max_holding_days": None,
            "completed_holding_episodes": 0,
        }
    trading = episodes["trading_days"].astype(float)
    calendar = episodes["calendar_days"].astype(float)
    return {
        "average_holding_period_days": float(trading.mean()),
        "mean_holding_period_days": float(trading.mean()),
        "median_holding_period_days": float(trading.median()),
        "max_holding_period_days": int(trading.max()),
        "mean_holding_trading_days": float(trading.mean()),
        "median_holding_trading_days": float(trading.median()),
        "max_holding_trading_days": int(trading.max()),
        "mean_holding_calendar_days": float(calendar.mean()),
        "median_holding_calendar_days": float(calendar.median()),
        "max_holding_calendar_days": int(calendar.max()),
        "mean_holding_days": float(trading.mean()),
        "median_holding_days": float(trading.median()),
        "max_holding_days": int(trading.max()),
        "completed_holding_episodes": int(len(episodes)),
    }


def _episodes_attributed_to_fold(
    ledger: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
) -> pd.DataFrame:
    """Assign each completed episode to the fold containing its exit session."""
    episodes = completed_holding_periods(ledger)
    if episodes.empty:
        return episodes
    exits = pd.to_datetime(episodes["exit_date"])
    return episodes.loc[exits.ge(start) & exits.le(end)].copy()


def _fold_turnover_audit(
    ledger: pd.DataFrame,
    trades: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    initial_deployment_date: pd.Timestamp | None,
) -> dict[str, object]:
    """Compute canonical turnover for real trades executed in one fold."""
    segment = ledger.loc[start:end]
    years = max((segment.index[-1] - segment.index[0]).days / 365.25, 1 / 365.25)
    if len(trades):
        dates = pd.to_datetime(trades["date"])
        scoped = trades.loc[dates.ge(start) & dates.le(end)].copy()
    else:
        scoped = trades
    if not len(scoped):
        return {
            "included_normalized_turnover": 0.0,
            "years": years,
            "annual_turnover": 0.0,
            "nonzero_trade_dates": 0,
            "nonzero_trade_rebalances": 0,
            "gross_traded_notional": 0.0,
            "number_of_trades": 0,
        }
    dates = pd.to_datetime(scoped["date"])
    if initial_deployment_date is None and len(trades):
        initial_deployment_date = pd.to_datetime(trades["date"]).min()
    include = ~(dates.eq(initial_deployment_date) & scoped["side"].eq("BUY")).to_numpy()
    denominator_series = ledger["pretrade_equity"] if "pretrade_equity" in ledger else ledger["equity"]
    denominators = denominator_series.reindex(dates).to_numpy(dtype=float)
    if not pd.Series(denominators[include]).notna().all():
        raise AssertionError("fold turnover denominator is missing on a real trade date")
    normalized = float(
        (scoped.loc[include, "notional"].abs().to_numpy(dtype=float) / denominators[include]).sum(),
    )
    included_dates = dates.loc[include]
    return {
        "included_normalized_turnover": normalized,
        "years": years,
        "annual_turnover": normalized / years,
        "nonzero_trade_dates": int(included_dates.nunique()),
        "nonzero_trade_rebalances": int(included_dates.nunique()),
        "gross_traded_notional": float(scoped["notional"].abs().sum()),
        "number_of_trades": int(len(scoped)),
    }


def _segment_metrics(
    ledger: pd.DataFrame,
    trades: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    prior_equity: float,
    strategy: str,
    mode: str,
    year: int,
    initial_deployment_date: pd.Timestamp | None = None,
) -> dict[str, object]:
    """Return diagnostic fold metrics from a continuous ledger slice."""
    segment = ledger.loc[start:end].copy()
    if segment.empty:
        raise ValueError("fold has no evaluation sessions")
    segment.iloc[0, segment.columns.get_loc("daily_return")] = (
        float(segment.equity.iloc[0]) / float(prior_equity) - 1.0
    )
    if len(trades):
        dates = pd.to_datetime(trades["date"])
        segment_trades = trades.loc[dates.ge(start) & dates.le(end)].copy()
    else:
        segment_trades = trades
    result = performance_metrics(segment, segment_trades, prior_equity)
    result.update(_fold_turnover_audit(
        ledger, trades, start, end,
        initial_deployment_date,
    ))
    result.update(_holding_stats(_episodes_attributed_to_fold(ledger, start, end)))
    fold_realized_tax_paid = float(segment["tax_paid"].sum()) if "tax_paid" in segment else 0.0
    cumulative_tax_path = ledger.loc[ledger.index <= end, "tax_paid"].cumsum()
    cumulative_realized_tax_paid = float(cumulative_tax_path.iloc[-1]) if len(cumulative_tax_path) else 0.0
    result.update({
        "strategy": strategy,
        "tax_mode": mode,
        "test_year": year,
        "result_type": "diagnostic_fold",
        "fold_realized_tax_paid": fold_realized_tax_paid,
        "cumulative_realized_tax_paid": cumulative_realized_tax_paid,
        "tax_semantics": TAX_SEMANTICS_AFTER if mode == "after_tax" else TAX_SEMANTICS_PRE,
    })
    return result


def _warmup_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    """Describe the fixed MA200 warm-up and evaluation calendars."""
    rows: list[dict[str, object]] = []
    for asset in ("QQQ", "SPY"):
        frame = prices[asset]
        decision = ma_trend_decision(frame["adjusted_close"], MA_WINDOW)
        before = frame.loc[frame.index < start]
        through_start = frame.loc[:start]
        lookback = through_start.tail(MA_WINDOW)
        rows.append({
            "signal_asset": asset,
            "ma_window": MA_WINDOW,
            "evaluation_start": str(start.date()),
            "evaluation_end": str(end.date()),
            "signal_rows_full": int(len(frame)),
            "pre_start_warmup_rows": int(len(before)),
            "lookback_observations_at_start": int(len(lookback)),
            "lookback_start_at_start": str(lookback.index[0].date()) if len(lookback) else None,
            "lookback_end_at_start": str(lookback.index[-1].date()) if len(lookback) else None,
            "first_valid_ma_date": str(decision.index[MA_WINDOW - 1].date()),
            "first_evaluation_signal_date": str(frame.loc[start:].index[0].date()),
            "missing_aligned_targets": 0,
        })
    return rows


def _alignment_rows(
    prices: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
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
            "missing_aligned_targets": int(len(held_index.difference(signal_index))),
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


def _write_standard_plots(
    curves: pd.DataFrame,
    drawdowns: pd.DataFrame,
    metrics: pd.DataFrame,
    capital: float,
    output: Path,
) -> None:
    pre = curves[curves.tax_mode.eq("pre_tax")]
    plt.figure(figsize=(11, 6))
    for name, part in pre.groupby("strategy"):
        plt.plot(part.date, part.equity / capital, label=name, alpha=.7)
    plt.yscale("log"); plt.legend(fontsize=7, ncol=2); plt.tight_layout()
    plt.savefig(output / "equity_curve.png", dpi=150); plt.close()

    pre_dd = drawdowns[drawdowns.tax_mode.eq("pre_tax")]
    plt.figure(figsize=(11, 6))
    for name, part in pre_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.7, label=name)
    plt.legend(fontsize=7, ncol=2); plt.tight_layout()
    plt.savefig(output / "drawdown.png", dpi=150); plt.close()

    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for _, part in pre.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(
                lambda x: (x / x.cummax() - 1).min()
                if is_dd else x.iloc[-1] / x.iloc[0] - 1,
            )
            plt.plot(values.index, values, alpha=.7)
        plt.tight_layout(); plt.savefig(output / filename, dpi=150); plt.close()

    points = metrics[metrics.tax_mode.eq("pre_tax")]
    plt.figure(figsize=(9, 7)); plt.scatter(points.max_drawdown.abs(), points.cagr)
    for _, row in points.iterrows():
        plt.annotate(row.strategy.replace("_OOS", ""), (abs(row.max_drawdown), row.cagr), fontsize=6)
    plt.xlabel("Absolute Max Drawdown"); plt.ylabel("OOS CAGR"); plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150); plt.close()


def _write_oos_report(
    output: Path,
    metrics: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    folds: list[object],
    warmups: list[dict[str, object]],
    alignments: list[dict[str, object]],
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution_rate: float,
    tax_rate: float,
) -> None:
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].sort_values(["rule", "frequency"])
    lines = [
        "# Fixed-Rule Chronological OOS — MA200",
        "",
        "## Experiment contract",
        "",
        f"The continuous OOS evaluation period is **{start.date()} through {end.date()}** (inclusive), "
        f"covering {len(folds)} chronological calendar-year diagnostic folds. The fixed strategy universe "
        "is QQQ_MA200_QQQ, QQQ_MA200_QLD, and SPY_MA200_SSO at weekly, monthly, bimonthly, and "
        "quarterly frequencies: 3 × 4 × 2 tax modes = 24 stitched rows. The MA window is permanently "
        "fixed at 200; `parameter_results.csv` records `selected=False`, `searched_for_selection=False`, "
        "and `selection_performed=False` for this fixed baseline. No optimization or parameter-selection "
        "claim is made.",
        "",
        "Signal is the adjusted close of the unleveraged underlying at close t. A completed close decision "
        "can first affect the next eligible trading-day open t+1. Annual folds are diagnostic slices only; "
        "the economic OOS ledger is continuous and never resets capital, holdings, average-cost basis, "
        "tax loss pools, or trades at a fold boundary.",
        "",
        "## Warm-up and calendar alignment",
        "",
        "Historical observations before the OOS start provide the legitimate 200-session MA warm-up. They "
        "create no pre-start equity, positions, trades, or tax entries. The first evaluation target uses "
        "only information available by the preceding close, and all signal/held calendars are aligned with "
        "zero missing targets.",
        "",
        "| Signal asset | Window | Full rows | Pre-start rows | Lookback observations | Lookback start | First valid MA date | First evaluation date | Missing targets |",
        "|---|---:|---:|---:|---:|---|---|---|---:|",
    ]
    for row in warmups:
        lines.append(
            f"| {row['signal_asset']} | {row['ma_window']} | {row['signal_rows_full']} | "
            f"{row['pre_start_warmup_rows']} | {row['lookback_observations_at_start']} | "
            f"{row['lookback_start_at_start']} | {row['first_valid_ma_date']} | "
            f"{row['first_evaluation_signal_date']} | {row['missing_aligned_targets']} |",
        )
    lines += [
        "",
        "| Rule | Signal asset | Held asset | Signal rows | Held rows | Common rows | Missing aligned targets |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in alignments:
        lines.append(
            f"| {row['rule']} | {row['signal_asset']} | {row['held_asset']} | "
            f"{row['signal_calendar_rows']} | {row['held_calendar_rows']} | {row['common_evaluation_rows']} | "
            f"{row['missing_aligned_targets']} |",
        )
    lines += [
        "",
        "## Metrics and tax semantics",
        "",
        "Primary after-tax wealth is the live ledger after realized tax paid to date. Terminal liquidation "
        f"is a non-mutating diagnostic using the {tax_rate:.5f} tax rate and execution cost rate "
        f"{execution_rate:.8f}; it does not add a SELL, affect turnover or holding periods, or alter the "
        "tax ledger. Fold metrics never perform hypothetical liquidation.",
        "",
        "Turnover is `sum(abs(trade_notional) / contemporaneous_open_pretrade_equity) / calendar_years`. "
        "The global initial deployment BUY and hypothetical terminal liquidation are excluded; every other "
        "genuine strategy trade is included. Fold turnover includes only execution dates inside that fold.",
        "",
        "Holding periods are completed risky-position episodes measured in trading sessions. Episodes begin "
        "on CASH→risky and complete on risky→CASH. An open terminal episode is excluded, and fold boundaries "
        "do not terminate or restart an episode. For fold diagnostics, a completed episode is attributed to "
        "the fold containing its actual exit date, preserving a December-to-January episode in full.",
        "",
        "| Rule | Frequency | Pre-tax CAGR | Pre-tax MaxDD | After-tax CAGR | Annual turnover | Mean hold | Median hold | Max hold | Terminal CAGR |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in pre.iterrows():
        after = metrics.loc[
            metrics.strategy.eq(row.strategy) & metrics.tax_mode.eq("after_tax")
        ].iloc[0]
        lines.append(
            f"| {row.rule} | {row.frequency} | {_format_value(row.cagr, percent=True)} | "
            f"{_format_value(row.max_drawdown, percent=True)} | {_format_value(after.cagr, percent=True)} | "
            f"{_format_value(row.annual_turnover)} | {_format_value(row.mean_holding_period_days)} | "
            f"{_format_value(row.median_holding_period_days)} | {_format_value(row.max_holding_period_days)} | "
            f"{_format_value(after.terminal_liquidation_cagr, percent=True)} |",
        )
    lines += [
        "",
        "## Diagnostic fold continuity",
        "",
        "The fold table is a chronological diagnostic view of the single stitched ledger. Fold 2013 starts "
        "from the configured initial capital; each later fold starts from the prior session's live equity. "
        "No fold-end liquidation or state reconstruction is used. Cross-year episodes and tax loss-pool state "
        "therefore remain continuous.",
        "",
        f"`oos_fold_metrics.csv` contains {len(fold_metrics)} rows (24 stitched combinations × {len(folds)} folds).",
        "",
        "## Scope statement",
        "",
        "This is fixed-rule chronological OOS evidence for the already-frozen MA200 baseline. The expanding "
        "annual folds are reporting slices, not parameter-fitting intervals. No window is chosen from these "
        "results, and this artifact makes no Walk-Forward parameter-selection claim.",
    ]
    (output / "oos_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_walk_forward_fixed_ma200"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    prices = {
        asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    end = min(frame.index.max() for frame in prices.values())
    folds = expanding_calendar_year_folds(prices["SSO"].loc[:end].index)
    start = folds[0].test_start
    capital = float(config["initial_capital"])
    commission_bps = float(config["execution"]["commission_bps"])
    slippage_bps = float(config["execution"]["slippage_bps"])
    execution_rate = (commission_bps + slippage_bps) / 10_000.0
    tax_rate = float(config["tax"]["capital_gains_rate"])
    rows: list[dict[str, object]] = []
    fold_rows: list[dict[str, object]] = []
    curves: list[pd.DataFrame] = []
    drawdowns: list[pd.DataFrame] = []
    positions: list[pd.DataFrame] = []
    trades: list[pd.DataFrame] = []
    taxes: list[pd.DataFrame] = []

    for rule, (signal_asset, held_asset) in STRATEGIES.items():
        held_prices = prices[held_asset].loc[start:end]
        for frequency in FREQUENCIES:
            target = trend_target_next_open(
                prices[signal_asset]["adjusted_close"], frequency, MA_WINDOW,
            ).reindex(held_prices.index)
            if target.isna().any() or not target.index.equals(held_prices.index):
                raise ValueError("MA200 target and held-asset calendars are not aligned")
            for mode, mode_tax_rate in (("pre_tax", None), ("after_tax", tax_rate)):
                strategy = f"{rule}_{frequency}_OOS"
                # This is the sole execution call for the complete OOS span.
                # Annual folds below only slice its returned continuous ledger.
                ledger, position, trade, tax = single_asset_timed_backtest(
                    held_prices, target, initial_capital=capital,
                    commission_bps=commission_bps, slippage_bps=slippage_bps,
                    tax_rate=mode_tax_rate,
                )
                reporting_ledger = _add_pretrade_equity(ledger, held_prices, capital)
                metric = performance_metrics(
                    reporting_ledger,
                    trade,
                    capital,
                    terminal_tax_rate=mode_tax_rate,
                    terminal_cost_rate=execution_rate if mode_tax_rate is not None else 0.0,
                )
                metric.update({
                    "strategy": strategy,
                    "rule": rule,
                    "signal_asset": signal_asset,
                    "held_asset": held_asset,
                    "frequency": frequency,
                    "ma_window": MA_WINDOW,
                    "tax_mode": mode,
                    "result_type": "stitched_OOS",
                    "cumulative_realized_tax_paid": float(metric["tax_paid"]),
                    "tax_semantics": TAX_SEMANTICS_AFTER if mode == "after_tax" else TAX_SEMANTICS_PRE,
                })
                rows.append(metric)
                initial_date = pd.to_datetime(trade["date"]).min() if len(trade) else None
                for fold in folds:
                    prior = capital if fold.test_year == folds[0].test_year else float(
                        reporting_ledger.loc[reporting_ledger.index < fold.test_start, "equity"].iloc[-1],
                    )
                    fold_rows.append(_segment_metrics(
                        reporting_ledger,
                        trade,
                        fold.test_start,
                        fold.test_end,
                        prior,
                        strategy,
                        mode,
                        fold.test_year,
                        initial_date,
                    ))
                # Preserve the economic path tables exactly as produced by the
                # frozen execution engine; pretrade_equity is reporting-only.
                curves.append(ledger[["equity"]].assign(strategy=strategy, tax_mode=mode).reset_index())
                drawdowns.append(
                    drawdown_series(ledger.equity, capital).rename("drawdown").to_frame()
                    .assign(strategy=strategy, tax_mode=mode).reset_index(names="date")
                )
                positions.append(position.assign(strategy=strategy, tax_mode=mode))
                if len(trade):
                    trades.append(trade.assign(strategy=strategy, tax_mode=mode))
                if len(tax):
                    taxes.append(tax.assign(strategy=strategy, tax_mode=mode))

    metrics = pd.DataFrame(rows)
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].reset_index(drop=True)
    after = metrics.loc[metrics.tax_mode.eq("after_tax")].reset_index(drop=True)
    if len(pre) != 12 or len(after) != 12:
        raise AssertionError("Fixed MA200 OOS must produce 12 rows per tax mode")
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    metrics.to_csv(output / "oos_results.csv", index=False)
    pd.DataFrame(fold_rows).to_csv(output / "oos_fold_metrics.csv", index=False)
    fold_table(folds).to_csv(output / "walk_forward_folds.csv", index=False)
    pd.DataFrame([{
        "ma_window": MA_WINDOW,
        "selected": False,
        "searched_for_selection": False,
        "selection_performed": False,
        "selection_reason": "fixed MA200 baseline; no optimization",
    }]).to_csv(output / "parameter_results.csv", index=False)

    curve_table = pd.concat(curves, ignore_index=True)
    dd_table = pd.concat(drawdowns, ignore_index=True)
    position_table = pd.concat(positions, ignore_index=True)
    trade_table = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    tax_table = pd.concat(taxes, ignore_index=True) if taxes else pd.DataFrame()
    curve_table.to_csv(output / "equity_curve.csv", index=False)
    dd_table.to_csv(output / "drawdown.csv", index=False)
    position_table.to_csv(output / "positions.csv", index=False)
    trade_table.to_csv(output / "trades.csv", index=False)
    tax_table.to_csv(output / "tax_ledger.csv", index=False)

    _write_standard_plots(curve_table, dd_table, metrics, capital, output)
    _write_oos_report(
        output,
        metrics,
        pd.DataFrame(fold_rows),
        folds,
        _warmup_rows(prices, start, end),
        _alignment_rows(prices, start, end),
        start=start,
        end=end,
        execution_rate=execution_rate,
        tax_rate=tax_rate,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Fixed MA200 chronological OOS prerequisite")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
