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
    """Tables of the supplied KMA guide, extracted verbatim to docs/kma/asos-guide-extract.json before the
    DOCX was removed from the repository (source SHA-256 recorded there). Indexes follow the original order."""
    extract = json.loads((asos.ROOT/'docs/kma/asos-guide-extract.json').read_text(encoding='utf-8'))
    assert extract['source_sha256'] == 'c4484c0ae95e63eee5b2b8c3fd4e49fff4401321dbb792eae6055288b606c318'
    return extract['tables']


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


def fake_main(monkeypatch, tmp_path, transport, key=KEY):
    """No real credentials or API: main is exercised only through injected fakes."""
    table = asos.station_table(); real = asos.Downloader
    monkeypatch.setattr(asos, 'station_table', lambda: table)
    monkeypatch.setattr(asos, 'ROOT', tmp_path)
    monkeypatch.setattr(asos, 'read_api_key', lambda path: key)
    monkeypatch.setattr(asos, 'Downloader', lambda value, size, delay:
                        real(value, size, delay, transport=transport, sleep=lambda _: None))


def error_xml(code='30', message='SERVICE_KEY_IS_NOT_REGISTERED_ERROR'):
    root = ET.fromstring(page([], code=code))
    root.find('header/resultMsg').text = message
    return ET.tostring(root, encoding='utf-8')


def test_http_error_preserves_status_body_and_exception_without_url(monkeypatch, capsys):
    from urllib.error import HTTPError
    message = 'SERVICE_KEY_IS_NOT_REGISTERED_ERROR ' + KEY + ' http://example.invalid/request?serviceKey=' + quote(KEY, safe='')
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 403, KEY, {'X-Test': 'NEVER-PRINT-HEADERS'}, BytesIO(error_xml(message=message)))
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    with pytest.raises(asos.FetchError) as caught:
        asos.Downloader(KEY).fetch('119', DAY, DAY)
    error = caught.value
    assert error.stage == 'HTTP 응답' and error.http_status == 403 and error.exception_class == 'HTTPError'
    asos.print_failure(error, KEY)
    output = capsys.readouterr()
    assert not output.out
    assert 'HTTP 상태 코드: 403' in output.err and 'resultCode: 30' in output.err
    assert 'SERVICE_KEY_IS_NOT_REGISTERED_ERROR' in output.err and '예외 클래스: HTTPError' in output.err
    assert len(output.err.splitlines()) == 5
    for secret in [KEY, quote(KEY, safe=''), 'example.invalid', 'http://', 'X-Test', 'NEVER-PRINT-HEADERS']:
        assert secret not in output.err


def test_http_200_api_error_reaches_main_with_masked_body(monkeypatch, tmp_path, capsys):
    payload = asos.XmlResponse(error_xml(message='SERVICE_ACCESS_DENIED_ERROR '+KEY), 200)
    fake_main(monkeypatch, tmp_path, lambda params: payload)
    assert asos.main(['--check']) == 1
    output = capsys.readouterr()
    assert '키 길이:' in output.out and "'%' 문자 포함: 아니오" in output.out
    assert '실패 단계: HTTP 응답' in output.err and 'HTTP 상태 코드: 200' in output.err
    assert 'resultCode: 30' in output.err and 'SERVICE_ACCESS_DENIED_ERROR' in output.err
    assert '[키 마스킹]' in output.err and KEY not in output.out + output.err
    assert not (tmp_path/'data/samples').exists()


@pytest.mark.parametrize('xml', [
    b'<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>SERVICE ERROR</errMsg><returnAuthMsg>DENIED</returnAuthMsg><returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>',
    b'<e:error xmlns:e="urn:synthetic-test"><e:diagnosticCode>30</e:diagnosticCode><e:diagnosticMessage>DENIED</e:diagnosticMessage></e:error>',
])
def test_diagnostic_only_xml_uses_present_error_leaves(xml, capsys):
    # These are synthetic error bodies, not additions to the guide's normal response contract.
    with pytest.raises(asos.FetchError) as caught:
        asos.Downloader(KEY, transport=lambda p: asos.XmlResponse(xml, 200)).fetch('119', DAY, DAY)
    assert caught.value.stage == 'HTTP 응답'
    assert caught.value.result_code == '30' and 'DENIED' in caught.value.result_msg
    asos.print_failure(caught.value, KEY)
    output = capsys.readouterr().err
    assert 'HTTP 상태 코드: 200' in output and 'resultCode: 30' in output and 'DENIED' in output


