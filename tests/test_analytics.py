from __future__ import annotations

from pathlib import Path

import pandas as pd

from l1.analytics import save_risk_contribution


ROOT = Path(__file__).resolve().parents[1]


def test_risk_chart_writer():
    contribution = pd.Series(
        {"SPY": 0.4, "IEF": 0.25, "GLD": 0.2, "BIL": 0.15}
    )
    output = save_risk_contribution(contribution, ROOT / "tmp" / "risk.png")
    assert output.exists()
    assert output.stat().st_size > 1_000
