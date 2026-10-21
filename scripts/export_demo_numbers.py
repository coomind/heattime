"""Export presentation numbers from the committed scene snapshots and analysis results (no hand copying).

Writes data/output/demo-numbers.json and the same content as data/output/demo-numbers.md.
Sources: frontend/src/demo/observed-snapshot*.json, docs/real-data/replay-results.json,
docs/wbgt-sanity/sensitivity-results.json, backend/config/*.yaml. The (가)(나)(다) day table is
re-solved here with the same analysis function as the 62-day sensitivity (scripts/wbgt_sanity.variant_context).
All WBGT values are estimates from observed weather for a virtual tournament (decision support only).
"""
from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.decision_breakdown import breakdown
from backend.display_names import match_name, placeholder_name
from backend.engine.policy import policies
from backend.original_issues import original_issues
from scripts.build_observed_snapshot import SCENES

OUT = ROOT/'data/output'
ACTIONS = {'none': '통상 진행', 'cooling_break': '쿨링브레이크', 'shorten': '시간 단축', 'move': '시간 이동', 'postpone': '연기'}
TITLES = {'demo': '8월 10일: 재편성으로 전부 소화하는 날', 'extreme': '8월 8일: 재편성해도 연기가 생기는 날',
          'extreme-2day': '8월 8~9일: 같은 대회를 이틀 일정으로 다시 짠 경우'}
CONDITIONS = [('가', '구장 보정 +2.5℃, 범위 상단으로 판정 (이전 기준)', 2.5, True),
              ('나', '구장 보정 +2.5℃, 중앙 추정으로 판정 (지금 기준)', 2.5, False),
              ('다', '구장 보정 없음, 중앙 추정으로 판정', 0.0, False)]


def load(prefix):
    return json.loads((ROOT/f'frontend/src/demo/{prefix}.json').read_text(encoding='utf-8'))['approved']


def team(s, tid):
    return placeholder_name(tid) if tid.startswith('winner:') else next((t['name'] for t in s['teams'] if t['id'] == tid), tid)


def venue(s, vid):
    return next((v['name'] for v in s['venues'] if v['id'] == vid), vid).replace(' · 가상 예시', '')


def hm(t):
    return t[5:10].replace('-', '/') + ' ' + t[11:16]


def levels(xs):
    c = Counter(xs)
    return [c.get(i, 0) for i in range(5)]


def postpone_text(p, s, ids):
    """Same wording rules as frontend/src/Dashboard.jsx postponeReason."""
    if '선행 경기' in p['reason']:
        m = next(x for x in s['matches'] if x['id'] == p['match_id'])
        before = [match_name(d) for d in m['depends_on'] if d in ids]
        return f"앞선 경기{('(' + ', '.join(before) + ')') if before else ''}가 연기되어 함께 연기합니다."
    if p.get('coverage_proven') is False:
        return '제한 시간 안에 배정하지 못해 연기로 표시했습니다. 배정이 불가능하다는 증명은 아닙니다.'
    return '운동 중지 시간대를 피하면서 팀 휴식, 구장 정리, 일몰 전 종료 조건을 모두 지키는 시간이 없어 연기합니다.'


def match_length(m):
    return m['duration_min'] + (m['halves'] - 1) * m['half_break_min']


def window_risks(s, m):
    start = datetime.fromisoformat(m['scheduled_start']); end = start + timedelta(minutes=match_length(m))
    hours = {(start + timedelta(hours=i)).replace(minute=0) for i in range(0, 4)} | {start.replace(minute=0)}
    # Same window as backend/schedule/recommend.py and frontend/src/stage-window.js: hours from the kickoff hour up to and including the end.
    return [r for r in s['risks'] if r['venue_id'] == m['venue_id'] and datetime.fromisoformat(r['valid_time']) <= end
            and datetime.fromisoformat(r['valid_time']) in hours]


