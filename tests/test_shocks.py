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
        for suffix in ("prepre", "pre", "post", "mates_prepre", "mates_pre", "mates_post"):
            assert f"{metric}_{suffix}" in table.columns
    assert table["goal"].dtype == bool


def test_a_longer_window_keeps_fewer_shots(raw_match):
    events, spans = prepare_match(raw_match, match_id=1001)
    assert len(match_shocks(events, spans, 30.0)) < len(match_shocks(events, spans, 5.0))


def test_earlier_window_is_missing_only_when_the_shooter_was_not_yet_on(raw_match):
    events, spans = prepare_match(raw_match, match_id=1001)
    table = match_shocks(events, spans, WINDOW)
    on = spans.drop_duplicates("player").set_index("player").loc[table["player"], "on"]
    has_earlier = table["clock"].to_numpy() - 2 * WINDOW >= on.to_numpy()
    assert has_earlier.any() and not has_earlier.all()
    assert table.loc[has_earlier, "receipts_prepre"].notna().all()
    assert table.loc[~has_earlier, "receipts_prepre"].isna().all()
    assert table.loc[~has_earlier, "receipts_mates_prepre"].isna().all()
