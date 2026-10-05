"""Offline: stronger deterministic baselines and frozen-plan stress scenarios."""
from datetime import date
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.repository import Repository
from backend.service import Service
from backend.schedule.optimizer import candidates_for,participants,validate
from backend.plan_review import review,restore
from scripts.compare_schedule_methods import digest,input_digest,verify_assignments,json_row

METHODS=('earliest_input','earliest_reverse','weighted_critical')


def descendant_counts(matches):
    return {m.id:sum(m.id in ancestor_ids(other.id,matches) for other in matches if other.id!=m.id) for m in matches}


def ancestor_ids(mid,matches):
    by={m.id:m for m in matches};seen=set();pending=list(by[mid].depends_on)
    while pending:
        current=pending.pop()
        if current in seen:continue
        seen.add(current);pending+=by[current].depends_on
    return seen


def secondary_cost(candidate,match,settings):
    return candidate.heat_score*settings.heat_weight+abs((candidate.start-match.scheduled_start).total_seconds()/60)*settings.time_weight+(candidate.venue_id!=match.venue_id)*settings.venue_penalty


def greedy_variant(matches,tournament,venues,risks,settings,engine,method,options=None):
    if method not in METHODS:raise ValueError('Unknown comparison method')
    options=options or {m.id:candidates_for(m,tournament,venues,risks,settings,engine) for m in matches}
    priority=descendant_counts(matches) if method=='weighted_critical' else {}
    pending=list(reversed(matches)) if method=='earliest_reverse' else list(matches)
    if priority:pending.sort(key=lambda m:(-priority[m.id],m.id))
    chosen=[]
    while pending:
        ids={m.id for m in pending};ready=[m for m in pending if not set(m.depends_on)&ids]
        if not ready:raise ValueError('Cyclic dependencies')
        for m in ready:
            key=(lambda c:(secondary_cost(c,m,settings),c.start,c.venue_id)) if method=='weighted_critical' else (lambda c:(c.start,c.end,c.venue_id,c.heat_score))
            for c in sorted(options[m.id],key=key):
                if not validate(chosen+[c],matches,tournament,venues,risks,settings):chosen.append(c);break
            pending.remove(m)
    return chosen


def describe(selected,matches,settings):
    by={m.id:m for m in matches}
    return {'assigned':len(selected),'postponed':len(matches)-len(selected),
            'secondary_cost':int(sum(secondary_cost(a,by[a.match_id],settings) for a in selected)),
            'assignments':[json_row(a) for a in selected]}


def summarize(days):
    names=['existing_heat_first',*METHODS,'best_of_four']
    methods={}
    for name in names:
        rows=[d['baselines'][name] for d in days]
        common=[d['comparisons'][name] for d in days if d['comparisons'][name]['common_match_ids']]
        methods[name]={'assigned':sum(r['assigned'] for r in rows),'postponed':sum(r['postponed'] for r in rows),
                       'complete_days':sum(r['postponed']==0 for r in rows),
                       'cp_more_days':sum(d['cp']['assigned']>d['baselines'][name]['assigned'] for d in days),
                       'cp_equal_days':sum(d['cp']['assigned']==d['baselines'][name]['assigned'] for d in days),
                       'cp_fewer_days':sum(d['cp']['assigned']<d['baselines'][name]['assigned'] for d in days),
                       'baseline_common_heat':sum(r['baseline_common_heat'] for r in common),
                       'cp_common_heat':sum(r['cp_common_heat'] for r in common),
                       'equal_coverage_secondary_win_days':sum(d['cp']['assigned']==d['baselines'][name]['assigned'] and d['cp']['secondary_cost']<d['baselines'][name]['secondary_cost'] for d in days),
                       'equal_coverage_secondary_loss_days':sum(d['cp']['assigned']==d['baselines'][name]['assigned'] and d['cp']['secondary_cost']>d['baselines'][name]['secondary_cost'] for d in days)}
    scenarios={}
    for id in ['wbgt_-1','wbgt_+0','wbgt_+1','wbgt_+2','missing_critical_hour']:
        rows=[d['plan_review']['missing_case'] if id=='missing_critical_hour' else next(s for s in d['plan_review']['scenarios'] if s['id']==id) for d in days]
        scenarios[id]={'applicable_days':sum(r['applicable'] for r in rows),
                       'same_choices_valid_days':sum(r['same_choices_valid'] for r in rows),
                       'needs_review_days':sum(r['needs_review'] for r in rows),
                       'heat_blocked_matches':sum(len(r['blocked_match_ids']) for r in rows),
                       'missing_matches':sum(len(r['missing_match_ids']) for r in rows)}
    return {'days':len(days),'cp_assigned':sum(d['cp']['assigned'] for d in days),'baselines':methods,'scenarios':scenarios}


