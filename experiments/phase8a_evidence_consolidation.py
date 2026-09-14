from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from market_timing_quant.configuration import load_config
from market_timing_quant.portfolio import buy_and_hold


OOS_START = pd.Timestamp("2013-01-02")
OOS_END = pd.Timestamp("2026-08-31")
INITIAL_CAPITAL = 100_000.0
SOURCE_RUNS = {
    "phase7a": "20260913_phase7a_metrics_tax_audited_final",
    "phase7b": "20260914_phase7b_turnover_audit_final",
    "fixed_ma200": "20260914_oos_fixed_ma200_audit_final",
}
FREQUENCIES = ("weekly", "monthly", "bimonthly", "quarterly")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_path(reports_root: Path, phase: str, filename: str) -> Path:
    return reports_root / SOURCE_RUNS[phase] / filename


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _exposure_from_positions(
    positions: pd.DataFrame,
    *,
    strategy: str,
    tax_mode: str,
    phase7a: bool = False,
) -> tuple[float, float]:
    scoped = positions.loc[
        positions.strategy.eq(strategy)
        & positions.tax_mode.eq(tax_mode)
        & positions.date.ge(OOS_START.strftime("%Y-%m-%d"))
        & positions.date.le(OOS_END.strftime("%Y-%m-%d"))
    ].copy()
    if phase7a and "period" in scoped:
        scoped = scoped.loc[scoped.period.eq("chronological_oos")]
    if scoped.empty:
        raise AssertionError(f"missing positions for {strategy}/{tax_mode}")
    actual = scoped.assign(date=pd.to_datetime(scoped.date)).groupby("date")["actual_weight"].sum()
    invested = actual > 1e-12
    return float(invested.mean()), float((~invested).mean())


