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


def test_pdf_never_prints_none_celsius_for_missing_weather(tmp_path):
    """B-7: a recommendation without weather coverage is described, not printed as None℃."""
    from io import BytesIO
    from pypdf import PdfReader
    from backend.exports import records_pdf
    from backend.repository import Repository
    from backend.service import Service
    from datetime import date
    svc = Service(Repository(tmp_path/'p.sqlite3'))
    s = svc.replay(date(2026, 8, 1))
    s['risks'] = [r for r in s['risks'] if not r['valid_time'].startswith('2026-08-01T10')]
    from backend.schedule.recommend import recommend
    t, m, v, risks, settings, engine = Service.context(s)
    from fastapi.encoders import jsonable_encoder
    s['recommendations'] = jsonable_encoder([recommend(x, risks, engine) for x in m])
    assert any(r['wbgt_c'] is None for r in s['recommendations'])
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(s))).pages)
    assert 'None℃' not in text and 'None' not in text.split('현장 보정')[0] and '기상 자료 누락' in text


def test_pdf_decision_and_counterfactual_values_are_labelled_estimates():
    """E-2: every decision/counterfactual WBGT in the PDF carries '추정' and the counterfactual a range."""
    import json, re
    from io import BytesIO
    from pathlib import Path
    from pypdf import PdfReader
    from backend.exports import records_pdf
    s = json.loads((Path(__file__).resolve().parents[1]/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(s))).pages).replace('\n', '')
    assert text.count('판정값(추정)') >= 1 and '판정값 ' not in text.replace('판정값(추정', '')
    assert re.search(r'보정0℃·중앙값 WBGT 추정: [0-9.]+℃ \(범위 [0-9.]+~[0-9.]+℃\)', text)


def test_synthetic_pdf_states_virtual_tournament(tmp_path):
    """E-4: synthetic-mode PDF says the tournament/teams/venues are virtual examples."""
    from io import BytesIO
    from datetime import date
    from pypdf import PdfReader
    from backend.exports import records_pdf
    from backend.repository import Repository
    from backend.service import Service
    s = Service(Repository(tmp_path/'s.sqlite3')).replay(date(2026, 8, 1))
    first = PdfReader(BytesIO(records_pdf(s))).pages[0].extract_text().replace('\n', '')
    assert '대회·팀·구장도 가상 예시입니다' in first


def test_pdf_has_no_raw_boolean_mock_flag():
    """E-5: the weather origin is worded, never '가상 예시 True/False'."""
    import json
    from io import BytesIO
    from pathlib import Path
    from pypdf import PdfReader
    from backend.exports import records_pdf
    s = json.loads((Path(__file__).resolve().parents[1]/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(s))).pages)
    assert '가상 예시 False' not in text and '가상 예시 True' not in text and '실제 관측 기상(가상 예시 아님)' in text


