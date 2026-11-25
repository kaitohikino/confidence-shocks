"""The pipeline steps, as plain functions. The CLI and the Makefile are thin layers over these."""

from __future__ import annotations

import logging

import pandas as pd

from confidence_shocks import estimate as est
from confidence_shocks.config import Config
from confidence_shocks.data import statsbomb
from confidence_shocks.prep import prepare_match
from confidence_shocks.shocks import build_shocks
from confidence_shocks.viz.plots import forest

log = logging.getLogger(__name__)


def list_matches(cfg: Config, source=statsbomb) -> pd.DataFrame:
    """All matches in the configured competitions, labelled with competition and season."""
    tables = []
    for comp in cfg.competitions:
        table = source.matches(comp["name"], comp["season"])
        table.insert(1, "competition", comp["name"])
        table.insert(2, "season", comp["season"])
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def audit(cfg: Config, source=statsbomb) -> pd.DataFrame:
    """How many matches and teams each configured competition really contains."""
    matches = list_matches(cfg, source)
    teams = matches.melt(
        id_vars=["competition", "season"], value_vars=["home_team", "away_team"], value_name="team"
    )
    summary = matches.groupby(["competition", "season"]).size().to_frame("matches")
    summary["teams"] = teams.groupby(["competition", "season"])["team"].nunique()
    return summary.reset_index()


def ingest(cfg: Config, source=statsbomb) -> pd.DataFrame:
    """Download each match once and store it as tidy parquet. Safe to re-run: it resumes."""
    matches = list_matches(cfg, source)
    for folder in (cfg.events_dir, cfg.spans_dir, cfg.matches_path.parent):
        folder.mkdir(parents=True, exist_ok=True)
    matches.to_parquet(cfg.matches_path, index=False)

    for i, match_id in enumerate(matches["match_id"], start=1):
        events_path = cfg.events_dir / f"{match_id}.parquet"
        if not events_path.exists():
            events, spans = prepare_match(source.raw_events(int(match_id)), int(match_id))
            spans.to_parquet(cfg.spans_dir / f"{match_id}.parquet", index=False)
            events.to_parquet(events_path, index=False)  # written last: marks the match as done
        if i % 25 == 0 or i == len(matches):
            log.info("ingest: %d/%d matches", i, len(matches))
    return matches


def shocks(cfg: Config) -> pd.DataFrame:
    return build_shocks(cfg)


def estimate(cfg: Config) -> pd.DataFrame:
    """Write results.csv, balance.csv and the forest plot for this config."""
    table = pd.read_parquet(cfg.shocks_path)
    kwargs = {"controls": cfg.controls, "n_boot": cfg.n_boot, "seed": cfg.seed}
    adjusted = est.estimate_all(table, adjust=True, **kwargs)
    naive = est.estimate_all(table, adjust=False, **kwargs)
    placebo = est.balance(table, **kwargs)

    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    adjusted.to_csv(cfg.out_dir / "results.csv", index=False)
    naive.to_csv(cfg.out_dir / "results_unadjusted.csv", index=False)
    placebo.to_csv(cfg.out_dir / "balance.csv", index=False)

    title = f"{cfg.name}: {cfg.window_minutes:g} minutes after scoring (controls: {cfg.controls})"
    figure = forest({"shooter only": naive, "minus teammates": adjusted}, title)
    figure.savefig(cfg.out_dir / "forest.png", dpi=200)
    log.info("estimate: wrote results, balance check and figure to %s", cfg.out_dir)
    return adjusted
