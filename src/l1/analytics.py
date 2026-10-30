"""Risk, attribution and chart helpers for the L1 portfolio case."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "vermillion": "#D55E00",
    "pink": "#CC79A7",
    "sky": "#56B4E9",
    "ink": "#17324d",
    "muted": "#5f6f83",
    "grid": "#d6dde1",
    "paper": "#fbfcf8",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.family": "serif",
            "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.grid": True,
            "grid.color": PALETTE["grid"],
            "grid.linewidth": 0.55,
            "grid.alpha": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "legend.frameon": False,
        }
    )


def tidy_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(PALETTE["paper"])
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.55)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#9fb0bd")
    ax.tick_params(colors=PALETTE["muted"], labelsize=9)
    ax.xaxis.label.set_color(PALETTE["ink"])
    ax.yaxis.label.set_color(PALETTE["ink"])


def save_performance(
    series: dict[str, pd.Series],
    output_path: str | Path,
) -> Path:
    configure_style()
    fig, ax = plt.subplots(figsize=(9.2, 5.2), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    styles = [
        (PALETTE["ink"], "-"),
        (PALETTE["blue"], "-"),
        (PALETTE["orange"], "--"),
        (PALETTE["green"], "-."),
    ]
    for (label, nav), (color, linestyle) in zip(series.items(), styles):
        ax.plot(nav.index, nav, label=label, color=color, linestyle=linestyle, linewidth=1.8)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of HKD 1")
    ax.set_title("Figure 1 | Growth of HKD 1", loc="left", color=PALETTE["ink"], fontsize=12)
    ax.legend(ncol=2, loc="upper left")
    fig.text(
        0.01,
        0.01,
        "Source: public ETF adjusted closes translated to HKD; monthly returns after 10 bps cost.",
        fontsize=8,
        color=PALETTE["muted"],
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target


def save_risk_return_map(
    metrics: dict[str, dict],
    output_path: str | Path,
) -> Path:
    """Place portfolios on the full-sample risk/return plane."""
    configure_style()
    fig, ax = plt.subplots(figsize=(8.4, 4.9), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    styles = {
        "L1 SAA": (PALETTE["ink"], "o", (8, 10), "left"),
        "L1 TAA": (PALETTE["blue"], "s", (8, -16), "left"),
        "60/40": (PALETTE["orange"], "^", (8, 8), "left"),
        "Equal weight": (PALETTE["green"], "D", (8, -17), "left"),
    }
    for label, values in metrics.items():
        color, marker, offset, alignment = styles[label]
        x = values["annual_volatility"] * 100
        y = values["cagr"] * 100
        ax.scatter(
            x,
            y,
            s=62,
            marker=marker,
            color=color,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        ax.annotate(
            label,
            (x, y),
            xytext=offset,
            textcoords="offset points",
            ha=alignment,
            va="center",
            fontsize=9,
            color=color,
            fontweight="bold",
        )

    ax.set_xlabel("Annualised volatility (%)")
    ax.set_ylabel("Annualised return (%)")
    ax.set_xlim(7.0, 10.2)
    ax.set_ylim(4.8, 9.0)
    ax.set_title(
        "Figure 2 | Full-sample risk and return",
        loc="left",
        color=PALETTE["ink"],
        fontsize=12,
    )
    fig.text(
        0.01,
        0.01,
        "Source: public ETF data translated to HKD; monthly net returns after 10 bps cost.",
        fontsize=8,
        color=PALETTE["muted"],
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target


def save_allocation_history(
    history: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Show how grouped tactical target weights changed through the sample."""
    configure_style()
    groups = {
        "Equity": ["target_SPY", "target_VEA", "target_EEM"],
        "Fixed income & credit": ["target_IEF", "target_LQD"],
        "Real assets": ["target_GLD", "target_DBC"],
        "Cash": ["target_BIL"],
    }
    weights = pd.DataFrame(
        {label: history[columns].sum(axis=1) for label, columns in groups.items()},
        index=history.index,
    ).mul(100)
    colors = [PALETTE["ink"], PALETTE["sky"], PALETTE["green"], PALETTE["orange"]]

    fig, ax = plt.subplots(figsize=(9.2, 4.7), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    ax.stackplot(
        weights.index,
        [weights[column] for column in weights.columns],
        labels=weights.columns,
        colors=colors,
        alpha=0.94,
    )
    ax.axhline(40, color="white", linewidth=1.0, linestyle="--", alpha=0.9)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Target portfolio weight (%)")
    ax.set_title(
        "Figure 5 | Tactical allocation history",
        loc="left",
        color=PALETTE["ink"],
        fontsize=12,
    )
    ax.legend(loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.26))
    fig.text(
        0.01,
        0.01,
        "Source: L1 TAA month-end target weights; dashed line marks the 40% strategic equity allocation.",
        fontsize=8,
        color=PALETTE["muted"],
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target


def save_drawdown(drawdowns: dict[str, pd.Series], output_path: str | Path) -> Path:
    configure_style()
    fig, ax = plt.subplots(figsize=(9.2, 4.2), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["green"]]
    for (label, series), color in zip(drawdowns.items(), colors):
        ax.plot(series.index, series * 100, label=label, color=color, linewidth=1.6)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Figure 3 | Drawdown path", loc="left", color=PALETTE["ink"], fontsize=12)
    ax.legend(loc="lower left", ncol=3)
    fig.text(0.01, 0.01, "Source: tutorial calculations from public market data.", fontsize=8, color=PALETTE["muted"])
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target


def save_allocation(
    policy: pd.Series,
    current: pd.Series,
    output_path: str | Path,
) -> Path:
    configure_style()
    labels = list(policy.index)
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8.6, 4.8), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    ax.barh(y + 0.19, policy.loc[labels].to_numpy() * 100, height=0.34, color=PALETTE["sky"], label="Policy SAA")
    ax.barh(y - 0.19, current.loc[labels].to_numpy() * 100, height=0.34, color=PALETTE["green"], label="Current TAA")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Weight (%)")
    ax.set_title("Figure 4 | Policy versus current allocation", loc="left", color=PALETTE["ink"], fontsize=12)
    ax.legend(loc="lower right")
    fig.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target


def save_risk_contribution(contribution: pd.Series, output_path: str | Path) -> Path:
    configure_style()
    ordered = contribution.sort_values()
    colors = [PALETTE["vermillion"] if value < 0 else PALETTE["blue"] for value in ordered]
    fig, ax = plt.subplots(figsize=(8.2, 4.4), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    ax.barh(ordered.index, ordered * 100, color=colors)
    ax.axvline(0, color=PALETTE["muted"], linewidth=0.8)
    ax.set_xlabel("Share of portfolio variance (%)")
    ax.set_title("Figure 6 | Risk contribution by asset", loc="left", color=PALETTE["ink"], fontsize=12)
    fig.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target


def save_attribution(contribution: pd.Series, output_path: str | Path) -> Path:
    configure_style()
    ordered = contribution.sort_values()
    colors = [PALETTE["vermillion"] if value < 0 else PALETTE["green"] for value in ordered]
    fig, ax = plt.subplots(figsize=(8.2, 4.4), facecolor=PALETTE["paper"])
    tidy_axis(ax)
    ax.barh(ordered.index, ordered * 100, color=colors)
    ax.axvline(0, color=PALETTE["muted"], linewidth=0.8)
    ax.set_xlabel("Annualised return contribution (%)")
    ax.set_title("Figure 7 | Return attribution by asset sleeve", loc="left", color=PALETTE["ink"], fontsize=12)
    fig.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor=PALETTE["paper"])
    plt.close(fig)
    return target
