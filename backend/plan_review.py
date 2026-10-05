"""Read-only scenario review of frozen kickoff/venue choices, never reoptimizes."""
from dataclasses import replace
from datetime import datetime
from math import isfinite
from backend.engine.policy import policies, risk_level
from backend.exports import record_context
from backend.schedule.optimizer import Candidate, validate, heat_score
from backend.schedule.recommend import recommend, window_risks
from backend.service import Service

SCENARIOS = (-1, 0, 1, 2)
LIMITATION = '분석용 가상 변화량이며 실제 오차 범위·확률·안전 보장이 아닙니다. 재편성·승인·설정은 바뀌지 않습니다.'


def restore(rows):
    return [Candidate(**{**row, 'start': datetime.fromisoformat(row['start']),
                         'end': datetime.fromisoformat(row['end']),
                         'cooling_times': [datetime.fromisoformat(t) for t in row['cooling_times']]}) for row in rows]


def shifted(risks, delta, tournament, engine):
    if not isfinite(delta): raise ValueError('분석 변화량은 유한값이어야 합니다.')
    if delta == 0: return list(risks)  # Preserve classification before display rounding.
    result = []
    for r in risks:
        central, low, high = r.wbgt_c+delta, r.wbgt_low_c+delta, r.wbgt_high_c+delta
        level, decision = risk_level(central, high, tournament.age_group, tournament.policy_id, engine.age_escalation)
        result.append(replace(r, wbgt_c=central, wbgt_low_c=low, wbgt_high_c=high, level=level, decision_wbgt_c=decision))
    return result


def inspect_scenario(selected, matches, tournament, venues, risks, settings, engine):
    by = {m.id:m for m in matches}; adjusted = []; blocked = []; changed = []; missing = []
    for a in selected:
        rec = recommend(by[a.match_id].model_copy(update={'venue_id':a.venue_id, 'scheduled_start':a.start}), risks, engine)
        if rec.wbgt_c is None: missing.append(a.match_id)
        elif rec.level == 4: blocked.append(a.match_id)
        if (rec.level,rec.action,rec.end,rec.duration_min,rec.cooling_times) != (a.level,a.action,a.end,a.duration_min,a.cooling_times):
            changed.append(a.match_id)
        adjusted.append(replace(a, end=rec.end,level=rec.level,action=rec.action,duration_min=rec.duration_min,cooling_times=rec.cooling_times))
    errors = validate(adjusted,matches,tournament,venues,risks,settings)
    return {'applicable':bool(selected), 'assigned_in_frozen_plan':len(selected),
            'blocked_match_ids':blocked, 'missing_match_ids':missing, 'changed_match_ids':changed,
            'constraint_errors':errors, 'same_choices_valid':bool(selected) and not errors,
            'needs_review':bool(selected) and bool(errors or changed),
            'note':'고정 킥오프·구장에서 기존 권고를 다시 산정했습니다. 배정 가능 경기 수의 재풀이가 아닙니다.'}


def stop_threshold(tournament,engine):
    policy=policies()[tournament.policy_id]
    threshold=policy['postpone_above'] if tournament.policy_id=='football' else policy['boundaries'][-1]
    if tournament.policy_id!='football' and engine.age_escalation and tournament.age_group in policies()['age']['upper_bound_groups']:
        threshold=policy['boundaries'][-2]
    return threshold


def review(session, view='proposed'):
    if view not in {'proposed','approved'}:raise ValueError('알 수 없는 일정 보기입니다.')
    if view == 'approved':
        if not session.get('decision') or session['decision']['operator_action']=='rejected':
            raise ValueError('승인된 일정이 없습니다.')
        s=record_context(session);plan=session['decision'];state='승인된 일정'
    else:
        if not session.get('proposal'):raise ValueError('먼저 재편성안을 만드세요.')
        s=session;plan=session['proposal'];state='승인 전 자동 제안'
    tournament,matches,venues,risks,settings,engine=Service.context(s)
    selected=restore(plan['assignments']);base=inspect_scenario(selected,matches,tournament,venues,risks,settings,engine)
    ids={a.match_id for a in selected};postponed=[p['match_id'] for p in plan.get('postponed',[])]
    if ids&set(postponed) or ids|set(postponed)!={m.id for m in matches} or len(postponed)!=len(set(postponed)):
        raise ValueError('고정 일정의 배정·연기 경기 집합이 일치하지 않습니다.')
    if base['constraint_errors'] or base['changed_match_ids']:raise ValueError('고정 일정과 원래 권고·제약이 일치하지 않습니다.')
    threshold=stop_threshold(tournament,engine)
    rows=[];critical=[]
    for a in selected:
        samples=window_risks(risks,a.venue_id,a.start,a.end)
        r=max(samples,key=lambda r:r.decision_wbgt_c)
        margin=threshold-r.decision_wbgt_c
        critical.extend(samples)
        rows.append({'match_id':a.match_id,'venue_id':a.venue_id,'start':a.start.isoformat(),
                     'valid_time':r.valid_time.isoformat(),'wbgt_c':r.wbgt_c,'wbgt_low_c':r.wbgt_low_c,
                     'wbgt_high_c':r.wbgt_high_c,'decision_wbgt_c':r.decision_wbgt_c,'level':r.level,
                     'stop_margin_c':round(margin,3),'inputs_hash':r.inputs_hash})
    scenarios=[]
    for delta in SCENARIOS:
        scenarios.append({'id':f'wbgt_{delta:+d}','delta_c':delta,
                          **inspect_scenario(selected,matches,tournament,venues,shifted(risks,delta,tournament,engine),settings,engine)})
    lost=max(critical,key=lambda r:r.decision_wbgt_c) if critical else None
    missing_risks=[r for r in risks if not lost or (r.venue_id,r.valid_time)!=(lost.venue_id,lost.valid_time)]
    missing_case={'id':'missing_critical_hour','missing_point':{'venue_id':lost.venue_id,'valid_time':lost.valid_time.isoformat()} if lost else None,
                  **inspect_scenario(selected,matches,tournament,venues,missing_risks,settings,engine)}
    return {'view':view,'plan_state':state,'label':s['label'],'limitation':LIMITATION,
            'threshold_c':threshold,'stop_comparison':'>' if tournament.policy_id=='football' else '>=',
            'age_group':tournament.age_group,'policy_id':tournament.policy_id,
            'assigned':len(selected),'postponed':len(plan.get('postponed',[])),
            'base':base,'matches':rows,'scenarios':scenarios,'missing_case':missing_case,
            'reference_method':'WBGT 중앙·하단·상단을 같은 양만큼 이동. 원 입력/가정의 지문은 원본 참조용이며 새 엔진 계산을 뜻하지 않습니다.'}