def _source_metric_rows(reports_root: Path) -> list[dict[str, object]]:
    phase7b = _read(_source_path(reports_root, "phase7b", "phase7b_stitched_oos_results.csv"))
    fixed = _read(_source_path(reports_root, "fixed_ma200", "oos_results.csv"))
    phase7a = _read(_source_path(reports_root, "phase7a", "metrics_pre_tax.csv"))
    phase7a_after = _read(_source_path(reports_root, "phase7a", "metrics_after_tax.csv"))
    phase7a_positions = _read(_source_path(reports_root, "phase7a", "positions.csv"))
    fixed_positions = _read(_source_path(reports_root, "fixed_ma200", "positions.csv"))

    rows: list[dict[str, object]] = []

    def add_group(
        source: pd.DataFrame,
        *,
        source_phase: str,
        artifact: str,
        strategy_id: str,
        strategy_label: str,
        source_strategy: str,
        frequencies: tuple[str, ...],
        position_source: pd.DataFrame | None = None,
        phase7a_positions_source: bool = False,
        source_start: str | None = None,
    ) -> None:
        scoped = source.loc[source.strategy.eq(source_strategy)] if source_strategy else source
        if source_start is not None:
            scoped = scoped.loc[scoped.start.eq(source_start)]
        for frequency in frequencies:
            freq_rows = scoped.loc[scoped.frequency.eq(frequency)]
            if len(freq_rows) != 2:
                raise AssertionError(f"expected pre/after rows for {strategy_id}/{frequency}, got {len(freq_rows)}")
            for _, row in freq_rows.iterrows():
                mode = str(row.tax_mode)
                invested, cash = (None, None)
                if position_source is not None:
                    invested, cash = _exposure_from_positions(
                        position_source,
                        strategy=str(row.strategy),
                        tax_mode=mode,
                        phase7a=phase7a_positions_source,
                    )
                elif "invested_session_pct" in row and pd.notna(row.get("invested_session_pct")):
                    invested = float(row.invested_session_pct)
                    cash = float(row.cash_session_pct)
                rows.append({
                    "strategy_id": strategy_id,
                    "strategy_label": strategy_label,
                    "source_phase": source_phase,
                    "source_run_id": SOURCE_RUNS[source_phase],
                    "source_artifact": artifact,
                    "source_strategy": str(row.strategy),
                    "frequency": frequency,
                    "tax_mode": mode,
                    "start_date": str(row.start),
                    "end_date": str(row.end),
                    "ending_value": _float(row.ending_value),
                    "cagr": _float(row.cagr),
                    "max_drawdown": _float(row.max_drawdown),
                    "calmar": _float(row.calmar),
                    "sharpe": _float(row.sharpe),
                    "sortino": _float(row.sortino),
                    "ulcer_index": _float(row.ulcer_index),
                    "recovery_trading_days": _float(row.recovery_trading_days),
                    "annual_turnover": _float(row.annual_turnover),
                    "number_of_trades": int(row.number_of_trades),
                    "mean_holding_period_days": _float(
                        row.mean_holding_period_days if pd.notna(row.mean_holding_period_days)
                        else row.average_holding_period_days,
                    ),
                    "median_holding_period_days": _float(row.median_holding_period_days),
                    "max_holding_period_days": _float(row.max_holding_period_days),
                    "transaction_costs": _float(row.transaction_costs),
                    "raw_tax_paid": _float(row.tax_paid),
                    "invested_session_pct": invested,
                    "cash_session_pct": cash,
                })

    # The benchmark rows are single, tax-neutral benchmark observations from
    # the accepted Phase 7B run. Their terminal fields already carry the
    # report-only liquidation diagnostics.
    for asset in ("QQQ", "QLD"):
        row = phase7b.loc[phase7b.strategy.eq(f"{asset}_BUY_HOLD")]
        if len(row) != 1:
            raise AssertionError(f"missing canonical {asset} benchmark")
        row = row.iloc[0]
        rows.append({
            "strategy_id": f"{asset}_BUY_HOLD",
            "strategy_label": f"{asset} buy-and-hold",
            "source_phase": "phase7b",
            "source_run_id": SOURCE_RUNS["phase7b"],
            "source_artifact": "phase7b_stitched_oos_results.csv",
            "source_strategy": str(row.strategy),
            "frequency": "none",
            "tax_mode": "benchmark",
            "start_date": str(row.start),
            "end_date": str(row.end),
            "ending_value": _float(row.ending_value),
            "cagr": _float(row.cagr),
            "max_drawdown": _float(row.max_drawdown),
            "calmar": _float(row.calmar),
            "sharpe": _float(row.sharpe),
            "sortino": _float(row.sortino),
            "ulcer_index": _float(row.ulcer_index),
            "recovery_trading_days": _float(row.recovery_trading_days),
            "annual_turnover": _float(row.annual_turnover),
            "number_of_trades": int(row.number_of_trades),
            "mean_holding_period_days": _float(row.mean_holding_period_days),
            "median_holding_period_days": _float(row.median_holding_period_days),
            "max_holding_period_days": _float(row.max_holding_period_days),
            "transaction_costs": _float(row.transaction_costs),
            "raw_tax_paid": _float(row.tax_paid),
            "invested_session_pct": float(row.invested_session_pct),
            "cash_session_pct": float(row.cash_session_pct),
        })

    # Fixed rows are selected by held asset rather than a single source
    # strategy name because the accepted run also contains QQQ and SSO rules.
    fixed_rows = fixed.loc[fixed.held_asset.eq("QLD")].copy()
    add_group(
        fixed_rows,
        source_phase="fixed_ma200",
        artifact="oos_results.csv",
        strategy_id="FIXED_MA200_QQQ_TO_QLD",
        strategy_label="Fixed MA200 QQQ signal → QLD/CASH",
        source_strategy="",
        frequencies=FREQUENCIES,
        position_source=fixed_positions,
    )

    phase7a_oos = phase7a.loc[phase7a.start.eq(OOS_START.strftime("%Y-%m-%d"))]
    phase7a_after_oos = phase7a_after.loc[phase7a_after.start.eq(OOS_START.strftime("%Y-%m-%d"))]
    phase7a_both = pd.concat([phase7a_oos, phase7a_after_oos], ignore_index=True)
    add_group(
        phase7a_both,
        source_phase="phase7a",
        artifact="metrics_pre_tax.csv + metrics_after_tax.csv",
        strategy_id="PHASE7A_FIXED_FOUR_STATE",
        strategy_label="Phase 7A fixed four-state strategy",
        source_strategy="",
        frequencies=FREQUENCIES,
        position_source=phase7a_positions,
        phase7a_positions_source=True,
    )

    for model, strategy_id, label in (
        ("MODEL_A_QLD_TREND", "PHASE7B_MODEL_A_SELECTED", "Phase 7B Model A selected Walk-Forward"),
        ("MODEL_B_FOUR_STATE", "PHASE7B_MODEL_B_SELECTED", "Phase 7B Model B selected Walk-Forward"),
    ):
        model_rows = phase7b.loc[phase7b.model.eq(model)]
        add_group(
            model_rows,
            source_phase="phase7b",
            artifact="phase7b_stitched_oos_results.csv",
            strategy_id=strategy_id,
            strategy_label=label,
            source_strategy="",
            frequencies=FREQUENCIES,
        )

    return rows


