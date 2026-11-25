"""Figures for the report. Functions take result tables and return a matplotlib Figure."""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure


def forest(estimates: dict[str, pd.DataFrame], title: str) -> Figure:
    """Effect per metric in SD units with 95% intervals. One series per entry in `estimates`."""
    metrics = next(iter(estimates.values()))["metric"].tolist()
    rows = np.arange(len(metrics))
    step = 0.3 / max(len(estimates) - 1, 1)

    # Figure() rather than pyplot: saves to file without needing a display or a global backend.
    fig = Figure(figsize=(8, 0.45 * len(metrics) + 1.5))
    ax = fig.subplots()
    for i, (label, table) in enumerate(estimates.items()):
        centre = table["effect_sd"].to_numpy()
        errors = [centre - table["lo_sd"].to_numpy(), table["hi_sd"].to_numpy() - centre]
        ax.errorbar(centre, rows + 0.15 - i * step, xerr=errors, fmt="o", capsize=3, label=label)

    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(rows)
    ax.set_yticklabels(metrics)
    ax.invert_yaxis()
    ax.set_xlabel("change after a goal vs. after a comparable non-goal (SDs, 95% interval)")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig
