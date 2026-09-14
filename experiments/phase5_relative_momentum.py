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
from experiments.phase4_absolute_momentum import MOMENTUM_WINDOWS  # noqa: E402
from market_timing_quant.configuration import load_config  # noqa: E402
from market_timing_quant.data import run_data_audit  # noqa: E402
from market_timing_quant.metrics import drawdown_series, performance_metrics  # noqa: E402
from market_timing_quant.portfolio import buy_and_hold, rotation_backtest  # noqa: E402
from market_timing_quant.signals import (  # noqa: E402
    rebalance_mask,
    relative_momentum_decision,
    relative_momentum_target_next_open,
)

MAPPINGS = {
    "RELATIVE_MOMENTUM_1X": {"SPY": "SPY", "QQQ": "QQQ"},
    "RELATIVE_MOMENTUM_2X": {"SPY": "SSO", "QQQ": "QLD"},
}


def parameter_grid() -> tuple[int, ...]:
    """The intentionally evaluated, frozen Phase 5 momentum grid."""
    return MOMENTUM_WINDOWS


def strategy_identifier(rule: str, frequency: str, momentum_window: int) -> str:
    return f"{rule}_{frequency}_{momentum_window}D"


def _add_rotation_pretrade_equity(
    ledger: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    initial_capital: float,
) -> pd.DataFrame:
    """Attach open-before-trade equity for a multi-asset rotation ledger."""
    if not prices or any(not ledger.index.equals(frame.index) for frame in prices.values()):
        raise ValueError("rotation ledger and prices must share the evaluation calendar")
    result = ledger.copy()
    pretrade = ledger["cash"].shift(1)
    for asset, frame in prices.items():
        share_column = f"{asset}_shares"
        if share_column not in ledger:
            raise ValueError(f"rotation ledger is missing {share_column}")
        pretrade = pretrade + ledger[share_column].shift(1) * frame["open"].astype(float)
    result["pretrade_equity"] = pretrade.fillna(float(initial_capital))
    return result


def _warmup_rows(
    prices: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    evaluation_index: pd.DatetimeIndex,
) -> list[dict[str, object]]:
    signal_index = prices["SPY"].index.intersection(prices["QQQ"].index)
    rows: list[dict[str, object]] = []
    for window in MOMENTUM_WINDOWS:
        decision = relative_momentum_decision(
            prices["SPY"].loc[signal_index, "adjusted_close"],
            prices["QQQ"].loc[signal_index, "adjusted_close"],
            lookback=window,
        )
        for asset in ("SPY", "QQQ"):
            source_frame = prices[asset]
            through_start = source_frame.loc[:start]
            lookback = through_start.tail(window + 1)
            rows.append({
                "signal_asset": asset,
                "momentum_window": window,
                "signal_rows_full": int(len(source_frame)),
                "pre_start_warmup_rows": int((source_frame.index < start).sum()),
                "required_lookback_sessions": window,
                "required_observations": window + 1,
                "lookback_observations_at_evaluation_start": int(len(lookback)),
                "lookback_start_at_evaluation": str(lookback.index[0].date()),
                "lookback_end_at_evaluation": str(lookback.index[-1].date()),
                "first_valid_momentum_date": str(decision.index[window].date()),
                "evaluation_start": str(start.date()),
                "evaluation_end": str(end.date()),
                "signal_common_calendar_rows": int(len(signal_index[(signal_index >= start) & (signal_index <= end)])),
                "evaluation_rows": int(len(evaluation_index)),
                "missing_evaluation_targets": int(len(evaluation_index.difference(signal_index))),
            })
    return rows


