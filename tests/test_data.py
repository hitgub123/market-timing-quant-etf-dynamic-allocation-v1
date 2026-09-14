from pathlib import Path

import pandas as pd
import pytest

from market_timing_quant.data import RAW_COLUMNS, audit_asset, to_processed


def _raw_frame(index: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    index = index if index is not None else pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    return pd.DataFrame({
        "Open": [100, 101], "High": [102, 103], "Low": [99, 100], "Close": [101, 102],
        "Adj Close": [101, 102], "Volume": [1, 1], "Dividends": [0, 0], "Stock Splits": [0, 0],
    }, index=index)


def test_data_audit_accepts_valid_sessions():
    frame = _raw_frame()
    summary, missing, _ = audit_asset("SPY", frame)
    assert summary["rows"] == 2
    assert missing.empty


def test_to_processed_applies_corporate_action_factor_to_all_ohlc():
    frame = _raw_frame()
    frame["Adj Close"] = frame["Close"].astype(float) / 2
    processed = to_processed(frame)
    for raw, adjusted in (("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close")):
        pd.testing.assert_series_equal(
            processed[adjusted], frame[raw] * frame["Adj Close"] / frame["Close"], check_names=False,
        )


@pytest.mark.parametrize("index", [
    pd.DatetimeIndex(["2024-01-02", "2024-01-02"]),
    pd.DatetimeIndex(["2024-01-03", "2024-01-02"]),
])
def test_data_audit_rejects_duplicate_or_nonmonotonic_dates(index):
    with pytest.raises(ValueError, match="unique and strictly increasing"):
        audit_asset("SPY", _raw_frame(index))


def test_data_audit_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="missing required raw fields"):
        audit_asset("SPY", _raw_frame().drop(columns=[RAW_COLUMNS[0]]))


def test_data_audit_rejects_ohlc_violations():
    frame = _raw_frame()
    frame.loc[frame.index[0], "High"] = 98
    with pytest.raises(ValueError, match="OHLC violations"):
        audit_asset("SPY", frame)


def test_large_return_is_reported_and_retained_without_claiming_cross_snapshot_check():
    frame = _raw_frame()
    frame.loc[frame.index[1], ["Open", "High", "Low", "Close", "Adj Close"]] = [140, 145, 135, 142, 142]
    summary, _, outliers = audit_asset("SPY", frame)
    assert summary["rows"] == len(frame)
    assert len(to_processed(frame)) == len(frame)
    assert len(outliers) == 1
    assert "not performed by audit_asset" in outliers.iloc[0].review
    assert outliers.iloc[0].independent_verification == "pending manifest review"
