import pandas as pd
import pytest

from market_timing_quant.execution import shift_decisions_to_next_open, transaction_cost


def test_transaction_cost_is_exact_bps():
    assert transaction_cost(10_000, 2, 5) == pytest.approx(7.0)


def test_close_signal_never_changes_same_or_prior_open():
    decisions = pd.Series([0.0, 1.0, 0.0], index=pd.date_range("2024-01-01", periods=3))
    executions = shift_decisions_to_next_open(decisions)
    assert executions.tolist() == [0.0, 0.0, 1.0]

