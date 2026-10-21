"""Values shown on the demo dashboard stay fixed through the redesign.

The fixture was produced by scripts/freeze_display_baseline.py from the committed snapshot and a
fresh replay (they had to agree). Any change here means calculation or judgment changed.
"""
import json
from datetime import date
from pathlib import Path
import pytest
from backend.repository import Repository
from backend.service import Service
from scripts.freeze_display_baseline import summarize

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT/'tests/fixtures/display-baseline-2026-08-10.json').read_text(encoding='utf-8'))


def test_baseline_headline_values():
    assert (BASE['assigned'], BASE['postponed'], BASE['postponed_ids']) == (13, 2, ['final', 'semi2'])
    assert BASE['original_levels'] == [0, 0, 0, 1, 14] and BASE['proposed_levels'] == [0, 0, 0, 13, 0]
    assert BASE['heat'] == [6442, 3879] and BASE['max_decision']['value'] == 32.8
    assert (BASE['teams'], BASE['venues'], BASE['matches']) == (12, 3, 15) and len(BASE['cells']) == 72


def test_committed_snapshot_matches_baseline():
    snapshot = json.loads((ROOT/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    assert summarize(snapshot) == BASE


def test_fresh_replay_matches_baseline(tmp_path):
    service = Service(Repository(tmp_path/'baseline.sqlite3'))
    session = service.replay(date.fromisoformat(BASE['date']), mode='observed')
    service.optimize(session['id'])
    assert summarize(service.repo.get('sessions', session['id'])) == BASE
