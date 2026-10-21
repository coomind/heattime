"""Only mock delivery is implemented; real gateways require verified provider specs."""
from datetime import datetime
from typing import Protocol
from uuid import uuid4
from backend.weather.models import KST
from backend.schedule.models import Match
from backend.schedule.optimizer import participants
from backend.display_names import match_name


class NotificationSender(Protocol):
    def send(self, team: dict, match_id: str, message: str) -> dict: ...


class MockSender:
    def send(self, team, match_id, message):
        # Contact strings are metadata only. No network calls or real delivery.
        return {'id': uuid4().hex, 'team_id': team['id'], 'team_name': team['name'],
                'recipient': '가상 예시 · 모의 수신함', 'match_id': match_id,
                'sent_at': datetime.now(KST).isoformat(), 'channel': 'mock',
                'label': '가상 예시 · 모의 발송', 'message': message}


class RealSender:
    def send(self, team, match_id, message):
        # TODO: user-selected SMS/Kakao provider's verified endpoint/schema/consent flow.
        raise NotImplementedError('실제 발송은 연결되지 않았습니다')


def build_notifications(session, sender=None):
    sender = sender or MockSender()
    decision = session['decision']
    if not decision or decision['operator_action'] == 'rejected':
        return []
    matches = [Match(**m) for m in session['matches']]
    possible = participants(matches)
    teams = {t['id']: t for t in session['teams']}
    venues = {v['id']: v['name'] for v in session['venues']}
    assignments = {a['match_id']: a for a in decision['assignments']}
    postponed = {p['match_id']: p for p in decision['postponed']}
    logs = []
    for match in matches:
        if match.id in assignments:
            a = assignments[match.id]
            cooling = ', '.join(a['cooling_times']) or '계획 없음'
            message = (f"가상 예시 · {match_name(match.id)} 변경 일정: 킥오프 {a['start']}, "
                       f"종료 {a['end']}, 구장 {venues[a['venue_id']]} / "
                       f"쿨링브레이크 시각 {cooling} / 수분 보충 안내: 개인 물을 준비하고 "
                       '운영자 안내에 따라 휴식·수분 보충. 최종 운영 판단은 주최자.')
        elif match.id in postponed:
            message = (f"가상 예시 · {match_name(match.id)} 연기 / 사유: {postponed[match.id]['reason']} / "
                       '새 일정 및 쿨링브레이크 시각 미정. 수분 보충 안내: 개인 물을 준비하고 '
                       '운영자 후속 안내를 확인하세요.')
        else:
            continue
        # Knockout winners are unknown: label every potential recipient explicitly.
        for team_id in sorted(possible[match.id]):
            if team_id in teams:
                suffix = ' / 진출 가능 팀 대상 모의 안내 · 결과 확정 후 재확인' if match.depends_on else ''
                logs.append(sender.send(teams[team_id], match.id, message + suffix))
    return logs
