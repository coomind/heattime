from datetime import datetime,timedelta
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.repository import Repository
from backend.weather.aws_live import (LiveProvider,LiveFailure,load_key,parse_observation,
    FIELDS,MAX_RESPONSE_BYTES,DAILY_CALLS,DAILY_BYTES,request_bytes,NoRedirect)
from backend.weather.models import KST

NOW=datetime(2026,10,5,12,0,tzinfo=KST)
# Published PDF 202302010900 station119 example, with observation time replaced
# in transport fixtures only. This is not a real collected response.
SAMPLE='202302010900 119 303.3 1.5 297.8 1.5 265.7 0.9 0.3 0.0 0.0 0.0 0.0 0.0 98.9 1013.0 1018.0 0.1'
def body(row=SAMPLE):return ('#START7777\n# '+' '.join(FIELDS)+'\n'+row+'\n#7777END').encode()
def current_body():return body(SAMPLE.replace('202302010900','202610051200'))
def provider(tmp_path,transport=None):
    repo=Repository(tmp_path/'test.sqlite3')
    return LiveProvider(repo,key_loader=lambda:'fake-secret-for-tests',transport=transport or (lambda *args:current_body()),clock=lambda:NOW)

def test_official_example_units_and_missing_radiation():
    p=parse_observation(body(),119,NOW)
    assert p.valid_time==datetime(2023,2,1,9,tzinfo=KST)
    assert (p.ta_c,p.rh_pct,p.ws_ms)==(0.3,98.9,0.9)
    assert (p.station_pressure_hpa,p.sea_level_pressure_hpa,p.rain_60m_mm)==(1013,1018,0)
    point=p.point('venue')
    assert point.source=='aws_obs' and not point.is_mock
    assert point.solar_wm2 is None and point.sky_code is None and point.cloud_fraction is None
    assert point.provenance['wind_field']=='WS10'
    assert point.data_label=='기상청 관측 자료(수원 119·2023-02-01)'

@pytest.mark.parametrize('field,value',[('TA','-99.9'),('HM','-50'),('WS10','-99.7'),('TA','nan'),('HM','101'),('WS10','-1')])
def test_invalid_required_observations_are_not_replaced_by_mock(field,value):
    parts=SAMPLE.split();parts[FIELDS.index(field)]=value
    with pytest.raises(LiveFailure) as error:parse_observation(body(' '.join(parts)),119,NOW)
    assert error.value.details['stage']=='응답 파싱'

def test_zero_observations_are_valid_optional_missing_is_null():
    parts=SAMPLE.split()
    for field in ['TA','HM','WS10']:parts[FIELDS.index(field)]='0'
    for field in ['PA','PS','RN-60m']:parts[FIELDS.index(field)]='-99.9'
    p=parse_observation(body(' '.join(parts)),119,NOW)
    assert (p.ta_c,p.rh_pct,p.ws_ms)==(0,0,0)
    assert p.station_pressure_hpa is None and p.sea_level_pressure_hpa is None and p.rain_60m_mm is None

@pytest.mark.parametrize('response',[b'<html>error</html>',b'',body(SAMPLE+' 1'),body().replace(b' WS10 ',b' UNKNOWN '),body(SAMPLE.replace('202302010900','invalid-time')),body(SAMPLE.replace('119','120')),body(SAMPLE.replace('202302010900','202610051202'))])
def test_unknown_responses_are_rejected_without_body_leak(response):
    with pytest.raises(LiveFailure):parse_observation(response,119,NOW)

def test_select_latest_row_and_documented_tm_header():
    result=parse_observation(body(SAMPLE+'\n'+SAMPLE.replace('202302010900','202302010901')).replace(b'YYMMDDHHMI',b'TM'),119,NOW)
    assert result.valid_time.minute==1

def test_runtime_root_key_loader_uses_only_supplied_temporary_root(tmp_path,monkeypatch):
    monkeypatch.delenv('KMA_APIHUB_KEY',raising=False)
    with pytest.raises(LiveFailure,match='키를 찾지 못함'):load_key(tmp_path)
    (tmp_path/'.env').write_text('KMA_API_KEY=old-irrelevant\nKMA_APIHUB_KEY="fake-test-value"\n',encoding='utf-8')
    monkeypatch.chdir(tmp_path.parent)
    assert load_key(tmp_path)=='fake-test-value'
    monkeypatch.setenv('KMA_APIHUB_KEY','process-test-value')
    assert load_key(tmp_path)=='process-test-value'
    (tmp_path/'.env').write_text('KMA_APIHUB_KEY=\n',encoding='utf-8')
    monkeypatch.delenv('KMA_APIHUB_KEY')
    with pytest.raises(LiveFailure,match='키를 찾지 못함'):load_key(tmp_path)

