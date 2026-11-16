import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pipeline', ROOT/'scripts/pipeline.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

class StatisticsTests(unittest.TestCase):
    def test_known_difference_and_symmetry(self):
        r = p.difference_in_proportions(100, 1000, 200, 1000)
        reverse = p.difference_in_proportions(200, 1000, 100, 1000)
        self.assertAlmostEqual(r['absolute_lift'], .1)
        self.assertLess(r['p_value'], 1e-8)
        self.assertLess(r['ci_low'], .1)
        self.assertGreater(r['ci_high'], .1)
        self.assertAlmostEqual(r['p_value'], reverse['p_value'])
        self.assertAlmostEqual(r['ci_low'], -reverse['ci_high'])

    def test_equal_rates_and_invalid_denominators(self):
        self.assertEqual(p.difference_in_proportions(50,100,50,100)['p_value'], 1)
        with self.assertRaises(ValueError): p.difference_in_proportions(0,0,1,100)
        with self.assertRaises(ValueError): p.difference_in_proportions(101,100,1,100)

    def test_srm_finds_broken_allocation(self):
        self.assertTrue(p.srm_test(5000,5000)['passed'])
        self.assertFalse(p.srm_test(6000,4000)['passed'])

    def test_maturity_boundary(self):
        self.assertTrue(p.mature('2026-10-01',30))
        self.assertFalse(p.mature('2026-10-02',30))

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.result = p.run(cls.root)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_ingestion_audit_and_rerun(self):
        q = self.result['quality']
        self.assertEqual(q['duplicates_removed'],437)
        self.assertEqual(q['quarantined_events'],4)
        self.assertTrue(q['reconciliation_passed'])
        first = (self.root/'dashboard/data.json').read_bytes()
        p.run(self.root)
        self.assertEqual(first, (self.root/'dashboard/data.json').read_bytes())

    def test_itt_includes_unexposed_users(self):
        c = sqlite3.connect(self.root/'data/experiment.sqlite')
        self.assertEqual(c.execute('SELECT COUNT(*) FROM user_outcomes').fetchone()[0],12000)
        self.assertGreater(c.execute('SELECT COUNT(*) FROM user_outcomes WHERE exposed=0').fetchone()[0],0)
        self.assertEqual(sum(v['assigned_users'] for v in self.result['variants']),12000)
        c.close()

    def test_immature_retention_is_null_not_zero(self):
        immature = [c for c in self.result['cohorts'] if c['eligible_d30']==0]
        self.assertGreater(len(immature),0)
        self.assertTrue(all(c['d30_rate'] is None for c in immature))
        for row in self.result['cohorts']:
            self.assertLessEqual(row['retained_d30'],row['eligible_d30'])
            self.assertLessEqual(row['eligible_d30'],row['users'])

    def test_guardrail_blocks_superficial_win(self):
        self.assertGreater(self.result['primary']['ci_low'],0)
        self.assertFalse(self.result['guardrail']['passed'])
        self.assertEqual(self.result['decision'],'HOLD')

    def test_sql_windows_and_join_multiplicity(self):
        c = sqlite3.connect(':memory:')
        c.executescript('CREATE TABLE assignments(user_id TEXT, variant TEXT, assigned_on TEXT, segment TEXT); CREATE TABLE events(event_id TEXT, user_id TEXT, event_type TEXT, event_date TEXT);')
        c.executemany('INSERT INTO assignments VALUES (?,?,?,?)', [('a','control','2026-10-01','solo'),('b','treatment','2026-10-02','solo'),('c','control','2026-10-01','solo')])
        c.executemany('INSERT INTO events VALUES (?,?,?,?)', [('1','a','first_value','2026-10-07'),('2','a','first_value','2026-10-07'),('3','b','first_value','2026-10-09'),('4','a','active','2026-10-31')])
        c.executescript((ROOT/'sql/marts.sql').read_text().replace('{{as_of}}','2026-10-31'))
        rows=c.execute('SELECT user_id,activated_7d,retained_d30,observed_days FROM user_outcomes ORDER BY user_id').fetchall()
        self.assertEqual(rows,[('a',1,1,30),('b',0,0,29),('c',0,0,30)])
        c.close()

if __name__ == '__main__': unittest.main()
