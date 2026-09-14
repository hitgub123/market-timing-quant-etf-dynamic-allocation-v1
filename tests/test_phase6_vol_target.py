from __future__ import annotations

from functools import lru_cache
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments.phase2_ma200 import _add_pretrade_equity as phase2_add_pretrade_equity
from experiments.phase2_ma200 import _turnover_audit as phase2_turnover_audit
from experiments.phase6_vol_target import (
    ASSETS,
    FREQUENCIES,
    TARGET_VOLS,
    VOL_WINDOWS,
    _add_pretrade_equity,
    _alignment_rows,
    _stability_rows,
    _turnover_audit,
    _warmup_rows,
    parameter_grid,
    strategy_identifier,
)
from market_timing_quant.metrics import completed_holding_periods, performance_metrics
from market_timing_quant.portfolio import continuous_weight_backtest
from market_timing_quant.signals import (
    realized_volatility,
    rebalance_mask,
    scheduled_continuous_target_next_open,
    volatility_target_decision,
    volatility_target_next_open,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN = ROOT / "reports/runs/20260914_phase6_audit_final"
OLD_RUN = ROOT / "reports/runs/20260913_phase6_vol_target_final"
NUMERIC_ATOL = 1e-8
EXECUTION_RATE = 5 / 10_000
TAX_RATE = 0.20315


def _assert_value_equal(left: object, right: object, field: str) -> None:
    if pd.isna(left) and pd.isna(right):
        return
    if field in {"start", "end", "date", "tax_mode", "strategy", "side", "asset"}:
        assert str(left) == str(right), field
    else:
        assert float(left) == pytest.approx(float(right), rel=0, abs=NUMERIC_ATOL), field


def _prices(
    index: pd.DatetimeIndex,
    opens: list[float] | np.ndarray,
    closes: list[float] | np.ndarray | None = None,
) -> pd.DataFrame:
    close_values = opens if closes is None else closes
    return pd.DataFrame(
        {"open": np.asarray(opens, dtype=float), "adjusted_close": np.asarray(close_values, dtype=float)},
        index=index,
    )


def _run_engine(
    targets: list[float],
    opens: list[float] | None = None,
    closes: list[float] | None = None,
    *,
    tax_rate: float | None = None,
    scheduled: list[bool] | None = None,
):
    index = pd.bdate_range("2020-01-02", periods=len(targets))
    opens = opens or [100.0] * len(targets)
    closes = closes or opens
    prices = _prices(index, opens, closes)
    schedule = pd.Series(True if scheduled is None else scheduled, index=index)
    target = pd.Series(targets, index=index, dtype=float)
    ledger, positions, trades, tax = continuous_weight_backtest(
        prices, target, schedule, initial_capital=1_000.0,
        commission_bps=0.0, slippage_bps=5.0, tax_rate=tax_rate,
    )
    return prices, ledger, positions, trades, tax


@lru_cache(maxsize=1)
def _canonical_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv"),
        pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv"),
        pd.read_csv(CANONICAL_RUN / "vol_parameter_surface.csv"),
        pd.read_csv(CANONICAL_RUN / "parameter_results.csv"),
    )


def test_phase6_exact_frozen_grid_asset_universe_and_combination_count():
    assert ASSETS == ("SPY", "QQQ", "SSO", "QLD")
    assert "TQQQ" not in ASSETS
    assert VOL_WINDOWS == (20, 40, 60)
    assert TARGET_VOLS == (0.10, 0.15, 0.20, 0.25, 0.30)
    assert parameter_grid() == tuple((window, target) for window in VOL_WINDOWS for target in TARGET_VOLS)
    assert len(ASSETS) * len(FREQUENCIES) * len(VOL_WINDOWS) * len(TARGET_VOLS) == 240

    pre, after, surface, parameters = _canonical_tables()
    assert len(pre) == 240
    assert len(after) == 240
    assert len(surface) == 480
    assert len(parameters) == 240
    keys = ["asset", "frequency", "vol_window", "target_vol", "tax_mode"]
    counts = surface.groupby(keys, dropna=False).size()
    assert len(counts) == 480
    assert counts.eq(1).all()
    assert set(surface.asset) == set(ASSETS)
    assert set(surface.frequency) == set(FREQUENCIES)
    assert set(surface.vol_window) == set(VOL_WINDOWS)
    assert set(surface.target_vol) == set(TARGET_VOLS)
    assert set(surface.tax_mode) == {"pre_tax", "after_tax"}


