from copy import deepcopy
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import pytest
from backend.plan_review import review,shifted,stop_threshold
from backend.service import Service
from backend.repository import Repository
from backend.engine.policy import policies,risk_level
from backend.engine.settings import EngineSettings
from backend.schedule.models import Tournament
from scripts.analyze_without_field import METHODS,greedy_variant,summarize,secondary_cost
from scripts.compare_schedule_methods import verify_assignments,digest,input_digest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def demo():return json.loads((ROOT/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']

@pytest.mark.parametrize('view',['proposed','approved'])
def test_review_is_readonly_and_baseline_reproduces_frozen_plan(demo,view):
    original=deepcopy(demo);result=review(demo,view)
    assert demo==original
    assert result['assigned']==13 and result['postponed']==2  # 2026-08-10 snapshot: semi2 and final postponed
    assert not result['base']['needs_review'] and result['base']['same_choices_valid']
    zero=next(r for r in result['scenarios'] if r['delta_c']==0)
    assert zero['changed_match_ids']==zero['blocked_match_ids']==zero['constraint_errors']==[]
    assert '오차 범위' in result['limitation'] and '재편성하지' not in result['base']['note']
    assert len(result['matches'])==13  # one row per assigned match in the 2026-08-10 snapshot
    assert all(r['wbgt_low_c']<=r['wbgt_c']<=r['wbgt_high_c'] and r['inputs_hash'] for r in result['matches'])

def test_missing_point_explicitly_holds_affected_games(demo):
    result=review(demo)
    missing=result['missing_case']
    assert missing['missing_match_ids'] and 'missing risk' in missing['constraint_errors']
    assert missing['needs_review'] and not missing['same_choices_valid']
    assert missing['missing_point']['valid_time']

def test_ascending_scenarios_cannot_reduce_stop_games(demo):
    result=review(demo)
    counts=[len(s['blocked_match_ids']) for s in result['scenarios']]
    assert counts==sorted(counts)
    assert all(s['assigned_in_frozen_plan']==13 for s in result['scenarios'])  # 2026-08-10 snapshot assigns 13

@pytest.mark.parametrize('mutate', ['no_proposal','no_decision','rejected','duration','lost_coverage','duplicate_postponement'])
def test_invalid_or_unapproved_reference_is_not_analysis_success(demo,mutate):
    s=deepcopy(demo);view='proposed'
    if mutate=='no_proposal':s['proposal']=None
    if mutate=='no_decision':s['decision']=None;view='approved'
    if mutate=='rejected':s['decision']['operator_action']='rejected';view='approved'
    if mutate=='duration':s['proposal']['assignments'][0]['duration_min']=1
    if mutate=='lost_coverage':s['proposal']['assignments'].pop()
    if mutate=='duplicate_postponement':s['proposal']['postponed']=[{'match_id':s['matches'][0]['id']},{'match_id':s['matches'][0]['id']}]
    with pytest.raises(ValueError):review(s,view)

@pytest.mark.parametrize('age,escalate,policy', [('U12',False,'general'),('U12',True,'general'),('adult',True,'general'),('U12',True,'football')])
def test_margin_uses_actual_policy_and_age_rules(age,escalate,policy):
    tournament=Tournament(id='test',name='가상 예시',date_start=date(2026,7,10),date_end=date(2026,7,10),age_group=age,policy_id=policy)
    engine=EngineSettings(age_escalation=escalate)
    threshold=stop_threshold(tournament,engine)
    # Stage uses the displayed 0.1℃ value; go beyond the rounding half-step.
    eps=0.051
    assert risk_level(threshold-eps,threshold-eps,age,policy,escalate)[0]<4
    assert risk_level(threshold+eps,threshold+eps,age,policy,escalate)[0]==4

@pytest.mark.parametrize('delta',[-1,0,1,2])
def test_perturbation_preserves_inputs_and_range_width(demo,delta):
    t,m,v,risks,settings,engine=Service.context(demo)
    before=deepcopy(risks)
    result=shifted(risks,delta,t,engine)
    assert risks==before
    for old,new in zip(risks,result):
        assert new.wbgt_c==old.wbgt_c+delta
        assert new.wbgt_high_c-new.wbgt_low_c==pytest.approx(old.wbgt_high_c-old.wbgt_low_c)
        assert new.inputs==old.inputs and new.inputs_hash==old.inputs_hash

def test_zero_does_not_reclassify_rounded_display_value(demo):
    t,m,v,r,settings,engine=Service.context(demo)
    rounded=replace(r[0],level=3,wbgt_high_c=policies()['general']['boundaries'][-1])
    assert shifted([rounded],0,t,engine)[0].level==3

@pytest.mark.parametrize('delta',[float('nan'),float('inf'),float('-inf')])
def test_nonfinite_shift_rejected(demo,delta):
    t,m,v,r,settings,engine=Service.context(demo)
    with pytest.raises(ValueError):shifted(r,delta,t,engine)

@pytest.mark.parametrize('method',METHODS)
def test_stronger_baselines_use_original_constraints_without_mutation(demo,method):
    original=deepcopy(demo);t,m,v,r,settings,engine=Service.context(demo)
    chosen=greedy_variant(m,t,v,r,settings,engine,method)
    from scripts.compare_schedule_methods import json_row
    verify_assignments([json_row(a) for a in chosen],demo)
    assert demo==original
    assert len({a.match_id for a in chosen})==len(chosen)

@pytest.fixture(scope='module')
def evidence():return json.loads((ROOT/'docs/competition-evidence/no-field-analysis.json').read_text(encoding='utf-8'))

@pytest.fixture(scope='module')
def service(tmp_path_factory):return Service(Repository(tmp_path_factory.mktemp('no-field')/'offline.sqlite3'))

@pytest.mark.parametrize('index',range(62))
def test_all_dates_validate_every_baseline_and_scenario_against_current_rules(index,evidence,service):
    row=evidence['days'][index];s=service.replay(date.fromisoformat(row['date']),mode='observed')
    assert input_digest(s)==row['input_sha256']
    cp=verify_assignments(row['cp']['assignments'],s)
    for name,baseline in row['baselines'].items():
        selected=verify_assignments(baseline['assignments'],s)
        assert len(selected)==baseline['assigned'] and baseline['assigned']+baseline['postponed']==15
        common={a.match_id for a in selected}&{a['match_id'] for a in row['cp']['assignments']}
        assert set(row['comparisons'][name]['common_match_ids'])==common
        assert row['comparisons'][name]['baseline_common_heat']==sum(a.heat_score for a in selected if a.match_id in common)
        assert row['comparisons'][name]['cp_common_heat']==sum(a.heat_score for a in cp if a.match_id in common)
    best=min([name for name in row['baselines'] if name!='best_of_four'],key=lambda name:(-row['baselines'][name]['assigned'],row['baselines'][name]['secondary_cost'],name))
    assert row['baselines']['best_of_four']['selected_method']==best
    s['proposal']={'assignments':row['cp']['assignments'],'postponed':[{'match_id':m['id'],'reason':'원 고정 제안의 미배정'} for m in s['matches'] if m['id'] not in {a['match_id'] for a in row['cp']['assignments']}]}
    assert review(s)==row['plan_review']

def test_summary_includes_all_62_dates_zero_days_and_adverse_results(evidence):
    assert evidence['summary']==summarize(evidence['days'])
    assert len(evidence['days'])==62
    zero=[d for d in evidence['days'] if not d['cp']['assigned']]
    # 2026-10-11 recalculation (solar interval alignment etc.): 10 zero-assignment days.
    assert [d['date'] for d in zero]==['2026-07-11','2026-07-12','2026-07-13','2026-07-31','2026-08-01',
        '2026-08-03','2026-08-04','2026-08-05','2026-08-06','2026-08-07']
    assert all(not scenario['applicable'] and not scenario['same_choices_valid'] for d in zero for scenario in d['plan_review']['scenarios'])
    ledger=json.loads((ROOT/'docs/competition-evidence/frozen-solutions.json').read_text(encoding='utf-8'))
    assert evidence['ledger_sha256']==digest(ledger)
    asset=json.loads((ROOT/'frontend/src/demo/no-field-analysis.json').read_text(encoding='utf-8'))
    assert asset['summary']==evidence['summary']
