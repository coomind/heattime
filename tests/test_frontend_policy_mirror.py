import re
from pathlib import Path
from backend.engine.policy import policies

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_upper_bound_groups_mirror_policy_yaml():
    text = (ROOT/'frontend/src/decision-breakdown.js').read_text(encoding='utf-8')
    groups = re.search(r"UPPER_BOUND_GROUPS=\[([^\]]*)\]", text).group(1)
    assert [g.strip().strip("'") for g in groups.split(',') if g.strip()] == policies()['age']['upper_bound_groups']


def test_frontend_round1_mirrors_backend_rule():
    text = (ROOT/'frontend/src/format.js').read_text(encoding='utf-8')
    assert 'Math.round(Number(value)*1e6)/1e6' in text and 'Math.round(Math.abs(x)*10+1e-9)/10' in text