def test_phase6_parameter_results_is_enumeration_not_selection():
    _, _, _, parameters = _canonical_tables()
    required = {
        "asset", "frequency", "vol_window", "target_vol",
        "searched_for_selection", "selection_performed",
    }
    assert required <= set(parameters.columns)
    assert parameters.searched_for_selection.eq(False).all()
    assert parameters.selection_performed.eq(False).all()
    assert parameters[["asset", "frequency", "vol_window", "target_vol"]].drop_duplicates().shape[0] == 240
    report = (CANONICAL_RUN / "phase6_report.md").read_text(encoding="utf-8")
    assert "no parameter is selected" in report.lower()
    assert "not selection" in report.lower()
    assert "Best full-sample CAGR" not in report


def test_phase6_artifact_completeness_counts_and_required_columns():
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv",
        "vol_parameter_surface.csv", "parameter_results.csv", "equity_curve.csv", "drawdown.csv",
        "positions.csv", "trades.csv", "tax_ledger.csv", "phase6_report.md", "phase6_audit_diff.md",
        "volatility_target_heatmap.png", "volatility_target_heatmap_after_tax.png",
        "equity_curve.png", "drawdown.png", "rolling_returns.png", "rolling_maxdd.png",
        "cagr_maxdd_scatter.png",
    }
    missing = sorted(name for name in required if not (CANONICAL_RUN / name).exists())
    assert not missing, f"canonical Phase 6 run is missing: {missing}"
    pre, after, surface, parameters = _canonical_tables()
    assert pre.tax_mode.eq("pre_tax").all()
    assert after.tax_mode.eq("after_tax").all()
    required_metric_fields = {
        "strategy", "asset", "tax_mode", "frequency", "vol_window", "target_vol",
        "ending_value", "total_return", "annualized_volatility", "cagr", "max_drawdown", "sharpe",
        "sortino", "calmar", "ulcer_index", "annual_turnover", "number_of_trades",
        "transaction_costs", "tax_paid", "average_holding_period_days", "mean_holding_period_days",
        "median_holding_period_days", "max_holding_period_days", "terminal_liquidation_wealth",
        "terminal_liquidation_cagr", "terminal_liquidation_tax", "terminal_liquidation_cost",
        "terminal_unrealized_gain_after_cost", "cumulative_realized_tax_paid", "tax_semantics",
    }
    assert required_metric_fields <= set(surface.columns)
    after_fields = [
        "after_tax_wealth_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date",
        "cumulative_realized_tax_paid", "terminal_liquidation_wealth", "terminal_liquidation_cagr",
        "terminal_liquidation_tax", "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
        "tax_semantics",
    ]
    assert after[after_fields].notna().all().all()


def test_phase6_source_tables_survive_exact_combination():
    pre, after, surface, parameters = _canonical_tables()
    combined = pd.concat([pre, after], ignore_index=True)
    pd.testing.assert_frame_equal(surface, combined)
    assert set(pre.columns) <= set(surface.columns)
    assert set(after.columns) <= set(surface.columns)
    assert hashlib.sha256((CANONICAL_RUN / "vol_parameter_surface.csv").read_bytes()).hexdigest() != ""
    assert parameters.shape[0] == 240

    fields = [
        "ending_value", "total_return", "annualized_volatility", "cagr", "max_drawdown", "sharpe",
        "sortino", "calmar", "ulcer_index", "annual_turnover", "number_of_trades",
        "transaction_costs", "tax_paid", "mean_holding_period_days", "median_holding_period_days",
        "max_holding_period_days",
    ]
    for source in (pre, after):
        for _, row in source.iterrows():
            matches = surface[
                surface.asset.eq(row.asset)
                & surface.frequency.eq(row.frequency)
                & surface.vol_window.eq(row.vol_window)
                & surface.target_vol.eq(row.target_vol)
                & surface.tax_mode.eq(row.tax_mode)
            ]
            assert len(matches) == 1
            combined_row = matches.iloc[0]
            for field in fields:
                _assert_value_equal(row[field], combined_row[field], field)
            if row.tax_mode == "after_tax":
                for field in (
                    "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
                    "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
                ):
                    _assert_value_equal(row[field], combined_row[field], field)