def test_mock_mode_never_loads_key_or_calls_network(tmp_path):
    p=provider(tmp_path)
    def forbidden(*args):raise AssertionError('must not access key/network')
    p.key_loader=forbidden;p.transport=forbidden
    result=p.get(119,'mock')
    assert result['status']=='mock' and result['observation']['is_mock']
    assert result['usage']['calls']==0 and result['usage']['bytes']==0

def test_cache_shared_concurrent_requests_and_restart_cooldown(tmp_path):
    calls=[];p=provider(tmp_path,lambda *args:calls.append(args) or current_body())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:p.get(119,'api'),range(8)))
    assert len(calls)==1 and sum(r['status']=='ready' for r in results)==1
    assert all(r['observation']['ws_ms']==0.9 for r in results)
    assert results[-1]['usage']['calls']==1 and results[-1]['usage']['bytes']==len(current_body())
    assert p.get(120,'api')['status']=='waiting' # global cooldown, not each venue/station
    restarted=LiveProvider(p.repo,key_loader=p.key_loader,transport=p.transport,clock=p.clock)
    assert restarted.get(119,'api')['status']=='waiting'
    assert len(calls)==1
    p.clock=lambda:NOW+timedelta(seconds=60)
    assert p.get(119,'api')['status']=='ready' and len(calls)==2

@pytest.mark.parametrize('calls,size',[(DAILY_CALLS,0),(0,DAILY_BYTES-MAX_RESPONSE_BYTES+1)])
def test_daily_budget_blocks_transport(tmp_path,calls,size):
    p=provider(tmp_path,lambda *args:pytest.fail('quota must block transport'))
    with p.repo.connect() as conn:conn.execute('INSERT INTO live_usage VALUES(?,?,?,?)',(NOW.date().isoformat(),calls,size,NOW.timestamp()-61))
    result=p.get(119,'api')
    assert result['status']=='error' and result['error']['stage']=='호출 한도'
    assert result['usage']['calls']==calls

def test_midnight_still_respects_cooldown_but_resets_daily_count(tmp_path):
    p=provider(tmp_path);p.clock=lambda:NOW.replace(hour=23,minute=59,second=50)
    p.get(119,'api');p.clock=lambda:NOW.replace(hour=23,minute=59,second=50)+timedelta(seconds=20)
    assert p.get(119,'api')['status']=='cached' and p.get(119,'api')['usage']['calls']==0
    p.clock=lambda:NOW+timedelta(days=1)
    assert p.get(119,'api')['status']=='ready' and p.get(119,'api')['usage']['calls']==1

def test_failure_retains_dated_observation_and_never_leaks_secrets(tmp_path):
    p=provider(tmp_path);first=p.get(119,'api')
    p.clock=lambda:NOW+timedelta(seconds=61)
    def failure(*args):raise OSError('fake-secret-for-tests https://private.example/?authKey=fake-secret-for-tests')
    p.transport=failure
    result=p.get(119,'api')
    assert result['status']=='error' and result['observation']==first['observation']
    assert result['usage']['calls']==2 and result['usage']['bytes']==len(current_body())+MAX_RESPONSE_BYTES
    assert result['error']['exception_class']=='OSError'
    assert 'fake-secret' not in json.dumps(result,default=str) and 'https://' not in json.dumps(result,default=str)
    assert p.get(119,'api')['status']=='error'
    with p.repo.connect() as conn:
        assert 'fake-secret' not in str(conn.execute('SELECT * FROM live_usage').fetchall())

def test_response_key_echo_is_rejected(tmp_path):
    p=provider(tmp_path,lambda *args:current_body()+b'fake-secret-for-tests')
    result=p.get(119,'api')
    assert result['status']=='error' and result['observation'] is None
    assert 'fake-secret' not in json.dumps(result,default=str)