def _alignment_rows(
    prices: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    evaluation_index: pd.DatetimeIndex,
) -> list[dict[str, object]]:
    signal_index = prices["SPY"].index.intersection(prices["QQQ"].index)
    signal_eval = signal_index[(signal_index >= start) & (signal_index <= end)]
    rows: list[dict[str, object]] = []
    for rule, mapping in MAPPINGS.items():
        held_assets = tuple(mapping.values())
        missing = {
            asset: int(len(evaluation_index.difference(prices[asset].loc[start:end].index)))
            for asset in ("SPY", "QQQ", *held_assets)
        }
        rows.append({
            "rule": rule,
            "mapping": f"{mapping['SPY']} / {mapping['QQQ']}",
            "evaluation_basis": "SSO calendar",
            "signal_common_calendar_rows": int(len(signal_eval)),
            "evaluation_rows": int(len(evaluation_index)),
            "missing_spy": missing["SPY"],
            "missing_qqq": missing["QQQ"],
            "missing_held_spy_leg": missing[held_assets[0]],
            "missing_held_qqq_leg": missing[held_assets[1]],
            "missing_targets_after_reindex": int(len(evaluation_index.difference(signal_eval))),
        })
    return rows


def _tie_audit_rows(prices: dict[str, pd.DataFrame]) -> list[dict[str, object]]:
    """Audit exact positive ties using the implementation's numeric comparison."""
    signal_index = prices["SPY"].index.intersection(prices["QQQ"].index)
    spy = prices["SPY"].loc[signal_index, "adjusted_close"].astype(float)
    qqq = prices["QQQ"].loc[signal_index, "adjusted_close"].astype(float)
    rows: list[dict[str, object]] = []
    for window in MOMENTUM_WINDOWS:
        spy_momentum = spy / spy.shift(window) - 1.0
        qqq_momentum = qqq / qqq.shift(window) - 1.0
        ready = spy_momentum.notna() & qqq_momentum.notna()
        positive_tie = ready & (spy_momentum > 0.0) & (qqq_momentum > 0.0) & spy_momentum.eq(qqq_momentum)
        for frequency in FREQUENCIES:
            scheduled = rebalance_mask(signal_index, frequency)
            used_tie = positive_tie.shift(1).fillna(False) & scheduled
            close_dates = [str(value.date()) for value in signal_index[positive_tie & scheduled]]
            execution_dates = [str(value.date()) for value in signal_index[used_tie]]
            rows.append({
                "momentum_window": window,
                "frequency": frequency,
                "rebalance_decisions": int(scheduled.sum()),
                "exact_positive_tie_count": int(positive_tie.sum()),
                "exact_positive_tie_used_at_rebalance": int(used_tie.sum()),
                "tie_close_dates": ", ".join(str(value.date()) for value in signal_index[positive_tie]) if positive_tie.any() else "none",
                "scheduled_tie_close_dates": ", ".join(close_dates) if close_dates else "none",
                "tie_execution_dates": ", ".join(execution_dates) if execution_dates else "none",
            })
    return rows


