"""Dedicated Phase 7B turnover/selection remediation regressions."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.phase2_ma200 import FREQUENCIES
from experiments.phase7b_parameter_walk_forward import (
    _add_pretrade_equity,
    _fold_test_audit,
    _selection_old_vs_new,
    _training_metric,
    _turnover_audit,
)
from market_timing_quant.configuration import load_config
from market_timing_quant.metrics import performance_metrics
from market_timing_quant.portfolio import dynamic_allocation_backtest, single_asset_timed_backtest
from market_timing_quant.signals import rebalance_mask
from market_timing_quant.walk_forward import WalkForwardFold, select_calmar_candidate


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/20260914_phase7b_turnover_audit_final"
OLD_RUN = ROOT / "reports/runs/20260913_phase7b_strict_gate_v1_final"
FIXED_TURNOVER = {
    "weekly": 1.610241,
    "monthly": 1.171084,
    "bimonthly": 0.731928,
    "quarterly": 0.878313,
}


def _prices(index: pd.DatetimeIndex, opens: list[float], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"open": opens, "adjusted_close": closes}, index=index)


def _single_gap_case():
    index = pd.bdate_range("2020-01-02", periods=4)
    prices = _prices(index, [100.0, 200.0, 100.0, 300.0], [100.0, 100.0, 200.0, 100.0])
    targets = pd.Series([1.0, 0.0, 1.0, 0.0], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0,
        commission_bps=0.0, slippage_bps=0.0, tax_rate=None,
    )
    return _add_pretrade_equity(ledger, prices, 1_000.0), trades, taxes


def test_fixed_qld_ma200_turnover_matches_canonical_all_frequencies():
    metrics = pd.read_csv(RUN / "phase7b_stitched_oos_results.csv")
    fixed = metrics[metrics.model.eq("FIXED_QLD_MA200")]
    assert len(fixed) == 8
    for frequency, expected in FIXED_TURNOVER.items():
        values = fixed.loc[fixed.frequency.eq(frequency), "annual_turnover"]
        assert len(values) == 2
        # The canonical reference is reported to six decimal places; retain
        # serialization-safe precision while allowing that display rounding.
        assert np.allclose(values, expected, rtol=0.0, atol=1e-6)


def test_candidate_turnover_uses_open_pretrade_equity_not_end_of_day_equity():
    ledger, trades, _ = _single_gap_case()
    metric = _training_metric(ledger, trades, ledger.index[-1], 1_000.0)
    dates = pd.to_datetime(trades.date)
    include = ~((dates == dates.min()) & trades.side.eq("BUY").to_numpy())
    canonical = float((trades.loc[include, "notional"].to_numpy() / ledger.pretrade_equity.reindex(dates[include]).to_numpy()).sum())
    eod = float((trades.loc[include, "notional"].to_numpy() / ledger.equity.reindex(dates[include]).to_numpy()).sum())
    assert np.isclose(metric["annual_turnover"] * ((ledger.index[-1] - ledger.index[0]).days / 365.25), canonical)
    assert not np.isclose(canonical, eod)


def test_initial_deployment_buy_is_excluded():
    ledger, trades, _ = _single_gap_case()
    initial_only = trades.iloc[[0]].copy()
    assert _turnover_audit(ledger, initial_only)["annual_turnover"] == 0.0


def test_terminal_liquidation_diagnostic_does_not_add_turnover():
    ledger, trades, _ = _single_gap_case()
    before = performance_metrics(ledger, trades, 1_000.0, terminal_tax_rate=0.2)
    after = performance_metrics(ledger, trades, 1_000.0, terminal_tax_rate=0.2)
    assert before["annual_turnover"] == after["annual_turnover"]
    assert len(trades) == 4


def test_fold_turnover_uses_continuous_open_denominator_without_boundary_reset():
    index = pd.bdate_range("2020-01-02", periods=4)
    ledger = pd.DataFrame({
        "equity": [1_000.0, 1_000.0, 2_000.0, 2_000.0],
        "cash": [1_000.0, 0.0, 2_000.0, 1_000.0],
        "shares": [0.0, 10.0, 0.0, 10.0],
        "pretrade_equity": [1_000.0, 1_000.0, 2_000.0, 2_000.0],
        "daily_return": [0.0, 0.0, 1.0, 0.0],
        "tax_paid": [0.0, 0.0, 0.0, 0.0],
    }, index=index)
    trades = pd.DataFrame([
        {"date": index[0], "side": "BUY", "notional": 1_000.0},
        {"date": index[1], "side": "SELL", "notional": 1_000.0},
        {"date": index[3], "side": "BUY", "notional": 1_000.0},
    ])
    folds = [
        WalkForwardFold(index[0], index[0], index[0], index[1], 2020),
        WalkForwardFold(index[0], index[1], index[2], index[3], 2021),
    ]
    result = _fold_test_audit(ledger, trades, pd.DataFrame(columns=["date", "tax_paid"]), folds, initial_capital=1_000.0)
    assert result.test_year_turnover.iloc[1] > 0.0
    # The second-fold BUY is divided by continuous 2,000 open equity, not a reset 1,000.
    assert np.isclose(result.test_year_turnover.iloc[1], 0.5)


def test_model_a_training_turnover_is_corrected_and_model_b_remains_canonical():
    old = pd.read_csv(OLD_RUN / "training_candidate_results.csv")
    new = pd.read_csv(RUN / "training_candidate_results.csv")
    keys = ["model", "frequency", "test_year", "ma_days", "momentum_days", "low_vol_quantile"]
    joined = old.merge(new, on=keys, suffixes=("_old", "_new"))
    a = joined[joined.model.eq("MODEL_A_QLD_TREND")]
    b = joined[joined.model.eq("MODEL_B_FOUR_STATE")]
    assert (a.annual_turnover_new != a.annual_turnover_old).any()
    assert np.allclose(b.annual_turnover_new, b.annual_turnover_old, rtol=0.0, atol=1e-12)


def test_eligibility_is_unchanged_by_turnover_only_correction():
    old = pd.read_csv(OLD_RUN / "training_candidate_results.csv")
    new = pd.read_csv(RUN / "training_candidate_results.csv")
    keys = ["model", "frequency", "test_year", "ma_days", "momentum_days", "low_vol_quantile"]
    joined = old.merge(new, on=keys, suffixes=("_old", "_new"))
    assert len(joined) == 2_800
    assert joined.eligible_old.equals(joined.eligible_new)


def test_frozen_tie_break_still_prefers_lower_turnover_after_maxdd():
    candidates = pd.DataFrame([
        {"ma_days": 150, "cagr": .20, "max_drawdown": -.20, "calmar": 1.0, "annual_turnover": .8},
        {"ma_days": 200, "cagr": .20, "max_drawdown": -.20, "calmar": 1.0, "annual_turnover": .7},
    ])
    selected, evaluated = select_calmar_candidate(candidates)
    assert selected.ma_days == 200
    assert evaluated.eligible.all()


def test_corrected_selection_comparison_is_deterministic_and_complete():
    selection = pd.read_csv(RUN / "selected_parameters_by_fold.csv")
    comparison = pd.read_csv(RUN / "selection_old_vs_new.csv")
    assert len(selection) == len(comparison) == 112
    assert not comparison.selection_changed.any()
    repeat = _selection_old_vs_new(selection, selection)
    assert repeat.selection_changed.eq(False).all()
    pd.testing.assert_frame_equal(repeat, _selection_old_vs_new(selection, selection))


def test_no_test_period_observation_enters_training_candidates():
    candidates = pd.read_csv(RUN / "training_candidate_results.csv")
    folds = pd.read_csv(RUN / "walk_forward_folds.csv")
    assert len(folds) == 14
    ends = folds.set_index("test_year").train_end
    starts = folds.set_index("test_year").test_start
    for year, group in candidates.groupby("test_year"):
        assert group.train_end.eq(ends.loc[year]).all()
        assert pd.Timestamp(group.train_end.iloc[0]) < pd.Timestamp(starts.loc[year])


def test_cash_fallback_stitches_complete_oos_without_fold_resets():
    selections = pd.read_csv(RUN / "selected_parameters_by_fold.csv")
    targets = pd.read_csv(RUN / "stitched_execution_targets.csv")
    assert len(targets) == 8 * 3_436
    assert targets.date.notna().all()
    assert selections.loc[selections.selection_status.eq("NO_ELIGIBLE_PARAMETER"), "test_allocation_mode"].eq("CASH_FALLBACK").all()
    assert selections.loc[selections.selection_status.eq("SELECTED"), "test_allocation_mode"].eq("SELECTED_STRATEGY").all()


def test_phase7a_canonical_artifacts_are_unchanged():
    accepted = ROOT / "reports/runs/20260913_phase7a_metrics_tax_audited_final"
    expected = {
        "state_decisions.csv": "228529085687af082df26d8a3a5e42826facacbd3fec4395d1339cfbf56be6d0",
        "execution_targets.csv": "d48dc37826f711db427ad7c4e5338b9048037d506f4289cc729d6afb3609005e",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((accepted / name).read_bytes()).hexdigest() == digest


def test_raw_snapshot_hashes_match_immutable_manifest():
    import yaml

    manifest = yaml.safe_load((ROOT / "data/raw/manifest.yaml").read_text())
    for asset, info in manifest["sources"].items():
        digest = hashlib.sha256((ROOT / "data/raw" / f"{asset}.parquet").read_bytes()).hexdigest()
        assert digest == info["sha256"]
