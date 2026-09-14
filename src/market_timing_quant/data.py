from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yaml

ASSETS = ("SPY", "QQQ", "SSO", "QLD", "TQQQ")
RAW_COLUMNS = ("Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits")


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    missing = sorted(set(RAW_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing required raw fields: {missing}")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("raw index must be DatetimeIndex")
    result = frame.loc[:, RAW_COLUMNS].copy()
    if result.index.tz is not None:
        result.index = result.index.tz_localize(None)
    result.index = result.index.normalize()
    result.index.name = "date"
    return result


def audit_asset(asset: str, frame: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    if asset not in ASSETS:
        raise ValueError(f"unsupported asset: {asset}")
    missing_fields = sorted(set(RAW_COLUMNS) - set(frame.columns))
    if missing_fields:
        raise ValueError(f"{asset}: missing required raw fields: {missing_fields}")
    if frame.empty or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"{asset}: dates must be unique and strictly increasing")
    numeric = frame.loc[:, RAW_COLUMNS].apply(pd.to_numeric, errors="coerce")
    missing_cells = int(numeric.isna().sum().sum())
    if missing_cells:
        raise ValueError(f"{asset}: {missing_cells} missing required values")
    price = numeric[["Open", "High", "Low", "Close", "Adj Close"]]
    if (price <= 0).any().any() or (numeric["Volume"] < 0).any():
        raise ValueError(f"{asset}: non-positive price or negative volume")
    bad_ohlc = ~(
        (numeric["Low"] <= numeric["Open"])
        & (numeric["Open"] <= numeric["High"])
        & (numeric["Low"] <= numeric["Close"])
        & (numeric["Close"] <= numeric["High"])
        & (numeric["High"] >= numeric["Low"])
    )
    if bad_ohlc.any():
        raise ValueError(f"{asset}: {int(bad_ohlc.sum())} OHLC violations")
    schedule = mcal.get_calendar("NYSE").schedule(frame.index.min(), frame.index.max()).index.tz_localize(None)
    missing_dates = schedule.difference(frame.index)
    missing = pd.DataFrame({"asset": asset, "date": missing_dates})
    returns = numeric["Adj Close"].pct_change()
    mask = returns.abs() > 0.30
    outliers = pd.DataFrame({
        "asset": asset,
        "date": frame.index[mask],
        "adjusted_close": numeric.loc[mask, "Adj Close"].to_numpy(),
        "daily_return": returns.loc[mask].to_numpy(),
        "split": numeric.loc[mask, "Stock Splits"].to_numpy(),
        "review": "raw OHLC validated; retained; independent cross-snapshot verification not performed by audit_asset",
        "independent_verification": "pending manifest review",
        "evidence": "none in audit_asset",
    })
    summary = {
        "asset": asset,
        "start": str(frame.index.min().date()),
        "end": str(frame.index.max().date()),
        "rows": int(len(frame)),
        "missing_exchange_days": int(len(missing_dates)),
        "return_outliers_over_30pct": int(mask.sum()),
    }
    return summary, missing, outliers


def to_processed(frame: pd.DataFrame) -> pd.DataFrame:
    """Create total-return-compatible adjusted OHLC without changing raw files."""
    factor = frame["Adj Close"] / frame["Close"]
    result = pd.DataFrame(index=frame.index)
    for field in ("Open", "High", "Low", "Close"):
        result[field.lower()] = frame[field] * factor
    result["adjusted_close"] = frame["Adj Close"]
    result["volume"] = frame["Volume"]
    result["dividend"] = frame["Dividends"]
    result["split"] = frame["Stock Splits"]
    return result


def run_data_audit(raw_dir: str | Path, processed_dir: str | Path, audit_dir: str | Path) -> list[dict[str, object]]:
    raw_root, processed_root, audit_root = map(Path, (raw_dir, processed_dir, audit_dir))
    processed_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    sources = manifest.get("sources", {}) if isinstance(manifest, dict) else {}
    summaries, missing_tables, outlier_tables = [], [], []
    for asset in ASSETS:
        path = raw_root / f"{asset}.parquet"
        frame = load_raw(path)
        summary, missing, outliers = audit_asset(asset, frame)
        summary["raw_sha256"] = sha256(path)
        summaries.append(summary)
        missing_tables.append(missing)
        source = sources.get(asset, {}) if isinstance(sources, dict) else {}
        cross_review = source.get("cross_snapshot_review") if isinstance(source, dict) else None
        if len(outliers) and isinstance(cross_review, dict):
            outliers = outliers.copy()
            outliers["independent_verification"] = "documented in immutable raw manifest"
            outliers["evidence"] = (
                f"data/raw/manifest.yaml; primary_sha256={source.get('sha256', 'not recorded')}; "
                f"comparison_source={cross_review.get('comparison_snapshot', 'not recorded')}; "
                f"overlapping_rows={cross_review.get('overlapping_rows', 'not recorded')}; "
                f"raw_fields_exact={cross_review.get('raw_ohlcv_dividend_split_fields_exact', 'not recorded')}"
            )
        outlier_tables.append(outliers)
        to_processed(frame).to_parquet(processed_root / f"{asset}.parquet")
    pd.concat(missing_tables, ignore_index=True).to_csv(audit_root / "missing_days.csv", index=False)
    all_outliers = pd.concat(outlier_tables, ignore_index=True)
    all_outliers.to_csv(audit_root / "return_outliers.csv", index=False)
    lines = [
        "# Data Audit Report — Frozen v1",
        "",
        "Signal and return prices use adjusted prices. Raw snapshots remain unchanged.",
        "Return outliers above 30% are reported and are not automatically deleted.",
        "",
        "| Asset | Start | End | Rows | Missing exchange days | >30% outliers | SHA-256 |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['asset']} | {item['start']} | {item['end']} | {item['rows']} | "
            f"{item['missing_exchange_days']} | {item['return_outliers_over_30pct']} | `{item['raw_sha256']}` |"
        )
    if len(all_outliers):
        lines += ["", "## Retained return outliers", "", "| Asset | Date | Adjusted return | Split | Review | Independent verification | Evidence |", "|---|---|---:|---:|---|---|---|"]
        for row in all_outliers.itertuples(index=False):
            lines.append(
                f"| {row.asset} | {pd.Timestamp(row.date).date()} | {row.daily_return:.2%} | {row.split:g} | "
                f"{row.review} | {row.independent_verification} | {row.evidence} |"
            )
    lines += ["", "Gate result: PASS" if not any(x["missing_exchange_days"] for x in summaries) else "Gate result: FAIL — missing exchange sessions"]
    (audit_root / "data_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if any(item["missing_exchange_days"] for item in summaries):
        raise ValueError("data audit gate failed: missing exchange sessions")
    return summaries
