"""Offline guide contract and fake-transport tests; never use project .env."""
from datetime import date, datetime, timedelta
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, quote
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import pytest
from scripts import fetch_asos_samples as asos

KEY = 'synthetic-test-key+/=SECRET'
DAY = date(2026, 7, 1)


@pytest.fixture(autouse=True)
def offline_only_and_no_project_credentials(monkeypatch):
    import socket
    original_read = Path.read_text
    credential_path = (asos.ROOT/'.env').resolve()
    def guarded_read(path, *args, **kwargs):
        if path.resolve() == credential_path:
            raise AssertionError('Tests must not read project credentials')
        return original_read(path, *args, **kwargs)
    def blocked_connection(*args, **kwargs):
        raise AssertionError('ASOS sample tests must stay offline')
    monkeypatch.setattr(Path, 'read_text', guarded_read)
    monkeypatch.setattr(socket.socket, 'connect', blocked_connection)


def row(hour, station='119', **fields):
    return {'tm': f'2026-07-01 {hour:02d}:00', 'stnId': station, 'stnNm': '수원',
            'rnum': str(hour + 1), 'ta': '30.5', 'hm': '45', 'icsr': '', **fields}


def page(rows, number=1, total=None, code='00'):
    root = ET.Element('response'); header = ET.SubElement(root, 'header')
    ET.SubElement(header, 'resultCode').text = code
    ET.SubElement(header, 'resultMsg').text = 'NORMAL_SERVICE'
    body = ET.SubElement(root, 'body'); ET.SubElement(body, 'dataType').text = 'XML'
    items = ET.SubElement(body, 'items')
    for record in rows:
        item = ET.SubElement(items, 'item')
        for field, value in record.items(): ET.SubElement(item, field).text = value
    for field, value in [('numOfRows', len(rows)), ('pageNo', number), ('totalCount', len(rows) if total is None else total)]:
        ET.SubElement(body, field).text = str(value)
    return ET.tostring(root, encoding='utf-8')


