from __future__ import annotations

import numpy as np
import pandas as pd


def transaction_cost(traded_notional: float, commission_bps: float, slippage_bps: float) -> float:
    values = np.asarray([traded_notional, commission_bps, slippage_bps], dtype=float)
    if not np.isfinite(values).all() or traded_notional < 0 or commission_bps < 0 or slippage_bps < 0:
        raise ValueError("notional and bps must be finite and nonnegative")
    return float(traded_notional * (commission_bps + slippage_bps) / 10_000.0)


def shift_decisions_to_next_open(decisions_at_close: pd.DataFrame | pd.Series):
    """A close-t decision first becomes executable in row t+1."""
    shifted = decisions_at_close.shift(1)
    return shifted.fillna(0.0)

