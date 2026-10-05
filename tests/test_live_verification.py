"""Offline tests only. Importing the verifier does not load a real key."""
import json
from pathlib import Path
from datetime import datetime
import pytest
from scripts.verify_live_connection import safe_shape,canonical_sample,receipt
from tests.test_aws_live import body,SAMPLE
from backend.weather.aws_live import parse_observation


def test_shape_and_canonical_sample_exclude_raw_comments_headers_and_url():
    raw=body()+b'\n# secret https://private.example/?authKey=secret\n'
    shape=safe_shape(raw)
    assert shape['headers'][0]['matches_documented'] and shape['data_column_counts']==[18]
    sample=canonical_sample(raw)
    assert 'secret' not in sample and 'https://' not in sample
    assert len(sample.splitlines()[1].split())==18
    assert 'secret' not in json.dumps(shape)

@pytest.mark.parametrize('data',[b'<html>secret https://private/</html>',b'\xff',body(SAMPLE+' secret'),body(SAMPLE.replace('0.3','nan'))])
def test_unknown_response_is_not_saved_as_sample(data):
    assert canonical_sample(data) is None
    assert 'secret' not in json.dumps(safe_shape(data)) and 'https://' not in json.dumps(safe_shape(data))

def test_unknown_header_names_are_redacted():
    shape=safe_shape(body().replace(b' WS10 ',b' secret '))
    assert shape['headers'][0]['matches_documented'] is False
    assert '<unknown>' in shape['headers'][0]['documented_columns']
    assert 'secret' not in json.dumps(shape)

def test_receipt_distinguishes_application_response_and_upstream_error():
    payload={'status':'error','error':{'stage':'HTTP 응답','http_status':403},
             'retry_after_seconds':0,'observation':None,'usage':{},'risks':[]}
    result=receipt(payload,1,{})
    assert result['application_http_status']==200 and result['upstream_http_status']==403
    payload['error']['http_status']=None
    assert receipt(payload,1,{})['upstream_http_status'] is None

def test_actual_authorized_sample_preserves_verified_units_and_timestamp():
    root=Path(__file__).resolve().parents[1]
    verified=json.loads((root/'docs/kma/live-connection-verification.json').read_text(encoding='utf-8'))
    obs=verified['observation']
    sample=(root/'tests/fixtures/aws-119-20261005-2335.txt').read_bytes()
    point=parse_observation(sample,119,datetime.fromisoformat(obs['fetched_at']))
    assert verified['upstream_http_status']==200
    assert verified['upstream_shape']['headers'][0]['matches_documented']
    assert point.valid_time.isoformat()=='2026-10-05T23:35:00+09:00'
    assert (point.ta_c,point.rh_pct,point.ws_ms)==(11.9,58.3,0.2)
    assert (point.station_pressure_hpa,point.sea_level_pressure_hpa,point.rain_60m_mm)==(1011.3,1016.1,0)
    assert point.point('fixture').solar_wm2 is None and not point.is_mock
    assert obs['valid_time']==point.valid_time.isoformat()
