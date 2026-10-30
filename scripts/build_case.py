"""Build the reproducible multi-asset shadow-portfolio case."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from l1.analytics import (
    PALETTE,
    save_allocation,
    save_allocation_history,
    save_attribution,
    save_drawdown,
    save_performance,
    save_risk_return_map,
    save_risk_contribution,
)
from l1.backtest import build_targets, make_research_frame, simulate, summarize
from l1.data import load_prices, write_data_manifest


def constant_targets(
    weights: dict[str, float],
    index: pd.Index,
) -> pd.DataFrame:
    return pd.DataFrame([weights] * len(index), index=index, dtype=float)


def latest_signals(monthly_prices: pd.DataFrame, lookback: int) -> pd.Series:
    return monthly_prices[["SPY", "VEA", "EEM"]].pct_change(lookback).iloc[-1]


def main() -> None:
    config = json.loads((ROOT / "configs" / "policy_v1.json").read_text(encoding="utf-8"))
    tickers = list(config["tickers"])
    policy = config["policy_weights"]
    cost_bps = float(config["transaction_cost_bps"])

    raw = load_prices(ROOT / "data" / "public_prices.csv")
    monthly, returns = make_research_frame(
        raw,
        tickers,
        evaluation_start=config["evaluation_start"],
    )
    saa_targets, taa_targets = build_targets(
        monthly,
        policy,
        config["equity_sleeves"],
        config["trend_lookback_months"],
        config["tactical_equity_reduction"],
    )

    strategies = {
        "L1 SAA": saa_targets.loc[returns.index],
        "L1 TAA": taa_targets.loc[returns.index],
        "60/40": constant_targets(config["benchmark_weights"], returns.index),
        "Equal weight": constant_targets(
            {ticker: 1 / len(tickers) for ticker in tickers},
            returns.index,
        ),
    }

    histories: dict[str, pd.DataFrame] = {}
    contributions: dict[str, pd.DataFrame] = {}
    metrics: dict[str, dict] = {}
    for name, targets in strategies.items():
        history, attribution = simulate(returns, targets, cost_bps)
        histories[name] = history
        contributions[name] = attribution
        metrics[name] = summarize(history, name)

    taa_history = histories["L1 TAA"]
    taa_contributions = contributions["L1 TAA"]
    latest_weights = (
        taa_history.filter(like="end_")
        .iloc[-1]
        .rename(lambda value: value.removeprefix("end_"))
        .astype(float)
    )

    covariance = returns.tail(36).cov().loc[tickers, tickers]
    portfolio_variance = float(latest_weights @ covariance @ latest_weights)
    risk_contribution = (
        latest_weights * (covariance @ latest_weights) / portfolio_variance
    )
    annual_contribution = taa_contributions.mean() * 12

    yearly_returns = (
        taa_history["net_return"]
        .groupby(taa_history.index.year)
        .apply(lambda values: (1 + values).prod() - 1)
    )
    signals = latest_signals(monthly, int(config["trend_lookback_months"])).round(4)

    image_dir = ROOT / "assets" / "img"
    image_dir.mkdir(parents=True, exist_ok=True)
    save_performance(
        {name: history["nav"] for name, history in histories.items()},
        image_dir / "performance.png",
    )
    save_risk_return_map(metrics, image_dir / "risk-return.png")
    save_drawdown(
        {
            name: histories[name]["nav"] / histories[name]["nav"].cummax() - 1
            for name in ("L1 SAA", "L1 TAA", "60/40")
        },
        image_dir / "drawdown.png",
    )
    save_allocation(
        pd.Series(policy),
        latest_weights,
        image_dir / "allocation.png",
    )
    save_allocation_history(taa_history, image_dir / "allocation-history.png")
    save_risk_contribution(risk_contribution, image_dir / "risk-contribution.png")
    save_attribution(annual_contribution, image_dir / "return-attribution.png")

    data_dir = ROOT / "assets" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    taa_history.to_csv(data_dir / "performance_history.csv", index_label="date")
    latest_weights.rename("weight").to_csv(
        data_dir / "latest_weights.csv",
        index_label="ticker",
    )
    risk_contribution.rename("risk_contribution").to_csv(
        data_dir / "risk_contributions.csv",
        index_label="ticker",
    )
    write_data_manifest(ROOT / "assets" / "data" / "data_manifest.json", raw, config)

    results = {
        "as_of": str(taa_history.index.max().date()),
        "market_data_through": str(raw.index.max().date()),
        "start": str(taa_history.index.min().date()),
        "version": config["version"],
        "frozen_on": config["frozen_on"],
        "base_currency": config["base_currency"],
        "cost_bps": cost_bps,
        "metrics": metrics,
        "latest_weights": latest_weights.round(4).to_dict(),
        "policy_weights": policy,
        "risk_contribution": risk_contribution.round(4).to_dict(),
        "annual_return_contribution": annual_contribution.round(4).to_dict(),
        "signals": signals.to_dict(),
        "yearly_returns": {str(year): round(float(value), 4) for year, value in yearly_returns.items()},
        "ticker_labels": config["tickers"],
        "notes": {
            "return_basis": "Adjusted-close total return, translated from USD to HKD without hedging.",
            "rebalance": "Monthly rebalance; signals use information through the prior month-end.",
            "cost": f"{cost_bps} bps per unit of one-way turnover.",
            "classification": "Paper research portfolio; no real money or PnL.",
        },
    }
    (data_dir / "results.json").write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )
    (data_dir / "results.js").write_text(
        "window.PORTFOLIO_RESULTS = " + json.dumps(results, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
