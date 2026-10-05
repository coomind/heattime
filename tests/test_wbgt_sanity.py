"""Unit/argument/physical decomposition audit, without relaxing existing tests."""
from dataclasses import asdict
from datetime import datetime
import json
import math
import pytest
from lwbgt import calculate
from backend.engine import wbgt
from backend.engine.settings import EngineSettings
from backend.weather.asos_samples import ROOT,load_dataset,numeric
from backend.weather.models import Venue
from scripts.wbgt_sanity import engine_input,shade_proxy,stull_wet_bulb,variant_context

TRACES=json.loads((ROOT/'docs/wbgt-sanity/peak-traces.json').read_text(encoding='utf-8'))
PEAKS=TRACES['rows']


def peak_risk(row):
    v=Venue(row['venue_id'],'가상 예시',row['input']['latitude_deg_north'],
            row['input']['longitude_deg_east'],asos_station_id='119')
    point=next(p for p in load_dataset().fetch(v,'119',datetime.fromisoformat(row['time_kst']).date())
               if p.valid_time.isoformat()==row['time_kst'])
    return v,point,wbgt.estimate(v,point)


@pytest.mark.parametrize('row',PEAKS,ids=lambda x:x['date'])
def test_actual_peak_argument_units_and_order(monkeypatch,row):
    original=wbgt.calculate;captured=[]
    def capture(item):
        captured.append(item)
        return original(item)
    monkeypatch.setattr(wbgt,'calculate',capture)
    v,point,r=peak_risk(row)
    assert len(captured)==1
    item=captured[0]
    assert asdict(item)==row['input']==asdict(engine_input(r))
    assert item.air_temperature_c==point.ta_c
    assert item.relative_humidity_percent==point.rh_pct  # percent, not fraction
    assert item.pressure_hpa==1013.25  # explicit assumption, not observed pa or ps
    assert item.solar_w_m2==pytest.approx(row['solar_raw_mj_m2']*1_000_000/3600)
    assert item.wind_speed_m_s==pytest.approx(max(point.ws_ms*(.2**.2),.13))
    assert item.wind_height_m==2 and item.gmt_offset_hours==9
    assert r.method_version=='liljegren-lwbgt-1.0.1' and r.inputs['fallback_reason'] is None
    assert r.wbgt_c==row['central_c'] and r.wbgt_high_c==row['upper_c']


@pytest.mark.parametrize('row',PEAKS,ids=lambda x:x['date'])
def test_native_components_explain_peak_and_shade_difference(row):
    v,point,r=peak_risk(row);out=calculate(engine_input(r))
    assert out.status==0
    assert out.wbgt_c==pytest.approx(.7*out.natural_wet_bulb_c+.2*out.globe_temperature_c+.1*point.ta_c,abs=5e-6)
    assert asdict(out)==row['result']
    assert out.wbgt_c+2.5==pytest.approx(r.wbgt_c,abs=.0005)
    assert r.wbgt_high_c==pytest.approx(r.wbgt_c+1.5)
    assert row['source_output_max_abs_diff_c']==0  # independently compiled pinned C
    assert sum(row['difference_components_c'].values())==pytest.approx(
        out.wbgt_c+2.5-row['shade_proxy_c'],abs=5e-6)
    assert row['shade_proxy_c']==pytest.approx(shade_proxy(point.ta_c,point.rh_pct))
    assert all(math.isfinite(x) for x in row['difference_components_c'].values())


@pytest.mark.parametrize('row',PEAKS,ids=lambda x:x['date'])
def test_native_solar_split_conserves_horizontal_energy(row):
    s=row['native_solar']
    assert s['direct_horizontal_wm2']+s['diffuse_horizontal_wm2']==pytest.approx(s['effective_ghi_wm2'],abs=1e-9)
    assert s['direct_normal_wm2']*s['cos_zenith']==pytest.approx(s['direct_horizontal_wm2'],abs=1e-9)
    assert 0<=s['direct_fraction']<=.9
    assert s['zenith_deg']==pytest.approx(math.degrees(math.acos(s['cos_zenith'])))
    # None of these peak inputs is changed by the internal upper irradiance cap.
    assert s['effective_ghi_wm2']==pytest.approx(row['input']['solar_w_m2'],abs=.0001)


@pytest.mark.parametrize('wind',[0.,.05,.1,.2,1.,5.])
def test_wind_height_correction_once_and_native_floor(monkeypatch,wind):
    v,p,r=peak_risk(PEAKS[0]);from dataclasses import replace
    captured=[];original=wbgt.calculate
    monkeypatch.setattr(wbgt,'calculate',lambda item:(captured.append(item),original(item))[1])
    changed=wbgt.estimate(v,replace(p,ws_ms=wind))
    assert len(captured)==1
    i=captured[0]
    assert i.wind_speed_m_s==pytest.approx(max(wind*(2/10)**.2,.13))
    assert i.wind_height_m==2.
    assert calculate(i).estimated_wind_speed_m_s==pytest.approx(i.wind_speed_m_s)
    assert changed.inputs['wind_2m_ms']==pytest.approx(wind*(2/10)**.2)


def test_independent_formula_matches_authors_published_example():
    # Author's textbook p95: 20degC,50% ->13.7degC (rounded to 0.1degC).
    assert stull_wet_bulb(20,50)==pytest.approx(13.7,abs=.05)
    assert shade_proxy(20,50)==pytest.approx(.7*stull_wet_bulb(20,50)+6)


def test_peak_selection_is_top_five_plus_demo_day():
    old=json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))
    top=sorted(old['days'],key=lambda x:(-x['max_wbgt_c'],x['date']))[:5]
    assert [r['date'] for r in PEAKS]==[r['date'] for r in top]+['2026-07-10']
    assert [r['central_c'] for r in PEAKS[:5]]==[r['max_wbgt_c'] for r in top]
    assert TRACES['all_62_day_maxima_verified']
    assert TRACES['original_sample_sha256']==load_dataset().original_sha256


def test_pressure_evidence_is_whitelisted_with_correct_units():
    data=json.loads((ROOT/'docs/wbgt-sanity/pressure-evidence.json').read_text(encoding='utf-8'))
    assert data['units']=={'pa':'hPa','ps':'hPa'}
    assert data['original_sample_sha256']==load_dataset().original_sha256
    assert len(data['records'])==1488
    assert all(set(r)=={'tm','pa','paQcflg','ps','psQcflg'} for r in data['records'])
    rows={r['tm']:r for r in data['records']}
    for p in PEAKS:
        row=rows[datetime.fromisoformat(p['time_kst']).strftime('%Y-%m-%d %H:%M')]
        assert row==p['pressure_observed']
        assert 900<numeric(row,'pa',True)<1100
        assert numeric(row,'ps',True)>numeric(row,'pa',True)
