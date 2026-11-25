from confidence_shocks.features import METRICS
from confidence_shocks.prep import prepare_match
from confidence_shocks.shocks import match_shocks

WINDOW = 15.0


def test_shock_rows_respect_the_design(raw_match):
    events, spans = prepare_match(raw_match, match_id=1001)
    table = match_shocks(events, spans, WINDOW)
    assert len(table) > 0

    # One row per kept shot, never a penalty.
    open_shots = events[(events["type"] == "Shot") & (events["shot_type"] != "Penalty")]
    assert len(table) <= len(open_shots)
    assert set(table["clock"]) <= set(open_shots["clock"])

    # The shooter was on the pitch for the whole window on both sides.
    span = spans.set_index("player").loc[table["player"]]
    assert (table["clock"].to_numpy() - WINDOW >= span["on"].to_numpy()).all()
    assert (table["clock"].to_numpy() + WINDOW <= span["off"].to_numpy()).all()

    for metric in METRICS:
        for suffix in ("pre", "post", "mates_pre", "mates_post"):
            assert f"{metric}_{suffix}" in table.columns
    assert table["goal"].dtype == bool


def test_a_longer_window_keeps_fewer_shots(raw_match):
    events, spans = prepare_match(raw_match, match_id=1001)
    assert len(match_shocks(events, spans, 30.0)) < len(match_shocks(events, spans, 5.0))