def test_stage_zero_is_shown_as_routine_operation_with_source_label():
    """W-1: stage 0 displays '통상 운영'; the guideline label '거의 안전' stays only as a sourced reference."""
    import json
    from io import BytesIO
    from pathlib import Path
    from pypdf import PdfReader
    from backend.engine.policy import policies
    from backend.exports import records_pdf
    root = Path(__file__).resolve().parents[1]
    assert policies()['general']['labels'][0] == '거의 안전'  # source label kept in the policy config
    s = json.loads((root/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    first = PdfReader(BytesIO(records_pdf(s))).pages[0].extract_text().replace('\n', '')
    assert '단계 표시: 0 통상 운영' in first and '원 지침 단계명(출처 표기): 0 거의 안전' in first
    app = (root/'frontend/src/App.jsx').read_text(encoding='utf-8')
    assert "const labels=['통상 운영'" in app and "'통상 운영':name" in app
    assert "['통상 운영'" in (root/'frontend/src/LiveWeather.jsx').read_text(encoding='utf-8')
    assert '0 통상 운영 (원 지침 표기: 거의 안전)' in (root/'docs/spec.md').read_text(encoding='utf-8')


def test_policy_verification_is_not_self_contradictory_in_pdf():
    """W-3: PDF says when the boundaries were checked and what review remains; config keeps its marker."""
    import json
    from io import BytesIO
    from pathlib import Path
    from pypdf import PdfReader
    from backend.engine.policy import policies
    from backend.exports import records_pdf
    assert policies()['general']['verification'].startswith('원문 대조 필요')
    s = json.loads((Path(__file__).resolve().parents[1]/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    first = PdfReader(BytesIO(records_pdf(s))).pages[0].extract_text().replace('\n', '')
    assert '원문 대조: 2026-10-01 경계값 대조 완료 · 원문 개정 시 다시 대조 필요 · 국내 대회 적용 전 전문가 검토 필요' in first
    assert '원문 대조 필요 · 2026-10-01' not in first


def test_stage_zero_label_in_csv_and_json_exports(tmp_path):
    """Item 3: CSV shows stage names with 통상 운영; JSON explains the guideline labels next to display names."""
    import csv, io
    from datetime import date
    from fastapi.testclient import TestClient
    from backend.app import create_app
    from backend.exports import records_csv, stage_display
    c = TestClient(create_app(tmp_path/'j.sqlite3'))
    s = c.post('/api/replays', json={'date': '2026-08-01', 'tournament_id': 'demo'}).json()
    s['recommendations'][0]['level'] = 0  # force a stage-0 row for the label check
    rows = list(csv.DictReader(io.StringIO(records_csv(s).decode('utf-8-sig'))))
    assert all(r['단계명'] for r in rows) and '거의 안전' not in ''.join(r['단계명'] for r in rows)
    body = c.get(f"/api/sessions/{s['id']}/export/json").json()
    assert body['stage_display']['labels_display'][0] == '통상 운영'
    assert '원 지침 단계명' in body['stage_display']['note'] and body['policy']['labels'][0] == '거의 안전'
    assert stage_display(body['policy'])['labels_display'][0] == '통상 운영'


def test_readable_names_in_notifications_pdf_and_csv():
    """f: no internal ids (semi1, group1, winner:) where people read; ids kept only in id columns."""
    import csv, io, json, re
    from io import BytesIO
    from pathlib import Path
    from pypdf import PdfReader
    from backend.display_names import match_name, placeholder_name
    from backend.exports import records_csv, records_pdf, CSV_HEADER
    from backend.notifications import build_notifications
    assert (match_name('g2-3'), match_name('semi1'), match_name('final')) == ('2조 3경기', '준결승 1', '결승')
    assert (placeholder_name('winner:group4'), placeholder_name('winner:semi2')) == ('4조 1위', '준결승 2 승자')
    s = json.loads((Path(__file__).resolve().parents[1]/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    raw = re.compile(r'winner:|\bgroup\d|\bsemi\d|\bfinal\b')
    for n in build_notifications(s):
        assert not raw.search(n['message']), n['message']
    pdf = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(s))).pages)
    assert '준결승 1 승자 vs 준결승 2 승자' in pdf and '1조 1위 vs 2조 1위' in pdf and 'winner:' not in pdf and 'semi1 승자' not in pdf
    rows = list(csv.DictReader(io.StringIO(records_csv(s).decode('utf-8-sig'))))
    assert list(rows[0].keys()) == CSV_HEADER and all(re.search('[가-힣]', h) for h in CSV_HEADER)
    assert {r['경기'] for r in rows} >= {'준결승 2', '결승', '1조 1경기'}


def test_pdf_stage_grid_uses_hatching_and_stage_numbers():
    """i: a venue x hour stage table with hatch density per stage, readable in black-and-white print."""
    import json
    from io import BytesIO
    from pathlib import Path
    from pypdf import PdfReader
    from reportlab.graphics.shapes import Line
    from backend.exports import records_pdf, stage_grid, STAGE_HATCH
    s = json.loads((Path(__file__).resolve().parents[1]/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    page = PdfReader(BytesIO(records_pdf(s))).pages[1].extract_text()
    assert '구장 × 시간 단계표' in page and '흑백으로 인쇄해도' in page and page.count('4단계') >= 21
    assert len({str(h) for h in STAGE_HATCH}) == 4  # 0 and 4 have no hatch (blank vs solid); 1-3 differ
    d = stage_grid(s, 500, 'Helvetica', 'Helvetica')
    assert sum(isinstance(x, Line) for x in d.contents) > 100
