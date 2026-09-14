"""Phase 8B-1: frozen pairwise OOS statistical inference.

This module consumes only the accepted Phase 8A aligned daily return file.
The comparison set, frequencies, seed, replication count, block lengths and
HAC lag rule are constants so that inference cannot become a selection loop.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import erfc, sqrt
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

PHASE8A_SOURCE_RUN_ID = "20260914_phase8a_oos_evidence_consolidation_final"
PHASE8A_RUN = PROJECT_ROOT / "reports/runs" / PHASE8A_SOURCE_RUN_ID
PHASE8A_DAILY_RETURNS = PHASE8A_RUN / "aligned_daily_returns.csv"
PHASE8A_CHAMPION = PHASE8A_RUN / "oos_champion_table.csv"
EXPECTED_PHASE8A_DAILY_RETURNS_SHA256 = "0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4"
EXPECTED_PHASE8A_CHAMPION_SHA256 = "718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af"

OOS_START = pd.Timestamp("2013-01-02")
OOS_END = pd.Timestamp("2026-08-31")
EXPECTED_SESSIONS = 3_436
INITIAL_CAPITAL = 100_000.0
TRADING_DAYS_PER_YEAR = 252.0

# Frozen before any inference output is inspected.
BOOTSTRAP_SEED = 8301
BOOTSTRAP_REPLICATIONS = 10_000
PRIMARY_BLOCK_LENGTH = 20
SENSITIVITY_BLOCK_LENGTHS = (5, 10, 40, 60)
BLOCK_LENGTHS = (5, 10, 20, 40, 60)
BOOTSTRAP_CHUNK_SIZE = 250
CONFIDENCE_LEVEL = 0.95

FREQUENCIES = ("weekly", "monthly", "bimonthly", "quarterly")

# These are the complete, frozen pairwise questions for Phase 8B-1.
PAIRWISE_COMPARISONS = (
    {
        "comparison_id": "A_FIXED_MA200_VS_QQQ",
        "comparison_label": "Fixed MA200 QQQ→QLD/CASH vs QQQ buy-and-hold",
        "strategy_id": "FIXED_MA200_QQQ_TO_QLD",
        "benchmark_id": "QQQ_BUY_HOLD",
        "benchmark_frequency": "none",
    },
    {
        "comparison_id": "B_PHASE7A_VS_QQQ",
        "comparison_label": "Phase 7A fixed four-state vs QQQ buy-and-hold",
        "strategy_id": "PHASE7A_FIXED_FOUR_STATE",
        "benchmark_id": "QQQ_BUY_HOLD",
        "benchmark_frequency": "none",
    },
    {
        "comparison_id": "C_PHASE7A_INCREMENTAL_VS_FIXED",
        "comparison_label": "Phase 7A fixed four-state vs Fixed MA200 QQQ→QLD/CASH",
        "strategy_id": "PHASE7A_FIXED_FOUR_STATE",
        "benchmark_id": "FIXED_MA200_QQQ_TO_QLD",
        "benchmark_frequency": "same_frequency",
    },
    {
        "comparison_id": "D_PHASE7B_MODEL_A_VS_FIXED",
        "comparison_label": "Phase 7B Model A selected WF vs Fixed MA200 QQQ→QLD/CASH",
        "strategy_id": "PHASE7B_MODEL_A_SELECTED",
        "benchmark_id": "FIXED_MA200_QQQ_TO_QLD",
        "benchmark_frequency": "same_frequency",
    },
    {
        "comparison_id": "E_PHASE7B_MODEL_B_VS_MODEL_A",
        "comparison_label": "Phase 7B Model B selected WF vs Model A selected WF",
        "strategy_id": "PHASE7B_MODEL_B_SELECTED",
        "benchmark_id": "PHASE7B_MODEL_A_SELECTED",
        "benchmark_frequency": "same_frequency",
    },
)

METRICS = (
    "annualized_mean_return_difference",
    "annualized_volatility_difference",
    "sharpe_difference",
    "cagr_difference",
    "max_drawdown_difference",
    "calmar_difference",
)

PRIOR_PHASE8B1_RUN_ID = "20260914_phase8b1_pairwise_inference_final"
PRIOR_PHASE8B1_RUN = PROJECT_ROOT / "reports/runs" / PRIOR_PHASE8B1_RUN_ID


def _normal_sf(value: float) -> float:
    """Standard-normal survival function without adding a runtime dependency."""
    return float(0.5 * erfc(value / sqrt(2.0)))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cagr(returns: np.ndarray, *, start: pd.Timestamp = OOS_START, end: pd.Timestamp = OOS_END) -> float:
    calendar_days = int((end - start).days)
    ending = INITIAL_CAPITAL * float(np.prod(1.0 + returns, dtype=np.float64))
    return float((ending / INITIAL_CAPITAL) ** (365.25 / calendar_days) - 1.0)


def _max_drawdown(returns: np.ndarray) -> float:
    equity = INITIAL_CAPITAL * np.cumprod(1.0 + returns, dtype=np.float64)
    augmented = np.concatenate(([INITIAL_CAPITAL], equity))
    running_peak = np.maximum.accumulate(augmented)
    return float(np.min(augmented[1:] / running_peak[1:] - 1.0))


def _calmar(cagr: float, max_drawdown: float) -> float:
    return float(cagr / abs(max_drawdown)) if max_drawdown < 0.0 else np.nan


def _path_metrics(strategy_returns: np.ndarray, benchmark_returns: np.ndarray) -> dict[str, float]:
    strategy_mean = float(np.mean(strategy_returns))
    benchmark_mean = float(np.mean(benchmark_returns))
    strategy_vol = float(np.std(strategy_returns, ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    benchmark_vol = float(np.std(benchmark_returns, ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    strategy_sharpe = float(strategy_mean * np.sqrt(TRADING_DAYS_PER_YEAR) / np.std(strategy_returns, ddof=1)) if strategy_vol > 0 else np.nan
    benchmark_sharpe = float(benchmark_mean * np.sqrt(TRADING_DAYS_PER_YEAR) / np.std(benchmark_returns, ddof=1)) if benchmark_vol > 0 else np.nan
    strategy_cagr = _cagr(strategy_returns)
    benchmark_cagr = _cagr(benchmark_returns)
    strategy_maxdd = _max_drawdown(strategy_returns)
    benchmark_maxdd = _max_drawdown(benchmark_returns)
    strategy_calmar = _calmar(strategy_cagr, strategy_maxdd)
    benchmark_calmar = _calmar(benchmark_cagr, benchmark_maxdd)
    return {
        "strategy_daily_mean": strategy_mean,
        "benchmark_daily_mean": benchmark_mean,
        "annualized_mean_return_difference": (strategy_mean - benchmark_mean) * TRADING_DAYS_PER_YEAR,
        "strategy_annualized_volatility": strategy_vol,
        "benchmark_annualized_volatility": benchmark_vol,
        "annualized_volatility_difference": strategy_vol - benchmark_vol,
        "strategy_sharpe": strategy_sharpe,
        "benchmark_sharpe": benchmark_sharpe,
        "sharpe_difference": strategy_sharpe - benchmark_sharpe if pd.notna(strategy_sharpe) and pd.notna(benchmark_sharpe) else np.nan,
        "strategy_cagr": strategy_cagr,
        "benchmark_cagr": benchmark_cagr,
        "cagr_difference": strategy_cagr - benchmark_cagr,
        "strategy_max_drawdown": strategy_maxdd,
        "benchmark_max_drawdown": benchmark_maxdd,
        "max_drawdown_difference": strategy_maxdd - benchmark_maxdd,
        "strategy_calmar": strategy_calmar,
        "benchmark_calmar": benchmark_calmar,
        "calmar_difference": strategy_calmar - benchmark_calmar if pd.notna(strategy_calmar) and pd.notna(benchmark_calmar) else np.nan,
    }


def stationary_bootstrap_indices(
    n_obs: int,
    n_replications: int,
    expected_block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate Politis–Romano stationary-bootstrap indices.

    Each position continues the previous circular block with probability
    ``1 - 1/L`` and starts a new uniformly sampled block with probability
    ``1/L``. One returned index matrix is applied to both members of a pair.
    """
    if n_obs <= 0 or n_replications <= 0 or expected_block_length <= 0:
        raise ValueError("stationary-bootstrap dimensions must be positive")
    indices = np.empty((n_replications, n_obs), dtype=np.int32)
    indices[:, 0] = rng.integers(0, n_obs, size=n_replications, dtype=np.int32)
    restart_probability = 1.0 / float(expected_block_length)
    for column in range(1, n_obs):
        restart = rng.random(n_replications) < restart_probability
        fresh = rng.integers(0, n_obs, size=n_replications, dtype=np.int32)
        continuation = (indices[:, column - 1] + 1) % n_obs
        indices[:, column] = np.where(restart, fresh, continuation)
    return indices


