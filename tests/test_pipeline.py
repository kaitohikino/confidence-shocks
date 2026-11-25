"""End-to-end run on synthetic matches: the same code path as `make all`, without the network."""

from confidence_shocks import pipeline
from confidence_shocks.config import load_config
from confidence_shocks.features import METRICS


def test_default_config_loads():
    cfg = load_config()
    assert cfg.competitions
    assert cfg.window_minutes > 0


def test_audit_counts_matches_and_teams(cfg, fake_source):
    summary = pipeline.audit(cfg, source=fake_source)
    assert summary["matches"].tolist() == [12]
    assert summary["teams"].tolist() == [24]


def test_ingest_shocks_estimate(cfg, fake_source):
    matches = pipeline.ingest(cfg, source=fake_source)
    assert len(list(cfg.events_dir.glob("*.parquet"))) == len(matches) == 12

    # Re-running must resume, not download again.
    fake_source.raw_events = None
    pipeline.ingest(cfg, source=fake_source)

    table = pipeline.shocks(cfg)
    assert table["goal"].any() and not table["goal"].all()
    assert {"competition", "season"} <= set(table.columns)

    results = pipeline.estimate(cfg)
    assert results["metric"].tolist() == METRICS
    assert results["q"].between(0, 1).all()
    assert (results["lo"] <= results["hi"]).all()
    outputs = ("results.csv", "results_unadjusted.csv", "balance.csv", "placebo.csv", "checks.csv")
    for name in (*outputs, "forest.png"):
        assert (cfg.out_dir / name).exists()


def test_change_method_still_runs(cfg, fake_source):
    from dataclasses import replace

    cfg = replace(cfg, method="change")
    pipeline.ingest(cfg, source=fake_source)
    pipeline.shocks(cfg)
    results = pipeline.estimate(cfg)
    assert results["effect"].notna().all()
