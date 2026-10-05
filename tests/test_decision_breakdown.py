from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from pypdf import PdfReader
import pytest
from backend.decision_breakdown import breakdown,explanation
from backend.exports import records_pdf

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def session():return json.loads((ROOT/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']

def test_every_observed_risk_decomposes_exactly_and_does_not_mutate(session):
    original=deepcopy(session)
    for r in session['risks']:
        b=breakdown(r)
        assert b['model_c']+b['field_offset_c']+b['surface_offset_c']+b['calibration_c']+b['upper_width_c']==pytest.approx(b['decision_c'],abs=.001)
        assert b['field_offset_c']==2.5 and b['upper_width_c']==1.5
        assert b['counterfactual_c']==pytest.approx(b['model_c'],abs=.001)
        assert b['counterfactual_level']<=b['level']
    assert session==original

def test_surface_calibration_and_adult_zero_upper_are_separate_terms(session):
    r=deepcopy(session['risks'][0]);r['inputs']['settings']['surface_offsets']['natural_grass']=.7
    r['inputs']['calibration']=[-.4,2];r['decision_wbgt_c']=r['wbgt_c']
    b=breakdown(r)
    assert b['surface_offset_c']==.7 and b['calibration_c']==-.4 and b['upper_width_c']==0
    assert b['counterfactual_c']==pytest.approx(r['wbgt_c']-3.2,abs=.001)
    assert '현장 보정' in explanation(r) and '표면 보정' in explanation(r)

def test_pdf_contains_decision_components_counterfactual_and_original_notice(session):
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(session))).pages)
    for term in ['모델 추정','구장 보정','판정 상단 폭','판정값','보정0℃·중앙값','설정/승인 변경 없음','본 자료는 의사결정 보조용 추정값','선택 방법','CP-SAT 상태']:
        assert term in text

