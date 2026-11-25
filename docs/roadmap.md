# Roadmap

Seven phases. Each has a deliverable and a "done when" test. Time estimates assume part-time work alongside courses and are rough.

The order matters: the simple, well-identified design comes first, and the machine-learning layer is added on top of it. A flexible model will always find *some* latent state; the shock design is what shows whether that state means anything.

## Phase 0 · Repo and environment (half a day)

- [ ] `make setup`, `make test`, `make all` all succeed locally
- [ ] Pushed to GitHub with CI green
- [ ] `uv.lock` committed

**Done when:** a fresh clone reproduces `reports/wc2022/forest.png` with three commands.

## Phase 1 · Data audit and ingest (about 1 week)

- [ ] `make audit CONFIG=configs/leagues_2015_16.yaml`; record match and team counts in `data/README.md`. Drop any league that is not a full season
- [ ] `make ingest` for the leagues (large download; it resumes if interrupted)
- [ ] Add a validation step: the final `score_diff` reconstructed from events must equal `home_score - away_score` for every match. Log the exceptions
- [ ] Sanity table: goals, shots and passes per match by league, compared with public figures

**Deliverable:** `notebooks/01_audit.ipynb` (score validation and sanity table are already in it). **Done when:** every ingested match passes validation or is listed as an exception.

## Phase 2 · Attributes (about 1 week)

The starting set is in `features.py`. Extend it, with a test for each addition:

- [ ] Shooting choice: xG per shot, shot distance, share of shots from outside the box
- [ ] Passing choice: progressive passes, long-pass share, passes into the box
- [ ] Execution under pressure: pass completion when `under_pressure`
- [ ] Involvement: touches in the final third, time between receipt and next action
- [ ] Pass difficulty model (event-only expected pass completion), so "risk" is how hard the attempted passes were and execution is completion minus expected
- [ ] Define one **choice index** and one **execution index** (standardised averages). These are the primary outcomes

**Deliverable:** `notebooks/04_attributes.ipynb` showing distributions by position. **Done when:** the indices are fixed in `docs/analysis_plan.md`.

## Phase 3 · Main estimate (about 1 week)

- [ ] Freeze `docs/analysis_plan.md` and commit it **before** running on the league data
- [ ] `make all CONFIG=configs/leagues_2015_16.yaml`
- [ ] Read `checks.csv` first (balance and placebo). If a check fails, understand why before looking at results
- [ ] `notebooks/02_shocks.ipynb` (event study around the shot) and `notebooks/03_results.ipynb`

**Deliverable:** `reports/leagues_2015_16/`. **Done when:** the primary result is written up in three sentences, whatever it shows.

## Phase 4 · Robustness (1 to 2 weeks)

- [ ] Window length: 5, 10, 20 minutes (code ready in `03_results`)
- [ ] Control group: `all`, `on_target`, `post`, `near_miss` (code ready in `03_results`)
- [ ] Estimator: `method: change` against `ancova`
- [ ] Drop the first few minutes after the shot (celebration and kick-off)
- [ ] Score state: level games only; leading versus trailing
- [ ] Event-study plot in 5-minute bins, from 15 minutes before to 30 after
- [ ] Placebo timing: fake "shots" at random times for the same players
- [ ] Negative shocks: missed big chance (xG above 0.3), error leading to an opponent shot, being dribbled past
- [ ] Heterogeneity by position group, age and home/away
- [ ] Next-match selection: did scorers get more minutes in the following match?

**Deliverable:** control-group and window robustness are in `notebooks/03_results.ipynb`; the rest goes in `notebooks/05_robustness.ipynb`, with a robustness table. **Done when:** the headline result is stable across these, or the write-up says clearly where it is not.

## Phase 5 · Second sources (1 to 2 weeks)

- [ ] **Impect Bundesliga:** add `data/impect.py` with the same two functions as `data/statsbomb.py` (kloppy can load it), map its event types onto the tidy schema, rerun Phases 3 and 4. A result that appears with two providers is much harder to dismiss
- [ ] **PFF 2022 World Cup tracking:** off-the-ball attributes around the same shots already in the StatsBomb World Cup table: distance covered, sprints, distance from the ball. Small sample, so descriptive only

**Done when:** a replication table sits beside the main result.

## Phase 6 · Machine-learning layer (3 to 4 weeks)

Each model here produces a better *outcome variable*. The estimator from Phase 3 stays the same.

- [ ] **6a · Expected-action baseline.** Gradient-boosted model of the next action type and pass risk, given location, score state, minute and player. The outcome becomes "riskier than this player normally is here". This is the benchmark anything fancier must beat
- [ ] **6b · Next-event transformer.** Fine-tune a small player-conditioned sequence model (the Large Events Model code is public). Outcome: per-action surprisal. Leave post-shot events out of the model's context so it cannot absorb the effect
- [ ] **6c · Latent state across matches.** GLM-HMM or switching state-space model (`ssm`, `dynamax`) on per-match choice and execution indices, with lottery shocks as inputs. Exploratory: states may capture role or opponent, so check what they correlate with

**Done when:** 6a is reported beside the Phase 3 result, and 6b or 6c is attempted with its limits stated.

## Phase 7 · Write-up (about 1 week)

- [ ] README results section: one figure, three sentences
- [ ] `docs/report.md`: question, design, data, results, robustness, limits
- [ ] Tag `v1.0.0`; optional Zenodo DOI
- [ ] Short public post, crediting StatsBomb

## Not doing (and why)

- Tracking-based pass-option models on SkillCorner: ten matches cannot support estimates.
- Anything from the 2026 World Cup report tables: no within-match timing.