def decision_example(s):
    recs = {r['match_id']: r for r in s['recommendations']}
    m = min(s['matches'], key=lambda m: (-recs[m['id']]['level'], -(recs[m['id']]['wbgt_c'] or 0), m['scheduled_start']))
    r = max(window_risks(s, m), key=lambda r: (r['decision_wbgt_c'], r['valid_time']))
    b = breakdown(r)
    return {'match': match_name(m['id']), 'match_id': m['id'], 'kickoff': hm(m['scheduled_start']), 'venue': venue(s, m['venue_id']),
            'stage_hour': r['valid_time'], 'observed_estimate_c': b['model_c'], 'venue_offset_c': b['field_offset_c'],
            'central_c': r['wbgt_c'], 'decision_c': r['decision_wbgt_c'], 'level': r['level'],
            'range_c': [r['wbgt_low_c'], r['wbgt_high_c']],
            'if_upper_bound': {'decision_c': b['upper_decision_c'], 'level': b['upper_level']},
            'if_no_offset': {'decision_c': b['counterfactual_decision_c'], 'level': b['counterfactual_level']},
            'formula': f"관측 기반 추정 {b['model_c']:.3f} + 구장 보정 {b['field_offset_c']} = 중앙 추정 {r['wbgt_c']:.3f} → 판정값 {r['decision_wbgt_c']:.1f}℃ (단계 {r['level']})"}


def scene_numbers(key):
    prefix = SCENES[key][0]; s = load(prefix); p = s['proposal']
    stage = policies()[s['tournament']['policy_id']]['labels']
    open_h, close_h = s['schedule_settings']['open_hour'], s['schedule_settings']['close_hour']
    ops = [w for w in s['weather'] if open_h <= int(w['valid_time'][11:13]) < close_h]
    venue_a = s['venues'][0]['id']
    ids = {x['match_id'] for x in p['postponed']}
    assigned = {a['match_id']: a for a in p['assignments']}
    recs = {r['match_id']: r for r in s['recommendations']}
    rows = []
    for m in sorted(s['matches'], key=lambda m: (m['scheduled_start'], m['venue_id'])):
        a = assigned.get(m['id']); r = recs[m['id']]
        rows.append({'name': match_name(m['id']), 'id': m['id'], 'teams': f"{team(s, m['team_a'])} 대 {team(s, m['team_b'])}",
                     'original': {'kickoff': hm(m['scheduled_start']), 'venue': venue(s, m['venue_id']), 'level': r['level'], 'action': ACTIONS[r['action']]},
                     'proposed': ({'kickoff': hm(a['start']), 'venue': venue(s, a['venue_id']), 'level': a['level'], 'action': ACTIONS[a['action']],
                                   'duration_min': a['duration_min']} if a else None),
                     'postponed': m['id'] in ids, 'shortened': bool(a and a['duration_min'] < m['duration_min'])})
    issues = original_issues(s)
    return {
        'key': key, 'title': TITLES[key], 'snapshot_file': f'frontend/src/demo/{prefix}.json', 'hash': '#' + prefix.replace('observed-snapshot', 'snapshot-observed'),
        'date': s['tournament']['date_start'], 'date_end': s['tournament']['date_end'], 'tournament': s['tournament']['name'],
        'station': {'name': s['observation_summary']['station']['name'], 'id': s['observation_summary']['station']['id']},
        'teams': len(s['teams']), 'venues': len(s['venues']), 'matches': len(s['matches']),
        'operating_hours': f'{open_h:02d}:00~{close_h:02d}:00',
        'max_ta_c_24h': max(w['ta_c'] for w in s['weather']),
        'operating_weather': {'basis': f'{open_h:02d}:00~{close_h - 1:02d}:00 정시 관측', 'max_ta_c': max(w['ta_c'] for w in ops),
                              'rh_pct': [min(w['rh_pct'] for w in ops), max(w['rh_pct'] for w in ops)]},
        'hourly_venue_a': [{'time': r['valid_time'], 'decision_c': r['decision_wbgt_c'], 'central_c': r['wbgt_c'],
                            'low_c': r['wbgt_low_c'], 'high_c': r['wbgt_high_c'], 'level': r['level'], 'stage': stage[r['level']].replace('거의 안전', '통상 운영')}
                           for r in sorted(s['risks'], key=lambda r: r['valid_time']) if r['venue_id'] == venue_a],
        'original_levels': levels(r['level'] for r in s['recommendations']),
        'assigned': len(p['assignments']), 'postponed': p['postponed_count'],
        'postponed_matches': [{'name': match_name(x['match_id']), 'id': x['match_id'], 'reason': x['reason'],
                               'screen_text': postpone_text(x, s, ids)} for x in sorted(p['postponed'], key=lambda x: x['match_id'])],
        'proposed_levels': levels(a['level'] for a in p['assignments']),
        'original_stop_assigned': sum(recs[m]['level'] == 4 for m in assigned),
        'heat': {'common_matches': len(p['common_match_ids']), 'original': p['original_heat_score'], 'proposed': p['proposed_heat_score']},
        'solver': {'status': p['cp_sat_status'], 'label': p['solver'], 'method': p['selected_method'], 'coverage_optimal': p['coverage_optimal'],
                   'solver_wall_sec': round(p['solver_wall_sec'], 3), 'elapsed_sec': round(p['elapsed_sec'], 3),
                   'note': '사전 계산 당시 이 개발 PC의 시간이며 다른 PC에서는 달라질 수 있습니다.'},
        'notifications': len(s['notifications']),
        'decision_reason': s['decision']['reason'],
        'matches_table': rows,
        'original_issues': issues,
        'decision_example': decision_example(s),
    }


