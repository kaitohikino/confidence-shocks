"""Estimate what changes after a goal, relative to a similar shot that did not go in.

Identification in one paragraph: conditional on a shot's xG, whether it goes in is close to
a weighted coin flip. So goals (treated) are compared with non-goals (control), with controls
re-weighted by xg / (1 - xg) so both groups have the same xG mix (the effect on the treated).
The outcome is the shooter's level in the window after the shot, net of his teammates' level
(which removes what the new scoreline does to the whole team), and the comparison adjusts for
the same quantities in the window before the shot. Uncertainty comes from resampling whole
matches, because shots within a match are not independent.

Why adjust for the before-shot level instead of using after-minus-before changes: if goals and
controls happen to start at different levels, a change score inherits that gap through
regression to the mean. The 2022 World Cup run showed exactly this (scorers had been quieter
before the shot, so every "effect" pointed the opposite way to the pre-shot gap). A weighted
regression on the before-shot level lets the data choose how much of the gap carries forward.
`method="change"` keeps the old estimator for comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from confidence_shocks.features import KIND, METRICS

# Which non-goals a goal is compared with. Tighter sets are cleaner but smaller.
CONTROL_SETS: dict[str, tuple[str, ...] | None] = {
    "all": None,  # every non-goal
    "on_target": ("Saved", "Saved to Post"),  # the keeper decided it
    "post": ("Post",),  # centimetres decided it
    "near_miss": ("Saved", "Saved to Post", "Post"),
}

METHODS = ("ancova", "change")

# Pre-shot quantities that no estimate adjusts for, so they must be balanced by the weights alone.
GATED = ("score_diff", "clock")


def select_controls(shocks: pd.DataFrame, controls: str = "on_target") -> pd.DataFrame:
    """Keep goals plus the chosen kind of non-goal."""
    outcomes = CONTROL_SETS[controls]
    if outcomes is None:
        return shocks
    return shocks[shocks["goal"] | shocks["outcome"].isin(outcomes)]


def level(shocks: pd.DataFrame, metric: str, window: str, adjust: bool = True) -> pd.Series:
    """The shooter's level of `metric` in `window` ("prepre", "pre" or "post"), net of mates."""
    own = shocks[f"{metric}_{window}"]
    if not adjust:
        return own
    return own - shocks[f"{metric}_mates_{window}"]


def player_norm(shocks: pd.DataFrame, metric: str) -> pd.Series:
    """The shooter's usual before-shot level of `metric`: the mean over his shots in OTHER matches.

    Other matches only, so the norm can never contain anything that happened after this shot.
    NaN for a player with no shots in any other match.
    """
    values = shocks[f"{metric}_pre"]
    present = values.notna()
    keys = {"player": shocks["player"], "match": shocks["match_id"]}
    frame = pd.DataFrame({**keys, "v": values.fillna(0.0), "n": present.astype(float)})
    by_player = frame.groupby("player")[["v", "n"]].transform("sum")
    by_match = frame.groupby(["player", "match"])[["v", "n"]].transform("sum")
    n_other = by_player["n"] - by_match["n"]
    return ((by_player["v"] - by_match["v"]) / n_other.where(n_other > 0)).rename(None)


def design(
    shocks: pd.DataFrame,
    metric: str,
    adjust: bool = True,
    method: str = "ancova",
    after: str = "post",
    before: str = "pre",
) -> tuple[pd.Series, pd.DataFrame | None]:
    """Outcome and covariates for one metric.

    ancova: outcome is the `after` level. Covariates, each with its own slope:
            - the shooter's `before` level, and his teammates' when `adjust`;
            - the shooter's usual level (`player_norm`), with a flag for players who have
              none. A quiet spell only predicts a rebound relative to a player's norm, so
              adjusting for the before level alone cannot remove regression to the mean
              when goals are more likely after unusually quiet spells.
    change: outcome is `after` minus `before`, no covariates (slope on `before` fixed at 1).
    """
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    y = level(shocks, metric, after, adjust)
    if method == "change":
        return y - level(shocks, metric, before, adjust), None
    norm = player_norm(shocks, metric)
    covariates = {
        "own_before": shocks[f"{metric}_{before}"],
        "own_norm": norm.fillna(norm.mean() if norm.notna().any() else 0.0),
        "has_norm": norm.notna().astype(float),
    }
    if adjust:
        covariates["mates_before"] = shocks[f"{metric}_mates_{before}"]
    return y, pd.DataFrame(covariates, index=shocks.index)


