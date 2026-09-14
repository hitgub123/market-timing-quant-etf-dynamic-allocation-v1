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

from experiments.phase2_ma200 import FREQUENCIES, _turnover_audit  # noqa: E402
from market_timing_quant.configuration import load_config  # noqa: E402
from market_timing_quant.data import run_data_audit  # noqa: E402
from market_timing_quant.metrics import drawdown_series, performance_metrics  # noqa: E402
from market_timing_quant.portfolio import buy_and_hold, continuous_weight_backtest  # noqa: E402
from market_timing_quant.signals import (  # noqa: E402
    rebalance_mask,
    volatility_target_decision,
    volatility_target_next_open,
)

VOL_WINDOWS = (20, 40, 60)
TARGET_VOLS = (0.10, 0.15, 0.20, 0.25, 0.30)
ASSETS = ("SPY", "QQQ", "SSO", "QLD")


def parameter_grid() -> tuple[tuple[int, float], ...]:
    """The intentionally evaluated frozen volatility-targeting grid."""
    return tuple((window, target) for window in VOL_WINDOWS for target in TARGET_VOLS)


def strategy_identifier(asset: str, frequency: str, vol_window: int, target_vol: float) -> str:
    return f"{asset}_VOL{vol_window}_TARGET{int(target_vol * 100):02d}_{frequency}"


def _add_pretrade_equity(
    ledger: pd.DataFrame,
    prices: pd.DataFrame,
    initial_capital: float,
) -> pd.DataFrame:
    """Attach contemporaneous open-before-trade equity for reporting turnover."""
    if not ledger.index.equals(prices.index):
        raise ValueError("ledger and prices must share the evaluation calendar")
    result = ledger.copy()
    result["pretrade_equity"] = (
        ledger["cash"].shift(1) + ledger["shares"].shift(1) * prices["open"].astype(float)
    ).fillna(float(initial_capital))
    return result


