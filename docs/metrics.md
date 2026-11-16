# Metric catalog v1 and dashboard contract

All periods are calendar dates in UTC. The fixture stores date-level events, so seven days means offsets 0 through 6 inclusive, not a rolling 168-hour timestamp window. Owner: project analyst. Unit of analysis: assigned user.

| Metric | Numerator | Denominator | Important rule |
|---|---|---|---|
| Activation 7d | assigned users with first_value at offsets 0–6 | all assigned users after every primary window matures | ITT; not exposure-conditioned |
| Support contact 7d | assigned users with ≥1 support_contact at offsets 0–6 | all assigned users | more is harmful; +0.5 pp upper bound gate |
| Exposure | assigned users with exposed at offsets 0–6 | all assigned users | diagnostic funnel step |
| Workspace creation | assigned users with workspace_created at offsets 0–6 | all assigned users | diagnostic; sequence guaranteed by simulation only |
| Exact-day D7 retention | eligible assigned users with active at offset 7 | assigned users with ≥7 observed days | not 'returned at any time within seven days' |
| Exact-day D30 retention | eligible assigned users with active at offset 30 | assigned users with ≥30 observed days | null when eligible count is zero |
| Absolute lift | treatment rate minus control rate | n/a | multiply by 100 to display percentage points |
| Relative lift | absolute lift / control rate | n/a | distinct from percentage-point lift |
| SRM | chi-square against 50/50 assignment | all assigned users | p <0.001 blocks launch |

`dashboard/data.json` schema:

- `project`, `data_label`, `as_of`, `assignment_window`, `users`: provenance and scope.
- `decision`, `decision_reason`: computed decision and explanation for this fixture.
- `primary`: rates, successes, denominators, absolute and relative lift, `ci_low`, `ci_high`, `p_value`, method. **All rates and interval values are fractions**, not percentages.
- `guardrail`: the same effect fields plus `maximum_acceptable_increase`, `passed`, and rule.
- `srm`: chi-square statistic, p-value, threshold, pass/fail.
- `variants`: assigned, exposed, workspace, activated, support, eligible and retained counts for each arm.
- `funnel`: stage rows with absolute `control` and `treatment` user counts. Denominator is assigned users if displayed as a rate.
- `cohorts`: week × variant rows, total users, `eligible_d7/d30`, `retained_d7/d30`, `d7_rate/d30_rate`. Preserve null as **Not mature**, never 0%.
- `segments`: exploratory counts; no segment significance or causal-targeting claim.
- `quality`: raw/clean/duplicate/rejected counts, primary maturity and reconciliation flags.
- `architecture`, `analysis_policy`: compact metadata for the portfolio.

A dashboard may filter descriptive cohort tables by variant/week. Do not re-label an overall experiment p-value as a filtered segment result. The overall launch decision uses the full registered sample.