def _batch_pair_statistics(
    strategy_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    indices: np.ndarray,
) -> dict[str, np.ndarray]:
    """Calculate all path statistics for one shared-index bootstrap chunk."""
    strategy = strategy_returns[indices]
    benchmark = benchmark_returns[indices]
    difference = strategy - benchmark
    strategy_mean = strategy.mean(axis=1)
    benchmark_mean = benchmark.mean(axis=1)
    strategy_std = strategy.std(axis=1, ddof=1)
    benchmark_std = benchmark.std(axis=1, ddof=1)
    strategy_vol = strategy_std * np.sqrt(TRADING_DAYS_PER_YEAR)
    benchmark_vol = benchmark_std * np.sqrt(TRADING_DAYS_PER_YEAR)
    strategy_sharpe = np.divide(
        strategy_mean * np.sqrt(TRADING_DAYS_PER_YEAR), strategy_std,
        out=np.full(len(strategy), np.nan), where=strategy_std > 0,
    )
    benchmark_sharpe = np.divide(
        benchmark_mean * np.sqrt(TRADING_DAYS_PER_YEAR), benchmark_std,
        out=np.full(len(benchmark), np.nan), where=benchmark_std > 0,
    )
    strategy_cagr = np.power(np.prod(1.0 + strategy, axis=1), 365.25 / (OOS_END - OOS_START).days) - 1.0
    benchmark_cagr = np.power(np.prod(1.0 + benchmark, axis=1), 365.25 / (OOS_END - OOS_START).days) - 1.0
    strategy_equity = INITIAL_CAPITAL * np.cumprod(1.0 + strategy, axis=1)
    benchmark_equity = INITIAL_CAPITAL * np.cumprod(1.0 + benchmark, axis=1)
    strategy_augmented = np.concatenate([np.full((len(strategy), 1), INITIAL_CAPITAL), strategy_equity], axis=1)
    benchmark_augmented = np.concatenate([np.full((len(benchmark), 1), INITIAL_CAPITAL), benchmark_equity], axis=1)
    strategy_dd = strategy_augmented / np.maximum.accumulate(strategy_augmented, axis=1) - 1.0
    benchmark_dd = benchmark_augmented / np.maximum.accumulate(benchmark_augmented, axis=1) - 1.0
    strategy_maxdd = strategy_dd[:, 1:].min(axis=1)
    benchmark_maxdd = benchmark_dd[:, 1:].min(axis=1)
    strategy_calmar = np.divide(strategy_cagr, np.abs(strategy_maxdd), out=np.full(len(strategy), np.nan), where=strategy_maxdd < 0)
    benchmark_calmar = np.divide(benchmark_cagr, np.abs(benchmark_maxdd), out=np.full(len(benchmark), np.nan), where=benchmark_maxdd < 0)
    return {
        "annualized_mean_return_difference": difference.mean(axis=1) * TRADING_DAYS_PER_YEAR,
        "annualized_volatility_difference": strategy_vol - benchmark_vol,
        "sharpe_difference": strategy_sharpe - benchmark_sharpe,
        "cagr_difference": strategy_cagr - benchmark_cagr,
        "max_drawdown_difference": strategy_maxdd - benchmark_maxdd,
        "calmar_difference": strategy_calmar - benchmark_calmar,
    }


def centered_null_bootstrap_means(
    difference: np.ndarray,
    indices: np.ndarray,
    *,
    observed_mean_daily: float | None = None,
) -> np.ndarray:
    """Return centered-null paired mean statistics for a shared index matrix.

    The boundary null is explicit: ``d0_t = d_t - observed_mean_daily``.
    The returned statistic is ``mean(d0_t[indices])`` for each replication.
    This path is intentionally separate from the ordinary uncentered paired
    bootstrap used for confidence intervals and path diagnostics.
    """
    difference = np.asarray(difference, dtype=float)
    indices = np.asarray(indices, dtype=np.int32)
    if difference.ndim != 1 or len(difference) == 0:
        raise ValueError("paired differences must be a non-empty one-dimensional array")
    if indices.ndim != 2 or indices.shape[1] != len(difference) or len(indices) == 0:
        raise ValueError("bootstrap indices must have shape (replications, len(difference))")
    if np.any(indices < 0) or np.any(indices >= len(difference)):
        raise ValueError("bootstrap indices are out of bounds")
    if not np.isfinite(difference).all():
        raise ValueError("paired differences must be finite")
    observed = float(np.mean(difference) if observed_mean_daily is None else observed_mean_daily)
    if not np.isfinite(observed):
        raise ValueError("observed mean daily difference must be finite")
    d0 = difference - observed
    return np.mean(d0[indices], axis=1, dtype=np.float64)