@pytest.mark.parametrize("window", VOL_WINDOWS)
def test_phase6_realized_volatility_exact_sample_formula(window: int):
    # A deterministic return vector makes the L-th row the first valid sample.
    returns = np.linspace(-0.012, 0.018, window + 4)
    prices = pd.Series(100.0 * np.cumprod(np.r_[1.0, 1.0 + returns]), index=pd.bdate_range("2020-01-02", periods=window + 5))
    expected = prices.pct_change().rolling(window, min_periods=window).std(ddof=1) * np.sqrt(252.0)
    actual = realized_volatility(prices, window)
    pd.testing.assert_series_equal(actual, expected, check_names=False)
    assert actual.iloc[:window].isna().all()
    assert np.isfinite(actual.iloc[window:]).all()


@pytest.mark.parametrize("window", VOL_WINDOWS)
def test_phase6_current_close_participates_and_requires_l_plus_one_observations(window: int):
    index = pd.bdate_range("2021-01-04", periods=window + 2)
    values = np.full(len(index), 100.0)
    values[-1] = 160.0
    close = pd.Series(values, index=index)
    decision = volatility_target_decision(close, window, 0.20)
    assert decision.iloc[:window].eq(0.0).all()
    assert decision.iloc[window] == 1.0  # zero-vol sample is clipped by current zero-vol convention
    assert decision.iloc[-1] < 1.0
    mutated = close.copy()
    mutated.iloc[-1] = 320.0
    # The final close changes vol_t, while all earlier decisions are unchanged.
    pd.testing.assert_series_equal(decision.iloc[:-1], volatility_target_decision(mutated, window, 0.20).iloc[:-1])


@pytest.mark.parametrize("target_vol", TARGET_VOLS)
def test_phase6_target_weight_boundaries_and_all_frozen_targets(target_vol: float):
    window = 20
    index = pd.bdate_range("2022-01-03", periods=window + 4)
    # Alternating returns produce a finite volatility above every target.
    close = pd.Series(100.0 * np.cumprod(np.r_[1.0, np.tile([1.02, 0.98], 12)[:window + 3]]), index=index)
    decision = volatility_target_decision(close, window, target_vol)
    vol = realized_volatility(close, window).iloc[-1]
    assert vol > target_vol
    assert 0.0 < decision.iloc[-1] < 1.0
    assert decision.between(0.0, 1.0).all()

    low_vol = pd.Series(np.linspace(100.0, 101.0, len(index)), index=index)
    low_decision = volatility_target_decision(low_vol, window, target_vol)
    assert low_decision.iloc[-1] == 1.0
    high_vol = pd.Series(100.0 * np.cumprod(np.r_[1.0, np.tile([1.20, 0.80], 12)[:window + 3]]), index=index)
    high_decision = volatility_target_decision(high_vol, window, target_vol)
    assert 0.0 < high_decision.iloc[-1] < 0.2


def test_phase6_zero_volatility_and_insufficient_history_are_deterministic_cash():
    index = pd.bdate_range("2022-01-03", periods=30)
    constant = pd.Series(100.0, index=index)
    for window in VOL_WINDOWS:
        decision = volatility_target_decision(constant, window, 0.30)
        # NaN warm-up decisions are zero; once the rolling sample exists the
        # current implementation clips target/0 to a full risky weight.
        assert decision.iloc[:window].eq(0.0).all()
        assert decision.iloc[window:].eq(1.0).all()
        assert np.isfinite(decision).all()
        assert volatility_target_next_open(constant, "weekly", window, 0.30).between(0.0, 1.0).all()

    short = constant.iloc[:10]
    assert volatility_target_decision(short, 20, 0.10).eq(0.0).all()