def test_http_error_json_diagnostics_do_not_change_xml_ingestion(monkeypatch, capsys):
    from urllib.error import HTTPError
    body = json.dumps({'response': {'header': {'resultCode': '20', 'resultMsg': 'DENIED ' + KEY}}}).encode()
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 401, 'unprinted', {}, BytesIO(body))
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    with pytest.raises(asos.FetchError) as caught: asos.request_xml({'serviceKey': KEY})
    asos.print_failure(caught.value, KEY)
    output = capsys.readouterr().err
    assert 'resultCode: 20' in output and 'HTTP 상태 코드: 401' in output and 'DENIED' in output
    assert KEY not in output
    with pytest.raises(asos.FetchError) as normal:
        asos.parse_page(body, KEY)
    assert normal.value.stage == '응답 파싱'  # JSON diagnostics are not a guessed ingestion schema.


@pytest.mark.parametrize('echo', [KEY, quote(KEY, safe=''), quote(quote(KEY, safe=''), safe=''),
                                  quote(KEY, safe='').replace('%2B', '%2b').replace('%2F', '%2f')])
def test_redaction_covers_raw_and_encoded_key_before_truncation(echo):
    message = '접근 거부 ' + echo + ' ' + ('long text ' * 200)
    output = asos.redact_diagnostic(message, KEY)
    assert '접근 거부' in output and '[키 마스킹]' in output and len(output) <= 1000
    assert not any(value in output for value in asos.secret_variants(KEY))


@pytest.mark.parametrize('message,forbidden', [
    ('접근 거부 '+quote('https://example.invalid/path?serviceKey='+KEY, safe=''), ['example.invalid', 'https:', KEY]),
    ('DENIED\nAuthorization: Bearer HEADER-SECRET\nHost: hidden.invalid\nX-Debug: hidden-header',
     ['HEADER-SECRET', 'hidden.invalid', 'hidden-header', 'Authorization:', 'X-Debug:']),
    ("DENIED headers: {'Custom-Request': 'HEADER-SECRET'}", ['HEADER-SECRET', 'Custom-Request']),
    ("DENIED {'Authorization': 'Bearer HEADER-SECRET'}", ['HEADER-SECRET']),
    ('GET /path?serviceKey=unrelated HTTP/1.1\nDENIED', ['GET /path', 'unrelated']),
])
def test_redaction_removes_url_and_request_headers(message, forbidden):
    output = asos.redact_diagnostic(message, KEY)
    assert 'DENIED' in output or '접근 거부' in output
    assert all(value not in output for value in forbidden)
    assert '\n' not in output and '\r' not in output


@pytest.mark.parametrize('exception', [TimeoutError(KEY+' http://example.invalid/request'),
                                      ConnectionRefusedError(KEY+' http://example.invalid/request')])
def test_network_class_and_stage_without_exception_text(monkeypatch, capsys, exception):
    class Opener:
        def open(self, request, timeout): raise exception
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    with pytest.raises(asos.FetchError) as caught: asos.Downloader(KEY).fetch('119', DAY, DAY)
    asos.print_failure(caught.value, KEY)
    output = capsys.readouterr().err
    assert '실패 단계: 네트워크 연결' in output and 'HTTP 상태 코드: 없음' in output
    assert f'예외 클래스: {type(exception).__name__}' in output
    assert KEY not in output and 'example.invalid' not in output


def test_read_failure_after_http_status_is_http_stage(monkeypatch, capsys):
    class Response(BytesIO):
        status = 200
        def read(self, size): raise TimeoutError(KEY+' http://example.invalid/request')
    class Opener:
        def open(self, request, timeout): return Response()
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    with pytest.raises(asos.FetchError) as caught: asos.request_xml({'serviceKey': KEY})
    asos.print_failure(caught.value, KEY)
    output = capsys.readouterr().err
    assert '실패 단계: HTTP 응답' in output and 'HTTP 상태 코드: 200' in output and '예외 클래스: TimeoutError' in output
    assert KEY not in output and 'example.invalid' not in output


