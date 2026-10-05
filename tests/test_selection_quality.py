import json
from datetime import date
from pathlib import Path
import pytest
from backend.schedule.alternatives import choose_validated,greedy,METHODS,secondary_cost
from backend.schedule.optimizer import optimize,candidates_for,validate
from scripts.analyze_tournament_scale import make_service
from scripts.analyze_without_field import greedy_variant
from scripts.compare_schedule_methods import verify_assignments
from tests.test_schedule import scenario


def test_selector_prefers_coverage_then_existing_cost_and_cp_on_equal():
    t,_,m,v,r=scenario(mild=True)
    from backend.schedule.models import ScheduleSettings
    from backend.engine.settings import EngineSettings
    settings=ScheduleSettings();engine=EngineSettings()
    options={match.id:candidates_for(match,t,v,r,settings,engine) for match in m}
    full=greedy(m,t,v,r,settings,options,'earliest_input')
    method,selected,records=choose_validated([('cp_sat',full[:-1]),('earliest_input',full)],m,t,v,r,settings)
    assert method=='earliest_input' and len(selected)==len(full)>len(full[:-1])
    assert all(row['constraints_ok'] for row in records)
    assert choose_validated([('earliest_input',full),('cp_sat',full)],m,t,v,r,settings)[0]=='cp_sat'


@pytest.mark.parametrize('day',['2026-07-09','2026-08-16'])
def test_larger_adverse_cases_select_all_27_without_changing_defaults(tmp_path,day):
    service=make_service(tmp_path/'case.sqlite3');s=service.replay(date.fromisoformat(day),tournament_id='benchmark16',mode='observed')
    t,m,v,r,settings,engine=service.context(s)
    assert settings.time_limit_sec==10 and settings.cleanup_min==5 and engine.uncertainty_c==1.5
    result=optimize(m,t,v,r,settings,engine)
    assert len(result.assignments)==27 and not result.postponed
    assert not validate(result.assignments,m,t,v,r,settings)
    assert result.cp_sat_status in {'OPTIMAL','FEASIBLE','UNKNOWN'}
    assert len(result.selection_candidates)>=4
    assert result.coverage_optimal==(result.cp_sat_status=='OPTIMAL')


def test_unproven_postponement_never_claims_infeasibility():
    t,_,m,v,r=scenario(all_stop=True)
    result=optimize(m,t,v,r,force_greedy=True)
    assert result.postponed and not result.coverage_optimal
    assert all(p['reason']=='제한 시간 내 배정하지 못함 · 불가능 증명 아님' and not p['coverage_proven'] for p in result.postponed)
    proven=optimize(m,t,v,r)
    assert proven.coverage_optimal and all(p['coverage_proven'] and '불가능 증명 아님' not in p['reason'] for p in proven.postponed)


@pytest.mark.parametrize('index',range(93))
def test_all_31_larger_and_62_original_updated_selections(index,tmp_path):
    root=Path(__file__).resolve().parents[1]
    packet=json.loads((root/'docs/competition-evidence/review-fix-results.json').read_text(encoding='utf-8'))
    assert len(packet['cases'])==93
    c=packet['cases'][index]
    from backend.service import Service
    from backend.repository import Repository
    service=make_service(tmp_path/'r.sqlite3') if c['teams']==16 else Service(Repository(tmp_path/'r.sqlite3'))
    s=service.replay(date.fromisoformat(c['start']),tournament_id='benchmark16' if c['teams']==16 else 'demo',mode='observed')
    from scripts.compare_schedule_methods import input_digest
    assert input_digest(s)==c['input_sha256']
    verify_assignments(c['selected']['assignments'],s)
    for baseline in c['baselines'].values():verify_assignments(baseline['assignments'],s)
    best=c['baselines'][c['best_baseline']]
    assert c['selected']['assigned']>=best['assigned']
    if c['selected']['assigned']==best['assigned']:assert c['selected']['secondary_cost']<=best['secondary_cost']
    if c['teams']==12:assert c['selected']['assigned']>=c['previous_assigned']
    assert c['coverage_optimal']==(c['cp_sat_status']=='OPTIMAL')
    if not c['coverage_optimal']:assert all('불가능 증명 아님' in p['reason'] for p in c['postponed'])
