"""Original (author) schedule issues come from the existing validate() and are shown, not hidden."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.original_issues import original_issues

ROOT = Path(__file__).resolve().parents[1]


def snapshot(name):
    return json.loads((ROOT/f'frontend/src/demo/{name}.json').read_text(encoding='utf-8'))['approved']


def test_observed_original_schedule_issues_are_found_by_validate():
    r = original_issues(snapshot('observed-snapshot'))
    assert r['note'] == '원래 일정은 작성자가 정한 가상 기준이며 다음 제약을 충족하지 않습니다.'
    assert set(r['full_errors']) == {'prohibited heat slot', 'team rest', 'venue overlap/cleanup'}
    pairs = {tuple(p['match_ids']): p for p in r['pairs']}
    assert set(pairs) == {('g1-1', 'g4-1'), ('g1-2', 'g4-2'), ('g1-3', 'g4-3'), ('g3-3', 'semi2'), ('g4-3', 'semi2')}
    assert pairs[('g1-1', 'g4-1')]['times'] == ['10:00~10:45', '10:45~11:30']
    assert '구장 정리 5분' in pairs[('g1-1', 'g4-1')]['text'][0]
    assert '진출할 수 있는 팀 기준' in pairs[('g3-3', 'semi2')]['text'][0]
    # 2026-10-21 rule (central estimate decides): 4 of the 15 original matches sit in a stage-4 slot.
    assert len([x for x in r['singles'] if 'prohibited heat slot' in x['errors']]) == 4


def test_snapshot_bundle_and_api_carry_the_same_issues(tmp_path):
    bundle = json.loads((ROOT/'frontend/src/demo/observed-snapshot-evidence.json').read_text(encoding='utf-8'))
    assert bundle['original_issues'] == original_issues(snapshot('observed-snapshot'))
    c = TestClient(create_app(tmp_path/'o.sqlite3'))
    s = c.post('/api/replays', json={'date': '2026-08-01', 'tournament_id': 'demo'}).json()
    body = c.get(f"/api/sessions/{s['id']}/original-issues").json()
    assert 'venue overlap/cleanup' in body['full_errors'] and body['pairs']
