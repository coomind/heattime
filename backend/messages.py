"""Korean user-facing text for errors raised with internal (English) messages.

Internal exceptions keep their original text for logs/tests; only HTTP responses and
CSV preview rows shown to operators are translated here.
"""
from pydantic import ValidationError

EXACT = {
    'Unknown resource kind': '알 수 없는 자료 종류입니다.',
    'Invalid resource fields': '입력 항목이 올바르지 않습니다.',
    'Match date outside tournament': '경기 날짜가 대회 기간 밖입니다.',
    'Team belongs to different tournament': '선택한 팀이 다른 대회에 속해 있습니다. 같은 대회의 팀 ID를 입력하세요.',
    'Winner placeholder needs predecessors': '승자 자리(winner:)를 쓰려면 선행 경기 ID를 입력하세요.',
    'Unknown replay mode': '알 수 없는 재현 방식입니다.',
    'Tournament has no matches': '이 대회에는 등록된 경기가 없습니다. 대진을 먼저 입력하세요.',
    'Session decision already recorded; create a new replay to reconsider': '이미 운영 판단이 기록되었습니다. 다시 검토하려면 새 재현을 실행하세요.',
    'Decision already recorded': '이미 운영 판단이 기록되었습니다.',
    'Optimize before deciding': '재편성을 먼저 실행하세요.',
    'Modified assignments required': '수정안에 경기 배정이 없습니다.',
    'Unknown match': '알 수 없는 경기입니다.',
    'Requested modified slot violates risk or operating constraints': '수정한 시간·구장이 위험 단계 또는 운영 제약(운영시간·휴식·구장 정리·일몰)을 어깁니다.',
    'Modification must preserve proposed match coverage': '수정안은 제안과 같은 경기 집합을 유지해야 합니다.',
    'Id cannot change': 'ID는 바꿀 수 없습니다.',
    'Existing match outside updated dates': '이미 등록된 경기가 바뀐 대회 기간 밖에 있습니다.',
    'Duplicate id': '같은 ID가 이미 있습니다.',
    'Referenced resource cannot be deleted': '다른 자료(경기·팀 등)가 참조하고 있어 삭제할 수 없습니다.',
    'Unknown export format': '지원하지 않는 내보내기 형식입니다.',
    'Resource not found': '요청한 자료를 찾을 수 없습니다.',
    'Invalid dates': '종료일이 시작일보다 빠릅니다.',
    'Invalid participants/dependency': '두 팀이 같거나 경기가 자기 자신을 선행 경기로 지정했습니다.',
    'Invalid hours/rest': '운영 시작·종료 시각 또는 휴식 시간이 올바르지 않습니다.',
    'Timezone-aware datetime required': '시각에 시간대(+09:00)를 포함하세요.',
    'Venue id/name required': '구장 ID와 이름을 입력하세요.',
    'Invalid surface': '구장 표면 값이 올바르지 않습니다.',
    'Invalid shade': '그늘 값이 올바르지 않습니다.',
    'Invalid latitude/longitude': '위도·경도가 올바르지 않습니다.',
    'Invalid latitude': '위도가 올바르지 않습니다.',
    'Invalid longitude': '경도가 올바르지 않습니다.',
    'Invalid field offset': '보정값은 -20~20℃ 범위여야 합니다.',
    'Outside KMA forecast grid: nx 1..149, ny 1..253': '좌표가 기상청 격자 범위 밖입니다.',
    'Cyclic dependencies': '선행 경기 관계가 순환합니다.',
    'Unknown predecessor': '선행 경기 ID를 찾지 못했습니다.',
    'Empty CSV or duplicate ids': 'CSV가 비어 있거나 경기 ID가 중복됩니다.',
    'CSV match outside dates': '경기 날짜가 대회 기간 밖입니다.',
    'Invalid CSV team': '참가팀이 다른 대회에 속해 있습니다.',
}
PREFIX = {
    'Invalid proposal: ': '제안이 하드 제약을 어깁니다: ',
    'Invalid ': '값이 올바르지 않습니다: ',
}
FIELDS = {'id': 'ID', 'tournament_id': '대회 ID', 'round': '라운드', 'team_a': '팀 A', 'team_b': '팀 B',
          'venue_id': '구장 ID', 'scheduled_start': '킥오프', 'duration_min': '경기시간(분)',
          'depends_on': '선행 경기', 'halves': '하프 수', 'half_break_min': '하프 휴식(분)', 'name': '이름',
          'lat': '위도', 'lon': '경도', 'date_start': '시작일', 'date_end': '종료일', 'age_group': '연령',
          'policy_id': '정책', 'field_offset_c': '보정값', 'surface': '표면', 'shade': '그늘',
          'contact': '연락처', 'valid_time': '시각', 'wbgt_c': 'WBGT', 'is_mock': '가상 예시 여부'}
TYPES = (('missing', '값이 필요합니다'), ('datetime', '날짜·시각 형식이 올바르지 않습니다(예: 2026-08-10T09:00:00+09:00)'),
         ('date', '날짜 형식이 올바르지 않습니다(예: 2026-08-10)'), ('int', '정수를 입력하세요'),
         ('float', '숫자를 입력하세요'), ('bool', '참/거짓 값이 필요합니다'), ('greater_than', '허용 범위보다 작습니다'),
         ('less_than', '허용 범위보다 큽니다'), ('literal', '허용된 값이 아닙니다'), ('enum', '허용된 값이 아닙니다'),
         ('string_too_short', '비어 있습니다'), ('string', '문자열이 필요합니다'), ('list', '목록이 필요합니다'),
         ('extra_forbidden', '허용되지 않는 항목입니다'))


def korean(message):
    text = str(message)
    if text in EXACT:
        return EXACT[text]
    for prefix, ko in PREFIX.items():
        if text.startswith(prefix):
            return ko + text[len(prefix):]
    return text


def validation_text(exc: ValidationError):
    parts = []
    for error in exc.errors():
        field = '·'.join(FIELDS.get(str(x), str(x)) for x in error.get('loc', ()) if not isinstance(x, int)) or '입력'
        kind = error.get('type', '')
        if kind == 'value_error':
            reason = korean(str(error.get('ctx', {}).get('error', error.get('msg', ''))))
        else:
            reason = next((ko for key, ko in TYPES if key in kind), '값이 올바르지 않습니다')
        parts.append(f'{field}: {reason}')
    return '입력값을 확인하세요. ' + ' / '.join(parts)


def user_message(exc):
    return validation_text(exc) if isinstance(exc, ValidationError) else korean(exc)
