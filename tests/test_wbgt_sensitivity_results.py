"""Saved analysis evidence: all dates, constraints, common heat and solver proof."""
from collections import Counter
from datetime import datetime
import json
import pytest
from backend.weather.asos_samples import ROOT,load_dataset
from backend.schedule.models import ScheduleSettings
from backend.schedule.optimizer import Candidate,validate,heat_score
from backend.schedule.recommend import recommend
from scripts.wbgt_sanity import SCENARIOS,variant_context

RESULT=json.loads((ROOT/'docs/wbgt-sanity/sensitivity-results.json').read_text(encoding='utf-8'))


def test_sensitivity_contains_every_predeclared_scenario_and_same_source():
    assert [x['name'] for x in RESULT['scenarios']]==list(SCENARIOS)
    assert RESULT['analysis_only']
    assert RESULT['original_sample_sha256']==load_dataset().original_sha256
    assert RESULT['settings']==ScheduleSettings().model_dump()


@pytest.mark.parametrize('name',SCENARIOS)
def test_scenario_all_dates_accounting_and_full_coverage_proof(name):
    scenario=next(x for x in RESULT['scenarios'] if x['name']==name)
    offset,upper,shifts=SCENARIOS[name]
    assert scenario['field_offset_c']==offset and scenario['decision_uses_upper']==upper
    assert scenario['hypothetical_site_shift_c']==shifts
    rows=scenario['days'];summary=scenario['summary']
    assert [r['date'] for r in rows]==[d.isoformat() for d in load_dataset().dates]
    assert all(r['assigned']+r['postponed']==15 for r in rows)
    assert summary['complete_days']==sum(r['assigned']==15 for r in rows)
    assert summary['incomplete_days']==sum(r['assigned']<15 for r in rows)
    assert summary['zero_assignment_days']==sum(r['assigned']==0 for r in rows)
    assert summary['assigned_total']==sum(r['assigned'] for r in rows)
    assert summary['postponed_total']==930-summary['assigned_total']
    assert summary['unproven_incomplete_days']==[r['date'] for r in rows if not r['full_coverage_proven']]
    for r in rows:
        assert r['solver'] in ('CP-SAT OPTIMAL','CP-SAT FEASIBLE','greedy-fallback')
        assert r['full_coverage_proven']==(r['assigned']==15 or r['coverage_optimal'])
        if r['coverage_optimal']:assert r['solver']=='CP-SAT OPTIMAL'


@pytest.mark.parametrize('name',[n for n in SCENARIOS if n!='baseline'])
def test_available_detailed_analysis_proposals_obey_all_constraints_and_common_heat(name):
    # Detailed schedules are generated locally; compact records are committed.
    # On a fresh clone, the offline reproduction command generates this evidence.
    sessions_path=ROOT/'data/output/wbgt-sanity/fresh-sessions.json'
    if not sessions_path.exists():
        pytest.skip('Run documented offline sensitivity to produce detailed schedules')
    sessions=json.loads(sessions_path.read_text(encoding='utf-8'))
    scenario=next(x for x in RESULT['scenarios'] if x['name']==name)
    for session,row in zip(sessions,scenario['days'],strict=True):
        evidence=ROOT/'data/output/wbgt-sanity'/name/(row['date']+'.json')
        assert evidence.exists()
        saved=json.loads(evidence.read_text(encoding='utf-8'));p=saved['proposal']
        assert saved['analysis_only'] and saved['summary']==row
        t,m,v,risks,settings,engine=variant_context(session,*SCENARIOS[name])
        assigned=[Candidate(**{**a,'start':datetime.fromisoformat(a['start']),
                              'end':datetime.fromisoformat(a['end'])}) for a in p['assignments']]
        assert validate(assigned,m,t,v,risks,settings)==[]
        common={a.match_id for a in assigned}
        assert common==set(p['common_match_ids'])
        assert len(common)==row['assigned'] and len(p['postponed'])==row['postponed']
        assert all(x['reason'] for x in p['postponed'])
        assert p['postponement_penalty']>p['secondary_cost_upper_bound']
        assert p['original_heat_score']==sum(heat_score(risks,x.venue_id,x.scheduled_start,
            recommend(x,risks,engine).end) for x in m if x.id in common)
        assert p['proposed_heat_score']==sum(a.heat_score for a in assigned)


def test_baseline_statement_uses_incomplete_not_impossible_days():
    b=next(x for x in RESULT['scenarios'] if x['name']=='baseline')
    # 2026-10-11 recalculation (solar interval alignment, 0.1C rounding, fixed tie-break): 47/10/15.
    assert b['summary']['incomplete_days']==47
    assert b['summary']['zero_assignment_days']==10
    assert b['summary']['complete_days']==15
    assert b['summary']['unproven_incomplete_days']==[]
    assert {x['date'] for x in b['days'] if x['assigned']==0}=={
        '2026-07-11','2026-07-12','2026-07-13','2026-07-31','2026-08-01',
        '2026-08-03','2026-08-04','2026-08-05','2026-08-06','2026-08-07'}
    # Regenerated baseline: all 62 days proved OPTIMAL (previously 61 OPTIMAL + 1 FEASIBLE).
    assert Counter(x['solver'] for x in b['days'])=={'CP-SAT OPTIMAL':62}
