"""Turn one match of raw StatsBomb events into a tidy, typed table plus on-pitch spans.

Raw quirks handled here (see notebooks/00_getting_acquainted.ipynb for the walkthrough):
rows arrive unsorted, `timestamp` restarts each period, locations are [x, y] lists,
period 5 is a penalty shootout, and many columns are missing when an event never occurred.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Columns the pipeline reads. Any that a match lacks are created as empty.
NEEDED = [
    "player",
    "position",
    "play_pattern",
    "under_pressure",
    "pass_length",
    "pass_outcome",
    "pass_end_location",
    "carry_end_location",
    "shot_end_location",
    "shot_statsbomb_xg",
    "shot_outcome",
    "shot_type",
    "dribble_outcome",
    "tactics",
    "substitution_replacement",
    "foul_committed_card",
    "bad_behaviour_card",
]

STRINGS = [
    "team",
    "player",
    "position",
    "type",
    "play_pattern",
    "pass_outcome",
    "shot_outcome",
    "shot_type",
    "dribble_outcome",
]
FLOATS = ["clock", "x", "y", "end_x", "end_y", "pass_length", "shot_statsbomb_xg"]
INTS = ["match_id", "index", "period", "minute", "score_diff"]
TIDY_COLUMNS = INTS + STRINGS + FLOATS + ["under_pressure"]

SENDING_OFF = {"Red Card", "Second Yellow"}


def _coord(series: pd.Series, i: int) -> np.ndarray:
    """Coordinate i from a column of [x, y] lists; NaN where there is no location."""
    return np.array(
        [v[i] if isinstance(v, (list, tuple, np.ndarray)) else np.nan for v in series],
        dtype=float,
    )


def add_clock_and_xy(raw: pd.DataFrame) -> pd.DataFrame:
    """Sort, drop shootouts, add `clock` (continuous minutes) and x / y / end_x / end_y."""
    ev = raw[raw["period"] <= 4].sort_values("index").reset_index(drop=True).copy()
    for col in NEEDED:
        if col not in ev.columns:
            ev[col] = np.nan

    seconds = pd.to_timedelta(ev["timestamp"]).dt.total_seconds()
    # Offset of each period = total length of the periods before it.
    offset = seconds.groupby(ev["period"]).max().cumsum().shift(fill_value=0)
    ev["clock"] = (seconds + ev["period"].map(offset)) / 60

    ev["x"], ev["y"] = _coord(ev["location"], 0), _coord(ev["location"], 1)
    ev["end_x"], ev["end_y"] = np.nan, np.nan
    for col in ("pass_end_location", "carry_end_location", "shot_end_location"):
        ev["end_x"] = ev["end_x"].fillna(pd.Series(_coord(ev[col], 0), index=ev.index))
        ev["end_y"] = ev["end_y"].fillna(pd.Series(_coord(ev[col], 1), index=ev.index))
    return ev


def add_score_state(ev: pd.DataFrame) -> pd.DataFrame:
    """Add `score_diff`: the acting team's goal difference just before each event."""
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (
        ev["type"] == "Own Goal For"
    )
    diff = np.zeros(len(ev), dtype="int64")
    for team in ev["team"].dropna().unique():
        own = (ev["team"] == team).to_numpy()
        scored_before = (is_goal.to_numpy() & own).cumsum() - (is_goal.to_numpy() & own)
        diff += np.where(own, scored_before, -scored_before)
    ev["score_diff"] = diff
    return ev


def on_pitch(ev: pd.DataFrame) -> pd.DataFrame:
    """Clock time each player came on and went off. Needs the output of `add_clock_and_xy`."""
    end = float(ev["clock"].max())
    spans: dict[str, dict] = {}

    for row in ev[ev["type"] == "Starting XI"].itertuples():
        if isinstance(row.tactics, dict):
            for slot in row.tactics["lineup"]:
                spans[slot["player"]["name"]] = {"team": row.team, "on": 0.0, "off": end}

    for row in ev[ev["type"] == "Substitution"].itertuples():
        spans.setdefault(row.player, {"team": row.team, "on": 0.0, "off": end})["off"] = row.clock
        sub = row.substitution_replacement
        sub = sub["name"] if isinstance(sub, dict) else sub
        spans[sub] = {"team": row.team, "on": row.clock, "off": end}

    sent_off = ev[
        ev["foul_committed_card"].isin(SENDING_OFF) | ev["bad_behaviour_card"].isin(SENDING_OFF)
    ]
    for row in sent_off.itertuples():
        if row.player in spans:
            spans[row.player]["off"] = min(spans[row.player]["off"], row.clock)

    out = pd.DataFrame.from_dict(spans, orient="index", columns=["team", "on", "off"])
    return out.rename_axis("player").reset_index()


def prepare_match(raw: pd.DataFrame, match_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Raw events for one match -> (tidy events, on-pitch spans), both safe to write to parquet."""
    ev = add_score_state(add_clock_and_xy(raw))
    spans = on_pitch(ev)
    spans.insert(0, "match_id", match_id)

    ev["match_id"] = match_id
    ev["under_pressure"] = ev["under_pressure"].eq(True)
    for col in STRINGS:
        ev[col] = ev[col].astype(object).where(ev[col].notna(), None)
    ev[FLOATS] = ev[FLOATS].astype(float)
    ev[INTS] = ev[INTS].astype("int64")
    return ev[TIDY_COLUMNS], spans
