"""Compare regenerated evidence while allowing platform libm rounding only."""
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def compare(expected, actual, path='$'):
    if type(expected) is not type(actual):
        raise AssertionError(f'{path}: type changed')
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            raise AssertionError(f'{path}: keys changed')
        for key in expected:
            compare(expected[key], actual[key], path+'.'+key)
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            raise AssertionError(f'{path}: length changed')
        for i, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, f'{path}[{i}]')
    elif isinstance(expected, float):
        if not math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-15):
            raise AssertionError(f'{path}: numeric evidence changed ({expected} vs {actual})')
    elif expected != actual:
        raise AssertionError(f'{path}: value changed ({expected!r} vs {actual!r})')

if __name__ == '__main__':
    original = subprocess.check_output(['git', 'show', 'HEAD:dashboard/data.json'], cwd=ROOT, text=True)
    compare(json.loads(original), json.loads((ROOT/'dashboard/data.json').read_text()))
    subprocess.run(['git', 'diff', '--exit-code', '--', 'docs/case-study.md'], cwd=ROOT, check=True)
    print('Evidence reproduced: exact structure/counts/text; floats agree within 1e-12 relative / 1e-15 absolute tolerance.')
