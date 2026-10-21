"""Hard-constraint issues of the author's original (virtual) schedule, found with the existing validate()."""
from datetime import datetime, timedelta
from itertools import combinations
from backend.display_names import match_name
from backend.schedule.optimizer import Candidate, validate

ERROR_TEXT = {
    'prohibited heat slot': '운동 중지 단계 시간대에 배정됨',
    'venue overlap/cleanup': '같은 구장에서 앞 경기 종료 후 구장 정리 시간이 확보되지 않음',
    'team rest': '같은 팀의 경기 사이 휴식 시간이 부족함',
    'dependency': '선행 경기가 끝나기 전에 시작함',
    'operating window/sunset': '운영 시간 또는 일몰 전 종료 조건을 벗어남',
    'slot alignment': '배정 단위(분)에 맞지 않는 킥오프',
    'missing risk': '기상 자료가 빠진 시간대에 배정됨',
    'date range': '대회 기간을 벗어남',
}


def original_candidates(session):
    from backend.service import Service
    t, matches, venues, risks, settings, engine = Service.context(session)
    rows = []
    for m in matches:
        length = m.duration_min + (m.halves - 1) * m.half_break_min
        rows.append(Candidate(m.id, m.venue_id, m.scheduled_start, m.scheduled_start + timedelta(minutes=length),
                              0, 0, length, [], 'original'))
    return rows, matches, t, venues, risks, settings


def original_issues(session):
    rows, matches, t, venues, risks, settings = original_candidates(session)
    by_match = {m.id: m for m in matches}
    singles, pairs = [], []
    single_errors = {}
    for r in rows:
        errors = [e for e in validate([r], matches, t, venues, risks, settings) if e != 'dependency']
        single_errors[r.match_id] = set(errors)
        if errors:
            singles.append({'match_ids': [r.match_id], 'names': [match_name(r.match_id)], 'errors': sorted(errors),
                            'text': [ERROR_TEXT.get(e, e) for e in sorted(errors)]})
    for a, b in combinations(rows, 2):
        errors = set(validate([a, b], matches, t, venues, risks, settings)) - single_errors[a.match_id] - single_errors[b.match_id]
        errors.discard('dependency')  # a pair alone lacks other predecessors; checked on the full schedule below
        if errors:
            early, late = sorted([a, b], key=lambda r: r.start)
            placeholder = any(by_match[x].depends_on for x in (a.match_id, b.match_id))
            text = []
            for e in sorted(errors):
                if e == 'team rest' and placeholder:
                    text.append(f"진출할 수 있는 팀 기준으로 경기 사이 휴식 {settings.rest_by_age[t.age_group]}분이 확보되지 않음")
                elif e == 'team rest':
                    text.append(f"같은 팀의 경기 사이 휴식 {settings.rest_by_age[t.age_group]}분이 확보되지 않음")
                elif e == 'venue overlap/cleanup':
                    text.append(f"같은 구장에서 앞 경기가 {early.end:%H:%M}에 끝나고 다음 경기가 {late.start:%H:%M}에 시작해 구장 정리 {settings.cleanup_min}분이 확보되지 않음")
                else:
                    text.append(ERROR_TEXT.get(e, e))
            pairs.append({'match_ids': [early.match_id, late.match_id], 'names': [match_name(early.match_id), match_name(late.match_id)],
                          'times': [f"{early.start:%H:%M}~{early.end:%H:%M}", f"{late.start:%H:%M}~{late.end:%H:%M}"],
                          'errors': sorted(errors), 'text': text})
    full = sorted(validate(rows, matches, t, venues, risks, settings))
    return {'note': '원래 일정은 작성자가 정한 가상 기준이며 다음 제약을 충족하지 않습니다.', 'full_errors': full,
            'full_text': [ERROR_TEXT.get(e, e) for e in full], 'singles': singles, 'pairs': pairs}