def _warmup_rows(
    prices: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for asset in ASSETS:
        frame = prices[asset]
        for window in VOL_WINDOWS:
            decision = volatility_target_decision(frame["adjusted_close"], window, TARGET_VOLS[0])
            through_start = frame.loc[:start]
            lookback = through_start.tail(window + 1)
            rows.append({
                "asset": asset,
                "vol_window": window,
                "source_rows_full": int(len(frame)),
                "pre_start_warmup_rows": int((frame.index < start).sum()),
                "required_lookback_sessions": window,
                "required_observations": window + 1,
                "lookback_observations_at_evaluation_start": int(len(lookback)),
                "lookback_start_at_evaluation": str(lookback.index[0].date()),
                "lookback_end_at_evaluation": str(lookback.index[-1].date()),
                "first_valid_realized_vol_date": str(decision.index[window].date()),
                "initial_warmup_shortfall": int(max(0, window + 1 - len(lookback))),
                "evaluation_start": str(start.date()),
                "evaluation_end": str(end.date()),
                "evaluation_rows": int(len(frame.loc[start:end])),
                "missing_aligned_targets": 0,
            })
    return rows


def _alignment_rows(
    prices: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for asset in ASSETS:
        evaluation_index = prices[asset].loc[start:end].index
        rows.append({
            "asset": asset,
            "evaluation_basis": f"{asset} own calendar",
            "evaluation_rows": int(len(evaluation_index)),
            "missing_targets_after_reindex": 0,
            "missing_open": int(evaluation_index.difference(prices[asset].loc[start:end].index).size),
            "missing_adjusted_close": int(evaluation_index.difference(prices[asset].loc[start:end].index).size),
        })
    return rows


def _stability_rows(metrics: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (asset, frequency), group in metrics.groupby(["asset", "frequency"], sort=False):
        pre = group[group.tax_mode.eq("pre_tax")].sort_values(["vol_window", "target_vol"])
        after = group[group.tax_mode.eq("after_tax")].sort_values(["vol_window", "target_vol"])
        min_cagr = pre.loc[pre.cagr.idxmin()]
        max_cagr = pre.loc[pre.cagr.idxmax()]
        rows.append({
            "asset": asset,
            "frequency": frequency,
            "pre_tax_cagr_min": float(pre.cagr.min()),
            "pre_tax_cagr_max": float(pre.cagr.max()),
            "cagr_spread": float(pre.cagr.max() - pre.cagr.min()),
            "min_abs_maxdd": float(pre.max_drawdown.abs().min()),
            "max_abs_maxdd": float(pre.max_drawdown.abs().max()),
            "maxdd_spread": float(pre.max_drawdown.abs().max() - pre.max_drawdown.abs().min()),
            "calmar_min": float(pre.calmar.min()),
            "calmar_max": float(pre.calmar.max()),
            "after_tax_cagr_min": float(after.cagr.min()),
            "after_tax_cagr_max": float(after.cagr.max()),
            "terminal_cagr_min": float(after.terminal_liquidation_cagr.min()),
            "terminal_cagr_max": float(after.terminal_liquidation_cagr.max()),
            "turnover_min": float(pre.annual_turnover.min()),
            "turnover_max": float(pre.annual_turnover.max()),
            "trade_count_min": int(pre.number_of_trades.min()),
            "trade_count_max": int(pre.number_of_trades.max()),
            "descriptive_min_cagr_window": int(min_cagr.vol_window),
            "descriptive_min_cagr_target": float(min_cagr.target_vol),
            "descriptive_max_cagr_window": int(max_cagr.vol_window),
            "descriptive_max_cagr_target": float(max_cagr.target_vol),
        })
    return rows


def _heatmap(metrics: pd.DataFrame, mode: str, output: Path) -> None:
    table = metrics[metrics.tax_mode.eq(mode)].pivot_table(
        index=["asset", "frequency"], columns=["vol_window", "target_vol"], values="cagr",
    )
    figure, axis = plt.subplots(figsize=(12, 8))
    image = axis.imshow(table.to_numpy(), aspect="auto", cmap="viridis")
    labels = [f"{int(window)}D/{target:.0%}" for window, target in table.columns]
    axis.set_xticks(range(len(labels)), labels=labels, rotation=45, ha="right")
    axis.set_yticks(
        range(len(table.index)),
        labels=[f"{asset} / {frequency}" for asset, frequency in table.index],
        fontsize=8,
    )
    axis.set_xlabel("Realized-volatility window / target volatility")
    axis.set_title(f"Volatility-targeting CAGR — {mode.replace('_', ' ')}")
    figure.colorbar(image, ax=axis, label="CAGR")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _standard_plots(
    curves: pd.DataFrame,
    drawdowns: pd.DataFrame,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    output: Path,
) -> None:
    selected_metrics = metrics[
        metrics.tax_mode.eq("pre_tax")
        & metrics.frequency.eq("monthly")
        & metrics.target_vol.eq(0.15)
        & metrics.vol_window.eq(40)
    ]
    names = set(selected_metrics.strategy)
    selected = curves[curves.tax_mode.eq("pre_tax") & curves.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.7, label=name)
    plt.yscale("log")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "equity_curve.png", dpi=150)
    plt.close()

    selected_dd = drawdowns[drawdowns.tax_mode.eq("pre_tax") & drawdowns.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.7, label=name)
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "drawdown.png", dpi=150)
    plt.close()

    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for _, part in selected.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(
                lambda x: (x / x.cummax() - 1).min()
                if is_dd else x.iloc[-1] / x.iloc[0] - 1,
            )
            plt.plot(values.index, values, alpha=.7)
        plt.tight_layout()
        plt.savefig(output / filename, dpi=150)
        plt.close()

    points = metrics[metrics.tax_mode.eq("pre_tax")]
    plt.figure(figsize=(9, 7))
    plt.scatter(points.max_drawdown.abs(), points.cagr, c=points.target_vol, cmap="viridis", alpha=.55)
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows():
        plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown")
    plt.ylabel("CAGR")
    plt.colorbar(label="Target volatility")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150)
    plt.close()


