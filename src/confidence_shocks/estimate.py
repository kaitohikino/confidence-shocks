"""Estimate what changes after a goal, relative to a similar shot that did not go in.

Identification in one paragraph: conditional on a shot's xG, whether it goes in is close to
a weighted coin flip. So goals (treated) are compared with non-goals (control), with controls
re-weighted by xg / (1 - xg) so both groups have the same xG mix (the effect on the treated).
Each shooter's before/after change is measured net of his teammates' change over the same
windows, which removes what the new scoreline does to the whole team. Uncertainty comes from
resampling whole matches, because shots within a match are not independent.
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


def select_controls(shocks: pd.DataFrame, controls: str = "on_target") -> pd.DataFrame:
    """Keep goals plus the chosen kind of non-goal."""
    outcomes = CONTROL_SETS[controls]
    if outcomes is None:
        return shocks
    return shocks[shocks["goal"] | shocks["outcome"].isin(outcomes)]


def outcome(shocks: pd.DataFrame, metric: str, adjust: bool = True) -> pd.Series:
    """After-minus-before change in `metric` for the shooter, net of teammates if `adjust`."""
    own = shocks[f"{metric}_post"] - shocks[f"{metric}_pre"]
    if not adjust:
        return own
    return own - (shocks[f"{metric}_mates_post"] - shocks[f"{metric}_mates_pre"])


def att(
    y: pd.Series,
    goal: pd.Series,
    xg: pd.Series,
    cluster: pd.Series,
    n_boot: int = 2000,
    seed: int = 0,
) -> dict[str, float]:
    """xG-weighted difference in mean `y`, goals minus controls, with a cluster bootstrap."""
    data = pd.DataFrame(
        {"y": y.to_numpy(float), "goal": goal.to_numpy(bool), "xg": xg.to_numpy(float)}
    )
    data["cluster"] = cluster.to_numpy()
    data = data.dropna()

    treated = data["goal"].to_numpy()
    propensity = data["xg"].clip(0.01, 0.99).to_numpy()
    weight = np.where(treated, 1.0, propensity / (1 - propensity))
    values = data["y"].to_numpy()

    # Per-match sums are all the bootstrap needs: [sum wy, sum w] for treated, then for control.
    parts = (
        pd.DataFrame(
            {
                "cluster": data["cluster"].to_numpy(),
                "ty": treated * weight * values,
                "tw": treated * weight,
                "cy": ~treated * weight * values,
                "cw": ~treated * weight,
            }
        )
        .groupby("cluster")
        .sum()
        .to_numpy()
    )

    def diff(sums: np.ndarray) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return sums[..., 0] / sums[..., 1] - sums[..., 2] / sums[..., 3]

    point = float(diff(parts.sum(axis=0)))
    rng = np.random.default_rng(seed)
    n = len(parts)
    counts = rng.multinomial(n, np.full(n, 1 / n), size=n_boot)  # how often each match is drawn
    boot = diff(counts @ parts)
    boot = boot[np.isfinite(boot)]

    lo, hi = np.percentile(boot, [2.5, 97.5])
    p = 2 * min((boot <= 0).mean(), (boot >= 0).mean())
    sd = float(data["y"].std())
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
    n_boot: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """One row per metric: effect of scoring, interval, p-value and FDR-adjusted q-value."""
    df = select_controls(shocks, controls)
    rows = []
    for metric in METRICS:
        change = outcome(df, metric, adjust)
        result = att(change, df["goal"], df["xg"], df["match_id"], n_boot, seed)
        rows.append({"metric": metric, "kind": KIND[metric], **result})
    out = pd.DataFrame(rows)
    out["q"] = benjamini_hochberg(out["p"].to_numpy())
    return out


def balance(
    shocks: pd.DataFrame, controls: str = "on_target", n_boot: int = 2000, seed: int = 0
) -> pd.DataFrame:
    """Placebo test: after weighting, goals and controls should look alike BEFORE the shot.

    Any "effect" on a pre-shot quantity cannot be caused by the shot's outcome, so intervals
    here that exclude zero mean the comparison is not yet fair.
    """
    df = select_controls(shocks, controls)
    pre_shot = {f"{m}_pre": df[f"{m}_pre"] for m in METRICS}
    pre_shot |= {"score_diff": df["score_diff"], "clock": df["clock"]}
    rows = [
        {"quantity": name, **att(series, df["goal"], df["xg"], df["match_id"], n_boot, seed)}
        for name, series in pre_shot.items()
    ]
    return pd.DataFrame(rows)
