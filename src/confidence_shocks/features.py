"""From events to attributes: summarise any slice of events into choice and execution metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Volumes: compared with teammates per player (pooled teammate count / N_TEAMMATES).
COUNTS = ["receipts", "passes", "carries", "pressures", "shots", "dribbles"]
# Averages over passes: compared with the pooled teammates' average directly.
RATES = ["fwd_pass_share", "pass_length", "pass_cmp"]
METRICS = COUNTS + RATES

# The split the whole project is organised around.
KIND = {
    "receipts": "involvement",
    "passes": "involvement",
    "carries": "involvement",
    "pressures": "involvement",
    "shots": "choice",
    "dribbles": "choice",
    "fwd_pass_share": "choice",
    "pass_length": "choice",
    "pass_cmp": "execution",
}

N_TEAMMATES = 10


def window_stats(df: pd.DataFrame) -> dict[str, float]:
    """Summarise a slice of tidy events (one player, or a pooled group of players)."""
    kind = df["type"]
    passes = df[kind == "Pass"]
    shots = df[kind == "Shot"]
    dribbles = df[kind == "Dribble"]
    has_pass, has_shot, has_dribble = len(passes) > 0, len(shots) > 0, len(dribbles) > 0
    return {
        # involvement
        "receipts": float((kind == "Ball Receipt*").sum()),
        "passes": float(len(passes)),
        "carries": float((kind == "Carry").sum()),
        "pressures": float((kind == "Pressure").sum()),
        # choices: what does he try?
        "shots": float(len(shots)),
        "dribbles": float(len(dribbles)),
        "fwd_pass_share": float((passes["end_x"] > passes["x"]).mean()) if has_pass else np.nan,
        "pass_length": float(passes["pass_length"].mean()) if has_pass else np.nan,
        "xg_per_shot": float(shots["shot_statsbomb_xg"].mean()) if has_shot else np.nan,
        # execution: how well does it come off?
        "pass_cmp": float(passes["pass_outcome"].isna().mean()) if has_pass else np.nan,
        "dribble_win": (
            float((dribbles["dribble_outcome"] == "Complete").mean()) if has_dribble else np.nan
        ),
        "goals_minus_xg": float(
            (shots["shot_outcome"] == "Goal").sum() - shots["shot_statsbomb_xg"].sum()
        ),
    }
