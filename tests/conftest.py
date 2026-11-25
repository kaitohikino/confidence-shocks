"""Synthetic matches with the same schema as raw StatsBomb events. No network, fully seeded."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from confidence_shocks.config import Config

EVENT_TYPES = ["Pass", "Ball Receipt*", "Carry", "Pressure", "Shot", "Dribble", "Duel"]
EVENT_PROBS = [0.33, 0.30, 0.20, 0.12, 0.015, 0.02, 0.015]


def _timestamp(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"00:{int(minutes):02d}:{secs:06.3f}"


def make_raw_match(match_id: int, shootout: bool = False) -> pd.DataFrame:
    """One fake match: two teams, two halves, one substitution per team, shuffled rows."""
    rng = np.random.default_rng(match_id)
    squads = {side: [f"{side}{match_id}_{i}" for i in range(12)] for side in ("Home", "Away")}
    on = {side: squad[:11] for side, squad in squads.items()}
    rows, index = [], 1

    for side, squad in squads.items():
        lineup = [{"player": {"id": i, "name": name}} for i, name in enumerate(squad[:11])]
        rows.append(
            {
                "index": index,
                "period": 1,
                "timestamp": _timestamp(0),
                "minute": 0,
                "team": side,
                "type": "Starting XI",
                "tactics": {"formation": 433, "lineup": lineup},
            }
        )
        index += 1

    for period in (1, 2, 5) if shootout else (1, 2):
        t, substituted = 0.0, set()
        length = 47 * 60 if period < 5 else 200
        while True:
            t += rng.exponential(2.5)
            if t >= length:
                break
            side = str(rng.choice(["Home", "Away"]))
            event = {
                "index": index,
                "period": period,
                "timestamp": _timestamp(t),
                "minute": int(t // 60) + (45 if period == 2 else 0),
                "team": side,
                "position": "Center Forward",
                "play_pattern": "Regular Play",
                "location": [float(rng.uniform(0, 120)), float(rng.uniform(0, 80))],
            }
            if period == 2 and t > 15 * 60 and side not in substituted:
                substituted.add(side)
                event |= {
                    "type": "Substitution",
                    "player": on[side][-1],
                    "substitution_replacement": squads[side][11],
                }
                on[side] = on[side][:-1] + [squads[side][11]]
            else:
                kind = "Shot" if period == 5 else str(rng.choice(EVENT_TYPES, p=EVENT_PROBS))
                event |= {"type": kind, "player": str(rng.choice(on[side]))}
                if rng.random() < 0.2:
                    event["under_pressure"] = True
                if kind == "Pass":
                    event["pass_end_location"] = [float(rng.uniform(0, 120)), 40.0]
                    event["pass_length"] = float(rng.uniform(3, 50))
                    if rng.random() < 0.2:
                        event["pass_outcome"] = "Incomplete"
                elif kind == "Carry":
                    event["carry_end_location"] = [float(rng.uniform(0, 120)), 40.0]
                elif kind == "Shot":
                    event["shot_statsbomb_xg"] = float(rng.beta(1, 8))
                    event["shot_outcome"] = str(
                        rng.choice(["Goal", "Saved", "Off T", "Post"], p=[0.25, 0.4, 0.3, 0.05])
                    )
                    penalty = period == 5 or rng.random() < 0.05
                    event["shot_type"] = "Penalty" if penalty else "Open Play"
                    event["shot_end_location"] = [120.0, 40.0, 1.2]
                elif kind == "Dribble":
                    event["dribble_outcome"] = str(rng.choice(["Complete", "Incomplete"]))
            rows.append(event)
            index += 1

    return pd.DataFrame(rows).sample(frac=1, random_state=0).reset_index(drop=True)


@pytest.fixture
def raw_match() -> pd.DataFrame:
    return make_raw_match(1001, shootout=True)


@pytest.fixture
def fake_source() -> SimpleNamespace:
    """Stands in for `confidence_shocks.data.statsbomb`: same two functions, no network."""

    def matches(name: str, season: str) -> pd.DataFrame:
        ids = np.arange(2000, 2012)
        return pd.DataFrame(
            {
                "match_id": ids,
                "match_date": [f"2022-12-{day:02d}" for day in range(1, 13)],
                "home_team": [f"H{i}" for i in ids],
                "away_team": [f"A{i}" for i in ids],
            }
        )

    return SimpleNamespace(matches=matches, raw_events=make_raw_match)


@pytest.fixture
def cfg(tmp_path) -> Config:
    return Config(
        name="test",
        competitions=[{"name": "Fake Cup", "season": "2022"}],
        n_boot=200,
        data_dir=tmp_path / "data",
        reports_dir=tmp_path / "reports",
    )
