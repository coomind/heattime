from dataclasses import replace
from datetime import date, datetime
import math
import pytest
from backend.weather.cli import demo_venues
from backend.weather.adapters import MockForecastAdapter, ManualInputAdapter
from backend.weather.models import KST
from backend.engine.wbgt import estimate, estimate_series, wind_at_2m
from backend.engine.policy import classify, risk_level
from backend.engine.solar import estimate_solar
from backend.engine.settings import EngineSettings
from backend.engine.validate_solar import compare

V=demo_venues()[0]
P=MockForecastAdapter().fetch(V,date(2026,8,1))[14]

@pytest.mark.parametrize("wbgt,level",[(20.999,0),(21,1),(24.999,1),(25,2),(28,3),(31,4)])
def test_general_boundaries(wbgt,level): assert classify(wbgt)==level

@pytest.mark.parametrize("wbgt,level",[(26,0),(26.001,2),(28,2),(28.001,4)])
def test_football_strict_exceedance(wbgt,level): assert classify(wbgt,'football')==level

def test_age_upper_bound_and_optional_escalation():
    assert risk_level(27,28.5,'U12')[0]==3
    assert risk_level(27,28.5,'adult')[0]==2
    assert risk_level(27,28.5,'senior',escalate=True)[0]==4

def test_day_night_rain_and_observed_priority():
    noon=estimate_solar(V,P); night=estimate_solar(V,replace(P,valid_time=datetime(2026,8,1,0,tzinfo=KST)))
    rain=estimate_solar(V,replace(P,pty_code=1)); observed=estimate_solar(V,replace(P,solar_wm2=321))
    assert noon.estimated_wm2>400
    assert night.estimated_wm2==0
    assert rain.estimated_wm2==pytest.approx(noon.estimated_wm2*.5)
    assert observed.used_wm2==321

@pytest.mark.parametrize("hour,temp,rh",[(14,40,90),(0,28,80),(14,35,95)])
def test_extremes_physical_finite_bounds(hour,temp,rh):
    p=replace(P,ta_c=temp,rh_pct=rh,valid_time=datetime(2026,8,1,hour,tzinfo=KST))
    r=estimate(V,p)
    assert r.method_version=='liljegren-lwbgt-1.0.1'
    assert 15<r.wbgt_c<55
    assert r.wbgt_low_c<r.wbgt_c<r.wbgt_high_c
    if rh==90: assert r.wbgt_c>38

def test_humidity_heat_and_solar_monotonic():
    cool=estimate(V,replace(P,ta_c=25,rh_pct=50,solar_wm2=0))
    hot=estimate(V,replace(P,ta_c=40,rh_pct=90,solar_wm2=900))
    assert hot.wbgt_c>cool.wbgt_c+10

def test_offset_wind_fallback_and_hash():
    base=estimate(V,P); shifted=estimate(replace(V,field_offset_c=3.5),P)
    assert shifted.wbgt_c==pytest.approx(base.wbgt_c+1,abs=.002)
    assert shifted.inputs_hash!=base.inputs_hash
    assert wind_at_2m(3)<3
    assert '간이 추정' in estimate(V,P,force_fallback=True).method_version

def test_manual_calibration_only_from_measurement_onward():
    points=MockForecastAdapter().fetch(V,date(2026,8,1)); raw=estimate_series(V,points)
    m=ManualInputAdapter().enter(V.id,points[12].valid_time,raw[12].wbgt_c+2,is_mock=True)
    calibrated=estimate_series(V,points,manual=[m])
    assert calibrated[11].wbgt_c==raw[11].wbgt_c
    assert calibrated[12].wbgt_c==pytest.approx(m.wbgt_c,abs=.002)
    assert calibrated[13].wbgt_c==pytest.approx(raw[13].wbgt_c+2,abs=.002)
    assert calibrated[13].wbgt_high_c-calibrated[13].wbgt_c>=1.5

def test_comparison_requires_data_and_mock_label(tmp_path):
    with pytest.raises(ValueError): compare(V,[P],tmp_path)
    result=compare(V,[replace(P,solar_wm2=450)],tmp_path)
    assert result['is_mock'] and 'NOT OBSERVATIONAL' in result['label']
    assert (tmp_path/'solar-comparison.png').stat().st_size>1000
    assert math.isfinite(result['mae_wm2'])
