"""Monthly target construction and portfolio simulation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_research_frame(
    raw_prices: pd.DataFrame,
    tickers: list[str],
    evaluation_start: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Translate USD assets into HKD and build month-end prices and returns."""
    frame = raw_prices.copy()
    frame.index = pd.to_datetime(frame.index)
    fx = frame["USDHKD"].ffill()
    monthly_assets = frame[tickers].resample("ME").last()
    monthly_fx = fx.resample("ME").last()
    hkd_prices = monthly_assets.mul(monthly_fx, axis=0)
    returns = hkd_prices.pct_change().dropna()
    start = pd.Timestamp(evaluation_start)
    return hkd_prices.loc[start:], returns.loc[start:]


def build_targets(
    monthly_prices: pd.DataFrame,
    policy_weights: dict[str, float],
    equity_sleeves: list[str],
    lookback_months: int,
    equity_reduction: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create SAA and trend-TAA targets using information through the prior month."""
    columns = list(policy_weights)
    saa = pd.DataFrame(
        [policy_weights.values()],
        index=monthly_prices.index,
        columns=columns,
        dtype=float,
    )
    trend = monthly_prices[equity_sleeves].pct_change(lookback_months).shift(1)
    taa = saa.copy()
    for date in taa.index:
        if date not in trend.index or trend.loc[date].isna().any():
            continue
        target = taa.loc[date].copy()
        for ticker in equity_sleeves:
            if trend.loc[date, ticker] < 0:
                reduction = target[ticker] * equity_reduction
                target[ticker] -= reduction
                target["BIL"] += reduction
        taa.loc[date] = target
    return saa, taa


def simulate(
    returns: pd.DataFrame,
    targets: pd.DataFrame,
    cost_bps: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate monthly rebalancing with drifting weights and transaction costs."""
    if not returns.index.equals(targets.loc[returns.index].index):
        raise ValueError("Returns and target dates are not aligned.")
    rows: list[dict] = []
    contribution_rows: list[pd.Series] = []
    end_weights: pd.Series | None = None

    for date, asset_returns in returns.iterrows():
        target = targets.loc[date].astype(float)
        if not np.isclose(target.sum(), 1.0, atol=1e-9):
            raise ValueError(f"Target weights do not sum to one on {date.date()}.")
        if (target < -1e-12).any():
            raise ValueError(f"Negative target weight on {date.date()}.")

        opening_weights = target if end_weights is None else end_weights
        turnover = (
            0.0
            if end_weights is None
            else float((opening_weights - target).abs().sum() / 2)
        )
        gross_contributions = target * asset_returns
        gross_return = float(gross_contributions.sum())
        cost = turnover * cost_bps / 10_000
        net_return = gross_return - cost
        ending_values = target * (1 + asset_returns)
        end_weights = ending_values / ending_values.sum()

        rows.append(
            {
                "date": date,
                "gross_return": gross_return,
                "cost": cost,
                "net_return": net_return,
                "turnover": turnover,
                **{f"target_{key}": value for key, value in target.items()},
                **{f"end_{key}": value for key, value in end_weights.items()},
            }
        )
        contribution_rows.append(gross_contributions.rename(date))

    history = pd.DataFrame(rows).set_index("date")
    contributions = pd.DataFrame(contribution_rows)
    history["nav"] = (1 + history["net_return"]).cumprod()
    history["drawdown"] = history["nav"] / history["nav"].cummax() - 1
    return history, contributions


def summarize(
    history: pd.DataFrame,
    label: str,
    annual_risk_free: float = 0.0,
) -> dict[str, float | str]:
    """Return decision-relevant performance metrics."""
    monthly = history["net_return"]
    months = len(monthly)
    nav = float(history["nav"].iloc[-1])
    cagr = nav ** (12 / months) - 1
    volatility = float(monthly.std(ddof=0) * np.sqrt(12))
    sharpe = (
        float(((monthly.mean() - annual_risk_free / 12) * 12) / volatility)
        if volatility > 0
        else np.nan
    )
    downside = monthly[monthly < annual_risk_free / 12]
    downside_vol = float(downside.std(ddof=0) * np.sqrt(12)) if len(downside) else np.nan
    sortino = (
        float(((monthly.mean() - annual_risk_free / 12) * 12) / downside_vol)
        if downside_vol and downside_vol > 0
        else np.nan
    )
    max_drawdown = float(history["drawdown"].min())
    return {
        "label": label,
        "start": str(history.index.min().date()),
        "end": str(history.index.max().date()),
        "months": months,
        "ending_nav": round(nav, 4),
        "cagr": round(float(cagr), 4),
        "annual_volatility": round(volatility, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown": round(max_drawdown, 4),
        "average_turnover": round(float(history["turnover"].mean()), 4),
        "total_cost": round(float(history["cost"].sum()), 4),
    }
