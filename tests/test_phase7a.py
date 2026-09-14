import numpy as np
import pandas as pd

from market_timing_quant.signals import phase7_state_decisions, phase7_targets_next_open


def _series(n=700):
    index = pd.bdate_range("2008-01-02", periods=n)
    returns = .0005 + .012 * np.sin(np.arange(n) / 13)
    return pd.Series(100 * np.cumprod(1 + returns), index=index)


def test_expanding_vol_quantile_is_strictly_prior_only():
    decisions = phase7_state_decisions(_series())
    valid = decisions.rv20.dropna()
    at = valid.index[100]
    expected = decisions.loc[:at, "rv20"].iloc[:-1].quantile(.33)
    assert decisions.loc[at, "rv_quantile"] == expected


def test_future_prices_do_not_change_past_states_or_quantiles():
    price = _series()
    original = phase7_state_decisions(price)
    changed = price.copy(); changed.iloc[-1] *= 10
    other = phase7_state_decisions(changed)
    pd.testing.assert_frame_equal(original.iloc[:-1], other.iloc[:-1])


def test_state_weights_follow_exact_priority_and_sum_to_one():
    decisions = phase7_state_decisions(_series())
    ready = decisions.dropna(subset=["ma", "momentum", "rv20", "rv_quantile"])
    expected = np.where(
        ready.adjusted_close <= ready.ma, "RISK_OFF",
        np.where(ready.momentum <= 0, "NORMAL", np.where(ready.rv20 <= ready.rv_quantile, "AGGRESSIVE", "LEVERAGED")),
    )
    assert ready.state.tolist() == expected.tolist()
    assert np.allclose(decisions.filter(like="weight_").sum(axis=1), 1.0)


def test_tqqq_is_zero_before_listing_and_aggressive_falls_back_to_qld():
    index = pd.bdate_range("2010-02-05", periods=7)
    decisions = pd.DataFrame({"state": "AGGRESSIVE", "weight_QQQ": 0.0,
                              "weight_QLD": .8, "weight_TQQQ": .2}, index=index)
    targets, _ = phase7_targets_next_open(decisions, "weekly", tqqq_first_session="2010-02-11")
    assert (targets.loc[:"2010-02-10", "TQQQ"] == 0).all()
    assert (targets.loc["2010-02-08":"2010-02-10", "QLD"] == 1).all()


def test_close_state_first_affects_later_open():
    index = pd.DatetimeIndex(["2024-01-30", "2024-01-31", "2024-02-01", "2024-02-02"])
    decisions = pd.DataFrame({"state": ["RISK_OFF", "LEVERAGED", "LEVERAGED", "LEVERAGED"],
                              "weight_QQQ": 0.0, "weight_QLD": [0.0, 1.0, 1.0, 1.0],
                              "weight_TQQQ": 0.0}, index=index)
    targets, _ = phase7_targets_next_open(decisions, "monthly", tqqq_first_session="2010-02-11")
    assert targets.QLD.iloc[1] == 0.0
    assert targets.QLD.iloc[2] == 1.0
