"""Thin wrapper around statsbombpy, so the rest of the package never imports it directly.

Any object with the same two functions, `matches(name, season)` and `raw_events(match_id)`,
can be passed to the pipeline as a source. The tests use a synthetic one.
"""

from __future__ import annotations

import warnings

import pandas as pd

MATCH_COLUMNS = [
    "match_id",
    "match_date",
    "kick_off",
    "competition_stage",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
]


def _sb():
    # Imported lazily so that tests and CI never need the package's network access.
    from statsbombpy import sb

    # statsbombpy warns on every call that the free tier is in use. That is expected.
    warnings.filterwarnings("ignore", message="credentials were not supplied")
    return sb


def competitions() -> pd.DataFrame:
    return _sb().competitions()


def find_season(comps: pd.DataFrame, name: str, season: str) -> tuple[int, int]:
    """Look up (competition_id, season_id) by name, so no IDs are hard-coded anywhere."""
    same_name = comps[comps["competition_name"] == name]
    if same_name.empty:
        known = ", ".join(sorted(comps["competition_name"].unique()))
        raise ValueError(f"No competition called {name!r}. Available: {known}")
    hit = same_name[same_name["season_name"] == season]
    if len(hit) != 1:
        known = ", ".join(sorted(same_name["season_name"].unique()))
        raise ValueError(f"{name!r} has no unique season {season!r}. Available: {known}")
    return int(hit["competition_id"].iloc[0]), int(hit["season_id"].iloc[0])


def matches(name: str, season: str) -> pd.DataFrame:
    competition_id, season_id = find_season(competitions(), name, season)
    out = _sb().matches(competition_id=competition_id, season_id=season_id)
    out = out.sort_values(["match_date", "kick_off"]).reset_index(drop=True)
    return out[[c for c in MATCH_COLUMNS if c in out.columns]]


def raw_events(match_id: int) -> pd.DataFrame:
    return _sb().events(match_id=match_id)
