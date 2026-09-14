import pandas as pd

from market_timing_quant.portfolio import enforce_asset_availability


def test_tqqq_weight_is_zero_before_listing():
    index = pd.date_range("2006-06-21", "2010-02-12", freq="B")
    requested = pd.DataFrame({"TQQQ": 1.0}, index=index)
    weights = enforce_asset_availability(requested, {"TQQQ": "2010-02-11"})
    assert (weights.loc[:"2010-02-10", "TQQQ"] == 0).all()
    assert (weights.loc["2010-02-11":, "TQQQ"] == 1).all()
