import pandas as pd

from experiments.phase7b_parameter_walk_forward import _stitch_frame, _stitch_series
from experiments.phase7b_parameter_walk_forward import _report_realized_tax_paid
from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.walk_forward import WalkForwardFold


def _folds():
    return [
        WalkForwardFold(pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03"), pd.Timestamp("2020-01-06"), 2020),
        WalkForwardFold(pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-06"), pd.Timestamp("2020-01-07"), pd.Timestamp("2020-01-08"), 2021),
    ]


def _selection(statuses):
    return pd.DataFrame([
        {"test_year": year, "selection_status": status, "ma_days": 200,
         "momentum_days": 252, "low_vol_quantile": .33}
        for year, status in zip((2020, 2021), statuses)
    ])


def test_first_no_eligible_fold_stitches_cash_for_every_test_session():
    index = pd.DatetimeIndex(["2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"])
    selections = _selection(["NO_ELIGIBLE_PARAMETER", "SELECTED"])
    series, modes = _stitch_series(
        selections, _folds(), {(200,): pd.Series(1.0, index=index)}, index, ("ma_days",)
    )
    assert series.iloc[:2].tolist() == [0.0, 0.0]
    assert modes.iloc[:2].tolist() == ["CASH_FALLBACK", "CASH_FALLBACK"]
    assert series.iloc[2:].tolist() == [1.0, 1.0]
    assert len(series) == len(index)


def test_fallback_uses_normal_execution_and_does_not_repeat_cash_trades():
    index = pd.bdate_range("2020-01-02", periods=5)
    prices = pd.DataFrame({"open": [100., 90., 90., 110., 110.], "adjusted_close": [100., 90., 90., 110., 110.]}, index=index)
    # Invested fold, followed by two failed CASH folds, then an eligible resumption.
    targets = pd.Series([1., 0., 0., 0., 1.], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1000., commission_bps=0., slippage_bps=5., tax_rate=.20315,
    )
    assert trades.side.tolist() == ["BUY", "SELL", "BUY"]
    assert len(taxes) == 1
    assert taxes.iloc[0].realized_gain < 0
    assert taxes.iloc[0].tax_paid == 0
    assert ledger.shares.iloc[1] == 0 and ledger.shares.iloc[2] == 0
    assert ledger.shares.iloc[4] > 0


def test_stitched_frame_preserves_cash_state_and_all_sessions():
    index = pd.DatetimeIndex(["2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"])
    selections = _selection(["NO_ELIGIBLE_PARAMETER", "SELECTED"])
    targets = pd.DataFrame({"QQQ": 0.0, "QLD": 1.0, "TQQQ": 0.0}, index=index)
    states = pd.Series("LEVERAGED", index=index)
    stitched, stitched_states, modes = _stitch_frame(
        selections, _folds(), {(200, 252, .33): (targets, states)}, index,
        ("ma_days", "momentum_days", "low_vol_quantile"),
    )
    assert stitched.iloc[0:2].to_numpy().sum() == 0
    assert stitched_states.iloc[0:2].tolist() == ["CASH_FALLBACK", "CASH_FALLBACK"]
    assert modes.iloc[0:2].tolist() == ["CASH_FALLBACK", "CASH_FALLBACK"]
    assert stitched.iloc[2:].QLD.tolist() == [1.0, 1.0]


def test_training_prefix_excludes_future_test_observation():
    from experiments.phase7b_parameter_walk_forward import _training_metric

    index = pd.bdate_range("2020-01-02", periods=4)
    ledger = pd.DataFrame({"equity": [1000., 990., 980., 1000000.], "cash": 0., "shares": 1.,
                           "daily_return": [0., -.01, -.0101, 1000.]}, index=index)
    trades = pd.DataFrame(columns=["date", "side", "notional", "transaction_cost"])
    metric = _training_metric(ledger, trades, index[2], 1000.)
    assert metric["ending_value"] == 980.


def test_report_tax_paid_uses_matching_after_tax_ledger_not_pre_tax_row():
    pre_row = pd.Series({"tax_mode": "pre_tax", "tax_paid": 0.0})
    after_row = pd.Series({"tax_mode": "after_tax", "tax_paid": 1234.5})
    assert _report_realized_tax_paid(pre_row, after_row) == 1234.5


def test_report_tax_paid_keeps_buy_and_hold_zero_realized_tax():
    benchmark_row = pd.Series({"tax_mode": "benchmark", "tax_paid": 0.0})
    assert _report_realized_tax_paid(benchmark_row, None) == 0.0