def analyze():
    ledger=json.loads((ROOT/'docs/competition-evidence/frozen-solutions.json').read_text(encoding='utf-8'))
    previous=json.loads((ROOT/'docs/competition-evidence/method-comparison.json').read_text(encoding='utf-8'))
    output=ROOT/'data/output/no-field';output.mkdir(parents=True,exist_ok=True)
    service=Service(Repository(output/(uuid4().hex+'.sqlite3')));days=[];started=perf_counter()
    for frozen,old in zip(ledger['days'],previous['days'],strict=True):
        if frozen['date']!=old['date']:raise ValueError('Date mismatch')
        s=service.replay(date.fromisoformat(frozen['date']),mode='observed')
        if input_digest(s)!=frozen['input_sha256']:raise ValueError('Frozen input mismatch')
        t,m,v,r,settings,engine=Service.context(s)
        cp=verify_assignments(frozen['assignments'],s)
        options={match.id:candidates_for(match,t,v,r,settings,engine) for match in m}
        baselines={'existing_heat_first':describe(verify_assignments(old['greedy_assignments'],s),m,settings)}
        for method in METHODS:
            chosen=greedy_variant(m,t,v,r,settings,engine,method,options)
            verify_assignments([json_row(a) for a in chosen],s)
            baselines[method]=describe(chosen,m,settings)
        best=min(baselines,key=lambda name:(-baselines[name]['assigned'],baselines[name]['secondary_cost'],name))
        baselines['best_of_four']={**baselines[best],'selected_method':best}
        comparisons={}
        for name,baseline in baselines.items():
            common={a.match_id for a in cp}&{a['match_id'] for a in baseline['assignments']}
            comparisons[name]={'common_match_ids':sorted(common),'cp_common_heat':sum(a.heat_score for a in cp if a.match_id in common),
                               'baseline_common_heat':sum(a['heat_score'] for a in baseline['assignments'] if a['match_id'] in common)}
        s['proposal']={'assignments':frozen['assignments'],'postponed':frozen['postponed']}
        days.append({'date':frozen['date'],'input_sha256':frozen['input_sha256'],'cp':describe(cp,m,settings),
                     'cp_solver':frozen['solver'],'baselines':baselines,'comparisons':comparisons,'plan_review':review(s)})
        print(json.dumps({'date':frozen['date'],'cp':len(cp),'best_greedy':baselines[best]['assigned']}),flush=True)
    result={'version':1,'label':'관측 입력 기반 가상 대회 · 사전 계산 · 현장 실측 아님',
            'original_sample_sha256':ledger['original_sample_sha256'],'ledger_sha256':digest(ledger),
            'baseline_rule':'4종 고정 규칙을 모든 날짜에 적용. 날짜별 배정 수 최대, 그 안에서 기존 부목적 비용 최소인 탐욕을 유리하게 선택.',
            'scenario_rule':'고정 WBGT 추정 전체를 -1/0/+1/+2℃ 이동하고 권고 종료·휴식·일몰 등을 재검사. 오차 범위/발생 확률 아님. 재편성하지 않음.',
            'summary':summarize(days),'days':days,'elapsed_sec':round(perf_counter()-started,3)}
    (ROOT/'docs/competition-evidence/no-field-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    compact={**result,'days':[{**d,'baselines':{k:{a:b for a,b in val.items() if a!='assignments'} for k,val in d['baselines'].items()}} for d in days]}
    (ROOT/'frontend/src/demo/no-field-analysis.json').write_text(json.dumps(compact,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=True),flush=True)
    return result

if __name__=='__main__':analyze()
