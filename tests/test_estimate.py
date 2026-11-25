import numpy as np
import pandas as pd
import pytest

from confidence_shocks.estimate import att, benjamini_hochberg, select_controls


def _simulate(effect: float, n: int = 4000, seed: int = 0) -> pd.DataFrame:
    """Shots whose outcome is a fair xG-weighted coin flip, with a known effect of scoring."""
    rng = np.random.default_rng(seed)
    xg = rng.beta(1, 6, n)
    goal = rng.random(n) < xg
    # y depends on xG (a confounder if left unweighted) plus the true effect for goals.
    y = 5 * xg + effect * goal + rng.normal(0, 1, n)
    return pd.DataFrame({"y": y, "goal": goal, "xg": xg, "match_id": rng.integers(0, 200, n)})


def test_att_recovers_a_known_effect_despite_confounding_by_xg():
    df = _simulate(effect=1.0)
    naive = df.loc[df["goal"], "y"].mean() - df.loc[~df["goal"], "y"].mean()
    result = att(df["y"], df["goal"], df["xg"], df["match_id"], n_boot=500)
    assert naive > 1.3  # the unweighted comparison is badly biased upwards
    assert result["effect"] == pytest.approx(1.0, abs=0.2)
    assert 0.5 < result["lo"] < result["hi"] < 1.5
    assert result["p"] < 0.05


def test_att_reports_nothing_when_there_is_nothing():
    df = _simulate(effect=0.0, seed=1)
    result = att(df["y"], df["goal"], df["xg"], df["match_id"], n_boot=500)
    assert abs(result["effect"]) < 0.2
    assert result["lo"] < result["hi"]


def test_att_ignores_rows_with_missing_outcomes():
    df = _simulate(effect=1.0)
    df.loc[:99, "y"] = np.nan
    result = att(df["y"], df["goal"], df["xg"], df["match_id"], n_boot=100)
    assert result["n_goal"] + result["n_control"] == len(df) - 100


def test_benjamini_hochberg_matches_a_worked_example():
    q = benjamini_hochberg(np.array([0.01, 0.04, 0.03, 0.02]))
    assert q == pytest.approx([0.04, 0.04, 0.04, 0.04])
    q = benjamini_hochberg(np.array([0.001, 0.5, 0.9]))
    assert q == pytest.approx([0.003, 0.75, 0.9])


def test_select_controls_keeps_goals_and_the_chosen_non_goals():
    shocks = pd.DataFrame(
        {"outcome": ["Goal", "Saved", "Off T", "Post"], "goal": [True, False, False, False]}
    )
    assert select_controls(shocks, "all")["outcome"].tolist() == ["Goal", "Saved", "Off T", "Post"]
    assert select_controls(shocks, "on_target")["outcome"].tolist() == ["Goal", "Saved"]
    assert select_controls(shocks, "post")["outcome"].tolist() == ["Goal", "Post"]
