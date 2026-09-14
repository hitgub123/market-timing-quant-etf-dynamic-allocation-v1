import numpy as np
import pandas as pd
import pytest

from experiments.phase4_absolute_momentum import MOMENTUM_WINDOWS, parameter_grid
from market_timing_quant.signals import absolute_momentum_decision, absolute_momentum_target_next_open


def test_absolute_momentum_grid_is_exactly_frozen():
    assert parameter_grid() == (126, 189, 252)
    with pytest.raises(ValueError, match="126, 189, or 252"):
        absolute_momentum_decision(pd.Series([1.0, 2.0]), 125)


def test_absolute_momentum_definition_and_zero_boundary():
    long_price = pd.Series([100.0] * 127 + [101.0])
    result = absolute_momentum_decision(long_price, 126)
    assert result.iloc[126] == 0.0
    assert result.iloc[127] == 1.0


def test_future_price_does_not_change_prior_momentum_targets():
    index = pd.bdate_range("2022-01-03", periods=300)
    price = pd.Series(np.arange(1.0, 301.0), index=index)
    target = absolute_momentum_target_next_open(price, "monthly", 126)
    changed = price.copy(); changed.iloc[-1] = 1e9
    other = absolute_momentum_target_next_open(changed, "monthly", 126)
    pd.testing.assert_series_equal(target.iloc[:-1], other.iloc[:-1])
