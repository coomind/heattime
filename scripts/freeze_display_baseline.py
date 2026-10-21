"""Freeze the values the dashboard shows for each observed demo scene, taken from execution.

Writes tests/fixtures/display-baseline-<scene file>.json from (1) the committed observed snapshot
and (2) a fresh observed replay + optimize of the same scene. Both must agree before writing.
Run only when the user approves a judgment-rule change; redesigns must keep the files unchanged.
"""
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.repository import Repository
from backend.service import Service


def summarize(session):
    proposal = session['proposal']
    peak = max(session['risks'], key=lambda r: r['decision_wbgt_c'])
    return {
        'date': session['tournament']['date_start'], 'date_end': session['tournament']['date_end'],
        'teams': len(session['teams']), 'venues': len(session['venues']), 'matches': len(session['matches']),
        'assigned': len(proposal['assignments']), 'postponed': proposal['postponed_count'],
        'postponed_ids': sorted(p['match_id'] for p in proposal['postponed']),
        'original_levels': [Counter(r['level'] for r in session['recommendations']).get(i, 0) for i in range(5)],
        'proposed_levels': [Counter(a['level'] for a in proposal['assignments']).get(i, 0) for i in range(5)],
        'heat': [proposal['original_heat_score'], proposal['proposed_heat_score']],
        'common': len(proposal['common_match_ids']),
        'max_decision': {'value': peak['decision_wbgt_c'], 'time': peak['valid_time'], 'venue': peak['venue_id']},
        'cells': sorted([r['venue_id'], r['valid_time'], r['level'], r['wbgt_c'], r['wbgt_low_c'], r['wbgt_high_c'],
                         r['decision_wbgt_c']] for r in session['risks']),
        'recommendations': sorted([r['match_id'], r['level'], r['action'], r['duration_min']] for r in session['recommendations']),
        'proposal': sorted([a['match_id'], a['venue_id'], a['start'], a['end'], a['level'], a['action']] for a in proposal['assignments']),
    }


# scene key -> (snapshot file prefix, fixture name)
FIXTURES = {'demo': ('observed-snapshot', '2026-08-10'), 'extreme': ('observed-snapshot-0808', '2026-08-08'),
            'extreme-2day': ('observed-snapshot-0808-2day', '2026-08-08-2day')}


def fresh_summary(scene, frozen):
    from scripts.build_observed_snapshot import SCENES, two_day_service
    if SCENES[scene][2]:
        service = two_day_service(frozen['date'])
    else:
        folder = ROOT/'data/output/display-baseline'; folder.mkdir(parents=True, exist_ok=True)
        service = Service(Repository(folder/f'{uuid4().hex}.sqlite3'))
    session = service.replay(date.fromisoformat(frozen['date']), mode='observed')
    service.optimize(session['id'])
    return summarize(service.repo.get('sessions', session['id']))


def build():
    for scene, (prefix, name) in FIXTURES.items():
        snapshot = json.loads((ROOT/f'frontend/src/demo/{prefix}.json').read_text(encoding='utf-8'))['approved']
        frozen = summarize(snapshot)
        if fresh_summary(scene, frozen) != frozen:
            raise SystemExit(f'{scene}: snapshot and fresh replay disagree; not freezing.')
        path = ROOT/f"tests/fixtures/display-baseline-{name}.json"
        path.write_text(json.dumps(frozen, ensure_ascii=False, indent=1) + chr(10), encoding='utf-8')
        print(json.dumps({'scene': scene} | {k: frozen[k] for k in ('date', 'date_end', 'assigned', 'postponed', 'postponed_ids',
              'original_levels', 'proposed_levels', 'heat', 'max_decision')}, ensure_ascii=False))


if __name__ == '__main__':
    build()
