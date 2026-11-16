# Case study: a better activation rate is not enough

**Evidence type:** deterministic synthetic experiment, not a client engagement. Generated from seed 418; analyzed as of 2026-10-31.

## Decision

**HOLD: do not launch the current onboarding treatment.** The simulation improves activation while creating an unacceptable support burden. Investigate the confusing step and rerun a separately registered experiment.

## Business question

Would a guided workspace setup help new users reach their first useful result within seven days, without causing more support contacts? The product manager owns the launch decision; the analyst owns definitions, estimation, and limitations.

## Measured findings

- Randomized users: 12,000; control 6,035, treatment 5,965. All have a complete seven-day outcome window.
- Activation: 27.47% control versus 31.00% treatment.
- Absolute lift: 3.52 percentage points; 95% interval [1.90, 5.15] pp; two-sided p=0.00002.
- Support-contact increase: 2.26 pp; 95% interval [1.49, 3.03] pp. The allowed increase is 0.50 pp, and the upper bound must be below that threshold. The guardrail fails.
- Sample-ratio mismatch p=0.5228; threshold 0.001. This allocation check passes, but cannot prove every aspect of randomization is valid.
- Raw event audit: 27,796 = 27,355 accepted + 437 duplicate replays + 4 quarantined.

## Why the analysis is defensible

The randomized-user table drives every denominator. A user who never saw onboarding remains in the primary analysis. Events are deduplicated before joining; the per-user outcome mart prevents event multiplicity from inflating conversions. Retention excludes users whose observation window is immature and always displays eligible counts. Weekly cohorts report the mature subset; the last cohort's D30 result is not estimable.

## Actions and uncertainty

1. Instrument individual onboarding steps and qualitative support reasons before another test.
2. Remove or simplify the step implicated by support investigation; this dataset does not identify a causal mechanism.
3. Register the next test's sample size, primary metric, and guardrail before collecting its data.

The Wald confidence interval is an approximation appropriate to this large simulated sample, not a universal method for sparse counts. The data-generating process deliberately embeds a treatment effect and a harmful guardrail effect. This project proves an analysis workflow, not a real product lift, external validity, or revenue impact. Segments and retention are exploratory; no subgroup launch claims are supported. No repeated peeking or post-hoc stopping rule is used.

## Five-slide narrative

1. Decision: activation must improve without more support burden.
2. Measurement: randomized-user grain, seven-day windows, event quality audit.
3. Evidence: lift and uncertainty, plus guardrail deterioration.
4. Recommendation: hold and redesign; avoid declaring a win from conversion alone.
5. Next experiment: revised onboarding, registered metrics, fixed sample, reviewed tracking.