def _attach_source_terminal_fields(metrics: pd.DataFrame, reports_root: Path) -> pd.DataFrame:
    """Copy after-tax diagnostic fields from each accepted source row."""
    result = metrics.copy()
    source_frames = {
        "phase7a": pd.concat([
            _read(_source_path(reports_root, "phase7a", "metrics_pre_tax.csv")),
            _read(_source_path(reports_root, "phase7a", "metrics_after_tax.csv")),
        ], ignore_index=True),
        "phase7b": _read(_source_path(reports_root, "phase7b", "phase7b_stitched_oos_results.csv")),
        "fixed_ma200": _read(_source_path(reports_root, "fixed_ma200", "oos_results.csv")),
    }
    for idx, row in result.iterrows():
        if row.strategy_id in {"QQQ_BUY_HOLD", "QLD_BUY_HOLD"}:
            src = source_frames["phase7b"].loc[source_frames["phase7b"].strategy.eq(row.source_strategy)].iloc[0]
        elif row.strategy_id == "FIXED_MA200_QQQ_TO_QLD":
            src = source_frames["fixed_ma200"].loc[
                source_frames["fixed_ma200"].held_asset.eq("QLD")
                & source_frames["fixed_ma200"].frequency.eq(row.frequency)
                & source_frames["fixed_ma200"].tax_mode.eq(row.tax_mode)
            ].iloc[0]
        elif row.strategy_id == "PHASE7A_FIXED_FOUR_STATE":
            src = source_frames["phase7a"].loc[
                source_frames["phase7a"].strategy.eq(row.source_strategy)
                & source_frames["phase7a"].frequency.eq(row.frequency)
                & source_frames["phase7a"].tax_mode.eq(row.tax_mode)
                & source_frames["phase7a"].start.eq(OOS_START.strftime("%Y-%m-%d"))
            ].iloc[0]
        else:
            src = source_frames["phase7b"].loc[
                source_frames["phase7b"].strategy.eq(row.source_strategy)
                & source_frames["phase7b"].frequency.eq(row.frequency)
                & source_frames["phase7b"].tax_mode.eq(row.tax_mode)
            ].iloc[0]
        result.loc[idx, "source_terminal_liquidation_wealth"] = _float(src.get("terminal_liquidation_wealth"))
        result.loc[idx, "source_terminal_liquidation_tax"] = _float(src.get("terminal_liquidation_tax"))
        result.loc[idx, "source_terminal_liquidation_cost"] = _float(src.get("terminal_liquidation_cost"))
        result.loc[idx, "source_terminal_unrealized_gain_after_cost"] = _float(src.get("terminal_unrealized_gain_after_cost"))
        result.loc[idx, "source_after_tax_CAGR_tax_paid_to_date"] = _float(src.get("after_tax_cagr_tax_paid_to_date"))
        result.loc[idx, "source_after_tax_ending_value_terminal_liquidation"] = _float(src.get("after_tax_terminal_liquidation"))
        result.loc[idx, "source_after_tax_CAGR_terminal_liquidation"] = _float(src.get("after_tax_cagr_terminal_liquidation"))
        result.loc[idx, "source_cumulative_realized_tax_paid"] = _float(src.get("cumulative_realized_tax_paid", src.get("tax_paid", 0.0)))
        # Preserve the source row's tax-mode-specific realized-tax value.
        # After-tax diagnostics are copied separately and may be repeated on
        # the matching pre-tax row for apples-to-apples display.
        result.loc[idx, "realized_tax_paid"] = _float(src.get("tax_paid", 0.0))
    for strategy_id, frequency in result[["strategy_id", "frequency"]].drop_duplicates().itertuples(index=False):
        mask = (result.strategy_id == strategy_id) & (result.frequency == frequency)
        after = result.loc[mask & result.tax_mode.eq("after_tax")]
        benchmark = result.loc[mask & result.tax_mode.eq("benchmark")]
        reference = after.iloc[0] if len(after) else benchmark.iloc[0]
        result.loc[mask, "after_tax_CAGR_tax_paid_to_date"] = float(reference.source_after_tax_CAGR_tax_paid_to_date if pd.notna(reference.source_after_tax_CAGR_tax_paid_to_date) else reference.cagr)
        result.loc[mask, "after_tax_ending_value_terminal_liquidation"] = float(reference.source_after_tax_ending_value_terminal_liquidation if pd.notna(reference.source_after_tax_ending_value_terminal_liquidation) else reference.ending_value)
        result.loc[mask, "after_tax_CAGR_terminal_liquidation"] = float(reference.source_after_tax_CAGR_terminal_liquidation if pd.notna(reference.source_after_tax_CAGR_terminal_liquidation) else reference.cagr)
    return result


