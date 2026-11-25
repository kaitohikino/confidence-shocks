# Analysis plan

Written before the league data is analysed, and committed, so that choices made here cannot be tuned to the results. Changes after that point go in the deviations log at the bottom.

## Question

Does scoring change what a player does in the following minutes, and does it change choices more than execution?

## Hypotheses

- **H1 (choice):** after scoring, a player's choice index rises relative to a player whose comparable shot did not go in.
- **H2 (execution):** the execution index changes less than the choice index.
- **H3 (asymmetry, secondary):** negative shocks move behaviour more than positive ones.

## Unit and sample

One row per open-play shot (penalties excluded) where the shooter was on the pitch for the full window before and after. Competitions: the 2015/16 leagues confirmed by `make audit CONFIG=configs/leagues_2015_16.yaml` on 2026-11-25: LIST THEM HERE WITH MATCH COUNTS. A league with fewer than 300 matches is excluded, because that means the free data covers only one club.

## Treatment and comparison

- **Treated:** the shot was a goal.
- **Primary control:** the shot was on target and saved (`controls: on_target`).
- Controls are weighted by `xg / (1 - xg)` so both groups share the same xG mix.

## Outcomes

- **Primary:** two indices, each built from the metrics in `features.METRICS`.
  - **Choice index** (how ambitious his play is): the mean of the z-scores of `shots`, `dribbles`, `fwd_pass_share` and `pass_length`. Higher means more ambitious.
  - **Execution index** (how well it comes off): the z-score of `pass_cmp`.
  - Z-scores use the mean and SD of each metric's before-shot level across all shots in the sample, so the same constants apply to every window. If a rate metric is missing in a window (no passes), the choice index averages the components that are present.
  - These definitions are fixed before the league estimates are run. Metrics added in Phase 2 are secondary outcomes only.
- **Secondary:** every individual metric in `features.METRICS`.
- Each outcome is the shooter's level in the window after the shot, minus the average teammate's level in the same window.

## Estimation and inference

- The two primary outcomes are corrected with Holm's method at α = 0.05. The primary specification is teammate-adjusted, `method: ancova`, `controls: on_target` and a 15-minute window.
- Weighted least squares of the outcome on a goal indicator and three before-shot covariates (`method: ancova`, `estimate.design` and `estimate.att`): the shooter's level in the window before the shot, the average teammate's level in that window, and the shooter's usual before-shot level in his other matches. Each covariate gets its own slope.
- Why not after-minus-before changes: on the 2022 World Cup test run, scorers had been less involved than controls before the shot, and every change-score "effect" pointed the opposite way to that gap (correlation −0.96 across the nine metrics), the signature of regression to the mean. Change scores (`method: change`) are reported as a robustness check only.
- 95% intervals from a bootstrap that resamples whole matches.
- Secondary metrics: Benjamini-Hochberg q-values. A secondary finding is reported as a finding only if q < 0.05.
- Window: 15 minutes each side.

## Smallest effect of interest

**0.1 SD** of the after-shot level, for both indices. Smaller shifts would not be visible in how a player looks on the pitch, and the World Cup test run puts individual-metric effects below about 0.3 SD. If a 95% interval lies entirely inside ±0.1 SD, the result is reported as "no meaningful effect".

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
