# L1 Multi-Asset Shadow Portfolio

**From views to weights: a reproducible, public-data multi-asset portfolio
research case.**

This project combines strategic asset allocation, a transparent tactical trend
overlay, portfolio construction, currency translation, transaction costs, risk
analysis and return attribution.

**Live research case:** https://aayloo.github.io/l1-multi-asset-shadow/

It is a **paper research portfolio**. It is not a live account, does not contain
real PnL and is not investment advice.

## Research design

- 40% equities: SPY, VEA, EEM
- 35% fixed income and credit: IEF, LQD
- 10% gold: GLD
- 5% commodities: DBC
- 10% short-term bills: BIL
- Monthly rebalancing
- 10 bps cost per unit of one-way turnover
- 10-month trend rule applied to each equity sleeve
- Unhedged HKD translation from USD proxies
- Fixed evaluation start: June 2008

The static SAA is the primary comparator. A 60/40 proxy and equal-weight
portfolio are external references.

## Reproduce

```bash
python -m pip install -e ".[dev]"
python scripts/build_case.py
python -m pytest -q
python -m http.server 8000
```

Open <http://localhost:8000>.

The first build downloads adjusted closes from Yahoo Finance through
`yfinance`. Raw data is stored under the ignored `data/` directory and is not
redistributed.

## Artifacts

- `configs/policy_v1.json`: frozen investment policy
- `assets/data/results.json`: portfolio metrics and latest snapshot
- `assets/data/performance_history.csv`: monthly portfolio history
- `assets/data/latest_weights.csv`: latest weights
- `reports/2026-10.md`: decision memo
- `assets/img/`: performance, drawdown, allocation, risk and attribution charts

## Important limitations

- Paper portfolio only
- Adjusted-close approximation
- Flat transaction-cost assumption
- No market impact, tax or broker execution
- No claim of statistically significant alpha
- Public historical results do not guarantee future returns

See [DISCLAIMER.md](DISCLAIMER.md).
