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
- Each outcome is the shooter's level in the window after the shot, minus the average teammate's level in the same window.

## Estimation and inference

- Weighted least squares of the outcome on a goal indicator and three before-shot covariates (`method: ancova`, `estimate.design` and `estimate.att`): the shooter's level in the window before the shot, the average teammate's level in that window, and the shooter's usual before-shot level in his other matches. Each covariate gets its own slope.
- Why not after-minus-before changes: on the 2022 World Cup test run, scorers had been less involved than controls before the shot, and every change-score "effect" pointed the opposite way to that gap (correlation −0.96 across the nine metrics), the signature of regression to the mean. Change scores (`method: change`) are reported as a robustness check only.
- 95% intervals from a bootstrap that resamples whole matches.
- Secondary metrics: Benjamini-Hochberg q-values. A secondary finding is reported as a finding only if q < 0.05.
- Window: 15 minutes each side.

## Smallest effect of interest

**To fill in before running:** the smallest standardised effect worth caring about (for example 0.05 SD). If the interval lies entirely inside plus or minus this value, the conclusion is "no meaningful effect", which is a result, not a failure.

## Validity checks, run before reading results

Both are written to `checks.csv` by `make estimate`, and failures are flagged in the log and the figure title.

1. **Balance:** score difference and match minute, which the estimator does not adjust for, differ by at most 0.1 SD between weighted groups (`max_smd`). Before-shot metric levels are reported in `balance.csv` for information; the estimator adjusts for them.
2. **Placebo:** the same estimator, moved one window back (outcome: the window before the shot; covariates: the window before that), shows no effect with q < 0.05 on any metric. A failure means goals were not a pure coin flip given xG and recent form; it is reported, and the results are read with that caveat.
3. Placebo timing (Phase 4): fake shot times for the same players show no effect.

## Planned robustness

Listed in `docs/roadmap.md`, Phase 4. These are reported whatever they show.

## Deviations log

| Date | Change | Reason |
|---|---|---|
| | | |