@pytest.mark.parametrize('status',[401,403,500,302])
def test_http_failures_do_not_return_error_body_headers_or_url(monkeypatch,status):
    from urllib.error import HTTPError
    class FakeOpener:
        def open(self,*args,**kwargs):raise HTTPError('https://private/?authKey=secret',status,'secret',{'secret':'secret'},None)
    monkeypatch.setattr('backend.weather.aws_live.build_opener',lambda *args:FakeOpener())
    with pytest.raises(LiveFailure) as error:request_bytes('secret',119)
    assert error.value.details['http_status']==status
    assert 'secret' not in json.dumps(error.value.details)
    assert NoRedirect().redirect_request(None,None,302,'',{},'https://other/') is None

def test_request_contract_current_time_single_station_and_bounded_read(monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    seen=[]
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):assert size==MAX_RESPONSE_BYTES+1;return current_body()
    class Opener:
        def open(self,req,timeout):seen.append((req,timeout));return Response()
    monkeypatch.setattr('backend.weather.aws_live.build_opener',lambda *args:Opener())
    assert request_bytes('test-only',119)==current_body()
    req,timeout=seen[0];params=parse_qs(urlsplit(req.full_url).query)
    assert params=={'stn':['119'],'disp':['0'],'help':['0'],'authKey':['test-only']}
    assert timeout==10 and urlsplit(req.full_url).scheme=='https'

def test_key_load_failure_is_separate_and_never_reserves_call(tmp_path):
    p=provider(tmp_path,lambda *args:pytest.fail('missing key must block transport'))
    def missing():raise LiveFailure('키 로드','키를 찾지 못함')
    p.key_loader=missing
    result=p.get(119,'api')
    assert result['error']['stage']=='키 로드' and result['usage']['calls']==0

def test_oversized_response_is_rejected_and_bounded_accounting_retained(tmp_path):
    p=provider(tmp_path,lambda *args:b'0'*(MAX_RESPONSE_BYTES+1))
    result=p.get(119,'api')
    assert result['status']=='error' and result['error']['stage']=='HTTP 응답'
    assert result['observation'] is None and result['usage']['bytes']==MAX_RESPONSE_BYTES

def test_transport_timeout_is_sanitized(monkeypatch):
    class Opener:
        def open(self,*args,**kwargs):raise TimeoutError('secret https://private/?authKey=secret')
    monkeypatch.setattr('backend.weather.aws_live.build_opener',lambda *args:Opener())
    with pytest.raises(LiveFailure) as error:request_bytes('secret',119)
    assert error.value.details['stage']=='네트워크 연결'
    assert error.value.details['exception_class']=='TimeoutError'
    assert 'secret' not in json.dumps(error.value.details)

def test_api_uses_existing_engine_shares_one_request_and_preserves_replay(tmp_path):
    app=create_app(tmp_path/'app.sqlite3');p=provider(tmp_path)
    # Install injected transport before using the API path. No project .env read.
    app.state.live_provider=p
    client=TestClient(app)
    before=app.state.repo.list('sessions')
    result=client.post('/api/live-observations',json={'mode':'api'}).json()
    assert result['status']=='ready' and len(result['risks'])==3
    assert result['usage']['calls']==1
    for risk in result['risks']:
        inputs=risk['inputs']
        assert inputs['settings']['pressure_hpa']==1013.25
        assert inputs['weather']['provenance']['observed_station_pressure_hpa']==1013
        assert inputs['weather']['solar_wm2'] is None and inputs['calibration'] is None
        assert inputs['solar']['source']=='일사량 추정'
        assert '하늘상태 누락: 운량 0.7 가정' in inputs['assumptions']
        assert risk['wbgt_low_c']<risk['wbgt_c']<risk['wbgt_high_c']
        from backend.engine.wbgt import estimate
        from backend.weather.models import Venue
        from backend.weather.aws_live import AwsObservation
        observation=AwsObservation(**{**result['observation'],
            'valid_time':datetime.fromisoformat(result['observation']['valid_time']),
            'fetched_at':datetime.fromisoformat(result['observation']['fetched_at'])})
        direct=estimate(Venue(**inputs['venue']),observation.point(risk['venue_id']))
        assert (risk['wbgt_c'],risk['wbgt_low_c'],risk['wbgt_high_c'],risk['level'])==(direct.wbgt_c,direct.wbgt_low_c,direct.wbgt_high_c,direct.level)
    assert app.state.repo.list('sessions')==before
    assert client.post('/api/live-observations',json={'station_id':0}).status_code==422
    assert client.post('/api/live-observations',json={'tournament_id':'missing'}).status_code==404
