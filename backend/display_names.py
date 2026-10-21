"""Names people read, for internal match ids and winner placeholders (mirrors frontend/src/labels.js)."""
import re


def match_name(match_id):
    m = re.fullmatch(r'g(\d+)-(\d+)', match_id)
    if m:
        return f'{m[1]}조 {m[2]}경기'
    m = re.fullmatch(r'semi(\d+)', match_id)
    if m:
        return f'준결승 {m[1]}'
    return '결승' if match_id == 'final' else match_id


def placeholder_name(team_id):
    ref = team_id.split(':', 1)[1]
    g = re.fullmatch(r'group(\d+)', ref)
    return f'{g[1]}조 1위' if g else f'{match_name(ref)} 승자'
