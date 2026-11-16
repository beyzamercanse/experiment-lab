import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('check_evidence', Path(__file__).resolve().parents[1]/'scripts/check_evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)

class EvidenceTests(unittest.TestCase):
    def test_platform_rounding_is_accepted(self):
        evidence.compare({'p': 2.1911839080096695e-5}, {'p': 2.1911839080096702e-5})

    def test_changed_counts_rates_and_conclusions_are_rejected(self):
        for expected, actual in [(12000,12001),(.31,.310001),('HOLD','SHIP'),(None,0),(True,1)]:
            with self.assertRaises(AssertionError): evidence.compare(expected, actual)

    def test_missing_or_extra_evidence_is_rejected(self):
        for expected, actual in [({'count':1},{}),([1,2],[1]),({'p':.1},{'p':.1,'new':0})]:
            with self.assertRaises(AssertionError): evidence.compare(expected, actual)
