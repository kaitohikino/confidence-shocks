# confidence-shocks

[![CI](https://github.com/kaitohikino/confidence-shocks/actions/workflows/ci.yml/badge.svg)](https://github.com/kaitohikino/confidence-shocks/actions/workflows/ci.yml)

**Does a soccer player's game change after something that should move his confidence, and which parts of it move most?**

Confidence is never in the data, so this project looks for events that should shift it and measures what the player does next. The working hypothesis is that confidence shows up in **choices** (what a player attempts) before it shows up in **execution** (how well it comes off).

## Approach

1. **A lottery.** Given a shot's expected-goals value (xG), whether it goes in is close to a weighted coin flip. Players who scored are compared with players whose similar shot was saved or hit the post.
2. **After the shot, net of teammates, adjusted for before.** For each shot, the shooter's next 15 minutes are measured relative to his teammates', which removes what a new scoreline does to the whole team. The comparison adjusts for his previous 15 minutes and his usual level, so a player who happened to be quiet before scoring is not mistaken for one whom scoring woke up (regression to the mean).
3. **Honest uncertainty.** Intervals come from resampling whole matches, p-values are corrected for testing many attributes, and two checks run before any result is read: the groups must match on score and minute, and the same estimator run one window *before* the shot must find nothing.

Details and the pre-specified analysis are in [`docs/analysis_plan.md`](docs/analysis_plan.md). Where the project is going is in [`docs/roadmap.md`](docs/roadmap.md).

## Results

None yet. This section will hold the headline figure and a three-sentence summary, including null results.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/kaitohikino/confidence-shocks.git
cd confidence-shocks
make setup      # install dependencies and git hooks
make test       # runs on synthetic data, no download needed
make all        # 2022 World Cup: download, build the shock table, estimate
```

Outputs land in `reports/wc2022/`: `checks.csv` (read this first), `results.csv`, `results_unadjusted.csv`, `balance.csv`, `placebo.csv` and `forest.png`.

To explore interactively, run `uv run jupyter lab` and open the numbered notebooks: `01_audit`, `02_shocks`, `03_results`.

The main analysis uses full league seasons, which is a larger download:

```bash
make audit CONFIG=configs/leagues_2015_16.yaml   # check what the free data really contains
make all   CONFIG=configs/leagues_2015_16.yaml
```

## Pipeline

| Step | Command | Reads | Writes |
|---|---|---|---|
| Audit | `make audit` | StatsBomb index | a printed table of matches and teams per competition |
| Ingest | `make ingest` | StatsBomb events | `data/interim/events/`, `data/interim/spans/` (one tidy parquet per match) |
| Shocks | `make shocks` | interim tables | `data/processed/<config>/shocks.parquet` (one row per shot) |
| Estimate | `make estimate` | shock table | `reports/<config>/` |

Every step is a plain function in `src/confidence_shocks/pipeline.py`. A run is fully described by one YAML file in `configs/`.

## Layout

```
configs/                 one YAML per analysis run
data/                    never committed; see data/README.md for sources and terms
docs/                    roadmap, analysis plan, references
notebooks/               numbered, exploratory; logic that stabilises moves into src/
src/confidence_shocks/
    data/statsbomb.py    the only module that talks to the data provider
    prep.py              raw events -> tidy events + on-pitch spans
    features.py          events -> choice and execution metrics
    shocks.py            one row per shot with before/after levels
    estimate.py          weighted regression, cluster bootstrap, FDR, balance and placebo checks
    viz/plots.py         figures
    pipeline.py, cli.py  steps and command line
tests/                   synthetic matches, no network
```

## Data and attribution

Match data comes from [StatsBomb open data](https://github.com/statsbomb/open-data) and is not redistributed here; the code downloads it on demand. Anything published from this project credits StatsBomb as the data source, as their terms require. Other sources and their terms are listed in [`data/README.md`](data/README.md).

## Development

```bash
make lint      # ruff check + format check
make format    # auto-fix
make test
```

CI runs the same three on every push.

## License and citation

Code is MIT licensed. To cite, see [`CITATION.cff`](CITATION.cff).