def test_parse_failure_preserves_http_status_and_parse_class(monkeypatch, tmp_path, capsys):
    fake_main(monkeypatch, tmp_path, lambda p: asos.XmlResponse(b'not XML', 200))
    assert asos.main(['--check']) == 1
    output = capsys.readouterr().err
    assert '실패 단계: 응답 파싱' in output and 'HTTP 상태 코드: 200' in output
    assert 'resultCode: 없음' in output and 'resultMsg: 없음' in output and '예외 클래스: ParseError' in output
    assert not (tmp_path/'data/samples').exists()


def test_second_page_connection_failure_does_not_reuse_first_status(capsys):
    def transport(params):
        if params['pageNo'] == 1: return asos.XmlResponse(page([row(0)], total=2), 200)
        raise TimeoutError(KEY)
    with pytest.raises(asos.FetchError) as caught:
        asos.Downloader(KEY, transport=transport, sleep=lambda _: None).fetch('119', DAY, DAY)
    assert caught.value.http_status is None and caught.value.result_code is None and caught.value.result_msg is None
    asos.print_failure(caught.value, KEY)
    assert 'HTTP 상태 코드: 없음' in capsys.readouterr().err


@pytest.mark.parametrize('content', [None, '', 'OTHER=value\n', 'KMA_API_KEY=\n', 'KMA_API_KEY=""\n'])
def test_missing_key_main_is_distinct_and_never_connects(monkeypatch, tmp_path, capsys, content):
    table = asos.station_table()
    monkeypatch.setattr(asos, 'station_table', lambda: table)
    monkeypatch.setattr(asos, 'ROOT', tmp_path)
    if content is not None: (tmp_path/'.env').write_text(content, encoding='utf-8')  # Synthetic only.
    def forbidden(*args): raise AssertionError('No transport without a key')
    monkeypatch.setattr(asos, 'Downloader', forbidden)
    assert asos.main(['--check']) == 1
    output = capsys.readouterr()
    assert not output.out and '키를 찾지 못함' in output.err
    assert '실패 단계: 키 로드' in output.err and '키 길이: 0' in output.err
    assert 'HTTP 상태 코드: 없음' in output.err
    assert 'OTHER=value' not in output.err and not (tmp_path/'data/samples').exists()


def test_root_key_path_and_check_one_suwon_day_page_no_files(monkeypatch, tmp_path, capsys):
    calls = []; loaded = []
    def transport(params):
        calls.append(dict(params))
        return asos.XmlResponse(page([row(h) for h in range(10)], total=24), 200)
    fake_main(monkeypatch, tmp_path, transport)
    monkeypatch.setattr(asos, 'read_api_key', lambda path: loaded.append(path) or KEY)
    elsewhere = tmp_path/'elsewhere'; elsewhere.mkdir(); monkeypatch.chdir(elsewhere)
    def forbidden(*args): raise AssertionError('Check must never collect/save partial samples')
    monkeypatch.setattr(asos, 'collect', forbidden); monkeypatch.setattr(asos, 'save_samples', forbidden)
    assert asos.main(['--check', '--start', '2026-07-01', '--end', '2026-08-31',
                      '--station', '108', '--page-size', '1', '--solar-station', '108']) == 0
    assert loaded == [tmp_path/'.env'] and not (tmp_path/'.env').exists()
    assert len(calls) == 1 and calls[0]['stnIds'] == '119' and calls[0]['pageNo'] == 1 and calls[0]['numOfRows'] == 10
    assert calls[0]['startDt'] == calls[0]['endDt'] == '20260701' and calls[0]['startHh'] == '00' and calls[0]['endHh'] == '23'
    output = capsys.readouterr()
    assert not output.err and '첫1페이지 / 10건 (저장하지 않음)' in output.out
    assert KEY not in output.out and 'http://' not in output.out
    assert not (tmp_path/'data/samples').exists()


