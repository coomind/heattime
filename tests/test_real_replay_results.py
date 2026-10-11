from datetime import datetime
import json
import pytest
from backend.weather.asos_samples import ROOT,load_dataset
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from backend.service import Service
from backend.schedule.optimizer import Candidate,heat_score,validate
from backend.schedule.recommend import recommend
from scripts.replay_asos_dates import candidate_order

RESULTS=json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('row',RESULTS['days'],ids=lambda row:row['date'])
def test_each_real_replay_hard_constraints_and_common_heat(row):
    # Compact result is committed; detailed per-day evidence is produced by the
    # reproducible offline script. Fresh checkouts still check result contracts.
    assert row['assigned']+row['postponed']==15 and row['constraints_ok']
    assert row['common_count']==row['assigned']
    assert len(row['postponement_reasons'])==row['postponed']
    assert all(p['reason'] for p in row['postponement_reasons'])
    assert row['solver'] in ('CP-SAT OPTIMAL','CP-SAT FEASIBLE','greedy-fallback')
    evidence=ROOT/'data/output/real'/(row['date']+'.json')
    if evidence.exists():
        s=json.loads(evidence.read_text(encoding='utf-8'))
        assert s['engine_settings']==EngineSettings().model_dump()
        assert s['schedule_settings']==ScheduleSettings().model_dump()
        assert all(not p['is_mock'] for p in s['weather'])
        t,m,v,r,settings,engine=Service.context(s)
        p=s['proposal'];assigned=[Candidate(**{**a,'start':datetime.fromisoformat(a['start']),'end':datetime.fromisoformat(a['end'])}) for a in p['assignments']]
        assert validate(assigned,m,t,v,r,settings)==[]
        common={a.match_id for a in assigned}
        assert common==set(p['common_match_ids'])
        assert row['original_heat']==sum(heat_score(r,match.venue_id,match.scheduled_start,recommend(match,r,engine).end) for match in m if match.id in common)
        assert row['proposed_heat']==sum(a.heat_score for a in assigned)
        assert row['max_wbgt_c']==max(risk.wbgt_c for risk in r)


def test_all_dates_and_candidate_selection_are_complete():
    data=load_dataset()
    assert [r['date'] for r in RESULTS['days']]==[d.isoformat() for d in data.dates]
    assert RESULTS['original_sample_sha256']==data.original_sha256
    assert RESULTS['candidates']==sorted(RESULTS['days'],key=candidate_order)[:3]
    assert [r['date'] for r in RESULTS['candidates']]==['2026-07-03','2026-08-20','2026-07-10']
    assert all(r['assigned']==15 and r['postponed']==0 and r['salvaged']>=9 for r in RESULTS['candidates'])
