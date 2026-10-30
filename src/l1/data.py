"""Public market-data acquisition and currency translation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


TICKERS = ["SPY", "VEA", "EEM", "IEF", "LQD", "GLD", "DBC", "BIL"]
FX_TICKER = "HKD=X"


def download_prices(start: str = "2007-01-01") -> pd.DataFrame:
    """Download adjusted ETF closes and the USD/HKD exchange rate."""
    import yfinance as yf

    symbols = [*TICKERS, FX_TICKER]
    raw = yf.download(
        symbols,
        start=start,
        auto_adjust=True,
        actions=False,
        progress=False,
    )["Close"]
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns={FX_TICKER: "USDHKD"})
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    return raw[[*TICKERS, "USDHKD"]].sort_index().ffill().dropna(how="all")


def load_prices(cache_path: str | Path, refresh: bool = False) -> pd.DataFrame:
    """Load cached public prices or download and cache a fresh copy."""
    path = Path(cache_path)
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=["Date"], index_col="Date")

    prices = download_prices()
    path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(path, index_label="Date")
    return prices


def write_data_manifest(path: str | Path, prices: pd.DataFrame, config: dict) -> None:
    """Document the public-data boundary without redistributing raw files."""
    target = Path(path)
    manifest = {
        "source": "Yahoo Finance via yfinance",
        "price_field": "Adjusted close",
        "currency_translation": "USD asset prices multiplied by USD/HKD; unhedged HKD investor view",
        "start": str(prices.index.min().date()),
        "end": str(prices.index.max().date()),
        "rows": int(len(prices)),
        "tickers": config["tickers"],
        "raw_redistributed": False,
    }
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