def one_sided_monte_carlo_p_value(
    observed_statistic: float,
    null_bootstrap_statistics: np.ndarray,
) -> float:
    """Finite-replication corrected one-sided bootstrap tail probability."""
    statistics = np.asarray(null_bootstrap_statistics, dtype=float)
    if statistics.ndim != 1 or len(statistics) == 0 or not np.isfinite(statistics).all():
        raise ValueError("null bootstrap statistics must be a non-empty finite vector")
    if not np.isfinite(observed_statistic):
        raise ValueError("observed statistic must be finite")
    exceedances = int(np.count_nonzero(statistics >= float(observed_statistic)))
    return float((1 + exceedances) / (len(statistics) + 1))


def centered_null_bootstrap_p_value(
    difference: np.ndarray,
    indices: np.ndarray,
    *,
    observed_mean_daily: float | None = None,
) -> float:
    """Compute the corrected one-sided p-value from the explicit centered null."""
    observed = float(np.mean(difference) if observed_mean_daily is None else observed_mean_daily)
    null_statistics = centered_null_bootstrap_means(
        difference,
        indices,
        observed_mean_daily=observed,
    )
    return one_sided_monte_carlo_p_value(observed, null_statistics)


def _seed_for_block(expected_block_length: int) -> int:
    return int(BOOTSTRAP_SEED + expected_block_length * 1_000_003)


def _bootstrap_pair(
    strategy_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    *,
    expected_block_length: int,
    n_replications: int = BOOTSTRAP_REPLICATIONS,
    seed: int | None = None,
    chunk_size: int = BOOTSTRAP_CHUNK_SIZE,
) -> tuple[dict[str, np.ndarray], str, float]:
    """Run one shared-index stationary bootstrap and return compact arrays."""
    if len(strategy_returns) != len(benchmark_returns):
        raise ValueError("paired series must have identical lengths")
    rng = np.random.default_rng(_seed_for_block(expected_block_length) if seed is None else seed)
    distributions = {metric: np.empty(n_replications, dtype=float) for metric in METRICS}
    digest = hashlib.sha256()
    cursor = 0
    while cursor < n_replications:
        count = min(chunk_size, n_replications - cursor)
        indices = stationary_bootstrap_indices(len(strategy_returns), count, expected_block_length, rng)
        digest.update(indices.tobytes())
        batch = _batch_pair_statistics(strategy_returns, benchmark_returns, indices)
        for metric in METRICS:
            distributions[metric][cursor:cursor + count] = batch[metric]
        cursor += count
    observed = _path_metrics(strategy_returns, benchmark_returns)
    return distributions, digest.hexdigest(), float(observed["annualized_mean_return_difference"])


def _paired_series(daily: pd.DataFrame, strategy_id: str, strategy_frequency: str, benchmark_id: str, benchmark_frequency: str) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    strategy = daily.loc[
        daily.strategy_id.eq(strategy_id)
        & daily.frequency.eq(strategy_frequency)
        & daily.tax_mode.eq("pre_tax")
    ].sort_values("date")
    benchmark_tax_mode = "benchmark" if benchmark_id.endswith("BUY_HOLD") else "pre_tax"
    benchmark = daily.loc[
        daily.strategy_id.eq(benchmark_id)
        & daily.frequency.eq(benchmark_frequency)
        & daily.tax_mode.eq(benchmark_tax_mode)
    ].sort_values("date")
    if len(strategy) != EXPECTED_SESSIONS or len(benchmark) != EXPECTED_SESSIONS:
        raise AssertionError(f"unexpected paired lengths for {strategy_id}/{strategy_frequency} vs {benchmark_id}/{benchmark_frequency}")
    dates = pd.DatetimeIndex(strategy.date)
    benchmark_dates = pd.DatetimeIndex(benchmark.date)
    if not dates.equals(benchmark_dates):
        raise AssertionError("paired dates differ")
    if len(dates) != EXPECTED_SESSIONS or dates[0] != OOS_START or dates[-1] != OOS_END or dates.has_duplicates:
        raise AssertionError("paired date calendar is not the frozen OOS calendar")
    return strategy.daily_return.to_numpy(dtype=float), benchmark.daily_return.to_numpy(dtype=float), dates


def _benchmark_frequency(comparison: dict[str, str], frequency: str) -> str:
    return "none" if comparison["benchmark_frequency"] == "none" else frequency