def att(
    y: pd.Series,
    goal: pd.Series,
    xg: pd.Series,
    cluster: pd.Series,
    covariates: pd.DataFrame | None = None,
    n_boot: int = 2000,
    seed: int = 0,
    scale: float | None = None,
) -> dict[str, float]:
    """Effect of scoring on `y`: weighted least squares of y on [1, goal, covariates].

    Controls get weight xg / (1 - xg), goals weight 1 (the effect on the treated). With no
    covariates this is exactly the weighted difference in means. Intervals come from a
    bootstrap over clusters (matches). `scale` sets the SD unit for the *_sd columns; by
    default it is the SD of `y`.
    """
    data = pd.DataFrame(
        {"y": y.to_numpy(float), "goal": goal.to_numpy(bool), "xg": xg.to_numpy(float)}
    )
    names: list[str] = []
    if covariates is not None:
        for name in covariates.columns:
            data[f"cov_{name}"] = covariates[name].to_numpy(float)
            names.append(f"cov_{name}")
    data["cluster"] = cluster.to_numpy()
    data = data.dropna()

    treated = data["goal"].to_numpy()
    propensity = data["xg"].clip(0.01, 0.99).to_numpy()
    weight = np.where(treated, 1.0, propensity / (1 - propensity))
    values = data["y"].to_numpy()

    # Design matrix. Covariates are centred so the intercept stays well scaled.
    columns = [np.ones(len(data)), treated.astype(float)]
    columns += [data[c].to_numpy() - data[c].mean() for c in names]
    x = np.column_stack(columns)
    k = x.shape[1]

    # Per-match sufficient statistics: X'WX (k*k), X'Wy (k), and the weight of each group,
    # which is all the bootstrap needs. Summing rows of `parts` = pooling those matches.
    xtwx = np.einsum("ni,nj,n->nij", x, x, weight).reshape(len(data), k * k)
    xtwy = x * (weight * values)[:, None]
    groups = np.column_stack([treated * weight, ~treated * weight])
    per_row = pd.DataFrame(np.hstack([xtwx, xtwy, groups]))
    parts = per_row.groupby(data["cluster"].to_numpy()).sum().to_numpy()

    def solve(sums: np.ndarray) -> np.ndarray:
        """Goal coefficient for one or many pooled sums (NaN where a group is empty)."""
        sums = np.atleast_2d(sums)
        a = sums[:, : k * k].reshape(-1, k, k)
        b = sums[:, k * k : k * k + k]
        ok = (sums[:, -2] > 0) & (sums[:, -1] > 0)
        out = np.full(len(sums), np.nan)
        if ok.any():
            # pinv rather than solve: a resample can make a covariate constant.
            out[ok] = np.einsum("nij,nj->ni", np.linalg.pinv(a[ok]), b[ok])[:, 1]
        return out

    point = float(solve(parts.sum(axis=0))[0])
    rng = np.random.default_rng(seed)
    n = len(parts)
    counts = rng.multinomial(n, np.full(n, 1 / n), size=n_boot)  # how often each match is drawn
    boot = solve(counts @ parts)
    boot = boot[np.isfinite(boot)]

    lo, hi = np.percentile(boot, [2.5, 97.5])
    p = 2 * min((boot <= 0).mean(), (boot >= 0).mean())
    sd = float(data["y"].std()) if scale is None else float(scale)
    return {
        "effect": point,
        "lo": float(lo),
        "hi": float(hi),
        "effect_sd": point / sd,
        "lo_sd": float(lo) / sd,
        "hi_sd": float(hi) / sd,
        "p": float(min(max(p, 1 / n_boot), 1.0)),
        "n_goal": int(treated.sum()),
        "n_control": int((~treated).sum()),
    }


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """False-discovery-rate adjusted p-values (q-values)."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(q, 0, 1)
    return out


def estimate_all(
    shocks: pd.DataFrame,
    controls: str = "on_target",
    adjust: bool = True,
    method: str = "ancova",
    n_boot: int = 2000,
    seed: int = 0,
    after: str = "post",
    before: str = "pre",
) -> pd.DataFrame:
    """One row per metric: effect of scoring, interval, p-value and FDR-adjusted q-value.

    Effects in SD units are scaled by the SD of the `after` level, whichever method is used,
    so ancova and change results can be compared directly.
    """
    df = select_controls(shocks, controls)
    rows = []
    for metric in METRICS:
        y, covariates = design(df, metric, adjust, method, after, before)
        scale = level(df, metric, after, adjust).std()
        result = att(y, df["goal"], df["xg"], df["match_id"], covariates, n_boot, seed, scale)
        rows.append({"metric": metric, "kind": KIND[metric], **result})
    out = pd.DataFrame(rows)
    out["q"] = benjamini_hochberg(out["p"].to_numpy())
    return out


def placebo(
    shocks: pd.DataFrame,
    controls: str = "on_target",
    adjust: bool = True,
    method: str = "ancova",
    n_boot: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """The same estimator, moved one window back in time, where the true effect must be zero.

    Outcome: the window just before the shot. Adjusted for: the window before that. A shot's
    outcome cannot cause anything that happened before it, so a clear "effect" here means the
    estimator is picking up something other than scoring. Rows without the earlier window
    (shooter not yet on the pitch) are dropped.
    """
    return estimate_all(
        shocks, controls, adjust, method, n_boot, seed, after="pre", before="prepre"
    )


def balance(
    shocks: pd.DataFrame, controls: str = "on_target", n_boot: int = 2000, seed: int = 0
) -> pd.DataFrame:
    """Standardised differences before the shot, after xG weighting.

    `effect_sd` is the standardised mean difference (goals minus weighted controls, in SDs).
    The before-shot metric levels are reported for information: the ancova estimator adjusts
    for them. Score difference and clock are not adjusted for, so `checks` gates on them.
    """
    df = select_controls(shocks, controls)
    pre_shot = {f"{m}_pre": df[f"{m}_pre"] for m in METRICS}
    pre_shot |= {"score_diff": df["score_diff"], "clock": df["clock"]}
    rows = [
        {
            "quantity": name,
            **att(series, df["goal"], df["xg"], df["match_id"], None, n_boot, seed),
        }
        for name, series in pre_shot.items()
    ]
    return pd.DataFrame(rows)


def checks(balance_table: pd.DataFrame, placebo_table: pd.DataFrame, max_smd: float = 0.1):
    """Pass/fail table, to read before any result.

    - balance: score difference and clock differ by at most `max_smd` SDs between groups.
    - placebo: no metric shows a pre-shot "effect" with q < 0.05.
    """
    rows = []
    gated = balance_table[balance_table["quantity"].isin(GATED)]
    for r in gated.itertuples():
        rows.append(
            {
                "check": "balance",
                "quantity": r.quantity,
                "value": r.effect_sd,
                "rule": f"|smd| <= {max_smd:g}",
                "passed": bool(abs(r.effect_sd) <= max_smd),
            }
        )
    for r in placebo_table.itertuples():
        rows.append(
            {
                "check": "placebo",
                "quantity": r.metric,
                "value": r.q,
                "rule": "q >= 0.05",
                "passed": bool(r.q >= 0.05),
            }
        )
    return pd.DataFrame(rows)
