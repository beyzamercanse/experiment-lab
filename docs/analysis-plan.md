# Analysis plan v1

This is the design specification for a **simulated** experiment. It is supplied with the generator for reproducibility; it is not evidence that a real experiment was prospectively registered.

## Hypothesis and unit

Guided onboarding increases the probability that a new user reaches a first useful result during days 0–6 after assignment. Randomize at user level, 50/50, once per user. The simulation assumes independent users, no cross-variant contamination, complete tracking, and no interference. Real collaborative workspaces might require account-level randomization and cluster-aware analysis instead.

## Eligibility and timing

- Enroll 12,000 new users across 2026-09-01 through 2026-10-15.
- Analyze once as of 2026-10-31, after all seven-day primary windows mature.
- Keep assigned users who were never exposed (intent to treat).
- D7/D30 retention is exploratory exact-day active-user retention; use only users with at least that many observed days. Publish both total cohort and eligible count.

## Primary and guardrail

- Primary: first_value on days 0–6 divided by all assigned users, once the primary windows mature.
- Primary statistical criterion: two-sided 95% CI for treatment minus control entirely above zero.
- Practical criterion: observed absolute gain at least 1.5 percentage points. This is a decision threshold; it is distinct from the planning MDE.
- Guardrail: any support_contact on days 0–6 divided by all assigned users. The two-sided 95% CI upper bound for the increase must be at most +0.5 pp. This is a conservative non-inferiority gate, not a test that 'no significant difference' proves safety.
- SRM gate: allocation chi-square p ≥ 0.001.
- Launch only when all gates pass. Otherwise hold; identify which gate failed.

## Sample size illustration

For baseline activation 28%, a planning minimum detectable difference of 2.5 pp, 80% power, and two-sided alpha 0.05, a simple equal-arm normal approximation gives:

`ceil(2 × (1.96 + 0.8416)^2 × 0.28 × 0.72 / 0.025^2) ≈ 5,064 users per arm.`

The 12,000-user simulation exceeds this approximation. A real experiment needs a full power calculation, separate guardrail power assessment, traffic estimates, clustering adjustment where relevant, and an explicit stopping date. This sample may be too small to certify a very tight support guardrail even when its true effect is zero.

## Inference

Use an unpooled standard error for the absolute-rate-difference 95% Wald interval; use the pooled null standard error for the two-sided z-test p-value. The normal approximation is appropriate for these large success and failure counts. Sparse events require a different interval/test. The primary test is singular; segment slices and retention are exploratory and are not used to make post-hoc significance claims.

## Exclusions and limitations

Exclude only invalid events from metric construction; do not remove randomized users due to bad or absent exposure. The generator intentionally adds duplicate event replays and contract violations for testing. This simulation cannot establish a real product effect, a causal explanation for support demand, revenue impact, seasonal stability, or external validity. A prelaunch instrumentation check, privacy review, and product-owner review are proposed operational steps, not completed production work.
