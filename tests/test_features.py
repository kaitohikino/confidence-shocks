import numpy as np
import pandas as pd
import pytest

from confidence_shocks.features import KIND, METRICS, window_stats

COLUMNS = ["type", "x", "end_x", "pass_length", "pass_outcome", "shot_statsbomb_xg"]
COLUMNS += ["shot_outcome", "dribble_outcome"]


def _events(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLUMNS)


def test_counts_and_rates_on_a_hand_built_slice():
    df = _events(
        [
            {"type": "Pass", "x": 50, "end_x": 70, "pass_length": 20},
            {"type": "Pass", "x": 50, "end_x": 40, "pass_length": 10, "pass_outcome": "Incomplete"},
            {"type": "Ball Receipt*"},
            {"type": "Shot", "shot_statsbomb_xg": 0.25, "shot_outcome": "Goal"},
            {"type": "Dribble", "dribble_outcome": "Complete"},
        ]
    )
    stats = window_stats(df)
    assert stats["passes"] == 2
    assert stats["receipts"] == 1
    assert stats["shots"] == 1
    assert stats["fwd_pass_share"] == pytest.approx(0.5)
    assert stats["pass_length"] == pytest.approx(15)
    assert stats["pass_cmp"] == pytest.approx(0.5)
    assert stats["xg_per_shot"] == pytest.approx(0.25)
    assert stats["goals_minus_xg"] == pytest.approx(0.75)
    assert stats["dribble_win"] == pytest.approx(1.0)


def test_rates_are_nan_not_zero_when_there_is_nothing_to_average():
    stats = window_stats(_events([{"type": "Pressure"}]))
    assert stats["pressures"] == 1
    assert stats["passes"] == 0
    assert np.isnan(stats["pass_cmp"])
    assert np.isnan(stats["xg_per_shot"])


def test_every_metric_is_classified():
    assert set(KIND) == set(METRICS)
    assert set(KIND.values()) == {"involvement", "choice", "execution"}
