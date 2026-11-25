# Data

Nothing in `raw/`, `interim/` or `processed/` is committed. The pipeline fetches third-party data on demand, and every transformation happens in code. `external/` is for small files made by hand (for example a player-ID crosswalk between providers) and is committed.

## Sources

| Source | What it is | Role in this project | Status |
|---|---|---|---|
| [StatsBomb / Hudl open data](https://github.com/hudl/open-data) | Event data for many competitions; 360 freeze frames for some | **Main dataset.** 2022 World Cup for development, full league seasons for the analysis | In use |
| [Impect open data](https://github.com/ImpectAPI/open-data) | Bundesliga event data | Replication on a second provider and season | Planned (Phase 5) |
| [Gradient Sports / PFF 2022 World Cup](https://www.gradientsports.com/blog/enhanced-2022-world-cup-dataset) | Tracking plus events for all 64 matches | Off-the-ball attributes (movement, work rate) for the same matches as StatsBomb's World Cup | Planned (Phase 5) |
| [SkillCorner open data](https://github.com/SkillCorner/opendata) | Broadcast tracking for a small sample of A-League matches | Prototyping tracking features only; too few matches for estimates | Optional |
| [Worldcup26](https://github.com/Alamyy/Worldcup26) | FIFA post-match report tables for the 2026 World Cup, aggregated per match | No within-match timing, so unusable for shock windows; possible cross-match descriptive use | Not used |

## Terms

- **StatsBomb:** free for research with attribution. Credit StatsBomb as the source in anything published, and read the user agreement in their repository before publishing.
- **Gradient Sports / PFF:** distributed after sign-up. Do not redistribute or commit any of it.
- **Impect, SkillCorner, Worldcup26:** each repository states its own licence. Read it and record it here before using the data.

## Provenance log

Record what was downloaded and when, so a result can be tied to a data version.

| Date | Config | Source version (commit or download date) | Matches | Notes |
|---|---|---|---|---|
| | | | | |

## Layout

```
raw/         untouched downloads from sources that need a manual download (e.g. PFF)
interim/     tidy per-match tables: events/<match_id>.parquet, spans/<match_id>.parquet
processed/   per config: matches.parquet, shocks.parquet
external/    hand-made lookup files (committed)
```

StatsBomb events are not kept in `raw/`: they are re-downloadable by `match_id`, and the tidy copy in `interim/` is much smaller.