def _observed_rows(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for comparison in PAIRWISE_COMPARISONS:
        for frequency in FREQUENCIES:
            benchmark_frequency = _benchmark_frequency(comparison, frequency)
            strategy, benchmark, dates = _paired_series(
                daily, comparison["strategy_id"], frequency,
                comparison["benchmark_id"], benchmark_frequency,
            )
            metrics = _path_metrics(strategy, benchmark)
            rows.append({
                "comparison_id": comparison["comparison_id"],
                "comparison_label": comparison["comparison_label"],
                "strategy_id": comparison["strategy_id"],
                "strategy_frequency": frequency,
                "benchmark_id": comparison["benchmark_id"],
                "benchmark_frequency": benchmark_frequency,
                "tax_mode": "pre_tax",
                "start_date": dates[0].date().isoformat(),
                "end_date": dates[-1].date().isoformat(),
                "n_sessions": len(dates),
                **metrics,
                "primary_inference_metric": "annualized_mean_return_difference",
                "primary_block_length": PRIMARY_BLOCK_LENGTH,
                "bootstrap_replications": BOOTSTRAP_REPLICATIONS,
            })
    return pd.DataFrame(rows)


def _bootstrap_rows(daily: pd.DataFrame, observed: pd.DataFrame, n_replications: int = BOOTSTRAP_REPLICATIONS) -> tuple[pd.DataFrame, dict[int, str]]:
    rows: list[dict[str, object]] = []
    checksums: dict[int, str] = {}
    pair_series: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]] = {}
    for comparison in PAIRWISE_COMPARISONS:
        for frequency in FREQUENCIES:
            benchmark_frequency = _benchmark_frequency(comparison, frequency)
            pair_series[(comparison["comparison_id"], frequency)] = _paired_series(
                daily, comparison["strategy_id"], frequency,
                comparison["benchmark_id"], benchmark_frequency,
            )
    for block_length in BLOCK_LENGTHS:
        # Generate one index stream per block length. The exact same matrices
        # are applied to both members of every pair and reused across all 20
        # comparisons, making the common-random-number construction explicit.
        rng = np.random.default_rng(_seed_for_block(block_length))
        observed_mean_daily_by_key = {
            key: float(np.mean(strategy - benchmark))
            for key, (strategy, benchmark, _) in pair_series.items()
        }
        null_exceedance_counts = {key: 0 for key in pair_series}
        distributions = {
            key: {metric: np.empty(n_replications, dtype=float) for metric in METRICS}
            for key in pair_series
        }
        digest = hashlib.sha256()
        cursor = 0
        while cursor < n_replications:
            count = min(BOOTSTRAP_CHUNK_SIZE, n_replications - cursor)
            indices = stationary_bootstrap_indices(EXPECTED_SESSIONS, count, block_length, rng)
            digest.update(indices.tobytes())
            for key, (strategy, benchmark, _) in pair_series.items():
                batch = _batch_pair_statistics(strategy, benchmark, indices)
                for metric in METRICS:
                    distributions[key][metric][cursor:cursor + count] = batch[metric]
                # The primary one-sided test has its own explicit boundary-null
                # path. It is intentionally not derived from the uncentered
                # strategy/benchmark metric distribution used for CIs.
                difference = strategy - benchmark
                observed_mean_daily = observed_mean_daily_by_key[key]
                null_statistics = centered_null_bootstrap_means(
                    difference,
                    indices,
                    observed_mean_daily=observed_mean_daily,
                )
                null_exceedance_counts[key] += int(np.count_nonzero(null_statistics >= observed_mean_daily))
            cursor += count
        checksum = digest.hexdigest()
        checksums[block_length] = checksum
        for comparison in PAIRWISE_COMPARISONS:
            for frequency in FREQUENCIES:
                key = (comparison["comparison_id"], frequency)
                strategy, benchmark, dates = pair_series[key]
                pair_distribution = distributions[key]
                observed_row = observed.loc[
                    observed.comparison_id.eq(comparison["comparison_id"])
                    & observed.strategy_frequency.eq(frequency)
                ].iloc[0]
                observed_mean_daily = observed_mean_daily_by_key[key]
                null_exceedances = null_exceedance_counts[key]
                null_p = float((1 + null_exceedances) / (n_replications + 1))
                benchmark_frequency = _benchmark_frequency(comparison, frequency)
                for metric in METRICS:
                    values = pair_distribution[metric]
                    finite = values[np.isfinite(values)]
                    probability_gt_zero = (
                        float(np.mean(finite > 0.0))
                        if metric != "max_drawdown_difference" and len(finite)
                        else np.nan
                    )
                    probability_maxdd = float(np.mean(values >= 0.0)) if metric == "max_drawdown_difference" else np.nan
                    ci_lower = float(np.quantile(finite, (1.0 - CONFIDENCE_LEVEL) / 2.0)) if len(finite) else np.nan
                    ci_upper = float(np.quantile(finite, 1.0 - (1.0 - CONFIDENCE_LEVEL) / 2.0)) if len(finite) else np.nan
                    rows.append({
                        "comparison_id": comparison["comparison_id"],
                        "comparison_label": comparison["comparison_label"],
                        "strategy_id": comparison["strategy_id"],
                        "strategy_frequency": frequency,
                        "benchmark_id": comparison["benchmark_id"],
                        "benchmark_frequency": benchmark_frequency,
                        "tax_mode": "pre_tax",
                        "start_date": dates[0].date().isoformat(),
                        "end_date": dates[-1].date().isoformat(),
                        "n_sessions": len(dates),
                        "metric": metric,
                        "observed_difference": float(observed_row[metric]),
                        "ci_lower_95": ci_lower,
                        "ci_upper_95": ci_upper,
                        "probability_difference_gt_zero": probability_gt_zero,
                        "probability_strategy_maxdd_ge_benchmark": probability_maxdd,
                        "one_sided_return_null_p_value": null_p if metric == "annualized_mean_return_difference" else np.nan,
                        "null_observed_mean_daily": observed_mean_daily if metric == "annualized_mean_return_difference" else np.nan,
                        "null_bootstrap_exceedance_count": null_exceedances if metric == "annualized_mean_return_difference" else np.nan,
                        "null_bootstrap_statistic": "mean((d - observed_mean_daily)[indices])" if metric == "annualized_mean_return_difference" else np.nan,
                        "null_p_value_correction": "(1 + count(null_bootstrap_stat >= observed_mean_daily)) / (B + 1)" if metric == "annualized_mean_return_difference" else np.nan,
                        "null_definition": "H0: expected paired excess return <= 0; H1: > 0; d0_t = d_t - observed_mean_daily" if metric == "annualized_mean_return_difference" else "path/ratio bootstrap diagnostic",
                        "bootstrap_method": "stationary_bootstrap_politis_romano",
                        "expected_block_length": block_length,
                        "block_role": "PRIMARY" if block_length == PRIMARY_BLOCK_LENGTH else "SENSITIVITY",
                        "bootstrap_replications": n_replications,
                        "random_seed": BOOTSTRAP_SEED,
                        "bootstrap_index_sha256": checksum,
                    })
    return pd.DataFrame(rows), checksums


