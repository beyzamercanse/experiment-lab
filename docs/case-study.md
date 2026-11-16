# Case study: more activations, still a no

Simulated experiment (seed 418), analysed as of 2026-10-31. The effects were built into the data, so this shows the method, not a real product result.

## The question

Guided workspace setup was meant to get new users to a first useful result within seven days. The product manager wanted to know whether to roll it out to everyone. The condition agreed up front: it must not create noticeably more support work.

## What I found

- 12,000 users were randomized: 6,035 control and 5,965 treatment. Everyone had a complete seven-day window.
- Activation went from 27.47% to 31.00%: **+3.52 pp**, 95% CI [1.90, 5.15] pp, p = 0.00002.
- Support contacts went up **+2.26 pp**, 95% CI [1.49, 3.03] pp. The agreed limit was +0.50 pp on the upper bound, so the guardrail fails by a wide margin.
- Allocation looks healthy (sample-ratio mismatch p = 0.5228).
- The raw events reconcile: 27,796 = 27,355 accepted + 437 replays + 4 quarantined.

**Decision: HOLD.** The flow works for activation, but something in it is confusing enough to send people to support. Shipping it would trade one problem for another.

## Why I trust the numbers

Every rate uses assigned users as the denominator, including the users who never saw onboarding. Events are deduplicated before they're joined to users, and each user collapses to one row, so repeated events can't inflate conversions. Retention only counts users old enough to have been observed for the full window. The most recent cohort shows "not mature" for D30 rather than a misleading zero.

## What I'd do next

1. Instrument each onboarding step and tag support tickets by reason. Right now the data shows *that* support went up, not *which step* caused it.
2. Fix or remove the step the tickets point to.
3. Before the rerun, agree the sample size and guardrail margin with the support team. [robustness.md](robustness.md) shows that at this sample size even a harmless change would pass the current guardrail only about 30% of the time.

## Caveats

The Wald interval is fine at these counts; the bootstrap in robustness.md agrees with it. Segment and retention views are exploratory and I don't draw subgroup conclusions from them. There was one analysis at a fixed date, with no peeking or early stopping.