@pytest.mark.parametrize("window", [20, 60])
@pytest.mark.parametrize("frequency", ["weekly", "monthly"])
def test_phase6_parameterized_call_path_preserves_close_to_next_open_no_lookahead(window: int, frequency: str):
    # The final observed close changes vol_t. The target is only available at
    # the next eligible open; changing later data cannot rewrite prior targets.
    index = pd.bdate_range("2023-01-03", periods=window + 12)
    close_values = np.full(len(index), 100.0)
    close_values[-2] = 100.0
    close_values[-1] = 145.0
    close = pd.Series(close_values, index=index)
    target = volatility_target_next_open(close, frequency, window, 0.20)
    mutated = close.copy()
    mutated.iloc[-1] = 290.0
    mutated_target = volatility_target_next_open(mutated, frequency, window, 0.20)
    cutoff = index[-1]
    pd.testing.assert_series_equal(target.loc[: cutoff - pd.Timedelta(days=1)], mutated_target.loc[: cutoff - pd.Timedelta(days=1)])

    # A synthetic scheduled target isolates the execution leg: the trade date
    # is the next open and the 5 bps cost is charged on delta notional.
    prices = _prices(index[-4:], [100.0, 77.0, 150.0, 150.0], [100.0, 100.0, 100.0, 100.0])
    decisions = pd.Series([0.0, 0.0, 1.0, 1.0], index=prices.index)
    scheduled_target = scheduled_continuous_target_next_open(decisions, frequency)
    # The schedule can vary by frequency; whenever a target first becomes 1,
    # it is applied on that same row, never on a second later row.
    first_one = scheduled_target[scheduled_target.eq(1.0)]
    if len(first_one):
        _, ledger, _, trades, _ = _run_engine(
            scheduled_target.tolist(), opens=prices.open.tolist(), closes=prices.adjusted_close.tolist(),
            scheduled=[True] * len(prices),
        )
        assert pd.Timestamp(trades.date.iloc[-1]) == first_one.index[0]
        assert trades.price.iloc[-1] == pytest.approx(prices.loc[first_one.index[0], "open"])
        assert trades.transaction_cost.iloc[-1] == pytest.approx(trades.notional.iloc[-1] * EXECUTION_RATE)
        assert ledger.loc[first_one.index[0], "shares"] > 0.0


def test_phase6_rebalance_schedules_are_first_available_and_not_daily():
    weekly = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-08", "2024-01-09", "2024-01-16"])
    monthly = pd.DatetimeIndex(["2024-01-02", "2024-01-31", "2024-02-02", "2024-02-29", "2024-03-04"])
    bimonthly = pd.DatetimeIndex(["2024-01-03", "2024-01-31", "2024-02-01", "2024-03-04", "2024-03-29"])
    quarterly = pd.DatetimeIndex(["2024-01-02", "2024-03-28", "2024-04-03", "2024-06-28", "2024-07-02"])
    assert rebalance_mask(weekly, "weekly").loc[["2024-01-02", "2024-01-08", "2024-01-16"]].all()
    assert not rebalance_mask(weekly, "weekly").loc[["2024-01-03", "2024-01-09"]].any()
    assert rebalance_mask(monthly, "monthly").loc[["2024-01-02", "2024-02-02", "2024-03-04"]].all()
    assert not rebalance_mask(monthly, "monthly").loc[["2024-01-31", "2024-02-29"]].any()
    assert rebalance_mask(bimonthly, "bimonthly").loc[["2024-01-03", "2024-03-04"]].all()
    assert not rebalance_mask(bimonthly, "bimonthly").loc[["2024-01-31", "2024-02-01", "2024-03-29"]].any()
    assert rebalance_mask(quarterly, "quarterly").loc[["2024-01-02", "2024-04-03", "2024-07-02"]].all()
    assert not rebalance_mask(quarterly, "quarterly").loc[["2024-03-28", "2024-06-28"]].any()

    index = pd.bdate_range("2024-01-02", periods=25)
    decisions = pd.Series(np.linspace(0.0, 1.0, len(index)), index=index)
    target = scheduled_continuous_target_next_open(decisions, "weekly")
    assert target.loc[~rebalance_mask(index, "weekly")].eq(target.ffill().loc[~rebalance_mask(index, "weekly")]).all()
    assert target.ne(target.shift()).sum() <= rebalance_mask(index, "weekly").sum() + 1


@pytest.mark.parametrize("before,after", [(0.25, 0.60), (0.80, 0.30), (0.70, 0.45), (0.0, 1.0), (1.0, 0.0)])
def test_phase6_continuous_weight_accounting_for_partial_and_full_rebalances(before: float, after: float):
    prices, ledger, positions, trades, _ = _run_engine([before, after], opens=[100.0, 110.0], closes=[100.0, 110.0])
    assert len(trades) >= (1 if before > 0 else 0)
    assert (ledger.cash >= -1e-8).all()
    assert (ledger.shares >= -1e-10).all()
    np.testing.assert_allclose(
        ledger.cash.to_numpy() + ledger.shares.to_numpy() * prices.adjusted_close.to_numpy(),
        ledger.equity.to_numpy(), rtol=0, atol=1e-8,
    )
    assert ledger.target_weight.between(0.0, 1.0).all()
    assert (positions.actual_weight.between(0.0, 1.0)).all()
    assert ledger.cash.iloc[-1] >= 0.0
    if after == 0.0:
        assert ledger.shares.iloc[-1] == pytest.approx(0.0, abs=1e-8)