def _hac_mean_return_rows(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for comparison in PAIRWISE_COMPARISONS:
        for frequency in FREQUENCIES:
            benchmark_frequency = _benchmark_frequency(comparison, frequency)
            strategy, benchmark, dates = _paired_series(
                daily, comparison["strategy_id"], frequency,
                comparison["benchmark_id"], benchmark_frequency,
            )
            difference = strategy - benchmark
            n_obs = len(difference)
            lag = int(np.floor(4.0 * (n_obs / 100.0) ** (2.0 / 9.0)))
            mean_daily = float(np.mean(difference))
            centered = difference - mean_daily
            long_run_variance = float(np.mean(centered * centered))
            for k in range(1, lag + 1):
                autocovariance = float(np.mean(centered[k:] * centered[:-k]))
                long_run_variance += 2.0 * (1.0 - k / (lag + 1.0)) * autocovariance
            long_run_variance = max(0.0, long_run_variance)
            standard_error_daily = float(np.sqrt(long_run_variance / n_obs))
            t_stat = float(mean_daily / standard_error_daily) if standard_error_daily > 0 else (np.inf if mean_daily > 0 else 0.0)
            p_value = _normal_sf(t_stat) if np.isfinite(t_stat) else (0.0 if t_stat > 0 else 1.0)
            rows.append({
                "comparison_id": comparison["comparison_id"],
                "comparison_label": comparison["comparison_label"],
                "strategy_id": comparison["strategy_id"],
                "strategy_frequency": frequency,
                "benchmark_id": comparison["benchmark_id"],
                "benchmark_frequency": benchmark_frequency,
                "tax_mode": "pre_tax",
                "start_date": dates[0].date().isoformat(),
                "end_date": dates[-1].date().isoformat(),
                "n_sessions": n_obs,
                "mean_daily_difference": mean_daily,
                "hac_lag": lag,
                "hac_standard_error_daily": standard_error_daily,
                "annualized_mean_return_difference": mean_daily * TRADING_DAYS_PER_YEAR,
                "annualized_hac_standard_error": standard_error_daily * TRADING_DAYS_PER_YEAR,
                "hac_t_statistic": t_stat,
                "one_sided_p_value": p_value,
                "hac_lag_rule": "floor(4 * (T / 100)^(2/9))",
                "hac_method": "Newey-West HAC variance of paired mean",
            })
    return pd.DataFrame(rows)


def _after_tax_descriptive_rows(champion: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def row_for(strategy_id: str, frequency: str, mode: str) -> pd.Series:
        match = champion.loc[
            champion.strategy_id.eq(strategy_id)
            & champion.frequency.eq(frequency)
            & champion.tax_mode.eq(mode)
        ]
        if len(match) != 1:
            raise AssertionError(f"missing Phase 8A champion row {strategy_id}/{frequency}/{mode}")
        return match.iloc[0]

    for comparison in PAIRWISE_COMPARISONS:
        for frequency in FREQUENCIES:
            benchmark_frequency = _benchmark_frequency(comparison, frequency)
            strategy = row_for(comparison["strategy_id"], frequency, "after_tax")
            benchmark_mode = "benchmark" if comparison["benchmark_id"].endswith("BUY_HOLD") else "after_tax"
            benchmark = row_for(comparison["benchmark_id"], benchmark_frequency, benchmark_mode)
            rows.append({
                "comparison_id": comparison["comparison_id"],
                "comparison_label": comparison["comparison_label"],
                "strategy_id": comparison["strategy_id"],
                "strategy_frequency": frequency,
                "benchmark_id": comparison["benchmark_id"],
                "benchmark_frequency": benchmark_frequency,
                "tax_mode": "after_tax_diagnostic",
                "start_date": str(strategy.start_date),
                "end_date": str(strategy.end_date),
                "after_tax_cagr_tax_paid_to_date_difference": float(strategy.after_tax_CAGR_tax_paid_to_date - benchmark.after_tax_CAGR_tax_paid_to_date),
                "terminal_liquidation_after_tax_cagr_difference": float(strategy.after_tax_CAGR_terminal_liquidation - benchmark.after_tax_CAGR_terminal_liquidation),
                "realized_tax_difference": float(strategy.realized_tax_paid - benchmark.realized_tax_paid),
                "strategy_after_tax_cagr_tax_paid_to_date": float(strategy.after_tax_CAGR_tax_paid_to_date),
                "benchmark_after_tax_cagr_tax_paid_to_date": float(benchmark.after_tax_CAGR_tax_paid_to_date),
                "strategy_terminal_liquidation_after_tax_cagr": float(strategy.after_tax_CAGR_terminal_liquidation),
                "benchmark_terminal_liquidation_after_tax_cagr": float(benchmark.after_tax_CAGR_terminal_liquidation),
                "strategy_realized_tax_paid": float(strategy.realized_tax_paid),
                "benchmark_realized_tax_paid": float(benchmark.realized_tax_paid),
                "descriptive_only": True,
                "terminal_liquidation_is_daily_return": False,
                "inference_performed": False,
            })
    return pd.DataFrame(rows)


def _load_inputs(phase8a_run: Path = PHASE8A_RUN) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if Path(phase8a_run).resolve() != PHASE8A_RUN.resolve():
        raise AssertionError(f"Phase 8B-1 accepts only the canonical Phase 8A run: {PHASE8A_SOURCE_RUN_ID}")
    daily_path = phase8a_run / "aligned_daily_returns.csv"
    champion_path = phase8a_run / "oos_champion_table.csv"
    actual_hash = _sha256(daily_path)
    if actual_hash != EXPECTED_PHASE8A_DAILY_RETURNS_SHA256:
        raise AssertionError(f"Phase 8A daily-return hash mismatch: {actual_hash}")
    champion_hash = _sha256(champion_path)
    if champion_hash != EXPECTED_PHASE8A_CHAMPION_SHA256:
        raise AssertionError(f"Phase 8A champion-table hash mismatch: {champion_hash}")
    daily = pd.read_csv(daily_path)
    daily["date"] = pd.to_datetime(daily.date)
    expected_dates = pd.DatetimeIndex(pd.date_range(OOS_START, OOS_END, freq="B"))
    # The accepted calendar excludes market holidays; use the benchmark row as
    # the immutable session authority and verify every identity against it.
    qqq_dates = pd.DatetimeIndex(daily.loc[daily.strategy_id.eq("QQQ_BUY_HOLD") & daily.tax_mode.eq("benchmark")].sort_values("date").date)
    if len(qqq_dates) != EXPECTED_SESSIONS or qqq_dates[0] != OOS_START or qqq_dates[-1] != OOS_END or qqq_dates.has_duplicates:
        raise AssertionError("Phase 8A QQQ benchmark calendar is not the accepted 3,436-session OOS calendar")
    del expected_dates
    for _, group in daily.groupby(["strategy_id", "frequency", "tax_mode"], sort=False):
        dates = pd.DatetimeIndex(group.sort_values("date").date)
        if not dates.equals(qqq_dates):
            raise AssertionError("Phase 8A aligned daily identities do not share the exact QQQ calendar")
    champion = pd.read_csv(champion_path)
    return daily, champion, actual_hash


def _configuration(index_checksums: dict[int, str], source_hash: str) -> dict[str, object]:
    return {
        "phase": "8B-1",
        "phase8a_source_run_id": PHASE8A_SOURCE_RUN_ID,
        "phase8a_aligned_daily_returns_sha256": source_hash,
        "phase8a_champion_table_sha256": EXPECTED_PHASE8A_CHAMPION_SHA256,
        "oos_start": OOS_START.date().isoformat(),
        "oos_end": OOS_END.date().isoformat(),
        "expected_sessions": EXPECTED_SESSIONS,
        "primary_tax_mode": "pre_tax",
        "random_seed": BOOTSTRAP_SEED,
        "bootstrap_replications": BOOTSTRAP_REPLICATIONS,
        "bootstrap_chunk_size": BOOTSTRAP_CHUNK_SIZE,
        "stationary_bootstrap": {
            "method": "Politis-Romano stationary bootstrap",
            "restart_probability": "1 / expected_block_length",
            "primary_expected_block_length": PRIMARY_BLOCK_LENGTH,
            "sensitivity_expected_block_lengths": list(SENSITIVITY_BLOCK_LENGTHS),
            "all_expected_block_lengths": list(BLOCK_LENGTHS),
            "same_indices_applied_to_pair_members": True,
            "index_sha256_by_block_length": {str(k): v for k, v in index_checksums.items()},
            "null_p_value": "explicitly resample d0_t = d_t - observed_mean_daily and count mean(d0_t[indices]) >= observed_mean_daily",
            "null_p_value_correction": "(1 + count(null_bootstrap_stat >= observed_stat)) / (B + 1)",
            "null_test": {
                "difference": "d_t = strategy_return_t - benchmark_return_t",
                "observed_statistic": "observed_mean_daily = mean(d_t)",
                "boundary_null_series": "d0_t = d_t - observed_mean_daily",
                "bootstrap_statistic": "null_bootstrap_mean_daily = mean(d0_t[indices])",
                "tail": "null_bootstrap_mean_daily >= observed_mean_daily",
                "monte_carlo_formula": "(1 + count(null_bootstrap_stat >= observed_stat)) / (B + 1)",
                "replication_count_symbol": "B",
                "uses_same_frozen_indices": True,
                "primary_metric_only": True,
            },
            "confidence_intervals": {
                "method": "ordinary uncentered paired stationary bootstrap",
                "centering_applied": False,
                "metrics": ["annualized_mean_return_difference", "sharpe_difference", "cagr_difference", "max_drawdown_difference", "calmar_difference"],
            },
        },
        "hac": {
            "lag_rule": "floor(4 * (T / 100)^(2/9))",
            "lag_for_3436_sessions": int(np.floor(4.0 * (EXPECTED_SESSIONS / 100.0) ** (2.0 / 9.0))),
            "method": "Newey-West HAC variance of paired daily mean",
            "role": "secondary cross-check only",
        },
        "annualization": {
            "arithmetic_mean_and_volatility": "252 trading sessions",
            "sharpe": "daily mean / daily sample standard deviation * sqrt(252), zero risk-free rate",
            "cagr": "canonical 365.25 / calendar-day exponent on the fixed OOS span",
        },
        "comparisons": [dict(item) for item in PAIRWISE_COMPARISONS],
        "selection_performed": False,
        "frequency_selection_performed": False,
        "winner_designation": False,
        "phase8b2_started": False,
    }


def _write_report(
    output: Path,
    observed: pd.DataFrame,
    bootstrap: pd.DataFrame,
    hac: pd.DataFrame,
    after_tax: pd.DataFrame,
    configuration: dict[str, object],
) -> None:
    primary = bootstrap.loc[
        bootstrap.expected_block_length.eq(PRIMARY_BLOCK_LENGTH)
        & bootstrap.metric.isin(("annualized_mean_return_difference", "sharpe_difference", "cagr_difference", "max_drawdown_difference", "calmar_difference"))
    ].copy()
    primary_view = primary[[
        "comparison_id", "strategy_frequency", "metric", "observed_difference",
        "ci_lower_95", "ci_upper_95", "probability_difference_gt_zero",
        "probability_strategy_maxdd_ge_benchmark", "one_sided_return_null_p_value",
    ]]
    hac_view = hac[[
        "comparison_id", "strategy_frequency", "mean_daily_difference", "hac_lag",
        "hac_standard_error_daily", "annualized_mean_return_difference",
        "annualized_hac_standard_error", "hac_t_statistic", "one_sided_p_value",
    ]]
    lines = [
        "# Phase 8B-1 — Frozen Pairwise OOS Statistical Inference",
        "",
        "This phase performs dependence-aware statistical inference on the already-frozen Phase 8A OOS evidence. It introduces no strategy, parameter, frequency, accounting, or execution change. No model or frequency is selected and no production winner is designated. Phase 8B-2 has not started.",
        "",
        "## Canonical input and frozen calendar",
        "",
        f"Input: `{PHASE8A_SOURCE_RUN_ID}/aligned_daily_returns.csv`. The verified SHA-256 is `{configuration['phase8a_aligned_daily_returns_sha256']}`. The paired calendar is **{OOS_START.date()} through {OOS_END.date()}**, exactly **{EXPECTED_SESSIONS:,}** sessions with no duplicate or missing identity/date rows.",
        "",
        f"Primary inference uses pre-tax daily returns. The arithmetic return and volatility annualization uses 252 trading sessions. CAGR keeps the audited 365.25/calendar-day convention. Cash-fallback zero-return sessions remain in the Model A and Model B series.",
        "",
        "## Frozen pairwise questions",
        "",
        "All five pre-frozen comparisons are run at weekly, monthly, bimonthly, and quarterly frequencies: A Fixed MA200 vs QQQ, B Phase 7A vs QQQ, C Phase 7A vs Fixed MA200, D Model A vs Fixed MA200, and E Model B vs Model A. This produces 20 comparison/frequency rows. No poor-performing comparison or frequency is removed.",
        "",
        "## Primary stationary bootstrap",
        "",
        f"For each pair, d_t = strategy return_t − benchmark return_t on the identical dates. The Politis–Romano stationary bootstrap uses seed **{BOOTSTRAP_SEED}**, **{BOOTSTRAP_REPLICATIONS:,}** replications, primary expected block length **{PRIMARY_BLOCK_LENGTH}**, and sensitivity lengths **{', '.join(map(str, SENSITIVITY_BLOCK_LENGTHS))}**. One shared index matrix is applied to both members of each pair. The primary one-sided return null test is an explicit centered-null path: observed_mean_daily = mean(d), d0_t = d_t − observed_mean_daily, and null_bootstrap_mean_daily = mean(d0_t[indices]). Its tail is null_bootstrap_mean_daily ≥ observed_mean_daily and its finite-replication p-value is (1 + count(null_bootstrap_stat ≥ observed_stat)) / (B + 1), with B = {BOOTSTRAP_REPLICATIONS:,}. Percentile 95% intervals are reported for mean return, Sharpe, and CAGR; MaxDD and Calmar intervals are explicitly path-dependent diagnostics.",
        "",
        "The null is H0: expected paired excess return ≤ 0 versus H1: expected paired excess return > 0. The centered series is used only for this one-sided null test. Ordinary percentile confidence intervals continue to use the uncentered paired strategy/benchmark bootstrap. A CAGR, Calmar, or drawdown interval is not relabeled as return evidence. Undefined Sharpe or Calmar values on zero-volatility/zero-drawdown CASH paths remain unavailable. No iid Student t-test is used as the primary method.",
        "",
        "### Primary block-length summary",
        "",
        primary_view.to_markdown(index=False),
        "",
        "## HAC cross-check",
        "",
        f"The secondary Newey–West HAC cross-check uses lag = floor(4 × (T / 100)^(2/9)) = {configuration['hac']['lag_for_3436_sessions']} for T = {EXPECTED_SESSIONS:,}. It reports the paired daily mean, HAC standard error, annualized mean difference, one-sided statistic, and p-value. Bootstrap results remain primary.",
        "",
        hac_view.to_markdown(index=False),
        "",
        "## After-tax evidence",
        "",
        "After-tax CAGR tax-paid-to-date, terminal-liquidation after-tax CAGR, and realized-tax differences are copied from Phase 8A as descriptive-only diagnostics. Terminal liquidation is not used as a daily return observation and receives no iid or bootstrap significance claim.",
        "",
        after_tax.to_markdown(index=False),
        "",
        "## Interpretation boundary",
        "",
        "The outputs distinguish descriptive economic outperformance, evidence for positive paired mean excess return, Sharpe evidence, drawdown/path evidence, tax impact, and incremental-complexity evidence. Frequency remains an experimental dimension. No frequency selection, parameter optimization, multiple-testing correction, Deflated Sharpe Ratio, White Reality Check, Hansen SPA, model research, or winner designation is performed in Phase 8B-1.",
        "",
        "The exact seed, index checksums, block lengths, replication count, source hash, lag rule, and software versions are in `bootstrap_configuration.json`.",
        "",
        "PHASE 8B-1 NULL-TEST REMEDIATION COMPLETE — AWAITING STATISTICAL AUDIT",
    ]
    (output / "phase8b1_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _max_numeric_difference(left: pd.DataFrame, right: pd.DataFrame, columns: list[str]) -> float:
    differences: list[float] = []
    for column in columns:
        left_values = pd.to_numeric(left[column], errors="coerce").to_numpy(dtype=float)
        right_values = pd.to_numeric(right[column], errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(left_values) & np.isfinite(right_values)
        if finite.any():
            differences.append(float(np.max(np.abs(left_values[finite] - right_values[finite]))))
        if np.any(np.isnan(left_values) != np.isnan(right_values)):
            differences.append(float("inf"))
    return max(differences, default=0.0)


def _write_remediation_audit_diff(output: Path, prior_output: Path) -> None:
    """Write the old→new statistical-remediation audit without touching inputs."""
    old_observed = pd.read_csv(prior_output / "pairwise_observed_metrics.csv")
    new_observed = pd.read_csv(output / "pairwise_observed_metrics.csv")
    old_bootstrap = pd.read_csv(prior_output / "stationary_bootstrap_results.csv")
    new_bootstrap = pd.read_csv(output / "stationary_bootstrap_results.csv")
    old_hac = pd.read_csv(prior_output / "hac_mean_return_results.csv")
    new_hac = pd.read_csv(output / "hac_mean_return_results.csv")
    old_config = json.loads((prior_output / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    new_config = json.loads((output / "bootstrap_configuration.json").read_text(encoding="utf-8"))

    observed_keys = ["comparison_id", "strategy_frequency"]
    observed_metric_columns = [
        "strategy_daily_mean", "benchmark_daily_mean", "annualized_mean_return_difference",
        "strategy_annualized_volatility", "benchmark_annualized_volatility",
        "annualized_volatility_difference", "strategy_sharpe", "benchmark_sharpe",
        "sharpe_difference", "strategy_cagr", "benchmark_cagr", "cagr_difference",
        "strategy_max_drawdown", "benchmark_max_drawdown", "max_drawdown_difference",
        "strategy_calmar", "benchmark_calmar", "calmar_difference",
    ]
    observed_join = old_observed[observed_keys + observed_metric_columns].merge(
        new_observed[observed_keys + observed_metric_columns],
        on=observed_keys,
        how="outer",
        suffixes=("_old", "_new"),
        validate="one_to_one",
    )
    observed_same = len(observed_join) == len(old_observed) == len(new_observed)
    observed_max_difference = 0.0
    if observed_same:
        for column in observed_metric_columns:
            observed_max_difference = max(
                observed_max_difference,
                _max_numeric_difference(
                    observed_join.rename(columns={f"{column}_old": column, f"{column}_new": f"{column}__new"}),
                    observed_join.rename(columns={f"{column}_new": column, f"{column}_old": f"{column}__old"}),
                    [column],
                ),
            )

    bootstrap_keys = ["comparison_id", "strategy_frequency", "expected_block_length", "metric"]
    ci_columns = ["ci_lower_95", "ci_upper_95"]
    ci_join = old_bootstrap[bootstrap_keys + ci_columns].merge(
        new_bootstrap[bootstrap_keys + ci_columns],
        on=bootstrap_keys,
        how="outer",
        suffixes=("_old", "_new"),
        validate="one_to_one",
    )
    ci_same = len(ci_join) == len(old_bootstrap) == len(new_bootstrap)
    ci_max_difference = 0.0
    if ci_same:
        for column in ci_columns:
            old_values = ci_join[f"{column}_old"].to_numpy(dtype=float)
            new_values = ci_join[f"{column}_new"].to_numpy(dtype=float)
            if not np.allclose(old_values, new_values, rtol=0.0, atol=1e-14, equal_nan=True):
                ci_same = False
            finite = np.isfinite(old_values) & np.isfinite(new_values)
            if finite.any():
                ci_max_difference = max(ci_max_difference, float(np.max(np.abs(old_values[finite] - new_values[finite]))))

    p_keys = ["comparison_id", "strategy_frequency", "expected_block_length"]
    p_old = old_bootstrap.loc[old_bootstrap.metric.eq("annualized_mean_return_difference"), p_keys + ["one_sided_return_null_p_value"]].rename(columns={"one_sided_return_null_p_value": "old_p_value"})
    p_new = new_bootstrap.loc[new_bootstrap.metric.eq("annualized_mean_return_difference"), p_keys + ["one_sided_return_null_p_value", "null_bootstrap_exceedance_count", "null_observed_mean_daily"]].rename(columns={"one_sided_return_null_p_value": "new_p_value"})
    p_table = p_old.merge(p_new, on=p_keys, how="outer", validate="one_to_one")
    p_table["p_value_delta"] = p_table["new_p_value"] - p_table["old_p_value"]
    p_table["changed"] = ~np.isclose(p_table["old_p_value"], p_table["new_p_value"], rtol=0.0, atol=0.0, equal_nan=True)
    p_table = p_table.sort_values(["expected_block_length", "comparison_id", "strategy_frequency"]).reset_index(drop=True)
    p_table_display = p_table[["comparison_id", "strategy_frequency", "expected_block_length", "old_p_value", "new_p_value", "p_value_delta", "null_bootstrap_exceedance_count"]].copy()
    for column in ("old_p_value", "new_p_value", "p_value_delta"):
        p_table_display[column] = p_table_display[column].map(lambda value: "" if pd.isna(value) else f"{float(value):.12f}")
    p_table_display["null_bootstrap_exceedance_count"] = p_table_display["null_bootstrap_exceedance_count"].map(lambda value: "" if pd.isna(value) else str(int(value)))

    old_index_hashes = old_config["stationary_bootstrap"]["index_sha256_by_block_length"]
    new_index_hashes = new_config["stationary_bootstrap"]["index_sha256_by_block_length"]
    index_hashes_same = old_index_hashes == new_index_hashes

    hac_keys = ["comparison_id", "strategy_frequency"]
    hac_columns = [column for column in old_hac.columns if column not in hac_keys]
    hac_join = old_hac.merge(new_hac, on=hac_keys, how="outer", suffixes=("_old", "_new"), validate="one_to_one")
    hac_same = len(hac_join) == len(old_hac) == len(new_hac)
    hac_max_difference = 0.0
    if hac_same:
        for column in hac_columns:
            old_column = hac_join[f"{column}_old"]
            new_column = hac_join[f"{column}_new"]
            if pd.api.types.is_numeric_dtype(old_column) and pd.api.types.is_numeric_dtype(new_column):
                old_values = old_column.to_numpy(dtype=float)
                new_values = new_column.to_numpy(dtype=float)
                finite = np.isfinite(old_values) & np.isfinite(new_values)
                if finite.any():
                    hac_max_difference = max(hac_max_difference, float(np.max(np.abs(old_values[finite] - new_values[finite]))))
                if np.any(np.isnan(old_values) != np.isnan(new_values)):
                    hac_same = False
            elif not old_column.astype("string").equals(new_column.astype("string")):
                hac_same = False

    phase8a_hashes_same = (
        new_config.get("phase8a_source_run_id") == PHASE8A_SOURCE_RUN_ID
        and new_config.get("phase8a_aligned_daily_returns_sha256") == EXPECTED_PHASE8A_DAILY_RETURNS_SHA256
        and new_config.get("phase8a_champion_table_sha256") == EXPECTED_PHASE8A_CHAMPION_SHA256
        and old_config.get("phase8a_source_run_id") == new_config.get("phase8a_source_run_id")
        and old_config.get("phase8a_aligned_daily_returns_sha256") == new_config.get("phase8a_aligned_daily_returns_sha256")
        and old_config.get("phase8a_champion_table_sha256") == new_config.get("phase8a_champion_table_sha256")
    )

    output_hashes = {
        name: _sha256(output / name)
        for name in (
            "pairwise_observed_metrics.csv",
            "stationary_bootstrap_results.csv",
            "hac_mean_return_results.csv",
            "after_tax_descriptive_comparisons.csv",
            "bootstrap_configuration.json",
            "phase8b1_report.md",
        )
    }
    lines = [
        "# Phase 8B-1 null-test remediation audit diff",
        "",
        f"This candidate run is `{output.name}`. The prior unaudited run `{prior_output.name}` is retained byte-for-byte for comparison. The correction is limited to the explicit centered-null implementation and finite-replication p-value reporting. No Phase 0–8A artifact or economic input was rewritten.",
        "",
        "## A. Invariant checks",
        "",
        f"- Observed paired metrics changed: **{not observed_same or observed_max_difference > 1e-14}**. Maximum numeric difference across the observed metric table: `{observed_max_difference:.3g}`.",
        f"- Ordinary uncentered percentile CIs changed: **{not ci_same}**. Maximum finite CI difference: `{ci_max_difference:.3g}`.",
        f"- Stationary-bootstrap index SHA-256 values changed: **{not index_hashes_same}**.",
        f"- Secondary HAC rows changed: **{not hac_same}**. Maximum finite numeric difference: `{hac_max_difference:.3g}`.",
        f"- Phase 8A source run and hashes remain unchanged: **{phase8a_hashes_same}**.",
        f"- Phase 0–8A artifacts changed: **False** (the candidate adds only a new Phase 8B-1 run; the canonical Phase 8A hashes above were re-verified).",
        "",
        "## B. Explicit null-test correction",
        "",
        "For each pair, the production code now constructs `d_t = strategy_return_t - benchmark_return_t`, `observed_mean_daily = mean(d_t)`, and `d0_t = d_t - observed_mean_daily`. The already-frozen index matrix for each block length is applied directly to `d0_t`; the null statistic is `mean(d0_t[indices])`. The reported one-sided p-value is `(1 + count(null_bootstrap_stat >= observed_stat)) / (B + 1)`, with B = 10,000. Ordinary percentile CIs remain on the ordinary uncentered paired strategy/benchmark bootstrap.",
        "",
        "The p-value table below includes every one of the 20 comparison/frequency rows for the primary block length and all four sensitivity block lengths. `null_bootstrap_exceedance_count` is the new explicit centered-null tail count.",
        "",
        p_table_display.to_markdown(index=False, disable_numparse=True),
        "",
        "## C. Frozen stream and provenance",
        "",
        f"- Seed: `{BOOTSTRAP_SEED}`; replications: `{new_config['bootstrap_replications']}`; primary block length: `{PRIMARY_BLOCK_LENGTH}`; sensitivities: `{', '.join(map(str, SENSITIVITY_BLOCK_LENGTHS))}`.",
        f"- Index SHA-256 values byte-identical to the prior run: **{index_hashes_same}**.",
        f"- Canonical Phase 8A daily input SHA-256: `{new_config['phase8a_aligned_daily_returns_sha256']}`.",
        f"- Canonical Phase 8A champion-table SHA-256: `{new_config['phase8a_champion_table_sha256']}`.",
        "",
        "## D. Candidate output hashes",
        "",
    ]
    lines.extend(f"- `{name}`: `{digest}`" for name, digest in output_hashes.items())
    lines.extend([
        "",
        "## E. Interpretation boundary",
        "",
        "This is a reporting/statistical-audit correction only. No model or frequency selection, multiple-testing correction, Phase 8B-2 work, or research-conclusion revision was performed. The candidate remains awaiting independent statistical audit.",
    ])
    (output / "phase8b1_audit_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *,
    phase8a_run: Path = PHASE8A_RUN,
    output_root: Path = PROJECT_ROOT / "reports/runs",
    run_id: str | None = None,
    n_replications: int = BOOTSTRAP_REPLICATIONS,
    prior_run: Path = PRIOR_PHASE8B1_RUN,
) -> Path:
    if n_replications < BOOTSTRAP_REPLICATIONS:
        raise ValueError("Phase 8B-1 requires at least 10,000 bootstrap replications")
    daily, champion, source_hash = _load_inputs(phase8a_run)
    output = output_root / (run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase8b1_pairwise_inference"))
    output.mkdir(parents=True, exist_ok=False)
    observed = _observed_rows(daily)
    bootstrap, checksums = _bootstrap_rows(daily, observed, n_replications=n_replications)
    hac = _hac_mean_return_rows(daily)
    after_tax = _after_tax_descriptive_rows(champion)
    configuration = _configuration(checksums, source_hash)
    configuration["bootstrap_replications"] = n_replications
    configuration["software_versions"] = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    observed.to_csv(output / "pairwise_observed_metrics.csv", index=False)
    bootstrap.to_csv(output / "stationary_bootstrap_results.csv", index=False)
    hac.to_csv(output / "hac_mean_return_results.csv", index=False)
    after_tax.to_csv(output / "after_tax_descriptive_comparisons.csv", index=False)
    (output / "bootstrap_configuration.json").write_text(json.dumps(configuration, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(output, observed, bootstrap, hac, after_tax, configuration)
    if prior_run.exists():
        _write_remediation_audit_diff(output, prior_run)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8B-1 frozen pairwise OOS inference")
    parser.add_argument("--phase8a-run", type=Path, default=PHASE8A_RUN)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--replications", type=int, default=BOOTSTRAP_REPLICATIONS)
    args = parser.parse_args()
    print(run(phase8a_run=args.phase8a_run, output_root=args.output_root, run_id=args.run_id, n_replications=args.replications))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
