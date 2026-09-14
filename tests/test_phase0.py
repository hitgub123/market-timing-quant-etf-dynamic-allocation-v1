from pathlib import Path

import pandas as pd

from experiments.phase0_buy_hold import run


def test_phase0_writes_required_artifacts(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    output = run(root / "config/base.yaml", tmp_path, "fixed_phase0")
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv", "equity_curve.csv",
        "drawdown.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "parameter_results.csv",
        "equity_curve.png", "drawdown.png", "rolling_returns.png", "rolling_maxdd.png", "cagr_maxdd_scatter.png",
    }
    assert required <= {path.name for path in output.iterdir()}
    metrics = pd.read_csv(output / "metrics_pre_tax.csv").set_index("strategy")
    assert "main_TQQQ" not in metrics.index
    assert metrics.loc["main_SPY", "start"] == "2006-06-21"
    common = metrics[metrics["period"].eq("common_2010") & metrics["asset"].ne("CASH")]
    assert set(common.asset) == {"SPY", "QQQ", "SSO", "QLD", "TQQQ"}
    assert common.start.nunique() == common.end.nunique() == 1
    assert common.start.iloc[0] == "2010-02-11"
    assert common.end.iloc[0] == "2026-08-31"
    trades = pd.read_csv(output / "trades.csv")
    assert pd.to_datetime(trades.loc[trades.strategy.eq("common_2010_TQQQ"), "date"]).min() >= pd.Timestamp("2010-02-11")
    after_tax = pd.read_csv(output / "metrics_after_tax.csv").set_index("strategy")
    for asset in ("SPY", "QQQ", "SSO", "QLD", "TQQQ"):
        row = after_tax.loc[f"common_2010_{asset}"]
        assert row.annual_turnover == 0
        assert pd.isna(row.mean_holding_period_days)
        assert row.after_tax_wealth_tax_paid_to_date == row.ending_value
        assert row.terminal_liquidation_wealth < row.after_tax_wealth_tax_paid_to_date
    report = (output / "phase0_report.md").read_text(encoding="utf-8")
    assert "## A. Live Main Period" in report
    assert "## B. Common TQQQ Period" in report
    assert "Terminal-liquidation after-tax metrics are diagnostic and do not mutate the strategy ledger." in report
    audit_report = (root / "data/audit/data_audit_report.md").read_text(encoding="utf-8")
    assert "documented in immutable raw manifest" in audit_report
    assert "primary_sha256=4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76" in audit_report