def day_conditions(day):
    """(가)(나)(다) for one day: re-solve with the sensitivity helper (analysis only, no setting change)."""
    from backend.repository import Repository
    from backend.service import Service
    from backend.schedule.optimizer import optimize
    from backend.schedule.recommend import recommend
    from scripts.wbgt_sanity import variant_context
    folder = OUT/'demo-numbers'; folder.mkdir(parents=True, exist_ok=True)
    svc = Service(Repository(folder/f'{uuid4().hex}.sqlite3'))
    s = svc.replay(date.fromisoformat(day), mode='observed'); rows = []
    for code, label, offset, upper in CONDITIONS:
        t, m, v, r, settings, engine = variant_context(s, offset, upper, {})
        res = optimize(m, t, v, r, settings, engine)
        peak = max(r, key=lambda x: (x.decision_wbgt_c, -x.valid_time.timestamp()))
        rows.append({'condition': code, 'label': label, 'current_rule': code == '나',
                     'original_levels': levels(recommend(x, r, engine).level for x in m),
                     'assigned': len(res.assignments), 'postponed': res.postponed_count,
                     'postponed_matches': [match_name(x['match_id']) for x in sorted(res.postponed, key=lambda x: x['match_id'])],
                     'proposed_levels': levels(a.level for a in res.assignments),
                     'heat': {'common_matches': len(res.common_match_ids), 'original': res.original_heat_score, 'proposed': res.proposed_heat_score},
                     'max_decision_c': peak.decision_wbgt_c, 'max_at': peak.valid_time.strftime('%H:%M') + ' ' + peak.venue_id[-1].upper(),
                     'status': res.cp_sat_status})
    return {'date': day, 'rows': rows}


def period():
    r = json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))
    days = r['days']
    return {'station': r['station'], 'days': len(days), 'matches_total': 15*len(days),
            'assigned_total': sum(d['assigned'] for d in days), 'postponed_total': sum(d['postponed'] for d in days),
            'complete_days': sum(d['postponed'] == 0 for d in days), 'partial_days': sum(0 < d['assigned'] < 15 for d in days),
            'zero_days': [d['date'] for d in days if d['assigned'] == 0],
            'solver_status': dict(Counter(d['solver'] for d in days)),
            'max_wbgt_c': max((d['max_wbgt_c'], d['date']) for d in days),
            'max_decision_c': max((d['max_decision_wbgt_c'], d['date']) for d in days),
            'hot_candidates': [{k: c[k] for k in ('date', 'assigned', 'postponed', 'max_ta_c', 'original_heat', 'proposed_heat')} for c in r['hot_candidates']],
            'note': '같은 가상 대회(12팀, 3구장, 15경기)를 2026-07-01~08-31 수원 관측 자료로 날마다 재현한 결과입니다.'}


def sensitivity():
    r = json.loads((ROOT/'docs/wbgt-sanity/sensitivity-results.json').read_text(encoding='utf-8'))
    return [{'name': x['name'], 'field_offset_c': x['field_offset_c'], 'decision_uses_upper': x['decision_uses_upper'],
             'site_shift_c': x['hypothetical_site_shift_c'], **x['summary']} for x in r['scenarios']]


