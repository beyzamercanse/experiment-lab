# Experiment Lab — would you ship this onboarding?

A reproducible product analytics case study that reaches an uncomfortable but defensible decision: **hold a treatment that improves activation because it worsens support demand.**

**Best fit:** Data Analyst / Product Analyst, with analytics engineering evidence in event contracts, user-grain SQL marts, tests, and reproducible metric definitions.

**Data honesty:** All events and assignments are synthetic, generated with Python seed 418. The outcomes are simulated; no customer, employer, revenue benefit, or real-world experiment is claimed. Production architecture is a documented proposal, not a deployed cloud platform.

## 30-second project tour

- **Business:** Should guided onboarding launch if more users activate but support burden rises?
- **Data:** 12,000 randomized users; 27,796 raw events; 437 replays removed and four invalid events quarantined.
- **Finding:** Activation increases from 27.47% to 31.00% (+3.52 percentage points; 95% interval +1.90 to +5.15 pp).
- **Decision:** Hold. Support-contact increase is +2.26 pp, exceeding the pre-specified +0.50 pp guardrail.
- **Evidence:** [case study](docs/case-study.md), [architecture](docs/architecture.md), [analysis plan](docs/analysis-plan.md), [metric catalog](docs/metrics.md), [dashboard data](dashboard/data.json).

## Run from a fresh checkout

Python 3.9 or newer; standard library only. No keys, cloud account, or package installation.

```bash
python3 scripts/pipeline.py
python3 -m unittest discover -s tests -v
```

The pipeline generates raw CSV fixtures, builds `data/experiment.sqlite`, runs the SQL marts, writes `dashboard/data.json`, and refreshes the evidence-based case study. It deliberately rebuilds its local database: this is a deterministic batch analysis, not an incremental ingestion implementation.

## Repository map

```text
scripts/pipeline.py       seeded fixtures, ingestion, statistics, JSON export
sql/marts.sql             user outcomes, variant summary, mature retention cohorts
tests/test_pipeline.py    inference, SRM, windows, ITT, quality, rerun, guardrail tests
docs/architecture.md      grains, lineage, tradeoffs, production extension
docs/analysis-plan.md     design, sample size, decision rules, limitations
docs/metrics.md           versioned metric definitions and dashboard data schema
docs/case-study.md        generated findings and five-slide narrative
dashboard/data.json      measured dashboard payload, suitable for static hosting
.github/workflows/ci.yml  rerun pipeline and tests on pull requests
```

## What makes this stronger than a conversion dashboard

1. Randomized assignments, not exposed users, drive the primary denominator.
2. Duplicate events cannot multiply users or conversions after the user-grain aggregation.
3. D30 rates exclude immature users; missing observation is represented as null, not churn.
4. Confidence intervals and a support guardrail constrain the launch recommendation.
5. An allocation audit detects sample-ratio mismatch; a deliberately skewed fixture tests the failure path.
6. Every dashboard metric comes from the committed analysis code and reproducible input generator.

## CV wording after reproducing and understanding the project

> Built a reproducible Python/SQL experimentation pipeline for 12,000 simulated users, validating allocation and event quality, estimating activation lift with confidence intervals, and implementing maturity-aware retention and launch guardrails.

Avoid saying you increased company activation or saved money. Those would not be supported by synthetic data.

## Interview walkthrough

Explain why the denominator is assigned users; demonstrate the SQL window boundary test; show how immature D30 cohorts become null; then defend the hold decision despite a statistically significant activation result. Be ready to discuss interference, instrumentation bias, the difference between statistical and practical significance, and why exploratory subgroup effects do not justify a targeted rollout.

## AI usage and verification

This repository was created with AI assistance. The candidate should reproduce the results, review every metric, and make a documented independent extension before representing it as their own portfolio work. Suggested extension: replace the simulation with a licensed randomized dataset, assess power for the guardrail, and compare the normal approximation with a bootstrap. Keep any revised decision rule in a new analysis version rather than changing it after seeing results.

## Interactive dashboard and portfolio

[Open the portfolio dashboard](https://beyza-data-portfolio.dewyisle36.chatgpt.site/#experiment-lab/dashboard) · [Project case study](https://beyza-data-portfolio.dewyisle36.chatgpt.site/#experiment-lab)

The hosted portfolio initially requires owner access. The self-contained local dashboard is available without hosting: open `dashboard/index.html`. After rerunning the data pipeline, run `python3 dashboard/refresh.py` to refresh its browser snapshot. All default dashboard figures are synthetic and generated by the pipeline.

AI assisted the initial code and documentation. Before using this project in applications, reproduce it, review its definitions and add an independently understood extension.
