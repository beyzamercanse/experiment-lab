#!/usr/bin/env python3
"""Reproducible, synthetic experiment analysis. Python 3.9+, no dependencies."""
import csv
import json
import math
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 10, 31)
EVENT_TYPES = {'exposed', 'workspace_created', 'first_value', 'active', 'support_contact'}


def difference_in_proportions(x_control, n_control, x_treatment, n_treatment):
    """Unpooled Wald interval; pooled two-sided z test, suitable for large counts."""
    if min(n_control, n_treatment) <= 0:
        raise ValueError('Both denominators must be positive')
    if not (0 <= x_control <= n_control and 0 <= x_treatment <= n_treatment):
        raise ValueError('Success counts must be within denominators')
    p0, p1 = x_control / n_control, x_treatment / n_treatment
    delta = p1 - p0
    se = math.sqrt(p0 * (1-p0) / n_control + p1 * (1-p1) / n_treatment)
    pooled = (x_control + x_treatment) / (n_control + n_treatment)
    pooled_se = math.sqrt(pooled * (1-pooled) * (1/n_control + 1/n_treatment))
    z = delta / pooled_se if pooled_se else 0.0
    return {'control_rate': p0, 'treatment_rate': p1, 'absolute_lift': delta,
            'relative_lift': delta / p0 if p0 else None,
            'ci_low': max(-1, delta - 1.959963984540054 * se),
            'ci_high': min(1, delta + 1.959963984540054 * se),
            'p_value': math.erfc(abs(z) / math.sqrt(2)), 'method': 'large-sample two-proportion z test; unpooled 95% Wald CI'}


def srm_test(control, treatment):
    total = control + treatment
    if total <= 0:
        raise ValueError('SRM requires nonempty assignments')
    expected = total / 2
    statistic = (control-expected)**2/expected + (treatment-expected)**2/expected
    return {'chi_square': statistic, 'p_value': math.erfc(math.sqrt(statistic/2)),
            'threshold': .001, 'passed': math.erfc(math.sqrt(statistic/2)) >= .001}


def mature(assigned_on, horizon, as_of=AS_OF):
    return (as_of - date.fromisoformat(assigned_on)).days >= horizon


def generate(root, seed=418):
    rng = random.Random(seed)
    raw = root / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    assignments, events = [], []
    event_sequence = 0
    def event(user, kind, day):
        nonlocal event_sequence
        if day <= AS_OF:
            event_sequence += 1
            events.append({'event_id': 'ev_%07d' % event_sequence, 'user_id': user,
                           'event_type': kind, 'event_date': day.isoformat()})
    for i in range(12000):
        user = 'u_%05d' % i
        assigned = date(2026, 9, 1) + timedelta(days=i % 45)
        variant = 'treatment' if rng.random() < .5 else 'control'
        segment = rng.choice(['small_team', 'solo', 'growing_team'])
        assignments.append({'user_id': user, 'variant': variant, 'assigned_on': assigned.isoformat(), 'segment': segment})
        exposed = rng.random() < .955
        workspace = exposed and rng.random() < .68
        activated = workspace and rng.random() < (.49 if variant == 'treatment' else .44)
        if exposed: event(user, 'exposed', assigned)
        if workspace: event(user, 'workspace_created', assigned + timedelta(days=1))
        if activated: event(user, 'first_value', assigned + timedelta(days=rng.randint(2, 6)))
        if rng.random() < (.060 if variant == 'treatment' else .042):
            event(user, 'support_contact', assigned + timedelta(days=rng.randint(0, 6)))
        for horizon, probability in [(7, .64 if activated else .075), (30, .43 if activated else .035)]:
            if rng.random() < probability:
                event(user, 'active', assigned + timedelta(days=horizon))
    # Replayed events and contract violations prove deduplication and quarantine paths.
    events.extend(dict(e) for e in events[:437])
    events.extend([{'event_id': 'orphan_'+str(i), 'user_id': 'unknown_'+str(i), 'event_type': 'exposed', 'event_date': '2026-10-01'} for i in range(3)])
    events.append({'event_id': 'invalid_type', 'user_id': 'u_00001', 'event_type': 'unknown_event', 'event_date': '2026-10-02'})
    for name, rows in [('assignments', assignments), ('events', events)]:
        with (raw / (name+'.csv')).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    return assignments, events