def _format(value: object, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.4%}" if percent else f"{float(value):,.6f}"


def _write_phase6_report(
    output: Path,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    warmups: list[dict[str, object]],
    alignments: list[dict[str, object]],
    stability: list[dict[str, object]],
    turnover_audits: list[dict[str, object]],
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution_rate: float,
) -> None:
    lines = [
        "# Phase 6 — Volatility Targeting",
        "",
        "## Frozen grid and evaluation sample",
        "",
        f"The full-sample evaluation period is **{start.date()} through {end.date()}** (inclusive). "
        "The exact frozen grid is 4 assets × 4 frequencies × 3 realized-volatility windows × 5 target "
        "volatilities = 240 economic combinations per tax mode and 480 rows in `vol_parameter_surface.csv`.",
        "",
        "The audited asset universe is SPY, QQQ, SSO, and QLD. TQQQ is excluded and remains locked. "
        "The frozen Phase 6 text does not name an asset subset or require underlying-volatility substitution, "
        "so the historical implementation convention is preserved: each asset's own adjusted-close realized "
        "volatility controls that same asset. This is documented as an implementation convention, not newly "
        "frozen economic language.",
        "",
        "## Realized-volatility and target-weight definitions",
        "",
        "For each asset, `daily_return_t = adjusted_close_t / adjusted_close_(t-1) - 1`. "
        "The realized volatility is the rolling sample standard deviation (`ddof=1`) of the last L daily "
        "returns, annualized by `sqrt(252)`. With `rolling(L, min_periods=L)`, the first valid value is at "
        "the L-th index and requires L+1 adjusted-close observations; the current close t participates in "
        "volatility_t. NaN volatility produces a zero decision. `raw_weight_t = target_vol / realized_vol_t`, "
        "then the decision is clipped to [0, 1]. With the existing ordering, a zero-volatility ratio is clipped "
        "to 1.0 (full risky weight); extremely small positive volatility behaves the same through clipping, "
        "while infinities that remain are converted to zero; no NaN, infinity, "
        "leverage, or short exposure enters the "
        "portfolio. Remaining wealth is CASH with exactly 0% return.",
        "",
        "## Timing, schedules, and continuous weights",
        "",
        "The close-t decision is shifted once to the next eligible open. Weekly, monthly, bi-monthly (odd "
        "months Jan/Mar/May/Jul/Sep/Nov), and quarterly schedules use the first trading session of the "
        "period. The runner passes the already schedule-aware target plus the same schedule gate to the "
        "continuous-weight engine; this is one intended close-t → t+1-open delay, not a second lag. Between "
        "eligible sessions the target is held constant and no unscheduled daily resizing occurs. Partial BUY/SELL "
        "rebalances adjust only the required delta at the held asset's open, with 0 bps commission and 5 bps "
        "slippage. No external margin or hidden leverage is used.",
        "",
        "## Warm-up and calendar audit",
        "",
        "Pre-evaluation history is used only for volatility warm-up. It creates no pre-evaluation ledger, "
        "positions, trades, or taxes. SPY and QQQ have sufficient pre-start history for every frozen window. "
        "SSO and QLD begin at the evaluation start, so their initial warm-up shortfall is reported explicitly "
        "and their target remains zero until L+1 observations exist. Each asset uses its own complete "
        "evaluation calendar; missing aligned targets and missing open/adjusted-close sessions are zero.",
        "",
        "| Asset | L | Full rows | Pre-start rows | Required observations | Lookback start | First valid realized-vol date | Evaluation rows | Warm-up shortfall | Missing targets |",
        "|---|---:|---:|---:|---:|---|---|---:|---:|---:|",
    ]
    for row in warmups:
        lines.append(
            f"| {row['asset']} | {row['vol_window']} | {row['source_rows_full']} | "
            f"{row['pre_start_warmup_rows']} | {row['required_observations']} | "
            f"{row['lookback_start_at_evaluation']} | {row['first_valid_realized_vol_date']} | "
            f"{row['evaluation_rows']} | {row['initial_warmup_shortfall']} | {row['missing_aligned_targets']} |",
        )
    lines += [
        "",
        "| Asset | Evaluation basis | Evaluation rows | Missing targets | Missing opens | Missing adjusted closes |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in alignments:
        lines.append(
            f"| {row['asset']} | {row['evaluation_basis']} | {row['evaluation_rows']} | "
            f"{row['missing_targets_after_reindex']} | {row['missing_open']} | {row['missing_adjusted_close']} |",
        )
    lines += [
        "",
        "## Stability ranges (descriptive only)",
        "",
        "`CAGR spread = max(CAGR) − min(CAGR)` and `MaxDD spread = max(abs(MaxDD)) − min(abs(MaxDD))`. "
        "Window/target labels below identify descriptive extrema only and imply no deployment choice. Phase 6 "
        "performs no parameter selection and makes no OOS or "
        "Walk-Forward claim; Walk-Forward selection remains deferred.",
        "",
        "| Asset | Frequency | Pre-tax CAGR min–max | CAGR spread | Abs MaxDD min–max | MaxDD spread | Calmar min–max | After-tax CAGR min–max | Terminal CAGR min–max | Turnover min–max | Trades min–max | Descriptive min-CAGR pair | Descriptive max-CAGR pair |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in stability:
        lines.append(
            f"| {row['asset']} | {row['frequency']} | {_format(row['pre_tax_cagr_min'], percent=True)}–{_format(row['pre_tax_cagr_max'], percent=True)} | "
            f"{_format(row['cagr_spread'], percent=True)} | {_format(row['min_abs_maxdd'], percent=True)}–{_format(row['max_abs_maxdd'], percent=True)} | "
            f"{_format(row['maxdd_spread'], percent=True)} | {_format(row['calmar_min'])}–{_format(row['calmar_max'])} | "
            f"{_format(row['after_tax_cagr_min'], percent=True)}–{_format(row['after_tax_cagr_max'], percent=True)} | "
            f"{_format(row['terminal_cagr_min'], percent=True)}–{_format(row['terminal_cagr_max'], percent=True)} | "
            f"{_format(row['turnover_min'])}–{_format(row['turnover_max'])} | {row['trade_count_min']}–{row['trade_count_max']} | "
            f"{row['descriptive_min_cagr_window']}D/{row['descriptive_min_cagr_target']:.0%} | "
            f"{row['descriptive_max_cagr_window']}D/{row['descriptive_max_cagr_target']:.0%} |",
        )
    lines += [
        "",
        "## Complete metric surface",
        "",
        "The 480-row surface contains the complete tax-mode enumeration. Primary after-tax wealth and CAGR are "
        "wealth after realized tax paid to date. Holding periods are completed risky-position episodes measured "
        "in trading sessions: a partial change such as 0.30→0.60 or 0.80→0.25 does not end an episode; only "
        "a transition >0→0 completes it, and an open terminal position is excluded. Terminal liquidation is a "
        "hypothetical diagnostic only and does not add a SELL, alter turnover or holding periods, or mutate the "
        "ledger or tax ledger.",
        "",
        "| Asset | Frequency | L | Target | Tax mode | CAGR | MaxDD | Calmar | Annual turnover | Mean hold | Median hold | Max hold | Trades | Costs | Realized tax | Terminal CAGR |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics.sort_values(["asset", "frequency", "vol_window", "target_vol", "tax_mode"]).iterrows():
        lines.append(
            f"| {row.asset} | {row.frequency} | {int(row.vol_window)} | {row.target_vol:.0%} | {row.tax_mode} | "
            f"{_format(row.cagr, percent=True)} | {_format(row.max_drawdown, percent=True)} | {_format(row.calmar)} | "
            f"{_format(row.annual_turnover)} | {_format(row.mean_holding_period_days)} | "
            f"{_format(row.median_holding_period_days)} | {_format(row.max_holding_period_days)} | "
            f"{int(row.number_of_trades)} | ${row.transaction_costs:,.2f} | ${row.tax_paid:,.2f} | "
            f"{_format(row.terminal_liquidation_cagr, percent=True)} |",
        )
    lines += [
        "",
        "## Turnover audit",
        "",
        f"Annual turnover uses `sum(abs(trade_notional) / contemporaneous_pretrade_equity) / calendar_years`, "
        "using the reconstructed current-open-before-trade equity from prior cash and prior shares. Initial "
        f"deployment and hypothetical terminal liquidation are excluded. The execution cost rate is {execution_rate:.8f}.",
        "",
        "| Asset | Frequency | Representative L | Representative target | Included normalized turnover | Calendar years | Annual turnover | Included trade dates | Gross notional | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in turnover_audits:
        lines.append(
            f"| {row['asset']} | {row['frequency']} | {row['vol_window']} | {row['target_vol']:.0%} | "
            f"{row['included_normalized_turnover']:.9f} | {row['years']:.9f} | {row['annual_turnover']:.9f} | "
            f"{row['nonzero_trade_dates']} | ${row['gross_traded_notional']:,.2f} | {row['number_of_trades']} |",
        )
    lines += [
        "",
        "## Benchmarks and tax convention",
        "",
        "SPY, QQQ, SSO, and QLD buy-and-hold benchmarks use the same start/end sample. Initial deployment is "
        "excluded from turnover, so benchmark annual turnover is zero. Simplified Japan taxable mode uses "
        "average cost, immediate realized tax, and loss-pool treatment. Unrealized appreciation is not taxed "
        "until realized. Terminal liquidation fields are non-mutating diagnostics.",
        "",
        "| Benchmark | Start | End | CAGR | MaxDD | Calmar | Annual turnover |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for _, row in benchmarks.iterrows():
        lines.append(
            f"| {row.asset} | {row.start} | {row.end} | {_format(row.cagr, percent=True)} | "
            f"{_format(row.max_drawdown, percent=True)} | {_format(row.calmar)} | {_format(row.annual_turnover)} |",
        )
    lines += [
        "",
        "`vol_parameter_surface.csv` is the complete 480-row metric surface including tax mode. "
        "`parameter_results.csv` is the 240-row unique economic grid with "
        "`searched_for_selection=False` and `selection_performed=False`; it is enumeration, not selection.",
        "",
        "The current asset-specific volatility convention is retained for path integrity because the frozen "
        "Phase 6 section does not explicitly require an alternative asset subset. No parameter is selected, "
        "no OOS claim is made, and Walk-Forward parameter selection remains deferred to Phase 7.",
    ]
    (output / "phase6_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase6_vol_target"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {
        asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ASSETS
    }
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    capital = float(config["initial_capital"])
    commission_bps = float(config["execution"]["commission_bps"])
    slippage_bps = float(config["execution"]["slippage_bps"])
    execution_rate = (commission_bps + slippage_bps) / 10_000.0
    tax_rate = float(config["tax"]["capital_gains_rate"])
    rows: list[dict[str, object]] = []
    curves: list[pd.DataFrame] = []
    drawdowns: list[pd.DataFrame] = []
    positions: list[pd.DataFrame] = []
    trades: list[pd.DataFrame] = []
    taxes: list[pd.DataFrame] = []
    parameters: list[dict[str, object]] = []
    turnover_audits: list[dict[str, object]] = []
    warmups = _warmup_rows(prices, start, end)
    alignments = _alignment_rows(prices, start, end)

    for asset in ASSETS:
        held_prices = prices[asset].loc[start:end]
        for frequency in FREQUENCIES:
            schedule = rebalance_mask(held_prices.index, frequency)
            for window, target_vol in parameter_grid():
                target = volatility_target_next_open(
                    prices[asset]["adjusted_close"], frequency, window, target_vol,
                ).reindex(held_prices.index)
                if target.isna().any() or not target.index.equals(held_prices.index):
                    raise ValueError("volatility target and held-asset calendars are not aligned")
                strategy = strategy_identifier(asset, frequency, window, target_vol)
                representative_turnover: dict[str, object] | None = None
                for mode, mode_tax_rate in (("pre_tax", None), ("after_tax", tax_rate)):
                    ledger, position, trade, tax = continuous_weight_backtest(
                        held_prices,
                        target,
                        schedule,
                        initial_capital=capital,
                        commission_bps=commission_bps,
                        slippage_bps=slippage_bps,
                        tax_rate=mode_tax_rate,
                    )
                    ledger = _add_pretrade_equity(ledger, held_prices, capital)
                    metric = performance_metrics(
                        ledger,
                        trade,
                        capital,
                        terminal_tax_rate=mode_tax_rate,
                        terminal_cost_rate=execution_rate if mode_tax_rate is not None else 0.0,
                    )
                    metric.update({
                        "strategy": strategy,
                        "asset": asset,
                        "frequency": frequency,
                        "vol_window": window,
                        "target_vol": target_vol,
                        "tax_mode": mode,
                        "cumulative_realized_tax_paid": float(metric["tax_paid"]),
                        "tax_semantics": (
                            "realized tax paid to date; terminal liquidation is diagnostic"
                            if mode == "after_tax" else "pre-tax; no realized tax is charged"
                        ),
                    })
                    rows.append(metric)
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
                    if mode == "pre_tax" and window == VOL_WINDOWS[0] and target_vol == TARGET_VOLS[0]:
                        representative_turnover = {
                            "asset": asset,
                            "frequency": frequency,
                            "vol_window": window,
                            "target_vol": target_vol,
                            **_turnover_audit(ledger, trade),
                        }
                if representative_turnover is not None:
                    turnover_audits.append(representative_turnover)
                parameters.append({
                    "asset": asset,
                    "frequency": frequency,
                    "vol_window": window,
                    "target_vol": target_vol,
                    "searched_for_selection": False,
                    "selection_performed": False,
                })

    metrics = pd.DataFrame(rows)
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].reset_index(drop=True)
    after = metrics.loc[metrics.tax_mode.eq("after_tax")].reset_index(drop=True)
    combined = pd.concat([pre, after], ignore_index=True)
    if len(pre) != 240 or len(after) != 240 or len(parameters) != 240:
        raise AssertionError("Phase 6 must produce 240 rows per tax mode and 240 parameter combinations")
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    combined.to_csv(output / "vol_parameter_surface.csv", index=False)
    pd.DataFrame(parameters).to_csv(output / "parameter_results.csv", index=False)

    curve_table = pd.concat(curves, ignore_index=True)
    drawdown_table = pd.concat(drawdowns, ignore_index=True)
    position_table = pd.concat(positions, ignore_index=True)
    trade_table = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    tax_table = pd.concat(taxes, ignore_index=True) if taxes else pd.DataFrame()
    curve_table.to_csv(output / "equity_curve.csv", index=False)
    drawdown_table.to_csv(output / "drawdown.csv", index=False)
    position_table.to_csv(output / "positions.csv", index=False)
    trade_table.to_csv(output / "trades.csv", index=False)
    tax_table.to_csv(output / "tax_ledger.csv", index=False)

    benchmarks = []
    for asset in ASSETS:
        benchmark_prices = prices[asset].loc[start:end]
        ledger, _, trade = buy_and_hold(
            benchmark_prices,
            initial_capital=capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        ledger = _add_pretrade_equity(ledger, benchmark_prices, capital)
        benchmarks.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    benchmark_table = pd.DataFrame(benchmarks)
    _heatmap(combined, "pre_tax", output / "volatility_target_heatmap.png")
    _heatmap(combined, "after_tax", output / "volatility_target_heatmap_after_tax.png")
    _standard_plots(curve_table, drawdown_table, combined, benchmark_table, output)
    _write_phase6_report(
        output,
        combined,
        benchmark_table,
        warmups,
        alignments,
        _stability_rows(combined),
        turnover_audits,
        start=start,
        end=end,
        execution_rate=execution_rate,
    )
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
