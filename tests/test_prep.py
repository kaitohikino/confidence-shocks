import pandas as pd

from confidence_shocks.prep import (
    TIDY_COLUMNS,
    add_clock_and_xy,
    add_score_state,
    on_pitch,
    prepare_match,
)


def test_clock_is_continuous_and_shootout_is_dropped(raw_match):
    ev = add_clock_and_xy(raw_match)
    assert ev["period"].max() == 2
    assert ev["clock"].is_monotonic_increasing
    # The second half must start where the first half ended, not back at zero.
    assert ev.loc[ev["period"] == 2, "clock"].min() >= ev.loc[ev["period"] == 1, "clock"].max()


def test_coordinates_are_unpacked(raw_match):
    ev = add_clock_and_xy(raw_match)
    passes = ev[ev["type"] == "Pass"]
    assert passes[["x", "y", "end_x", "end_y"]].notna().all().all()
    assert ev.loc[ev["type"] == "Starting XI", "x"].isna().all()


def test_score_diff_is_from_the_acting_teams_view_before_the_event():
    ev = pd.DataFrame(
        {
            "type": ["Pass", "Shot", "Pass", "Pass", "Own Goal For", "Pass"],
            "team": ["A", "A", "A", "B", "B", "A"],
            "shot_outcome": [None, "Goal", None, None, None, None],
        }
    )
    out = add_score_state(ev)
    # A scores (row 1): A is +1 and B is -1 afterwards. B is then credited an own goal: level.
    assert out["score_diff"].tolist() == [0, 0, 1, -1, -1, 0]


def test_on_pitch_handles_substitutions(raw_match):
    ev = add_clock_and_xy(raw_match)
    spans = on_pitch(ev).set_index("player")
    assert len(spans) == 24  # 22 starters + one substitute per team
    sub_off, sub_on = "Home1001_10", "Home1001_11"
    assert spans.at[sub_off, "on"] == 0
    assert spans.at[sub_off, "off"] == spans.at[sub_on, "on"] > 45
    assert spans.at[sub_on, "off"] == ev["clock"].max()


def test_on_pitch_ends_a_span_at_a_red_card(raw_match):
    ev = add_clock_and_xy(raw_match)
    victim = ev[(ev["type"] == "Duel") & (ev["clock"] > 20)].iloc[0]
    ev["foul_committed_card"] = ev["foul_committed_card"].astype(object)
    ev.loc[victim.name, "foul_committed_card"] = "Red Card"
    spans = on_pitch(ev).set_index("player")
    assert spans.at[victim["player"], "off"] <= victim["clock"]


def test_prepare_match_returns_typed_tidy_tables(raw_match):
    events, spans = prepare_match(raw_match, match_id=1001)
    assert list(events.columns) == TIDY_COLUMNS
    assert events["under_pressure"].dtype == bool
    assert (events["match_id"] == 1001).all()
    assert set(spans.columns) == {"match_id", "player", "team", "on", "off"}