def run(root=ROOT):
    root = Path(root)
    assignments, raw_events = generate(root)
    (root/'data').mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(root/'data/experiment.sqlite')
    conn.executescript('DROP TABLE IF EXISTS assignments; DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS quarantine; '
        'CREATE TABLE assignments(user_id TEXT PRIMARY KEY, variant TEXT NOT NULL CHECK(variant IN (\'control\',\'treatment\')), assigned_on TEXT NOT NULL, segment TEXT NOT NULL); '
        'CREATE TABLE events(event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES assignments(user_id), event_type TEXT NOT NULL, event_date TEXT NOT NULL); '
        'CREATE TABLE quarantine(event_id TEXT, reason TEXT);')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executemany('INSERT INTO assignments VALUES (:user_id,:variant,:assigned_on,:segment)', assignments)
    known_users = {row['user_id'] for row in assignments}
    seen = set(); duplicate_count = 0; rejected = 0
    for row in raw_events:
        if row['event_id'] in seen:
            duplicate_count += 1; continue
        seen.add(row['event_id'])
        reason = 'unknown user' if row['user_id'] not in known_users else ('unknown event type' if row['event_type'] not in EVENT_TYPES else None)
        if reason:
            conn.execute('INSERT INTO quarantine VALUES (?,?)', (row['event_id'], reason)); rejected += 1; continue
        conn.execute('INSERT INTO events VALUES (:event_id,:user_id,:event_type,:event_date)', row)
    conn.executescript((ROOT/'sql/marts.sql').read_text().replace('{{as_of}}', AS_OF.isoformat()))
    conn.row_factory = sqlite3.Row
    variants = [dict(row) for row in conn.execute('SELECT * FROM variant_summary ORDER BY variant')]
    control, treatment = variants
    primary = difference_in_proportions(control['activated_7d'], control['assigned_users'], treatment['activated_7d'], treatment['assigned_users'])
    primary.update({'metric': '7-day activation (ITT)', 'control_n': control['assigned_users'], 'treatment_n': treatment['assigned_users'], 'control_successes': control['activated_7d'], 'treatment_successes': treatment['activated_7d']})
    guardrail = difference_in_proportions(control['support_7d'], control['assigned_users'], treatment['support_7d'], treatment['assigned_users'])
    guardrail.update({'metric': '7-day support contact (ITT)', 'maximum_acceptable_increase': .005,
                     'passed': guardrail['ci_high'] <= .005, 'decision_rule': '95% CI upper bound <= +0.5 percentage points'})
    srm = srm_test(control['assigned_users'], treatment['assigned_users'])
    eligible = all(row['primary_mature_users'] == row['assigned_users'] for row in variants)
    decision = 'SHIP' if srm['passed'] and eligible and primary['ci_low'] > 0 and primary['absolute_lift'] >= .015 and guardrail['passed'] else 'HOLD'
    cohorts = [dict(row) for row in conn.execute('SELECT * FROM retention_cohorts ORDER BY cohort_week,variant')]
    funnel = [{'stage': label, 'control': control[key], 'treatment': treatment[key]} for label,key in [('Assigned','assigned_users'),('Exposed','exposed'),('Created workspace','workspace_created'),('Activated within 7 days','activated_7d')]]
    quality = {'raw_events': len(raw_events), 'clean_events': conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],
               'duplicates_removed': duplicate_count, 'quarantined_events': rejected, 'primary_window_mature': eligible,
               'assignments_unique': len(known_users) == len(assignments), 'reconciliation_passed': len(raw_events) == duplicate_count + rejected + conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]}
    output = {'project': 'Experiment Lab', 'data_label': 'Synthetic randomized product experiment • seed 418 • no real business outcomes',
        'as_of': AS_OF.isoformat(), 'assignment_window': ['2026-09-01','2026-10-15'], 'users': len(assignments),
        'decision': decision, 'decision_reason': 'Activation improves, but the support-contact guardrail fails. Simplify onboarding and rerun a preregistered experiment.',
        'primary': primary, 'guardrail': guardrail, 'srm': srm, 'variants': variants, 'funnel': funnel, 'cohorts': cohorts,
        'quality': quality, 'segments': [dict(row) for row in conn.execute('SELECT segment,variant,COUNT(*) AS users,SUM(activated_7d) AS activated_7d FROM user_outcomes GROUP BY segment,variant')],
        'architecture': ['Seeded assignments + event log','Contract validation + deduplication','SQLite user outcomes','Experiment + retention marts','Decision dashboard'],
        'analysis_policy': {'primary_alpha': .05, 'srm_alpha': .001, 'practical_lift_threshold': .015, 'guardrail_limit': .005, 'unit':'randomized user','retention':'Exact-day activity; mature users only; ITT denominator'}}
    out = root/'dashboard'; out.mkdir(parents=True, exist_ok=True)
    (out/'data.json').write_text(json.dumps(output, indent=2)+'\n')
    conn.commit(); conn.close()
    write_case_study(root, output)
    return output


def write_case_study(root, d):
    p, g, q = d['primary'], d['guardrail'], d['quality']
    (root/'docs').mkdir(parents=True, exist_ok=True)
    text = f'''# Case study: a better activation rate is not enough

**Evidence type:** deterministic synthetic experiment, not a client engagement. Generated from seed 418; analyzed as of {d['as_of']}.

## Decision

**{d['decision']}: do not launch the current onboarding treatment.** The simulation improves activation while creating an unacceptable support burden. Investigate the confusing step and rerun a separately registered experiment.

## Business question

Would a guided workspace setup help new users reach their first useful result within seven days, without causing more support contacts? The product manager owns the launch decision; the analyst owns definitions, estimation, and limitations.

## Measured findings

- Randomized users: {d['users']:,}; control {p['control_n']:,}, treatment {p['treatment_n']:,}. All have a complete seven-day outcome window.
- Activation: {p['control_rate']:.2%} control versus {p['treatment_rate']:.2%} treatment.
- Absolute lift: {p['absolute_lift']*100:.2f} percentage points; 95% interval [{p['ci_low']*100:.2f}, {p['ci_high']*100:.2f}] pp; two-sided p={p['p_value']:.5f}.
- Support-contact increase: {g['absolute_lift']*100:.2f} pp; 95% interval [{g['ci_low']*100:.2f}, {g['ci_high']*100:.2f}] pp. The allowed increase is 0.50 pp, and the upper bound must be below that threshold. The guardrail fails.
- Sample-ratio mismatch p={d['srm']['p_value']:.4f}; threshold 0.001. This allocation check passes, but cannot prove every aspect of randomization is valid.
- Raw event audit: {q['raw_events']:,} = {q['clean_events']:,} accepted + {q['duplicates_removed']:,} duplicate replays + {q['quarantined_events']} quarantined.

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
'''
    (root/'docs/case-study.md').write_text(text)


if __name__ == '__main__':
    result = run()
    print(json.dumps({'users': result['users'], 'decision': result['decision'], 'primary': result['primary'], 'guardrail': result['guardrail'], 'quality': result['quality']}, indent=2))