def guide_tables():
    path = next((asos.ROOT/'docs/kma').glob('*.docx'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with ZipFile(path) as z: root = ET.fromstring(z.read('word/document.xml'))
    return [[[ ''.join(t.text or '' for t in c.findall('.//w:t', ns)).strip()
                for c in r.findall('w:tc', ns)] for r in table.findall('w:tr', ns)]
            for table in root.find('w:body', ns).findall('w:tbl', ns)]


def test_contract_matches_only_supplied_guide():
    tables = guide_tables()
    assert asos.ENDPOINT in [cell for row in tables[2] for cell in row]
    response_fields = {row[0] for row in tables[4][1:]}
    assert set(asos.FIELDS) == response_fields - {'numOfRows', 'pageNo', 'totalCount', 'resultCode', 'resultMsg', 'dataType'}
    expected = {}
    for r in tables[6][1:]:
        for i in (0, 3):
            if r[i]: expected[r[i]] = {'id': r[i], 'name': r[i+1], 'office': r[i+2]}
    assert asos.station_table() == expected
    assert expected[asos.DEFAULT_STATION]['name'] == '수원'
    calls = []
    asos.Downloader(KEY, transport=lambda p: calls.append(p) or page([])).fetch('119', DAY, DAY)
    assert set(calls[0]) == {row[0] for row in tables[3][1:]}
    assert calls[0]['startHh'] == '00' and calls[0]['endHh'] == '23'


def test_cli_defaults_and_no_credentials_read_on_parse(monkeypatch):
    def blocked(*args): raise AssertionError('Unexpected credential read')
    monkeypatch.setattr(asos, 'read_api_key', blocked)
    args = asos.parser().parse_args([])
    assert args.station == '119' and args.start == date(2026, 7, 1) and args.end == date(2026, 8, 31)
    assert args.page_size == 10 and args.delay >= .1


@pytest.mark.parametrize('content', [f'KMA_API_KEY={KEY}\n', f'export KMA_API_KEY="{KEY}"\n', f"KMA_API_KEY='{KEY}'\n"])
def test_key_loader_uses_only_synthetic_temp_credentials(tmp_path, content):
    path = tmp_path/'synthetic-credentials.txt'; path.write_text('OTHER=ignored\n'+content, encoding='utf-8')
    assert asos.read_api_key(path) == KEY


@pytest.mark.parametrize('content', ['', 'KMA_API_KEY=\n', 'KMA_API_KEY=x\nKMA_API_KEY=y', 'KMA_API_KEY="unclosed'])
def test_bad_credentials_fail_without_echo(tmp_path, content):
    path = tmp_path/'synthetic-credentials.txt'; path.write_text(content, encoding='utf-8')
    with pytest.raises(asos.FetchError) as error: asos.read_api_key(path)
    assert 'unclosed' not in str(error.value)


def test_request_encodes_decoding_key_once_and_never_logs(monkeypatch, capsys):
    seen = []
    class Response(BytesIO):
        status = 200
    class Opener:
        def open(self, request, timeout):
            seen.append(parse_qs(urlsplit(request.full_url).query))
            assert request.get_method() == 'GET'
            return Response(page([]))
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    asos.request_xml({'serviceKey': KEY})
    assert seen[0]['serviceKey'] == [KEY]  # '+', '/', '=' preserved after exactly one encoding.
    assert capsys.readouterr() == ('', '')
    assert asos.NoRedirect().redirect_request(None, None, 302, '', {}, 'irrelevant') is None


@pytest.mark.parametrize('code', ['00', '0'])
def test_guide_success_code_variants(code):
    result = asos.parse_page(page([row(0)], code=code), KEY)
    assert result.total == 1 and result.records[0]['tm'] == row(0)['tm']


def test_pagination_merges_sorts_and_waits_between_calls():
    calls = []; waits = []
    def fake(params):
        calls.append(dict(params))
        return page([row(2), row(0)], total=3) if params['pageNo'] == 1 else page([row(1)], number=2, total=3)
    result = asos.Downloader(KEY, page_size=2, transport=fake, sleep=waits.append).fetch('119', DAY, DAY)
    assert [r['tm'] for r in result] == [row(h)['tm'] for h in range(3)]
    assert [p['pageNo'] for p in calls] == [1, 2] and waits == [.2]
    assert all(p['stnIds'] == '119' and p['dataCd'] == 'ASOS' and p['dateCd'] == 'HR' for p in calls)


def test_default_entire_two_months_and_final_partial_page():
    records = [row(0, tm=(datetime(2026, 7, 1) + timedelta(hours=h)).strftime('%Y-%m-%d %H:%M'))
               for h in range(62 * 24)]
    calls = []; waits = []
    def fake(params):
        calls.append(params['pageNo']); offset = (params['pageNo'] - 1) * params['numOfRows']
        return page(records[offset:offset + params['numOfRows']], number=params['pageNo'], total=len(records))
    result = asos.Downloader(KEY, transport=fake, sleep=waits.append).fetch('119', DAY, date(2026, 8, 31))
    assert result == records and len(result) == 1488
    assert calls == list(range(1, 150)) and len(waits) == 148
    summary = asos.daily_summary(result, DAY, date(2026, 8, 31))
    assert len(summary) == 62 and all(d['received_hours'] == 24 for d in summary)
    assert summary[-1]['date'] == '2026-08-31' and result[-1]['tm'] == '2026-08-31 23:00'


@pytest.mark.parametrize('second', [page([row(0)], number=2, total=2), page([], number=2, total=2),
                                    page([row(1)], number=2, total=3), page([row(1)], number=1, total=2)])
def test_pagination_incomplete_or_duplicate_must_fail(second):
    responses = iter([page([row(0)], total=2), second])
    with pytest.raises(asos.FetchError):
        asos.Downloader(KEY, transport=lambda p: next(responses), sleep=lambda _: None).fetch('119', DAY, DAY)


@pytest.mark.parametrize('bad', [row(0, station='108'), row(0, tm='2026-07-02 00:00'), row(0, tm='invalid')])
def test_wrong_station_period_or_time_fail(bad):
    with pytest.raises(asos.FetchError):
        asos.Downloader(KEY, transport=lambda _: page([bad])).fetch('119', DAY, DAY)


def test_documented_short_time_and_nodata_response():
    result = asos.Downloader(KEY, transport=lambda _: page([row(0, tm='2026-07-01 00')])).fetch('119', DAY, DAY)
    assert len(result) == 1
    assert asos.Downloader(KEY, transport=lambda _: page([], code='03')).fetch('119', DAY, DAY) == []


def test_daily_extremes_qc_missing_hours_and_zero_solar():
    records = [row(0, ta='29', hm='62', icsr='0.0'), row(1, ta='35', hm='40'),
               row(2, ta='60', taQcflg='1', hm='10', hmQcflg='9', icsr='not-numeric')]
    summary = asos.daily_summary(records, DAY, date(2026, 7, 2))
    assert summary[0]['max_ta_c'] == 35 and summary[0]['min_hm_pct'] == 40
    assert summary[0]['icsr_present'] and summary[0]['icsr_present_hours'] == 1
    assert summary[0]['icsr_missing_hours'] == 23 and summary[0]['missing_record_hours'] == 21
    assert summary[1]['icsr_missing_hours'] == 24 and summary[1]['max_ta_c'] is None
    text = asos.summary_text({'119': records}, DAY, DAY)
    assert '最高' not in text and '최고기온 35℃' in text and '최저습도 40%' in text and '결측 23시간' in text


def test_optional_solar_station_only_if_all_solar_missing():
    calls = []; waits = []
    def fake(params):
        calls.append(params['stnIds'])
        return page([row(0, station=params['stnIds'], icsr='' if params['stnIds'] == '119' else '0.7')])
    result = asos.collect(asos.Downloader(KEY, transport=fake, sleep=waits.append), '119', DAY, DAY, '108')
    assert set(result) == {'119', '108'} and calls == ['119', '108'] and waits == [.2]
    calls.clear()
    result = asos.collect(asos.Downloader(KEY, transport=lambda p: calls.append(p['stnIds']) or page([row(0, icsr='0')]),
                                          sleep=lambda _: None), '119', DAY, DAY, '108')
    assert set(result) == {'119'} and calls == ['119']


@pytest.mark.parametrize('echo', [KEY, quote(KEY, safe=''), 'http://example.invalid/request', 'serviceKey=echo'])
def test_secret_or_url_in_known_field_is_not_saved(echo, tmp_path):
    with pytest.raises(asos.FetchError): asos.parse_page(page([row(0, stnNm=echo)]), KEY)
    with pytest.raises(asos.FetchError): asos.save_samples({'119': [row(0, stnNm=echo)]}, DAY, DAY, KEY, tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_unknown_echo_is_excluded_and_saved_output_is_key_free(tmp_path):
    result = asos.parse_page(page([row(0, serviceKey=KEY, debug='http://example.invalid/request')]), KEY)
    paths = asos.save_samples({'119': result.records}, DAY, DAY, KEY, tmp_path/'out')
    assert len(paths) == 1
    text = paths[0].read_text(encoding='utf-8')
    assert KEY not in text and quote(KEY, safe='') not in text and 'http://' not in text
    saved = json.loads(text)
    assert 'serviceKey' not in saved['records'][0] and 'debug' not in saved['records'][0]
    assert saved['count'] == 1 and saved['daily_summary'][0]['icsr_missing_hours'] == 24
    with pytest.raises(asos.FetchError): asos.save_samples({'119': result.records}, DAY, DAY, KEY, tmp_path/'out')
    assert paths[0].read_text(encoding='utf-8') == text


def test_errors_never_echo_transport_or_result_message(capsys):
    def fake(params): raise RuntimeError(KEY + 'http://example.invalid/request')
    with pytest.raises(asos.FetchError) as error:
        asos.Downloader(KEY, transport=fake).fetch('119', DAY, DAY)
    assert KEY not in str(error.value) and 'http://' not in str(error.value)
    root = ET.fromstring(page([], code='30'))
    root.find('header/resultMsg').text = KEY + 'http://example.invalid/request'
    with pytest.raises(asos.FetchError) as error: asos.parse_page(ET.tostring(root), KEY)
    assert KEY not in str(error.value) and 'http://' not in str(error.value)
    assert capsys.readouterr() == ('', '')


def test_main_only_uses_injected_fake_key_and_transport(monkeypatch, tmp_path, capsys):
    loaded = []; real = asos.Downloader
    monkeypatch.setattr(asos, 'read_api_key', lambda path: loaded.append(path) or KEY)
    monkeypatch.setattr(asos, 'Downloader', lambda key, size, delay: real(key, size, delay, transport=lambda _: page([row(0)])))
    table = asos.station_table()
    monkeypatch.setattr(asos, 'station_table', lambda: table)
    monkeypatch.setattr(asos, 'ROOT', tmp_path)
    assert asos.main(['--start', '2026-07-01', '--end', '2026-07-01']) == 0
    assert loaded == [tmp_path/'.env']  # Stub only; no file was read or created.
    output = capsys.readouterr()
    assert KEY not in output.out + output.err and 'http://' not in output.out + output.err
    assert '결측 24시간' in output.out and not (tmp_path/'.env').exists()
    assert len(list((tmp_path/'data/samples').glob('*.json'))) == 1