def test_percent_key_reports_length_and_flag_only(monkeypatch, tmp_path, capsys):
    encoded_key = quote(KEY, safe='')
    fake_main(monkeypatch, tmp_path, lambda p: asos.XmlResponse(page([]), 200), key=encoded_key)
    assert asos.main(['--check']) == 0
    output = capsys.readouterr()
    assert f'키 길이: {len(encoded_key)}' in output.out and "'%' 문자 포함: 예" in output.out
    assert encoded_key not in output.out + output.err and KEY not in output.out + output.err


@pytest.mark.parametrize('payload', [page([row(0)], number=2), page([row(0, station='108')]),
                                     page([row(0, tm='2026-07-02 00:00')]), page([row(0), row(0)]),
                                     page([row(0)], total=0)])
def test_check_retains_page_station_date_and_duplicate_validation(payload):
    calls = []
    with pytest.raises(asos.FetchError):
        asos.Downloader(KEY, transport=lambda p: calls.append(p) or payload).check(DAY)
    assert len(calls) == 1


def test_url_masking_removes_whole_query_without_placeholder_fragments():
    url = 'http://hidden.invalid/path?serviceKey='+quote(KEY, safe='')+'&pageNo=1234'
    for message in [url, quote(url, safe=''), quote(quote(url, safe=''), safe='')]:
        output = asos.redact_diagnostic('DENIED '+message, KEY)
        assert output == 'DENIED [URL 마스킹]'
        assert 'pageNo' not in output and KEY not in output


def test_invalid_key_configuration_does_not_invent_metadata(monkeypatch, tmp_path, capsys):
    table = asos.station_table()
    monkeypatch.setattr(asos, 'station_table', lambda: table)
    monkeypatch.setattr(asos, 'ROOT', tmp_path)
    (tmp_path/'.env').write_text('KMA_API_KEY="'+KEY+'\n', encoding='utf-8')  # Synthetic only.
    assert asos.main(['--check']) == 1
    output = capsys.readouterr().err
    assert '실패 단계: 키 로드' in output and '키 길이: 확인 불가' in output
    assert "'%' 문자 포함: 확인 불가" in output and '키를 찾지 못함' not in output and KEY not in output


def test_urlerror_only_reports_class_not_reason_or_request(monkeypatch, capsys):
    from urllib.error import URLError
    class Opener:
        def open(self, request, timeout): raise URLError(KEY+' '+request.full_url)
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    with pytest.raises(asos.FetchError) as caught: asos.Downloader(KEY).fetch('119', DAY, DAY)
    asos.print_failure(caught.value, KEY)
    output = capsys.readouterr().err
    assert '예외 클래스: URLError' in output and '실패 단계: 네트워크 연결' in output
    assert KEY not in output and 'http://' not in output and 'serviceKey=' not in output


def test_unparseable_deep_http_error_body_still_reports_status(monkeypatch, capsys):
    from urllib.error import HTTPError
    body = b'[' * 1500 + json.dumps(KEY).encode() + b']' * 1500
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 503, KEY, {}, BytesIO(body))
    monkeypatch.setattr(asos, 'build_opener', lambda *a: Opener())
    with pytest.raises(asos.FetchError) as caught: asos.Downloader(KEY).fetch('119', DAY, DAY)
    asos.print_failure(caught.value, KEY)
    output = capsys.readouterr().err
    assert 'HTTP 상태 코드: 503' in output and '예외 클래스: HTTPError' in output
    assert 'resultCode: 없음' in output and 'resultMsg: 없음' in output
    assert KEY not in output and 'http://' not in output and 'Traceback' not in output


def test_unexpected_parser_exception_reports_parsing_without_raw_exception(monkeypatch, tmp_path, capsys):
    fake_main(monkeypatch, tmp_path, lambda p: asos.XmlResponse(page([row(0)]), 200))
    def unexpected(data, key):
        raw = (KEY+' http://example.invalid/request').encode()
        raise UnicodeDecodeError('utf-8', raw, 0, len(raw), KEY)
    monkeypatch.setattr(asos, 'parse_page', unexpected)
    assert asos.main(['--check']) == 1
    output = capsys.readouterr().err
    assert '실패 단계: 응답 파싱' in output and 'HTTP 상태 코드: 200' in output
    assert '예외 클래스: UnicodeDecodeError' in output and 'resultCode: 00' in output
    assert KEY not in output and 'http://' not in output and 'Traceback' not in output