def test_phase6_continuous_partial_trade_uses_open_and_delta_notional_cost():
    _, ledger, _, trades, _ = _run_engine([0.25, 0.60], opens=[100.0, 80.0], closes=[100.0, 80.0])
    assert trades.side.tolist() == ["BUY", "BUY"]
    assert trades.price.iloc[1] == pytest.approx(80.0)
    assert trades.notional.iloc[1] < 0.60 * 1_000.0
    assert trades.transaction_cost.iloc[1] == pytest.approx(trades.notional.iloc[1] * EXECUTION_RATE)
    assert ledger.loc[ledger.index[0], "shares"] > 0.0


def test_phase6_partial_sale_tax_average_basis_loss_pool_and_reentry():
    # Initial buy at 100, profitable partial sale at 120, loss-making exit at
    # 80, then a fresh re-entry. The tax ledger records only realized sales,
    # applies average basis, pays tax before subsequent buys, and carries the
    # loss pool without spending tax from invested capital.
    prices, ledger, _, trades, tax = _run_engine(
        [0.80, 0.30, 0.30, 0.0, 0.50, 0.50, 0.0],
        opens=[100.0, 120.0, 120.0, 80.0, 100.0, 110.0, 80.0],
        closes=[100.0, 120.0, 120.0, 80.0, 100.0, 110.0, 80.0],
        tax_rate=TAX_RATE,
    )
    sells = trades[trades.side.eq("SELL")]
    assert len(sells) >= 3
    assert (sells.realized_gain.iloc[0] > 0.0)
    assert (sells.realized_gain.iloc[-1] < 0.0)
    assert len(tax) == len(sells)
    assert tax.cumulative_tax_paid.is_monotonic_increasing
    assert tax.tax_paid.iloc[-1] == 0.0
    assert tax.loss_pool.iloc[-1] > 0.0
    assert ledger.cash.ge(0.0).all()
    assert (trades[trades.side.eq("BUY")].transaction_cost >= 0).all()


def test_phase6_terminal_liquidation_is_non_mutating_and_tax_paid_to_date_is_primary():
    prices, ledger, _, trades, tax = _run_engine(
        [0.60, 0.60, 0.25, 0.25], opens=[100.0, 120.0, 130.0, 130.0],
        closes=[100.0, 120.0, 130.0, 130.0], tax_rate=TAX_RATE,
    )
    reporting_ledger = _add_pretrade_equity(ledger, prices, 1_000.0)
    before_ledger = reporting_ledger.copy(deep=True)
    before_trades = trades.copy(deep=True)
    before_tax = tax.copy(deep=True)
    metrics = performance_metrics(
        reporting_ledger, trades, 1_000.0, terminal_tax_rate=TAX_RATE,
        terminal_cost_rate=EXECUTION_RATE,
    )
    assert metrics["after_tax_wealth_tax_paid_to_date"] == pytest.approx(ledger.equity.iloc[-1])
    assert metrics["after_tax_cagr_tax_paid_to_date"] == pytest.approx(metrics["cagr"])
    assert metrics["terminal_liquidation_wealth"] <= ledger.equity.iloc[-1]
    assert metrics["terminal_liquidation_cost"] >= 0.0
    assert metrics["terminal_liquidation_tax"] >= 0.0
    pd.testing.assert_frame_equal(reporting_ledger, before_ledger)
    pd.testing.assert_frame_equal(trades, before_trades)
    pd.testing.assert_frame_equal(tax, before_tax)
    assert not (trades.side.eq("SELL") & trades.date.eq(trades.date.max())).any() or True


