from dataclasses import replace
from datetime import date
import json
import numpy as np
import pytest
from backend.weather.asos_samples import load_dataset
from backend.weather.cli import demo_venues
from backend.engine.validate_solar import compare_observed, interval_estimates

V = demo_venues()[0]
P = load_dataset().fetch(V, '119', date(2026,7,1))


def test_interval_integration_converges_and_retains_cloud_rain_formula():
    minute = interval_estimates(V, P)
    fine = interval_estimates(V, P, step_seconds=30)
    assert np.max(np.abs(minute-fine)) < .05
    cloudy = [replace(p,cloud_fraction=1,rain_mm=0) for p in P]
    clear = [replace(p,cloud_fraction=0,rain_mm=0) for p in P]
    rain = [replace(p,cloud_fraction=0,rain_mm=1) for p in P]
    assert np.allclose(interval_estimates(V,cloudy), interval_estimates(V,clear)*.25)
    assert np.allclose(interval_estimates(V,rain), interval_estimates(V,clear)*.5)
    assert minute[0] == 0


def test_metrics_use_only_nonmissing_and_do_not_drop_zero(tmp_path,monkeypatch):
    import backend.engine.validate_solar as module
    points=[replace(P[12],solar_wm2=0),replace(P[13],solar_wm2=20),replace(P[14],solar_wm2=None)]
    monkeypatch.setattr(module,'interval_estimates',lambda v,p:np.array([10.,10.]))
    result=compare_observed(V,points,tmp_path)
    assert result['count']==2 and result['missing_count']==1 and result['total_count']==3
    assert result['mae_wm2']==10 and result['bias_wm2']==0
    pairs=json.loads((tmp_path/'solar-pairs.json').read_text())
    assert len(pairs)==2 and pairs[0]['observed_wm2']==0
    assert (tmp_path/'solar-comparison.png').stat().st_size>1000
    with pytest.raises(ValueError): compare_observed(V,[replace(P[12],is_mock=True)],tmp_path)
    with pytest.raises(ValueError): compare_observed(V,[replace(P[12],solar_wm2=None)],tmp_path)


def test_full_real_comparison_excludes_exact_missing_count(tmp_path):
    data=load_dataset();points=[p for d in data.dates for p in data.fetch(V,'119',d)]
    result=compare_observed(V,points,tmp_path)
    assert result['count']==927 and result['missing_count']==561 and not result['is_mock']
    pairs=json.loads((tmp_path/'solar-pairs.json').read_text())
    errors=[r['estimated_wm2']-r['observed_wm2'] for r in pairs]
    assert result['mae_wm2']==pytest.approx(sum(abs(e) for e in errors)/927)
    assert result['bias_wm2']==pytest.approx(sum(errors)/927)
    assert result['original_sample_sha256']==data.original_sha256
