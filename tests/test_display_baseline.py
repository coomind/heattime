"""Values shown for the observed demo scenes stay fixed (judgment rule (나): central estimate, +2.5℃ venue offset).

Fixtures were produced by scripts/freeze_display_baseline.py from the committed snapshots and fresh
replays (they had to agree). Any change here means calculation or judgment changed.
"""
import json
from datetime import date
from pathlib import Path
import pytest
from backend.repository import Repository
from backend.service import Service
from scripts.freeze_display_baseline import FIXTURES, fresh_summary, summarize

ROOT = Path(__file__).resolve().parents[1]
BASE = {scene: json.loads((ROOT/f'tests/fixtures/display-baseline-{name}.json').read_text(encoding='utf-8'))
        for scene, (_, name) in FIXTURES.items()}

# Expected headline values, copied from the 2026-10-21 execution output (docs/submission-report.md 1-2~1-4).
HEADLINES = {
    'demo': dict(dates=('2026-08-10', '2026-08-10'), assigned=15, postponed=0, ids=[], orig=[0, 0, 0, 11, 4],
                 prop=[0, 0, 0, 15, 0], heat=[5273, 4153], peak=31.3),
    'extreme': dict(dates=('2026-08-08', '2026-08-08'), assigned=10, postponed=5, ids=['final', 'g1-2', 'g4-1', 'semi1', 'semi2'],
                    orig=[0, 0, 1, 0, 14], prop=[0, 0, 0, 10, 0], heat=[5993, 2648], peak=34.8),
    'extreme-2day': dict(dates=('2026-08-08', '2026-08-09'), assigned=15, postponed=0, ids=[], orig=[0, 0, 1, 0, 14],
                         prop=[0, 0, 2, 13, 0], heat=[8608, 3681], peak=34.8),
}


@pytest.mark.parametrize('scene', list(FIXTURES))
def test_baseline_headline_values(scene):
    b, h = BASE[scene], HEADLINES[scene]
    assert (b['date'], b['date_end']) == h['dates']
    assert (b['assigned'], b['postponed'], b['postponed_ids']) == (h['assigned'], h['postponed'], h['ids'])
    assert b['original_levels'] == h['orig'] and b['proposed_levels'] == h['prop']
    assert b['heat'] == h['heat'] and b['max_decision']['value'] == h['peak']
    days = 2 if scene.endswith('2day') else 1
    assert (b['teams'], b['venues'], b['matches']) == (12, 3, 15) and len(b['cells']) == 72*days


@pytest.mark.parametrize('scene', list(FIXTURES))
def test_decision_value_is_the_rounded_central_estimate(scene):
    """(나): every cell decides on round(central); low/high stay central ∓ 1.5℃ and are only shown.

    The stored central is itself rounded to 0.001℃, so at an exact .x5 the engine's unrounded
    value may fall on either side (e.g. 8/9 08:00 stores 26.950 and decides 26.9 at venue A).
    """
    from backend.engine.policy import classify, round_decision
    for venue, time, level, central, low, high, decision in BASE[scene]['cells']:
        assert decision in {round_decision(central-0.0005), round_decision(central+0.0005)}
        assert level == classify(decision)
        assert round(central-low, 3) == 1.5 and round(high-central, 3) == 1.5


@pytest.mark.parametrize('scene', list(FIXTURES))
def test_committed_snapshot_matches_baseline(scene):
    prefix = FIXTURES[scene][0]
    snapshot = json.loads((ROOT/f'frontend/src/demo/{prefix}.json').read_text(encoding='utf-8'))['approved']
    assert summarize(snapshot) == BASE[scene]


@pytest.mark.parametrize('scene', list(FIXTURES))
def test_fresh_replay_matches_baseline(scene):
    assert fresh_summary(scene, BASE[scene]) == BASE[scene]