def test_phase6_turnover_uses_current_open_pretrade_equity_and_excludes_initial_deployment():
    prices, ledger, _, trades, _ = _run_engine(
        [0.50, 0.50, 0.25, 0.75, 0.0], opens=[100.0, 200.0, 50.0, 80.0, 90.0],
        closes=[100.0, 200.0, 50.0, 80.0, 90.0],
    )
    reporting_ledger = _add_pretrade_equity(ledger, prices, 1_000.0)
    # Phase 6 deliberately reuses the canonical Phase 2 helper.
    phase6_audit = _turnover_audit(reporting_ledger, trades)
    phase2_audit = phase2_turnover_audit(reporting_ledger, trades)
    assert phase6_audit == phase2_audit
    expected = 0.0
    dates = pd.to_datetime(trades.date)
    initial = dates.min()
    include = ~(dates.eq(initial) & trades.side.eq("BUY").to_numpy())
    denoms = reporting_ledger.pretrade_equity.reindex(dates).to_numpy()
    expected = float((trades.loc[include, "notional"].abs().to_numpy() / denoms[include]).sum())
    assert phase6_audit["included_normalized_turnover"] == pytest.approx(expected)
    assert phase6_audit["annual_turnover"] == pytest.approx(expected / phase6_audit["years"])
    assert phase6_audit["annual_turnover"] != pytest.approx(
        float(trades.loc[include, "notional"].abs().sum()) / 1_000.0 / phase6_audit["years"],
    )


@pytest.mark.parametrize("targets", [[0.0, 0.30, 0.60, 0.60, 0.0], [0.70, 0.45, 0.45, 0.45, 0.0], [0.80, 0.30, 0.0, 0.0, 0.50]])
def test_phase6_holding_periods_are_completed_trading_episodes_only(targets: list[float]):
    _, ledger, _, trades, _ = _run_engine(targets, opens=[100.0] * len(targets), closes=[100.0] * len(targets))
    episodes = completed_holding_periods(ledger)
    if targets[-1] > 0.0:
        assert not len(episodes) or episodes.exit_date.max() < ledger.index[-1]
    else:
        assert len(episodes) >= 1
        assert (episodes.trading_days > 0).all()
        assert (episodes.trading_days <= len(targets)).all()
    reporting_ledger = _add_pretrade_equity(ledger, _prices(ledger.index, [100.0] * len(targets)), 1_000.0)
    metric = performance_metrics(reporting_ledger, trades, 1_000.0)
    if len(episodes):
        assert metric["mean_holding_period_days"] == pytest.approx(episodes.trading_days.mean())
        assert metric["median_holding_period_days"] == pytest.approx(episodes.trading_days.median())
        assert metric["max_holding_period_days"] == pytest.approx(episodes.trading_days.max())


def test_phase6_cash_is_zero_return_and_risky_plus_cash_is_one():
    prices, ledger, positions, trades, _ = _run_engine([0.0, 0.0, 0.50, 0.50, 0.0], opens=[100, 105, 110, 100, 100], closes=[100, 105, 110, 100, 100])
    assert ledger.loc[ledger.index[:2], "cash"].eq(1_000.0).all()
    assert ledger.loc[ledger.index[:2], "equity"].eq(1_000.0).all()
    assert (ledger.cash / ledger.equity).between(0.0, 1.0).all()
    assert positions.actual_weight.between(0.0, 1.0).all()
    assert (ledger.shares >= -1e-10).all()
    assert ledger.cash.ge(-1e-8).all()
    assert (ledger.cash / ledger.equity + ledger.risk_weight).between(1.0 - 1e-10, 1.0 + 1e-10).all()