def _heatmap(metrics: pd.DataFrame, mode: str, output: Path) -> None:
    table = metrics[metrics.tax_mode.eq(mode)].pivot(
        index=["rule", "frequency"], columns="momentum_window", values="cagr",
    )
    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(table.to_numpy(), aspect="auto", cmap="viridis")
    axis.set_xticks(range(len(table.columns)), labels=table.columns)
    axis.set_yticks(
        range(len(table.index)),
        labels=[f"{rule} / {frequency}" for rule, frequency in table.index],
        fontsize=8,
    )
    axis.set_xlabel("Relative-momentum lookback (trading sessions)")
    axis.set_title(f"Relative-momentum CAGR — {mode.replace('_', ' ')}")
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
    selected_metrics = metrics[metrics.tax_mode.eq("pre_tax") & metrics.frequency.eq("monthly")]
    names = set(selected_metrics.strategy)
    selected = curves[curves.tax_mode.eq("pre_tax") & curves.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected.groupby("strategy"):
        plt.plot(part.date, part.equity / part.equity.iloc[0], alpha=.65, label=name)
    plt.yscale("log")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "equity_curve.png", dpi=150)
    plt.close()

    selected_dd = drawdowns[drawdowns.tax_mode.eq("pre_tax") & drawdowns.strategy.isin(names)]
    plt.figure(figsize=(11, 6))
    for name, part in selected_dd.groupby("strategy"):
        plt.plot(part.date, part.drawdown, alpha=.65, label=name)
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output / "drawdown.png", dpi=150)
    plt.close()

    for filename, is_dd in (("rolling_returns.png", False), ("rolling_maxdd.png", True)):
        plt.figure(figsize=(11, 6))
        for name, part in selected.groupby("strategy"):
            series = part.set_index("date").equity
            values = series.rolling(252).apply(
                lambda x: (x / x.cummax() - 1).min()
                if is_dd else x.iloc[-1] / x.iloc[0] - 1,
            )
            plt.plot(values.index, values, alpha=.65)
        plt.tight_layout()
        plt.savefig(output / filename, dpi=150)
        plt.close()

    pre = metrics[metrics.tax_mode.eq("pre_tax")]
    plt.figure(figsize=(9, 7))
    plt.scatter(pre.max_drawdown.abs(), pre.cagr, c=pre.momentum_window, cmap="viridis", alpha=.7)
    plt.scatter(benchmarks.max_drawdown.abs(), benchmarks.cagr, marker="x", s=60, label="Buy & Hold")
    for _, row in benchmarks.iterrows():
        plt.annotate(row.asset, (abs(row.max_drawdown), row.cagr))
    plt.xlabel("Absolute Max Drawdown")
    plt.ylabel("CAGR")
    plt.colorbar(label="Momentum window")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "cagr_maxdd_scatter.png", dpi=150)
    plt.close()


