from __future__ import annotations

import numpy as np
import pandas as pd

from l1.backtest import build_targets, simulate, summarize


def sample_prices(periods: int = 36) -> pd.DataFrame:
    dates = pd.date_range("2020-01-31", periods=periods, freq="ME")
    growth = np.linspace(100, 130, periods)
    return pd.DataFrame(
        {
            "SPY": growth,
            "VEA": growth * 0.6,
            "EEM": growth * 0.4,
            "IEF": np.linspace(90, 95, periods),
            "LQD": np.linspace(100, 103, periods),
            "GLD": np.linspace(120, 150, periods),
            "DBC": np.linspace(30, 28, periods),
            "BIL": np.linspace(90, 92, periods),
        },
        index=dates,
    )


def policy() -> dict[str, float]:
    return {
        "SPY": 0.2,
        "VEA": 0.1,
        "EEM": 0.1,
        "IEF": 0.2,
        "LQD": 0.15,
        "GLD": 0.1,
        "DBC": 0.05,
        "BIL": 0.1,
    }


def test_targets_are_long_only_and_fully_invested():
    prices = sample_prices()
    saa, taa = build_targets(
        prices,
        policy(),
        ["SPY", "VEA", "EEM"],
        lookback_months=10,
        equity_reduction=0.5,
    )
    for frame in (saa, taa):
        assert np.allclose(frame.sum(axis=1), 1.0)
        assert (frame >= 0).all().all()


def test_simulation_applies_costs_and_summarizes():
    prices = sample_prices()
    saa, taa = build_targets(
        prices,
        policy(),
        ["SPY", "VEA", "EEM"],
        lookback_months=10,
        equity_reduction=0.5,
    )
    returns = prices.pct_change().dropna()
    valid = taa.loc[returns.index].dropna().index
    history, contributions = simulate(returns.loc[valid], taa.loc[valid], cost_bps=10)
    assert (history["cost"] >= 0).all()
    assert contributions.shape == (len(valid), 8)
    metrics = summarize(history, "TAA")
    assert metrics["months"] == len(valid)
    assert metrics["max_drawdown"] <= 0


def test_signal_uses_prior_month_only():
    prices = sample_prices()
    _, taa = build_targets(
        prices,
        policy(),
        ["SPY", "VEA", "EEM"],
        lookback_months=10,
        equity_reduction=0.5,
    )
    # The first possible tactical decision needs ten completed returns plus one shift.
    first_non_base = (taa - pd.Series(policy(), dtype=float)).abs().sum(axis=1)
    assert (first_non_base.iloc[:10] == 0).all()
