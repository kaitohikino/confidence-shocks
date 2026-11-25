# Analysis plan

Written before the league data is analysed, and committed, so that choices made here cannot be tuned to the results. Changes after that point go in the deviations log at the bottom.

## Question

Does scoring change what a player does in the following minutes, and does it change choices more than execution?

## Hypotheses

- **H1 (choice):** after scoring, a player's choice index rises relative to a player whose comparable shot did not go in.
- **H2 (execution):** the execution index changes less than the choice index.
- **H3 (asymmetry, secondary):** negative shocks move behaviour more than positive ones.

## Unit and sample

One row per open-play shot (penalties excluded) where the shooter was on the pitch for the full window before and after. Competitions: as listed in `configs/leagues_2015_16.yaml` after the Phase 1 audit.

## Treatment and comparison

- **Treated:** the shot was a goal.
- **Primary control:** the shot was on target and saved (`controls: on_target`).
- Controls are weighted by `xg / (1 - xg)` so both groups share the same xG mix.

## Outcomes

- **Primary:** choice index and execution index (defined in Phase 2; record the exact formula here before running).
- **Secondary:** every individual metric in `features.METRICS`.
- Each outcome is the shooter's after-minus-before change, minus the same change for the average teammate.

## Estimation and inference

- Weighted difference in means, goals minus controls (`estimate.att`).
- 95% intervals from a bootstrap that resamples whole matches.
- Secondary metrics: Benjamini-Hochberg q-values. A secondary finding is reported as a finding only if q < 0.05.
- Window: 15 minutes each side.

## Smallest effect of interest

**To fill in before running:** the smallest standardised effect worth caring about (for example 0.05 SD). If the interval lies entirely inside plus or minus this value, the conclusion is "no meaningful effect", which is a result, not a failure.

## Validity checks, run before reading results

1. `balance.csv`: no pre-shot quantity differs between groups after weighting.
2. Placebo timing: random fake shot times show no effect.

## Planned robustness

Listed in `docs/roadmap.md`, Phase 4. These are reported whatever they show.

## Deviations log

| Date | Change | Reason |
|---|---|---|
| | | |
