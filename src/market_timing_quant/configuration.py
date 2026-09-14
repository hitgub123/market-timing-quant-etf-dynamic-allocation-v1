from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


EXPECTED = {
    "base_currency": "USD",
    "initial_capital": 100000,
    "excluded": ["SPMO", "semiconductor_etfs"],
}


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    for key, value in EXPECTED.items():
        if config.get(key) != value:
            raise ValueError(f"frozen configuration mismatch: {key}")
    if config["assets"] != {
        "benchmark": ["SPY", "QQQ"],
        "leveraged": ["SSO", "QLD", "TQQQ"],
        "risk_off": ["CASH"],
    }:
        raise ValueError("frozen asset universe mismatch")
    if config["cash"]["annual_return"] != 0.0:
        raise ValueError("cash annual return is frozen at zero")
    if config["portfolio"] != {
        "long_only": True,
        "external_margin": False,
        "max_total_weight": 1.0,
        "tqqq_max_weight": 0.20,
    }:
        raise ValueError("frozen portfolio constraints mismatch")
    if config["execution"] != {
        "signal_time": "close",
        "fill_time": "next_open",
        "slippage_bps": 5,
        "commission_bps": 0,
    }:
        raise ValueError("frozen execution parameters mismatch")
    if config["tax"] != {
        "capital_gains_rate": 0.20315,
        "cost_basis": "average",
        "payment_timing": "immediate",
    }:
        raise ValueError("frozen tax parameters mismatch")
    return config

