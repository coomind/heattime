"""B-10: operator-facing API/CSV errors are Korean; internal exception text is unchanged."""
from fastapi.testclient import TestClient
import pytest
from backend.app import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path/'k.sqlite3'))


def ascii_only(text):
    return all(ord(c) < 128 for c in text)


def test_team_from_other_tournament_is_explained_in_korean(client):
    client.post('/api/tournaments', json={'id': 'other', 'name': '다른 대회 · 가상 예시', 'date_start': '2026-08-01',
                                          'date_end': '2026-08-01', 'age_group': 'U12', 'policy_id': 'general'})
    match = {'id': 'x1', 'tournament_id': 'other', 'round': '조별', 'team_a': 't1', 'team_b': 't2',
             'venue_id': 'mock-suwon-a', 'scheduled_start': '2026-08-01T10:00:00+09:00', 'duration_min': 40, 'depends_on': []}
    r = client.post('/api/matches', json=match)
    assert r.status_code == 422 and '다른 대회' in r.text and 'Team belongs' not in r.text


def test_missing_resource_duplicate_and_reference_messages_are_korean(client):
    assert client.get('/api/venues/none').text == '요청한 자료를 찾을 수 없습니다.'
    venue = client.get('/api/venues').json()[0]
    dup = client.post('/api/venues', json=venue)
    assert dup.status_code == 409 and '같은 ID' in dup.json()['detail']
    used = client.delete('/api/venues/' + venue['id'])
    assert used.status_code == 409 and '삭제할 수 없습니다' in used.json()['detail']


def test_pydantic_validation_is_summarized_in_korean(client):
    match = {'id': 'x2', 'tournament_id': 'demo', 'round': '조별', 'team_a': 't1', 'team_b': 't2',
             'venue_id': 'mock-suwon-a', 'scheduled_start': '2026-08-01T25:00:00+09:00', 'duration_min': 40}
    r = client.post('/api/matches', json=match)
    assert r.status_code == 422 and r.text.startswith('입력값을 확인하세요.') and '킥오프' in r.text
    assert 'pydantic' not in r.text and 'validation error' not in r.text


def test_csv_preview_row_errors_are_korean(client):
    header = 'id,round,team_a,team_b,venue_id,scheduled_start,duration_min,depends_on\n'
    bad = header + 'b1,조별,t1,t2,mock-suwon-a,2026-08-01T25:00:00+09:00,40,\n'
    body = client.post('/api/tournaments/demo/matches/csv-preview', json={'csv_text': bad}).json()
    messages = [e['message'] for e in body['errors']]
    assert messages and all('행' in m and 'pydantic' not in m and not ascii_only(m) for m in messages)
