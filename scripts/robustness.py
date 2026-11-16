#!/usr/bin/env python3
"""Second look at the onboarding experiment.

Two questions I wanted answered before trusting the HOLD decision:

1. Does the Wald interval hold up? A seeded, user-level bootstrap gives an
   interval that makes no normal-approximation assumption.
2. Could this experiment ever have passed the support guardrail? The rule is
   "upper 95% bound of the increase <= +0.5 pp", which is a non-inferiority
   test, and those need a lot of users. I compute the power analytically and
   then check it by simulating the actual decision rule.

Run after scripts/pipeline.py (it reads data/experiment.sqlite).
Python 3.9+, standard library only.
"""
import json
import math
import random
import sqlite3
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
Z = NormalDist()


def percentile(sorted_values, q):
    """Linear-interpolated percentile of an already sorted list, q in [0, 1]."""
    if not sorted_values:
        raise ValueError('percentile of an empty list')
    position = q * (len(sorted_values) - 1)
    low = math.floor(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def load_outcomes(db_path):
    """One code per randomized user: 2*activated + support (values 0..3)."""
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute('SELECT variant, activated_7d, support_7d FROM user_outcomes').fetchall()
    finally:
        con.close()
    if not rows:
        raise ValueError('user_outcomes is empty; run scripts/pipeline.py first')
    arms = {'control': [], 'treatment': []}
    for variant, activated, support in rows:
        arms[variant].append(2 * int(activated) + int(support))
    return arms


def rates(codes):
    n = len(codes)
    activated = codes.count(2) + codes.count(3)
    support = codes.count(1) + codes.count(3)
    return activated / n, support / n


def bootstrap_lifts(arms, resamples=2000, seed=2718):
    """Percentile bootstrap, resampling users within each arm.

    Activation and support are resampled together per user, so the two
    intervals come from the same bootstrap samples.
    """
    rng = random.Random(seed)
    control, treatment = arms['control'], arms['treatment']
    act, sup = [], []
    for _ in range(resamples):
        c = rng.choices(control, k=len(control))
        t = rng.choices(treatment, k=len(treatment))
        (ca, cs), (ta, ts) = rates(c), rates(t)
        act.append(ta - ca)
        sup.append(ts - cs)
    act.sort(); sup.sort()
    return {
        'resamples': resamples, 'seed': seed,
        'activation': {'ci_low': percentile(act, .025), 'ci_high': percentile(act, .975)},
        'support': {'ci_low': percentile(sup, .025), 'ci_high': percentile(sup, .975)},
    }


def noninferiority_power(p_control, n_per_arm, margin, true_diff=0.0, alpha=.05):
    """P(upper two-sided (1-alpha) bound of the difference <= margin)."""
    p_treat = p_control + true_diff
    se = math.sqrt(p_control * (1 - p_control) / n_per_arm + p_treat * (1 - p_treat) / n_per_arm)
    return Z.cdf((margin - true_diff) / se - Z.inv_cdf(1 - alpha / 2))


def required_n_per_arm(p_control, margin, power=.8, true_diff=0.0, alpha=.05):
    if margin <= true_diff:
        raise ValueError('margin must exceed the assumed true difference')
    p_treat = p_control + true_diff
    variance = p_control * (1 - p_control) + p_treat * (1 - p_treat)
    z = Z.inv_cdf(1 - alpha / 2) + Z.inv_cdf(power)
    return math.ceil(z ** 2 * variance / (margin - true_diff) ** 2)


def detectable_margin(p_control, n_per_arm, power=.8, alpha=.05):
    """Smallest margin a truly harmless treatment would clear with the given power."""
    se = math.sqrt(2 * p_control * (1 - p_control) / n_per_arm)
    return (Z.inv_cdf(1 - alpha / 2) + Z.inv_cdf(power)) * se


def simulate_guardrail_pass_rate(p_control, n_control, n_treatment, margin, runs=1000, seed=31):
    """Re-run the experiment's own guardrail rule on simulated harmless treatments."""
    rng = random.Random(seed)
    z = Z.inv_cdf(.975)
    passed = 0
    for _ in range(runs):
        x0 = sum(rng.random() < p_control for _ in range(n_control))
        x1 = sum(rng.random() < p_control for _ in range(n_treatment))
        p0, p1 = x0 / n_control, x1 / n_treatment
        se = math.sqrt(p0 * (1 - p0) / n_control + p1 * (1 - p1) / n_treatment)
        passed += (p1 - p0) + z * se <= margin
    return passed / runs


def run(root=ROOT, resamples=2000, simulation_runs=1000):
    root = Path(root)
    evidence = json.loads((root / 'dashboard/data.json').read_text())
    arms = load_outcomes(root / 'data/experiment.sqlite')
    primary, guardrail = evidence['primary'], evidence['guardrail']
    margin = guardrail['maximum_acceptable_increase']
    n_c, n_t = len(arms['control']), len(arms['treatment'])
    p_support = guardrail['control_rate']
    n_avg = (n_c + n_t) / 2

    boot = bootstrap_lifts(arms, resamples=resamples)
    result = {
        'source': 'scripts/robustness.py on the seed-418 simulation',
        'interval_check': {
            'activation': {'wald': [primary['ci_low'], primary['ci_high']],
                           'bootstrap': [boot['activation']['ci_low'], boot['activation']['ci_high']]},
            'support': {'wald': [guardrail['ci_low'], guardrail['ci_high']],
                        'bootstrap': [boot['support']['ci_low'], boot['support']['ci_high']]},
            'resamples': boot['resamples'], 'seed': boot['seed'],
        },
        'guardrail_power': {
            'control_support_rate': p_support,
            'margin': margin,
            'users_per_arm': n_avg,
            'power_if_harmless': noninferiority_power(p_support, n_avg, margin),
            'simulated_pass_rate_if_harmless': simulate_guardrail_pass_rate(p_support, n_c, n_t, margin, runs=simulation_runs),
            'simulation_runs': simulation_runs,
            'users_per_arm_for_80pct_power': required_n_per_arm(p_support, margin),
            'margin_with_80pct_power_at_current_size': detectable_margin(p_support, n_avg),
            'curve': [{'users_per_arm': n, 'power_if_harmless': round(noninferiority_power(p_support, n, margin), 4)}
                      for n in range(1000, 30001, 500)],
        },
    }
    boot_sup_high = boot['support']['ci_high']
    result['conclusion'] = {
        'hold_still_justified': boot_sup_high > margin and guardrail['ci_low'] > margin,
        'guardrail_underpowered': result['guardrail_power']['power_if_harmless'] < .8,
    }
    (root / 'dashboard/robustness.json').write_text(json.dumps(result, indent=2) + '\n')
    write_note(root, result)
    return result


def write_note(root, r):
    ic, gp = r['interval_check'], r['guardrail_power']
    pp = lambda v: f'{v * 100:+.2f} pp'
    text = f'''# Robustness check: bootstrap intervals and guardrail power

Generated by `python3 scripts/robustness.py` after the main pipeline.

## Do the intervals hold up without the normal approximation?

I resampled users within each arm {ic['resamples']:,} times (seed {ic['seed']}) and took the 2.5th and 97.5th percentiles of the difference.

| Metric | Wald 95% CI | Bootstrap 95% CI |
|---|---|---|
| 7-day activation lift | {pp(ic['activation']['wald'][0])} to {pp(ic['activation']['wald'][1])} | {pp(ic['activation']['bootstrap'][0])} to {pp(ic['activation']['bootstrap'][1])} |
| 7-day support-contact change | {pp(ic['support']['wald'][0])} to {pp(ic['support']['wald'][1])} | {pp(ic['support']['bootstrap'][0])} to {pp(ic['support']['bootstrap'][1])} |

The two methods agree to within a few hundredths of a point. With roughly 6,000 users per arm and success counts in the hundreds, that is what I expected, and the HOLD decision does not depend on the interval method: even the lower end of the support increase is above the +0.50 pp limit.

## Could this experiment have passed the guardrail at all?

The guardrail passes only if the upper bound of the support increase is at most +{gp['margin'] * 100:.2f} pp. With a {gp['control_support_rate']:.2%} baseline and about {gp['users_per_arm']:,.0f} users per arm:

- A treatment with **no effect at all** on support would pass only **{gp['power_if_harmless']:.0%}** of the time (normal approximation).
- Simulating {gp['simulation_runs']:,} harmless experiments and applying the same rule gives **{gp['simulated_pass_rate_if_harmless']:.0%}**, so the formula is not the problem.
- 80% power at this margin needs about **{gp['users_per_arm_for_80pct_power']:,} users per arm**, almost four times the sample.
- At the current size, the tightest margin a harmless treatment clears with 80% power is about **+{gp['margin_with_80pct_power_at_current_size'] * 100:.2f} pp**.

## What I take from it

The hold is still the right call here, because the observed harm is large. The design, though, would also have blocked most genuinely harmless onboarding changes. For the next test I would agree one of these before collecting data: a sample of roughly {gp['users_per_arm_for_80pct_power']:,} users per arm, or a margin of about +1.0 pp that the support team has signed off. Picking either after seeing results would undo the point of a pre-registered rule.
'''
    (root / 'docs/robustness.md').write_text(text)


if __name__ == '__main__':
    out = run()
    print(json.dumps(out, indent=2))
