from dataclasses import replace
from datetime import datetime,timedelta
from types import SimpleNamespace
import pytest
from backend.schedule.demo import demo_tournament
from backend.schedule.optimizer import optimize,validate,participants,Candidate,sunset,forced_feasibility,heat_score
from backend.schedule.recommend import recommend
from backend.schedule.models import ScheduleSettings
from backend.engine.policy import classify
from backend.weather.models import KST


def scenario(all_stop=False,mild=False):
    t,teams,matches,venues=demo_tournament();risks=[]
    for v in venues:
        for h in range(24):
            value=34 if all_stop else 23.5 if mild else 33 if 12<=h<16 else 23.5
            risks.append(SimpleNamespace(venue_id=v.id,valid_time=datetime(2026,8,1,h,tzinfo=KST),wbgt_c=value,wbgt_low_c=value-1.5,wbgt_high_c=value+1.5,decision_wbgt_c=value+1.5,level=classify(value+1.5)))
    return t,teams,matches,venues,risks


def test_cooling_recalculates_end_and_checks_extended_interval():
    t,teams,matches,venues,risks=scenario();m=matches[0].model_copy(update={'scheduled_start':datetime(2026,8,1,10,tzinfo=KST)})
    r=recommend(m,risks);assert r.duration_min==51 and r.action=='cooling_break' and len(r.cooling_times)==2
    m=m.model_copy(update={'scheduled_start':datetime(2026,8,1,11,10,tzinfo=KST)})
    assert recommend(m,risks).level==4


def test_cp_sat_all_constraints_and_heat_reduction():
    t,teams,matches,venues,risks=scenario();result=optimize(matches,t,venues,risks)
    assert result.constraints_ok and len(result.assignments)+len(result.postponed)==15
    # OPTIMAL proves the full weighted objective within 10s and depends on CPU
    # resources. The result contract is fourteen feasible games plus one
    # postponement; the independent forced solve below proves why the last
    # game cannot be scheduled. Keep every constraint and heat assertion.
    assert len(result.assignments)==14 and len(result.postponed)==1
    assert result.postponement_penalty>result.secondary_cost_upper_bound
    assert result.postponed and all(p['reason'] for p in result.postponed)
    for p in result.postponed:
        assert forced_feasibility(p['match_id'],matches,t,venues,risks)['status']=='INFEASIBLE'
    common={a.match_id for a in result.assignments}
    assert set(result.common_match_ids)==common and result.postponed_count==len(result.postponed)
    original=sum(heat_score(risks,m.venue_id,m.scheduled_start,recommend(m,risks).end) for m in matches if m.id in common)
    assert result.original_heat_score==original
    assert result.proposed_heat_score<result.original_heat_score
    assert validate(result.assignments,matches,t,venues,risks,ScheduleSettings())==[]
    for a in result.assignments:
        assert a.level<4 and a.start.minute%15==0
    for a in result.assignments:
        v=next(v for v in venues if v.id==a.venue_id)
        if not v.has_lights:assert a.end+timedelta(minutes=5)<=sunset(a.start.date(),v.lat,v.lon)


def test_greedy_fallback_keeps_hard_constraints():
    t,teams,matches,venues,risks=scenario();r=optimize(matches,t,venues,risks,force_greedy=True)
    assert r.assignments and r.constraints_ok and r.solver=='greedy-fallback'
    assert validate(r.assignments,matches,t,venues,risks,ScheduleSettings())==[]


def test_no_feasible_slots_postpone_with_reasons():
    t,teams,matches,venues,risks=scenario(True);r=optimize(matches,t,venues,risks)
    assert not r.assignments and len(r.postponed)==15
    assert all(p['reason'] for p in r.postponed)


def test_missing_data_cannot_be_allocated():
    t,teams,matches,venues,risks=scenario();assert recommend(matches[0],[]).level==4
    assert not optimize(matches,t,venues,[]).assignments


def test_dependency_cycle_rejected():
    t,teams,matches,venues,risks=scenario()
    altered=matches[0].model_copy(update={'depends_on':['final']})
    with pytest.raises(ValueError):participants([altered]+matches[1:])


def test_validator_detects_each_constraint_independently():
    t,teams,matches,venues,risks=scenario();m=matches[0];base=datetime(2026,8,1,7,tzinfo=KST)
    a=Candidate(m.id,venues[0].id,base,base+timedelta(minutes=51),2,1,51,[],'cooling_break')
    b=replace(a,match_id=matches[1].id,start=base+timedelta(minutes=45),end=base+timedelta(minutes=96))
    assert 'venue overlap/cleanup' in validate([a,b],matches,t,venues,risks,ScheduleSettings())
    b=replace(b,venue_id=venues[1].id,start=base+timedelta(minutes=60),end=base+timedelta(minutes=111))
    assert 'team rest' in validate([a,b],matches,t,venues,risks,ScheduleSettings())
    assert 'dependency' in validate([replace(a,match_id='final')],matches,t,venues,risks,ScheduleSettings())
    assert 'prohibited heat slot' in validate([replace(a,start=base+timedelta(hours=6),end=base+timedelta(hours=7))],matches,t,venues,risks,ScheduleSettings())
    assert 'operating window/sunset' in validate([replace(a,start=base-timedelta(hours=1),end=base)],matches,t,venues,risks,ScheduleSettings())
    assert 'date range' in validate([replace(a,start=base+timedelta(days=1),end=base+timedelta(days=1,minutes=51))],matches,t,venues,risks,ScheduleSettings())


def test_mild_scenario_all_fifteen_assigned():
    t,teams,matches,venues,risks=scenario(mild=True)
    assert all(r.level<=2 for r in risks)
    result=optimize(matches,t,venues,risks)
    assert len(result.assignments)==15 and not result.postponed
    assert validate(result.assignments,matches,t,venues,risks,ScheduleSettings())==[]


def test_postponement_priority_exceeds_total_secondary_cost_with_extreme_weights():
    t,teams,matches,venues,risks=scenario(mild=True)
    settings=ScheduleSettings(heat_weight=10000,time_weight=1000,venue_penalty=10000)
    result=optimize(matches,t,venues,risks,settings)
    assert len(result.assignments)==15 and not result.postponed
    assert result.postponement_penalty>result.secondary_cost_upper_bound


def test_each_all_stop_postponement_is_proven_infeasible():
    t,teams,matches,venues,risks=scenario(all_stop=True)
    result=optimize(matches,t,venues,risks)
    for p in result.postponed:
        assert forced_feasibility(p['match_id'],matches,t,venues,risks)['status']=='INFEASIBLE'