def _benchmark_relative(metrics: pd.DataFrame) -> pd.DataFrame:
    qqq = metrics.loc[metrics.strategy_id.eq("QQQ_BUY_HOLD")].iloc[0]
    rows = []
    for _, row in metrics.iterrows():
        rows.append({
            "strategy_id": row.strategy_id,
            "strategy_label": row.strategy_label,
            "frequency": row.frequency,
            "tax_mode": row.tax_mode,
            "cagr_minus_qqq": row.cagr - qqq.cagr,
            "max_drawdown_minus_qqq": row.max_drawdown - qqq.max_drawdown,
            "calmar_minus_qqq": row.calmar - qqq.calmar if pd.notna(row.calmar) else np.nan,
            "sharpe_minus_qqq": row.sharpe - qqq.sharpe if pd.notna(row.sharpe) else np.nan,
            "sortino_minus_qqq": row.sortino - qqq.sortino if pd.notna(row.sortino) else np.nan,
            "terminal_after_tax_cagr_minus_qqq": row.after_tax_CAGR_terminal_liquidation - qqq.after_tax_CAGR_terminal_liquidation,
            "turnover_minus_qqq": row.annual_turnover - qqq.annual_turnover,
            "qqq_dominance": bool(
                row.cagr > qqq.cagr
                and row.max_drawdown >= qqq.max_drawdown
                and pd.notna(row.calmar)
                and row.calmar > qqq.calmar
            ),
            "qqq_benchmark_source_run_id": qqq.source_run_id,
        })
    return pd.DataFrame(rows)