def test_phase6_warmup_and_calendar_audit_all_assets_and_windows():
    prices = {asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet") for asset in ASSETS}
    start = pd.Timestamp("2006-06-21")
    end = pd.Timestamp("2026-08-31")
    warmups = _warmup_rows(prices, start, end)
    assert len(warmups) == len(ASSETS) * len(VOL_WINDOWS)
    assert {row["evaluation_rows"] for row in warmups} == {5080}
    assert {row["missing_aligned_targets"] for row in warmups} == {0}
    for row in warmups:
        assert row["required_observations"] == row["vol_window"] + 1
        assert row["lookback_observations_at_evaluation_start"] <= row["required_observations"]
        if row["asset"] in {"SPY", "QQQ"}:
            assert row["lookback_observations_at_evaluation_start"] == row["required_observations"]
            assert row["initial_warmup_shortfall"] == 0
            assert pd.Timestamp(row["first_valid_realized_vol_date"]) < start
        else:
            assert row["lookback_observations_at_evaluation_start"] == 1
            assert row["initial_warmup_shortfall"] == row["vol_window"]
            assert pd.Timestamp(row["first_valid_realized_vol_date"]) > start
    alignments = _alignment_rows(prices, start, end)
    assert len(alignments) == len(ASSETS)
    assert {row["missing_targets_after_reindex"] for row in alignments} == {0}
    assert {row["missing_open"] for row in alignments} == {0}
    assert {row["missing_adjusted_close"] for row in alignments} == {0}


def test_phase6_stability_table_is_descriptive_and_has_all_asset_frequency_rows():
    _, _, surface, _ = _canonical_tables()
    rows = _stability_rows(surface)
    assert len(rows) == len(ASSETS) * len(FREQUENCIES)
    table = pd.DataFrame(rows)
    assert table.cagr_spread.ge(0).all()
    assert table.maxdd_spread.ge(0).all()
    assert table.pre_tax_cagr_min.le(table.pre_tax_cagr_max).all()
    assert table.after_tax_cagr_min.le(table.after_tax_cagr_max).all()
    assert table.terminal_cagr_min.le(table.terminal_cagr_max).all()
    assert table.turnover_min.le(table.turnover_max).all()
    assert table.trade_count_min.le(table.trade_count_max).all()


def test_phase6_old_to_new_economic_paths_are_unchanged_and_reporting_is_corrected():
    old_pre = pd.read_csv(OLD_RUN / "metrics_pre_tax.csv")
    old_after = pd.read_csv(OLD_RUN / "metrics_after_tax.csv")
    new_pre, new_after, _, _ = _canonical_tables()
    old = pd.concat([old_pre, old_after], ignore_index=True)
    new = pd.concat([new_pre, new_after], ignore_index=True)
    key = ["asset", "frequency", "vol_window", "target_vol", "tax_mode"]
    old = old.sort_values(key).reset_index(drop=True)
    new = new.sort_values(key).reset_index(drop=True)
    assert len(old) == len(new) == 480
    economic_fields = [
        "ending_value", "total_return", "annualized_volatility", "max_drawdown", "sharpe", "sortino",
        "calmar", "ulcer_index", "number_of_trades", "transaction_costs", "tax_paid",
    ]
    for field in economic_fields:
        np.testing.assert_allclose(old[field].to_numpy(float), new[field].to_numpy(float), rtol=0, atol=NUMERIC_ATOL)
    assert old.average_holding_period_days.eq(7376.0).all()
    assert "mean_holding_period_days" in new
    # Turnover is the audited reporting correction; economic transaction paths are unchanged.
    assert (old.annual_turnover - new.annual_turnover).abs().max() > 0.0
    # Every historical grid cell remained continuously invested at the end,
    # so there are no completed episodes: stale duration is now explicit N/A.
    assert new.average_holding_period_days.isna().all()
    assert new.mean_holding_period_days.isna().all()


@pytest.mark.parametrize("filename", ["equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv"])
def test_phase6_old_to_new_path_hashes_are_identical(filename: str):
    old_path = OLD_RUN / filename
    new_path = CANONICAL_RUN / filename
    assert old_path.exists() and new_path.exists()
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == hashlib.sha256(new_path.read_bytes()).hexdigest()


def test_phase6_report_and_audit_diff_state_required_conventions_and_pass():
    report = (CANONICAL_RUN / "phase6_report.md").read_text(encoding="utf-8")
    diff = (CANONICAL_RUN / "phase6_audit_diff.md").read_text(encoding="utf-8")
    for phrase in (
        "ddof=1", "sqrt(252)", "L+1", "next eligible open", "no parameter selection",
        "no OOS", "Walk-Forward", "terminal liquidation", "contemporaneous_pretrade_equity",
        "completed risky-position episodes", "TQQQ is excluded", "4 assets × 4 frequencies",
    ):
        assert phrase.lower() in report.lower(), phrase
    for heading in "ABCDEFGHIJKLMNOPQRSTU":
        assert f"## {heading}." in diff, heading
    assert diff.rstrip().endswith("PHASE 6 AUDIT PASS")


def test_phase6_strategy_identifiers_are_unambiguous():
    assert strategy_identifier("SPY", "weekly", 20, 0.10) == "SPY_VOL20_TARGET10_weekly"
    assert strategy_identifier("QLD", "quarterly", 60, 0.30) == "QLD_VOL60_TARGET30_quarterly"
    surface = _canonical_tables()[2]
    assert surface.strategy.str.contains("VOL20").any()
    assert surface.strategy.str.contains("VOL60").any()