def criteria():
    policy = policies()['general']
    venue_offsets = sorted({v['field_offset_c'] for v in load('observed-snapshot')['venues']})
    return {'policy': policy['name'], 'source': policy['source_ref'], 'boundaries_c': policy['boundaries'],
            'stage_labels_display': [l.replace('거의 안전', '통상 운영') for l in policy['labels']],
            'venue_offset_c': venue_offsets, 'decision_value': '중앙 추정(관측 기반 추정 + 구장 보정)',
            'upper_bound_groups': policies()['age']['upper_bound_groups'],
            'uncertainty_c': load('observed-snapshot')['engine_settings']['uncertainty_c'],
            'note': '2026-10-21 작성자 결정 (나). 단계 경계와 보정값은 바꾸지 않았고, 범위는 참고로만 표시합니다.'}


def markdown(d):
    L = ['# HeatTime 시연 수치', '', f"생성: `scripts/export_demo_numbers.py` ({d['generated_at']}). 값은 스냅샷과 분석 결과에서 자동으로 뽑았습니다.",
         '모든 WBGT는 관측 기상으로 계산한 추정값이며, 대회·팀·구장은 가상 예시입니다. 의사결정 보조용이며 현장 실측과 도입 실적은 없습니다.', '']
    c = d['criteria']
    L += ['## 기준', '', f"- 정책: {c['policy']} ({c['source']})", f"- 단계 경계: {', '.join(map(str, c['boundaries_c']))}℃",
          f"- 구장 보정: +{', '.join(map(str, c['venue_offset_c']))}℃", f"- 판정에 쓰는 값: {c['decision_value']}",
          f"- 추정 범위: 중앙 ±{c['uncertainty_c']}℃ (참고 표시, 판정에 쓰지 않음)", f"- {c['note']}", '']
    for s in d['scenes']:
        L += [f"## {s['title']}", '', f"- 스냅샷: `{s['snapshot_file']}` / 주소 `{s['hash']}`",
              f"- 날짜 {s['date']}{'~' + s['date_end'] if s['date_end'] != s['date'] else ''}, 관측소 {s['station']['name']} {s['station']['id']}, {s['teams']}팀 {s['venues']}구장 {s['matches']}경기",
              f"- 24시간 최고기온 {s['max_ta_c_24h']}℃, 운영시간({s['operating_weather']['basis']}) 최고기온 {s['operating_weather']['max_ta_c']}℃, 습도 {s['operating_weather']['rh_pct'][0]}~{s['operating_weather']['rh_pct'][1]}%",
              f"- 원래 일정 단계별 경기 수(0~4): {' · '.join(map(str, s['original_levels']))}",
              f"- 배정 {s['assigned']}경기, 연기 {s['postponed']}경기, 재편성 후 단계(0~4): {' · '.join(map(str, s['proposed_levels']))}",
              f"- 원래 운동 중지였다가 배정된 경기: {s['original_stop_assigned']}",
              f"- 열 노출 점수(공통 {s['heat']['common_matches']}경기): {s['heat']['original']:,} → {s['heat']['proposed']:,}",
              f"- 결과 표기: {s['solver']['status']} ({s['solver']['label']}), 솔버 {s['solver']['solver_wall_sec']}초, 전체 {s['solver']['elapsed_sec']}초 ({s['solver']['note']})",
              f"- 모의 알림 {s['notifications']}건, 승인 사유: {s['decision_reason']}", '']
        if s['postponed_matches']:
            L += ['| 연기 경기 | 화면 사유 |', '|---|---|'] + [f"| {p['name']} | {p['screen_text']} |" for p in s['postponed_matches']] + ['']
        e = s['decision_example']
        L += [f"판정 근거 예시: {e['match']} ({e['kickoff']} {e['venue']}), {e['stage_hour'][11:16]} 칸: {e['formula']}. 범위 {e['range_c'][0]}~{e['range_c'][1]}℃. "
              f"범위 상단으로 판정하면 {e['if_upper_bound']['decision_c']}℃ 단계 {e['if_upper_bound']['level']}, 구장 보정 없이 판정하면 {e['if_no_offset']['decision_c']}℃ 단계 {e['if_no_offset']['level']}.", '']
        L += ['| 시각(구장 A) | 판정값 | 중앙 추정 | 범위 | 단계 |', '|---|---:|---:|---|---|']
        L += [f"| {h['time'][5:16].replace('T', ' ')} | {h['decision_c']} | {h['central_c']} | {h['low_c']}~{h['high_c']} | {h['level']} {h['stage']} |" for h in s['hourly_venue_a']]
        L += ['', '| 경기 | 대진 | 원래 | 제안 | 단축 |', '|---|---|---|---|---|']
        for r in s['matches_table']:
            o = r['original']; p = r['proposed']
            L.append(f"| {r['name']} | {r['teams']} | {o['kickoff']} {o['venue']} 단계 {o['level']} | "
                     + (f"{p['kickoff']} {p['venue']} 단계 {p['level']} ({p['action']}, {p['duration_min']}분)" if p else '연기') + f" | {'예' if r['shortened'] else '아니오'} |")
        L += ['', '원래 일정이 어기는 제약:']
        for kind in ('singles', 'pairs'):
            for x in s['original_issues'].get(kind, []):
                L.append(f"- {', '.join(x['names'])}: {' / '.join(x['text'])}")
        L.append('')
    L += ['## 기준별 비교 (가)(나)(다)', '']
    for day in d['conditions']:
        L += [f"### {day['date']}", '', '| 조건 | 원래 단계(0~4) | 배정/연기 | 연기 경기 | 재편성 후 단계 | 열 노출 점수 | 최고 판정값 |', '|---|---|---|---|---|---|---|']
        for r in day['rows']:
            L.append(f"| ({r['condition']}) {r['label']} | {' · '.join(map(str, r['original_levels']))} | {r['assigned']}/{r['postponed']} | "
                     f"{', '.join(r['postponed_matches']) or '없음'} | {' · '.join(map(str, r['proposed_levels']))} | {r['heat']['original']:,} → {r['heat']['proposed']:,} ({r['heat']['common_matches']}경기) | {r['max_decision_c']}℃ ({r['max_at']}) |")
        L.append('')
    p = d['period']
    L += ['## 62일 분석', '', p['note'], '', f"- 배정 {p['assigned_total']} / 연기 {p['postponed_total']} (전체 {p['matches_total']}경기)",
          f"- 전부 배정 {p['complete_days']}일, 일부 배정 {p['partial_days']}일, 0경기 배정 {len(p['zero_days'])}일 ({', '.join(x[5:] for x in p['zero_days']) or '없음'})",
          f"- 솔버 결과: {', '.join(f'{k} {v}' for k, v in p['solver_status'].items())}",
          f"- 최고 WBGT 중앙 추정 {p['max_wbgt_c'][0]}℃ ({p['max_wbgt_c'][1]}), 최고 판정값 {p['max_decision_c'][0]}℃ ({p['max_decision_c'][1]})", '']
    L += ['## 62일 민감도 (가정별 전부 배정 / 일부 / 0배정 / 배정 합계)', '', '| 가정 | 구장 보정 | 판정 값 | 전부 | 일부 | 0배정 | 배정 합계 |', '|---|---:|---|---:|---:|---:|---:|']
    for x in d['sensitivity']:
        L.append(f"| {x['name']}{' (지금 기준, 나)' if x['name'] == 'baseline' else ' (가)' if x['name'] == 'upper_bound' else ' (다)' if x['name'] == 'offset_0' else ''} | {x['field_offset_c']} | {'범위 상단' if x['decision_uses_upper'] else '중앙'}{' / 구장별 ' + json.dumps(x['site_shift_c'], ensure_ascii=False) if x['site_shift_c'] else ''} | {x['complete_days']} | {x['incomplete_days'] - x['zero_assignment_days']} | {x['zero_assignment_days']} | {x['assigned_total']} |")
    return '\n'.join(L) + '\n'


def build():
    data = {'generated_at': datetime.now().astimezone().isoformat(timespec='seconds'), 'criteria': criteria(),
            'scenes': [scene_numbers(k) for k in SCENES], 'conditions': [day_conditions(x) for x in ('2026-08-10', '2026-08-08')],
            'period': period(), 'sensitivity': sensitivity()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'demo-numbers.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (OUT/'demo-numbers.md').write_text(markdown(data), encoding='utf-8')
    print(json.dumps({s['key']: [s['assigned'], s['postponed'], s['heat']['original'], s['heat']['proposed']] for s in data['scenes']}))
    return data


if __name__ == '__main__':
    build()