def _complexity(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    comparisons = [
        ("PHASE7B_MODEL_B_MINUS_MODEL_A", "PHASE7B_MODEL_B_SELECTED", "PHASE7B_MODEL_A_SELECTED"),
        ("PHASE7A_FIXED_FOUR_STATE_MINUS_FIXED_MA200", "PHASE7A_FIXED_FOUR_STATE", "FIXED_MA200_QQQ_TO_QLD"),
    ]
    for name, right_id, left_id in comparisons:
        for frequency in FREQUENCIES:
            pre_right = metrics.loc[(metrics.strategy_id == right_id) & (metrics.frequency == frequency) & metrics.tax_mode.eq("pre_tax")].iloc[0]
            pre_left = metrics.loc[(metrics.strategy_id == left_id) & (metrics.frequency == frequency) & metrics.tax_mode.eq("pre_tax")].iloc[0]
            after_right = metrics.loc[(metrics.strategy_id == right_id) & (metrics.frequency == frequency) & metrics.tax_mode.eq("after_tax")].iloc[0]
            after_left = metrics.loc[(metrics.strategy_id == left_id) & (metrics.frequency == frequency) & metrics.tax_mode.eq("after_tax")].iloc[0]
            rows.append({
                "comparison": name,
                "right_strategy_id": right_id,
                "left_strategy_id": left_id,
                "frequency": frequency,
                "pre_tax_cagr_difference": pre_right.cagr - pre_left.cagr,
                "pre_tax_max_drawdown_difference": pre_right.max_drawdown - pre_left.max_drawdown,
                "pre_tax_calmar_difference": pre_right.calmar - pre_left.calmar if pd.notna(pre_right.calmar) and pd.notna(pre_left.calmar) else np.nan,
                "pre_tax_sharpe_difference": pre_right.sharpe - pre_left.sharpe if pd.notna(pre_right.sharpe) and pd.notna(pre_left.sharpe) else np.nan,
                "pre_tax_sortino_difference": pre_right.sortino - pre_left.sortino if pd.notna(pre_right.sortino) and pd.notna(pre_left.sortino) else np.nan,
                "pre_tax_turnover_difference": pre_right.annual_turnover - pre_left.annual_turnover,
                "after_tax_cagr_difference": after_right.cagr - after_left.cagr,
                "after_tax_terminal_cagr_difference": after_right.after_tax_CAGR_terminal_liquidation - after_left.after_tax_CAGR_terminal_liquidation,
                "after_tax_realized_tax_difference": after_right.realized_tax_paid - after_left.realized_tax_paid,
                "descriptive_only": True,
            })
    return pd.DataFrame(rows)


def _aligned_equity(
    reports_root: Path,
    oos_index: pd.DatetimeIndex,
    config_path: Path,
) -> pd.DataFrame:
    rows = []
    phase7b_curve = _read(_source_path(reports_root, "phase7b", "equity_curve.csv"))
    phase7b_curve.date = pd.to_datetime(phase7b_curve.date)
    fixed_curve = _read(_source_path(reports_root, "fixed_ma200", "equity_curve.csv"))
    fixed_curve.date = pd.to_datetime(fixed_curve.date)
    phase7a_curve = _read(_source_path(reports_root, "phase7a", "equity_curve.csv"))
    phase7a_curve.date = pd.to_datetime(phase7a_curve.date)

    def append_curve(frame: pd.DataFrame, source_strategy: str, strategy_id: str, phase: str, frequency: str, period: str | None = None) -> None:
        scoped = frame.loc[frame.strategy.eq(source_strategy) & frame.tax_mode.isin(("pre_tax", "after_tax"))]
        if period is not None and "period" in scoped:
            scoped = scoped.loc[scoped.period.eq(period)]
        if len(scoped) != len(oos_index) * 2:
            raise AssertionError(f"unexpected curve rows for {source_strategy}: {len(scoped)}")
        for mode, part in scoped.groupby("tax_mode", sort=False):
            part = part.sort_values("date")
            if not pd.DatetimeIndex(part.date).equals(oos_index):
                raise AssertionError(f"curve calendar mismatch for {source_strategy}/{mode}")
            for date, equity in zip(part.date, part.equity, strict=True):
                rows.append({
                    "date": date,
                    "strategy_id": strategy_id,
                    "source_phase": phase,
                    "source_run_id": SOURCE_RUNS[phase],
                    "frequency": frequency,
                    "tax_mode": mode,
                    "equity": float(equity),
                })

    for frequency in FREQUENCIES:
        append_curve(fixed_curve, f"QQQ_MA200_QLD_{frequency}_OOS", "FIXED_MA200_QQQ_TO_QLD", "fixed_ma200", frequency)
        append_curve(phase7b_curve, f"MODEL_A_QLD_TREND_{frequency}", "PHASE7B_MODEL_A_SELECTED", "phase7b", frequency)
        append_curve(phase7b_curve, f"MODEL_B_FOUR_STATE_{frequency}", "PHASE7B_MODEL_B_SELECTED", "phase7b", frequency)
        append_curve(phase7a_curve, f"PHASE7A_{frequency}", "PHASE7A_FIXED_FOUR_STATE", "phase7a", frequency, period="chronological_oos")

    # Benchmark daily paths use the exact frozen buy-and-hold engine and the
    # same processed immutable prices used for the accepted Phase 7B metric
    # rows. This is a daily-series expansion, not a new strategy evaluation.
    load_config(config_path)  # validate that the canonical config remains readable
    for asset in ("QQQ", "QLD"):
        prices = pd.read_parquet(PROJECT_ROOT / "data/processed" / f"{asset}.parquet").reindex(oos_index)
        ledger, _, _ = buy_and_hold(
            prices,
            initial_capital=INITIAL_CAPITAL,
            commission_bps=0.0,
            slippage_bps=5.0,
        )
        for date, equity in ledger.equity.items():
            rows.append({
                "date": date,
                "strategy_id": f"{asset}_BUY_HOLD",
                "source_phase": "phase7b",
                "source_run_id": SOURCE_RUNS["phase7b"],
                "frequency": "none",
                "tax_mode": "benchmark",
                "equity": float(equity),
            })
    result = pd.DataFrame(rows).sort_values(["strategy_id", "frequency", "tax_mode", "date"]).reset_index(drop=True)
    if result.duplicated(["strategy_id", "frequency", "tax_mode", "date"]).any():
        raise AssertionError("aligned daily equity has duplicate identity/date rows")
    return result


def _aligned_returns(equity: pd.DataFrame) -> pd.DataFrame:
    result = equity.copy()
    result["daily_return"] = result.groupby(["strategy_id", "frequency", "tax_mode"], sort=False).equity.pct_change()
    first = result.groupby(["strategy_id", "frequency", "tax_mode"], sort=False).head(1).index
    result.loc[first, "daily_return"] = result.loc[first, "equity"] / INITIAL_CAPITAL - 1.0
    return result


def _source_manifest(reports_root: Path) -> pd.DataFrame:
    files = {
        "phase7a": ("config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv", "equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "state_decisions.csv", "execution_targets.csv"),
        "phase7b": ("config_snapshot.yaml", "phase7b_stitched_oos_results.csv", "metrics_pre_tax.csv", "metrics_after_tax.csv", "equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "stitched_execution_targets.csv", "selected_parameters_by_fold.csv"),
        "fixed_ma200": ("config_snapshot.yaml", "oos_results.csv", "metrics_pre_tax.csv", "metrics_after_tax.csv", "equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "oos_fold_metrics.csv"),
    }
    rows = []
    for phase, names in files.items():
        for name in names:
            path = _source_path(reports_root, phase, name)
            if not path.exists():
                raise FileNotFoundError(path)
            rows.append({
                "source_phase": phase,
                "source_run_id": SOURCE_RUNS[phase],
                "artifact": name,
                "relative_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": _sha256(path),
            })
    return pd.DataFrame(rows)


def _write_report(output: Path, metrics: pd.DataFrame, relative: pd.DataFrame, complexity: pd.DataFrame, manifest: pd.DataFrame, aligned: pd.DataFrame) -> None:
    qqq = metrics.loc[metrics.strategy_id.eq("QQQ_BUY_HOLD")].iloc[0]
    lines = [
        "# Phase 8A — OOS Evidence Consolidation",
        "",
        "This is a descriptive consolidation of already-audited strategies on one common chronological OOS calendar. No new strategy, parameter optimization, parameter selection, or statistical inference was performed. Phase 8B is not started.",
        "",
        "## Scope and source runs",
        "",
        f"Common OOS period: **{OOS_START.date()} through {OOS_END.date()}**. Initial capital is **$100,000**. The canonical source run IDs are `phase7a={SOURCE_RUNS['phase7a']}`, `phase7b={SOURCE_RUNS['phase7b']}`, and `fixed_ma200={SOURCE_RUNS['fixed_ma200']}`. Exact artifact hashes are in `canonical_source_manifest.csv`.",
        "",
        "The two buy-and-hold benchmark rows use `frequency=none`. Fixed MA200, Phase 7A, and both Phase 7B models retain all four frozen frequencies. No frequency or strategy was removed, ranked as a winner, or designated for production.",
        "",
        "## Accounting and metric conventions",
        "",
        "The table copies canonical metric rows and preserves close decision → next eligible open execution, 5 bps slippage, zero commission, zero CASH return, continuous ledgers, simplified Japanese capital-gains tax at 20.315%, contemporaneous-open pretrade-equity turnover, initial deployment exclusion, report-only terminal liquidation, and completed risky-position holding episodes. No metric definition is changed here.",
        "",
        "`realized_tax_paid` preserves each source row's tax-mode-specific `tax_paid` value (zero on pre-tax and tax-neutral benchmark rows). `after_tax_CAGR_tax_paid_to_date`, terminal wealth, and terminal CAGR are copied from the source after-tax diagnostic row and repeated on the matching pre-tax row for apples-to-apples display.",
        "",
        "## Consolidated OOS rows",
        "",
        f"`oos_champion_table.csv` contains **{len(metrics)} rows**: 2 benchmark rows plus 4 frequencies × 2 tax modes for each of Fixed MA200, Phase 7A, Phase 7B Model A, and Phase 7B Model B. Each row is dated {metrics.start_date.min()}–{metrics.end_date.max()}.",
        "",
        metrics.merge(
            relative[["strategy_id", "frequency", "tax_mode", "qqq_dominance"]],
            on=["strategy_id", "frequency", "tax_mode"],
            how="left",
        )[["strategy_id", "frequency", "tax_mode", "cagr", "max_drawdown", "calmar", "annual_turnover", "number_of_trades", "qqq_dominance"]].to_markdown(index=False),
        "",
        "## Benchmark-relative evidence",
        "",
        "Every relative column uses the one QQQ buy-and-hold row on the exact same OOS calendar. `qqq_dominance` is the frozen boolean: strategy CAGR > QQQ CAGR AND strategy MaxDD >= QQQ MaxDD AND strategy Calmar > QQQ Calmar. This is evidence only and is not a production-selection rule.",
        "",
        "## Complexity comparisons",
        "",
        "`complexity_comparison.csv` preserves Phase 7B Model B minus Model A and Phase 7A fixed four-state minus Fixed MA200, by frequency. These are descriptive differences across the frozen experimental dimensions; no significance test or single-metric ranking is performed.",
        "",
        complexity.to_markdown(index=False),
        "",
        "## Daily alignment for the next phase",
        "",
        f"`aligned_daily_equity.csv` and `aligned_daily_returns.csv` contain {len(aligned)} rows each with identity keys and the exact {aligned.date.nunique()} common OOS sessions. Strategy curves are copied from accepted Phase 7A, Phase 7B, and Fixed-MA200 OOS artifacts. The two benchmark curves are the daily expansion of the accepted Phase 7B benchmark method on the immutable processed price snapshot; the consolidated benchmark metrics remain copied from the accepted Phase 7B metric artifact.",
        "",
        "No prior-phase source or canonical artifact was written by Phase 8A. No strategy winner, production recommendation, or Phase 8B statistical claim is made.",
        "",
        "PHASE 8A EVIDENCE CONSOLIDATION COMPLETE — NO NEW STRATEGY OR PARAMETER SELECTION PERFORMED",
    ]
    (output / "phase8a_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, reports_root: Path, output_root: Path, run_id: str | None = None) -> Path:
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase8a_oos_evidence"))
    output.mkdir(parents=True, exist_ok=False)
    metrics = pd.DataFrame(_source_metric_rows(reports_root))
    metrics = _attach_source_terminal_fields(metrics, reports_root)
    if metrics.duplicated(["strategy_id", "frequency", "tax_mode"]).any():
        raise AssertionError("consolidated table has duplicate strategy/frequency/tax rows")
    if not metrics.start_date.eq(OOS_START.strftime("%Y-%m-%d")).all() or not metrics.end_date.eq(OOS_END.strftime("%Y-%m-%d")).all():
        raise AssertionError("not all consolidated rows use the exact common OOS calendar")
    relative = _benchmark_relative(metrics)
    complexity = _complexity(metrics)
    manifest = _source_manifest(reports_root)
    oos_index = pd.DatetimeIndex(pd.date_range(OOS_START, OOS_END, freq="B"))
    fixed_curve = _read(_source_path(reports_root, "fixed_ma200", "equity_curve.csv"))
    oos_index = pd.DatetimeIndex(pd.to_datetime(fixed_curve.date).sort_values().unique())
    oos_index = oos_index[(oos_index >= OOS_START) & (oos_index <= OOS_END)]
    aligned = _aligned_equity(reports_root, oos_index, config_path)
    returns = _aligned_returns(aligned)

    metrics.to_csv(output / "oos_champion_table.csv", index=False)
    relative.to_csv(output / "benchmark_relative_metrics.csv", index=False)
    complexity.to_csv(output / "complexity_comparison.csv", index=False)
    manifest.to_csv(output / "canonical_source_manifest.csv", index=False)
    aligned.to_csv(output / "aligned_daily_equity.csv", index=False)
    returns.to_csv(output / "aligned_daily_returns.csv", index=False)
    # Carry forward the accepted canonical configuration snapshot for
    # reproducibility; Phase 8A itself introduces no configuration changes.
    shutil.copyfile(
        _source_path(reports_root, "phase7b", "config_snapshot.yaml"),
        output / "config_snapshot.yaml",
    )
    _write_report(output, metrics, relative, complexity, manifest, aligned)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8A OOS evidence consolidation")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config/base.yaml")
    parser.add_argument("--reports-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(run(args.config, args.reports_root, args.output_root, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
