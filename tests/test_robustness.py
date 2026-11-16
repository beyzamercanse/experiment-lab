import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('robustness', ROOT/'scripts/robustness.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


class PercentileTests(unittest.TestCase):
    def test_interpolates_between_ranks(self):
        values = [0, 10, 20, 30, 40]
        self.assertEqual(r.percentile(values, 0), 0)
        self.assertEqual(r.percentile(values, 1), 40)
        self.assertEqual(r.percentile(values, .5), 20)
        self.assertAlmostEqual(r.percentile(values, .1), 4)
        with self.assertRaises(ValueError):
            r.percentile([], .5)


class PowerTests(unittest.TestCase):
    def test_power_at_the_margin_is_alpha_over_two(self):
        # If the true harm equals the margin, the rule should pass ~2.5% of the time.
        self.assertAlmostEqual(r.noninferiority_power(.04, 6000, .005, true_diff=.005), .025, places=3)

    def test_power_grows_with_sample_size(self):
        small = r.noninferiority_power(.04, 2000, .005)
        large = r.noninferiority_power(.04, 20000, .005)
        self.assertLess(small, large)

    def test_required_n_is_the_smallest_n_reaching_target_power(self):
        n = r.required_n_per_arm(.04, .005)
        self.assertGreaterEqual(r.noninferiority_power(.04, n, .005), .8)
        self.assertLess(r.noninferiority_power(.04, n - 50, .005), .8)
        with self.assertRaises(ValueError):
            r.required_n_per_arm(.04, .005, true_diff=.005)

    def test_detectable_margin_gives_80_percent_power(self):
        margin = r.detectable_margin(.04, 6000)
        self.assertAlmostEqual(r.noninferiority_power(.04, 6000, margin), .8, places=3)

    def test_simulation_agrees_with_formula(self):
        analytic = r.noninferiority_power(.10, 500, .04)
        simulated = r.simulate_guardrail_pass_rate(.10, 500, 500, .04, runs=600, seed=5)
        self.assertLess(abs(analytic - simulated), .06)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        # 400 users per arm; codes are 2*activated + support.
        self.arms = {'control': [0] * 260 + [2] * 120 + [1] * 15 + [3] * 5,
                     'treatment': [0] * 230 + [2] * 140 + [1] * 22 + [3] * 8}

    def test_seeded_and_brackets_point_estimate(self):
        first = r.bootstrap_lifts(self.arms, resamples=300, seed=7)
        second = r.bootstrap_lifts(self.arms, resamples=300, seed=7)
        self.assertEqual(first, second)
        (ca, cs), (ta, ts) = r.rates(self.arms['control']), r.rates(self.arms['treatment'])
        self.assertLess(first['activation']['ci_low'], ta - ca)
        self.assertGreater(first['activation']['ci_high'], ta - ca)
        self.assertLess(first['support']['ci_low'], ts - cs)
        self.assertGreater(first['support']['ci_high'], ts - cs)

    def test_rates_decode_both_outcomes(self):
        self.assertEqual(r.rates([0, 1, 2, 3]), (.5, .5))


if __name__ == '__main__': unittest.main()