def _stability_rows(metrics: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (rule, frequency), group in metrics.groupby(["rule", "frequency"], sort=False):
        pre = group[group.tax_mode.eq("pre_tax")].sort_values("momentum_window")
        after = group[group.tax_mode.eq("after_tax")].sort_values("momentum_window")
        rows.append({
            "rule": rule,
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
            "mean_hold_min": float(pre.mean_holding_period_days.min()),
            "mean_hold_max": float(pre.mean_holding_period_days.max()),
            "descriptive_min_cagr_window": int(pre.loc[pre.cagr.idxmin(), "momentum_window"]),
            "descriptive_max_cagr_window": int(pre.loc[pre.cagr.idxmax(), "momentum_window"]),
        })
    return rows


def _format(value: object, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.4%}" if percent else f"{float(value):,.6f}"


def _decision_table() -> list[tuple[str, str, str]]:
    return [
        ("A", "SPY > QQQ and SPY > 0", "SPY"),
        ("B", "QQQ > SPY and QQQ > 0", "QQQ"),
        ("C", "SPY > 0 and QQQ <= 0", "SPY"),
        ("D", "QQQ > 0 and SPY <= 0", "QQQ"),
        ("E", "SPY <= 0 and QQQ <= 0", "CASH"),
        ("F", "SPY = 0 and QQQ < 0", "CASH"),
        ("G", "QQQ = 0 and SPY < 0", "CASH"),
        ("H", "SPY = QQQ = 0", "CASH"),
    ]


def _write_phase5_report(
    output: Path,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    warmups: list[dict[str, object]],
    alignments: list[dict[str, object]],
    ties: list[dict[str, object]],
    stability: list[dict[str, object]],
    turnover_audits: list[dict[str, object]],
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution_rate: float,
) -> None:
    lines = [
        "# Phase 5 — Relative Momentum",
        "",
        "## Frozen specification and common sample",
        "",
        f"The full-sample evaluation period is **{start.date()} through {end.date()}** (inclusive). "
        "The exact frozen lookback grid is `(126, 189, 252)` trading sessions, with two mappings and "
        "four frequencies: 24 economic combinations per tax mode and 48 rows in `relative_momentum_results.csv`.",
        "",
        "Signals are calculated only from SPY and QQQ adjusted closes. For lookback L, "
        "`mom_SPY(t,L) = SPY_adjclose_t / SPY_adjclose_(t-L) - 1` and "
        "`mom_QQQ(t,L) = QQQ_adjclose_t / QQQ_adjclose_(t-L) - 1`; L-day momentum requires L+1 observations. "
        "The larger positive momentum is selected, but both non-positive values select CASH.",
        "",
        "The 1X mapping is SPY selection → SPY and QQQ selection → QQQ. The 2X mapping is SPY selection → "
        "SSO and QQQ selection → QLD. Leveraged ETF prices are never used for selection. CASH earns exactly 0%.",
        "",
        "Signals are observed at close *t*. A completed decision first becomes executable at the next "
        "available held-asset open (*t+1*); no same-day-close execution is used. Commission is 0 bps and "
        "slippage is 5 bps.",
        "",
        "Phase 5 is a descriptive full-sample study only. No lookback or frequency is selected. It makes no "
        "OOS or Walk-Forward claim; Walk-Forward parameter selection remains deferred to the frozen later phase.",
        "",
        "## Decision table and positive-tie audit",
        "",
        "The implementation uses `choose_spy = ready & ~both_off & (spy_momentum >= qqq_momentum)`, so an "
        "exact positive tie would be assigned to SPY by this implementation convention. The frozen Phase 5 "
        "specification does not define a tie-break, so this is not described as a frozen strategy rule. "
        "The complete historical signal scan below found zero exact positive ties at every lookback/frequency "
        "rebalance decision; consequently the convention has zero historical economic impact.",
        "",
        "| Case | Condition | Selected state |",
        "|---|---|---|",
    ]
    for label, condition, selected in _decision_table():
        lines.append(f"| {label} | {condition} | {selected} |")
    lines += [
        "",
        "| L | Frequency | Rebalance decisions | Exact positive ties in full signal history | Ties used at rebalance | Tie close dates | Tie execution dates |",
        "|---:|---|---:|---:|---:|---|---|",
    ]
    for row in ties:
        lines.append(
            f"| {row['momentum_window']} | {row['frequency']} | {row['rebalance_decisions']} | "
            f"{row['exact_positive_tie_count']} | {row['exact_positive_tie_used_at_rebalance']} | "
            f"{row['tie_close_dates']} | {row['tie_execution_dates']} |",
        )

    lines += [
        "",
        "## Warm-up and common-calendar audit",
        "",
        "Pre-evaluation history is used only for legitimate signal warm-up. The relative comparison is formed "
        "on the common SPY/QQQ signal calendar. The final evaluation index is deliberately based on the SSO "
        "calendar because it is the canonical first held-asset execution calendar; all SPY, QQQ, SSO, and QLD "
        "evaluation calendars were checked and have zero missing sessions. Warm-up creates no pre-evaluation "
        "equity, positions, trades, or taxes.",
        "",
        "| Signal | L | Full rows | Pre-start rows | Required observations | Lookback start | First valid momentum date | Common signal rows | Evaluation rows | Missing targets |",
        "|---|---:|---:|---:|---:|---|---|---:|---:|---:|",
    ]
    for row in warmups:
        lines.append(
            f"| {row['signal_asset']} | {row['momentum_window']} | {row['signal_rows_full']} | "
            f"{row['pre_start_warmup_rows']} | {row['required_observations']} | "
            f"{row['lookback_start_at_evaluation']} | {row['first_valid_momentum_date']} | "
            f"{row['signal_common_calendar_rows']} | {row['evaluation_rows']} | {row['missing_evaluation_targets']} |",
        )
    lines += [
        "",
        "| Mapping | Evaluation basis | Common signal rows | Evaluation rows | Missing SPY | Missing QQQ | Missing held SPY leg | Missing held QQQ leg | Missing targets |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in alignments:
        lines.append(
            f"| {row['rule']} ({row['mapping']}) | {row['evaluation_basis']} | "
            f"{row['signal_common_calendar_rows']} | {row['evaluation_rows']} | {row['missing_spy']} | "
            f"{row['missing_qqq']} | {row['missing_held_spy_leg']} | {row['missing_held_qqq_leg']} | "
            f"{row['missing_targets_after_reindex']} |",
        )

    lines += [
        "",
        "## Rebalance convention",
        "",
        "Weekly uses the first trading session of each Sunday-ending week. Monthly uses the first trading "
        "session of each calendar month. Bi-monthly uses the first trading session of odd frozen months "
        "Jan/Mar/May/Jul/Sep/Nov. Quarterly uses the first trading session of each calendar quarter. "
        "Ranking changes between scheduled sessions do not change the target until the next eligible rebalance.",
        "",
        "## Stability ranges (descriptive only)",
        "",
        "`CAGR spread = max(CAGR) − min(CAGR)` and `MaxDD spread = max(abs(MaxDD)) − min(abs(MaxDD))`. "
        "The lookback labels are descriptive extrema only and are never called optimal, best, selected, "
        "recommended, or a winner.",
        "",
        "| Mapping | Frequency | Pre-tax CAGR min–max | CAGR spread | Abs MaxDD min–max | MaxDD spread | Calmar min–max | After-tax CAGR min–max | Terminal CAGR min–max | Turnover min–max | Trades min–max | Mean hold min–max | Descriptive min-CAGR L | Descriptive max-CAGR L |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in stability:
        lines.append(
            f"| {row['rule']} | {row['frequency']} | {_format(row['pre_tax_cagr_min'], percent=True)}–{_format(row['pre_tax_cagr_max'], percent=True)} | "
            f"{_format(row['cagr_spread'], percent=True)} | {_format(row['min_abs_maxdd'], percent=True)}–{_format(row['max_abs_maxdd'], percent=True)} | "
            f"{_format(row['maxdd_spread'], percent=True)} | {_format(row['calmar_min'])}–{_format(row['calmar_max'])} | "
            f"{_format(row['after_tax_cagr_min'], percent=True)}–{_format(row['after_tax_cagr_max'], percent=True)} | "
            f"{_format(row['terminal_cagr_min'], percent=True)}–{_format(row['terminal_cagr_max'], percent=True)} | "
            f"{_format(row['turnover_min'])}–{_format(row['turnover_max'])} | {row['trade_count_min']}–{row['trade_count_max']} | "
            f"{_format(row['mean_hold_min'])}–{_format(row['mean_hold_max'])} | "
            f"{row['descriptive_min_cagr_window']} | {row['descriptive_max_cagr_window']} |",
        )

    lines += [
        "",
        "## Complete metric surface",
        "",
        "All 48 tax-mode metric rows are retained. Holding periods are completed continuous risky-asset "
        "episodes measured in trading sessions; a SPY→QQQ or SSO→QLD switch ends one episode and starts another, "
        "and an open terminal position is not fabricated into a completed episode. After-tax wealth and CAGR "
        "mean wealth after realized tax paid to date. Terminal-liquidation fields are hypothetical diagnostics "
        "only: they do not add a SELL, change turnover or holding statistics, or mutate the tax ledger.",
        "",
        "| Mapping | Frequency | L | Tax mode | CAGR | MaxDD | Calmar | Annual turnover | Mean hold | Median hold | Max hold | Trades | Costs | Realized tax | Terminal CAGR |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics.sort_values(["rule", "frequency", "momentum_window", "tax_mode"]).iterrows():
        lines.append(
            f"| {row.rule} | {row.frequency} | {int(row.momentum_window)} | {row.tax_mode} | "
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
        "using the audited Phase 2 helper after reconstructing rotation open-before-trade equity from cash "
        "and each asset's prior-session shares valued at the current open. Initial deployment and hypothetical "
        "terminal liquidation are excluded. Both SELL and BUY legs of a rotation are included. The execution "
        f"cost rate is {execution_rate:.8f} (0 commission bps + 5 slippage bps).",
        "",
        "| Mapping | Frequency | L | Included normalized turnover | Calendar years | Annual turnover | Included trade dates | Gross notional | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in turnover_audits:
        lines.append(
            f"| {row['rule']} | {row['frequency']} | {row['momentum_window']} | "
            f"{row['included_normalized_turnover']:.9f} | {row['years']:.9f} | "
            f"{row['annual_turnover']:.9f} | {row['nonzero_trade_dates']} | "
            f"${row['gross_traded_notional']:,.2f} | {row['number_of_trades']} |",
        )

    lines += [
        "",
        "## Common-sample benchmarks",
        "",
        "SPY, QQQ, SSO, and QLD buy-and-hold endpoints use the same SSO-based evaluation sample and audited "
        "benchmark conventions. They are descriptive benchmarks, not predictive evidence.",
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
        "Tax convention: Simplified Japan taxable mode uses average cost, immediate payment, and loss-pool "
        "treatment at realized sales. Unrealized appreciation is not taxed merely for increasing in value. "
        "Cumulative realized tax paid is retained in `cumulative_realized_tax_paid`; terminal liquidation is "
        "non-mutating and diagnostic only.",
        "",
        "`relative_momentum_results.csv` is the complete 48-row metric surface including tax mode. "
        "`parameter_results.csv` is the 24-row unique frozen economic grid with "
        "`searched_for_selection=False` and `selection_performed=False`; it is enumeration, not parameter selection.",
        "",
        "No lookback or frequency is selected from Phase 5 results. Phase 5 is not OOS evidence, and Walk-Forward "
        "parameter selection remains deferred to the frozen later phase.",
    ]
    (output / "phase5_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, run_id: str | None = None) -> Path:
    config = load_config(config_path)
    run_data_audit(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/audit")
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase5_relative_momentum"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prices = {
        asset: pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    signal_index = prices["SPY"].index.intersection(prices["QQQ"].index)
    signal_spy = prices["SPY"].loc[signal_index, "adjusted_close"]
    signal_qqq = prices["QQQ"].loc[signal_index, "adjusted_close"]
    start = pd.Timestamp(config["backtest"]["live_start"])
    end = min(frame.index.max() for frame in prices.values())
    evaluation_index = prices["SSO"].loc[start:end].index
    if any(len(evaluation_index.difference(prices[asset].loc[start:end].index)) for asset in prices):
        raise ValueError("evaluation index is not present in every signal and held-asset calendar")
    capital = float(config["initial_capital"])
    commission_bps = float(config["execution"]["commission_bps"])
    slippage_bps = float(config["execution"]["slippage_bps"])
    execution_rate = (commission_bps + slippage_bps) / 10_000.0
    tax_rate = float(config["tax"]["capital_gains_rate"])
    tie_audits = _tie_audit_rows(prices)
    if any(row["exact_positive_tie_count"] for row in tie_audits):
        raise RuntimeError("UNRESOLVED_FROZEN_SPEC_TIE_BREAK")
    warmups = _warmup_rows(prices, start, end, evaluation_index)
    alignments = _alignment_rows(prices, start, end, evaluation_index)
    rows: list[dict[str, object]] = []
    curves: list[pd.DataFrame] = []
    drawdowns: list[pd.DataFrame] = []
    positions: list[pd.DataFrame] = []
    trades: list[pd.DataFrame] = []
    taxes: list[pd.DataFrame] = []
    parameters: list[dict[str, object]] = []
    turnover_audits: list[dict[str, object]] = []

    for rule, mapping in MAPPINGS.items():
        held_assets = tuple(mapping.values())
        held_prices = {asset: prices[asset].loc[evaluation_index] for asset in held_assets}
        for frequency in FREQUENCIES:
            for window in MOMENTUM_WINDOWS:
                underlying = relative_momentum_target_next_open(
                    signal_spy, signal_qqq, frequency, window,
                ).reindex(evaluation_index)
                if underlying.isna().any().any():
                    raise ValueError("signal and held-asset calendars are not aligned")
                targets = pd.DataFrame(
                    {mapping["SPY"]: underlying.SPY, mapping["QQQ"]: underlying.QQQ},
                    index=evaluation_index,
                )
                strategy = strategy_identifier(rule, frequency, window)
                for mode, mode_tax_rate in (("pre_tax", None), ("after_tax", tax_rate)):
                    ledger, position, trade, tax = rotation_backtest(
                        held_prices,
                        targets,
                        initial_capital=capital,
                        commission_bps=commission_bps,
                        slippage_bps=slippage_bps,
                        tax_rate=mode_tax_rate,
                    )
                    ledger = _add_rotation_pretrade_equity(ledger, held_prices, capital)
                    metric = performance_metrics(
                        ledger,
                        trade,
                        capital,
                        terminal_tax_rate=mode_tax_rate,
                        terminal_cost_rate=execution_rate if mode_tax_rate is not None else 0.0,
                    )
                    metric.update({
                        "strategy": strategy,
                        "rule": rule,
                        "rule_family": rule,
                        "legacy_rule": rule,
                        "legacy_strategy": strategy,
                        "mapping": "1X" if rule.endswith("1X") else "2X",
                        "signal_asset": "SPY+QQQ",
                        "held_asset": "+".join(held_assets),
                        "signal_assets": "SPY,QQQ",
                        "held_assets": ",".join(held_assets),
                        "frequency": frequency,
                        "momentum_window": window,
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
                    if mode == "pre_tax":
                        turnover_audits.append({
                            "rule": rule,
                            "frequency": frequency,
                            "momentum_window": window,
                            **_turnover_audit(ledger, trade),
                        })
                parameters.append({
                    "rule": rule,
                    "rule_family": rule,
                    "legacy_rule": rule,
                    "mapping": "1X" if rule.endswith("1X") else "2X",
                    "signal_assets": "SPY,QQQ",
                    "held_assets": ",".join(held_assets),
                    "frequency": frequency,
                    "momentum_window": window,
                    "searched_for_selection": False,
                    "selection_performed": False,
                })

    metrics = pd.DataFrame(rows)
    pre = metrics.loc[metrics.tax_mode.eq("pre_tax")].reset_index(drop=True)
    after = metrics.loc[metrics.tax_mode.eq("after_tax")].reset_index(drop=True)
    combined = pd.concat([pre, after], ignore_index=True)
    if len(pre) != 24 or len(after) != 24 or len(parameters) != 24:
        raise AssertionError("Phase 5 must produce 24 rows per tax mode and 24 parameter combinations")
    pre.to_csv(output / "metrics_pre_tax.csv", index=False)
    after.to_csv(output / "metrics_after_tax.csv", index=False)
    combined.to_csv(output / "relative_momentum_results.csv", index=False)
    pd.DataFrame(parameters).to_csv(output / "parameter_results.csv", index=False)

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

    benchmarks = []
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        ledger, _, trade = buy_and_hold(
            prices[asset].loc[evaluation_index],
            initial_capital=capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        benchmarks.append({"asset": asset, **performance_metrics(ledger, trade, capital)})
    benchmark_table = pd.DataFrame(benchmarks)
    _heatmap(combined, "pre_tax", output / "relative_momentum_heatmap.png")
    _heatmap(combined, "after_tax", output / "relative_momentum_heatmap_after_tax.png")
    _standard_plots(curve_table, dd_table, combined, benchmark_table, output)
    _write_phase5_report(
        output,
        combined,
        benchmark_table,
        warmups,
        alignments,
        tie_audits,
        _stability_rows(combined),
        turnover_audits,
        start=start,
        end=end,
        execution_rate=execution_rate,
    )
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
