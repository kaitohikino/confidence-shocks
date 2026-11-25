import numpy as np
import pandas as pd
import pytest

from confidence_shocks.estimate import (
    att,
    benjamini_hochberg,
    checks,
    design,
    player_norm,
    select_controls,
)


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


def _shocks_with_regression_to_the_mean(effect: float, n: int = 8000, seed: int = 2):
    """Shots where scorers were, by selection, quieter than usual just before the shot.

    Each of 300 players has a stable level. Every window is that level plus fresh noise, so a
    quiet before-window is followed by a return to normal whatever happens. Goals are more
    likely after an unusually quiet spell (beyond what xG says): the pattern in the 2022 World
    Cup run. Columns use the shock-table naming for a single metric called `m`.
    """
    rng = np.random.default_rng(seed)
    player = rng.integers(0, 300, n)
    usual = rng.normal(10, 2, 300)[player]
    prepre, pre, post = (usual + rng.normal(0, 2, n) for _ in range(3))
    xg = rng.beta(1, 6, n)
    quiet = (pre - usual) / 2
    goal = rng.random(n) < np.clip(xg * np.exp(-0.5 * quiet), 0, 1)
    return pd.DataFrame(
        {
            "player": player,
            "match_id": rng.integers(0, 400, n),
            "goal": goal,
            "xg": xg,
            "m_prepre": prepre,
            "m_pre": pre,
            "m_post": post + effect * goal,
        }
    )


def _fit(df, method, after="post", before="pre", n_boot=300):
    y, covariates = design(df, "m", adjust=False, method=method, after=after, before=before)
    return att(y, df["goal"], df["xg"], df["match_id"], covariates, n_boot=n_boot)


def test_change_scores_invent_an_effect_that_ancova_does_not():
    df = _shocks_with_regression_to_the_mean(effect=0.0)
    change, ancova = _fit(df, "change"), _fit(df, "ancova")
    assert change["lo"] > 0.3  # a confident, entirely spurious "effect of scoring"
    assert abs(ancova["effect"]) < 0.2
    assert ancova["lo"] < 0 < ancova["hi"]


def test_ancova_recovers_a_known_effect_under_the_same_selection():
    df = _shocks_with_regression_to_the_mean(effect=1.0, seed=3)
    result = _fit(df, "ancova")
    assert result["effect"] == pytest.approx(1.0, abs=0.2)
    assert result["lo"] > 0.5


def test_placebo_flags_selection_on_recent_form():
    # Placebo: outcome is the before-window, adjusted for the window before that. Here scorers
    # really were quieter than usual just before shooting, and the placebo should say so.
    df = _shocks_with_regression_to_the_mean(effect=0.0, seed=4)
    assert _fit(df, "ancova", after="pre", before="prepre")["hi"] < 0


def test_placebo_is_quiet_when_goals_are_a_pure_coin_flip_given_xg():
    df = _shocks_with_regression_to_the_mean(effect=1.0, seed=5)
    rng = np.random.default_rng(5)
    df["goal"] = rng.random(len(df)) < df["xg"]
    result = _fit(df, "ancova", after="pre", before="prepre")
    assert result["lo"] < 0 < result["hi"]


def test_player_norm_only_uses_other_matches():
    df = pd.DataFrame(
        {
            "player": ["a", "a", "a", "b"],
            "match_id": [1, 1, 2, 1],
            "m_pre": [1.0, 3.0, 10.0, 5.0],
        }
    )
    norm = player_norm(df, "m")
    assert norm.tolist()[:3] == [10.0, 10.0, 2.0]
    assert np.isnan(norm.iloc[3])


def test_att_without_covariates_is_the_weighted_difference_in_means():
    df = _simulate(effect=0.5, n=500, seed=5)
    result = att(df["y"], df["goal"], df["xg"], df["match_id"], n_boot=50)
    xg = df["xg"].clip(0.01, 0.99)
    w = np.where(df["goal"], 1.0, xg / (1 - xg))
    goals, others = df["goal"].to_numpy(), ~df["goal"].to_numpy()
    expected = np.average(df["y"][goals], weights=w[goals]) - np.average(
        df["y"][others], weights=w[others]
    )
    assert result["effect"] == pytest.approx(expected)


def test_checks_flag_imbalance_and_placebo_effects():
    balance_table = pd.DataFrame(
        {"quantity": ["receipts_pre", "score_diff", "clock"], "effect_sd": [-0.5, 0.05, 0.3]}
    )
    placebo_table = pd.DataFrame({"metric": ["receipts", "passes"], "q": [0.01, 0.6]})
    table = checks(balance_table, placebo_table, max_smd=0.1)
    failed = set(table.loc[~table["passed"], "quantity"])
    # receipts_pre is adjusted for by the estimator, so it is reported but not gated.
    assert failed == {"clock", "receipts"}


def test_design_rejects_unknown_methods():
    with pytest.raises(ValueError):
        design(pd.DataFrame(), "receipts", method="matching")
