"""Build the shock table: one row per open-play shot, with before/after levels of every metric.

This module only measures. Which shots count as treated or control, and how the levels are
turned into an effect, is decided in `estimate.py`.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from confidence_shocks.config import Config
from confidence_shocks.features import COUNTS, METRICS, N_TEAMMATES, window_stats

log = logging.getLogger(__name__)


def _levels(df: pd.DataFrame, t: float, window: float) -> tuple[dict, dict, dict]:
    """Metric levels in three windows: two before clock time t, one after.

    `prepre` is [t - 2w, t - w), used only by the placebo test.
    """
    prepre = window_stats(df[(df["clock"] >= t - 2 * window) & (df["clock"] < t - window)])
    before = window_stats(df[(df["clock"] >= t - window) & (df["clock"] < t)])
    after = window_stats(df[(df["clock"] > t) & (df["clock"] <= t + window)])
    return prepre, before, after


def match_shocks(events: pd.DataFrame, spans: pd.DataFrame, window: float = 15.0) -> pd.DataFrame:
    """Shock rows for one match.

    A shot is kept only if the shooter was on the pitch for the full window on both sides,
    so every row compares like with like. Penalties are excluded (a different kind of event).
    The `*_prepre` columns (one window earlier still, for the placebo test) are NaN when the
    shooter was not on the pitch for all of that earlier window.
    """
    spans = spans.drop_duplicates("player").set_index("player")
    shots = events[(events["type"] == "Shot") & (events["shot_type"] != "Penalty")]

    rows = []
    for shot in shots.itertuples():
        if shot.player not in spans.index:
            continue
        on, off = spans.at[shot.player, "on"], spans.at[shot.player, "off"]
        if shot.clock - window < on or shot.clock + window > off:
            continue

        team = events[events["team"] == shot.team]
        own = _levels(team[team["player"] == shot.player], shot.clock, window)
        mates = _levels(team[team["player"] != shot.player], shot.clock, window)
        has_prepre = shot.clock - 2 * window >= on

        row = {
            "match_id": shot.match_id,
            "team": shot.team,
            "player": shot.player,
            "position": shot.position,
            "period": shot.period,
            "clock": shot.clock,
            "score_diff": shot.score_diff,
            "xg": shot.shot_statsbomb_xg,
            "outcome": shot.shot_outcome,
            "goal": shot.shot_outcome == "Goal",
        }
        for metric in METRICS:
            scale = N_TEAMMATES if metric in COUNTS else 1  # pooled count -> per teammate
            for i, window_name in enumerate(("prepre", "pre", "post")):
                missing = window_name == "prepre" and not has_prepre
                row[f"{metric}_{window_name}"] = np.nan if missing else own[i][metric]
                row[f"{metric}_mates_{window_name}"] = (
                    np.nan if missing else mates[i][metric] / scale
                )
        rows.append(row)
    return pd.DataFrame(rows)


def build_shocks(cfg: Config) -> pd.DataFrame:
    """Run `match_shocks` over every ingested match in the config and save one table."""
    matches = pd.read_parquet(cfg.matches_path)
    tables = []
    for i, match_id in enumerate(matches["match_id"], start=1):
        events = pd.read_parquet(cfg.events_dir / f"{match_id}.parquet")
        spans = pd.read_parquet(cfg.spans_dir / f"{match_id}.parquet")
        table = match_shocks(events, spans, cfg.window_minutes)
        if not table.empty:
            tables.append(table)
        if i % 50 == 0 or i == len(matches):
            log.info("shocks: %d/%d matches", i, len(matches))

    shocks = pd.concat(tables, ignore_index=True)
    labels = matches[["match_id", "competition", "season"]]
    shocks = shocks.merge(labels, on="match_id", how="left")
    cfg.shocks_path.parent.mkdir(parents=True, exist_ok=True)
    shocks.to_parquet(cfg.shocks_path, index=False)
    n_goals = int(shocks["goal"].sum())
    log.info("shocks: %d shots kept (%d goals) -> %s", len(shocks), n_goals, cfg.shocks_path)
    return shocks
