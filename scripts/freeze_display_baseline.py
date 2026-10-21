"""Freeze the values the dashboard shows for the demo snapshot, taken from execution.

Writes tests/fixtures/display-baseline-<date>.json from (1) the committed observed snapshot
and (2) a fresh observed replay + optimize of the same date. Both must agree before writing.
Run only when the user approves a judgment-rule change; redesigns must keep the file unchanged.
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
        'date': session['tournament']['date_start'],
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


def build():
    snapshot = json.loads((ROOT/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))['approved']
    frozen = summarize(snapshot)
    folder = ROOT/'data/output/display-baseline'; folder.mkdir(parents=True, exist_ok=True)
    service = Service(Repository(folder/f'{uuid4().hex}.sqlite3'))
    session = service.replay(date.fromisoformat(frozen['date']), mode='observed')
    service.optimize(session['id'])
    fresh = summarize(service.repo.get('sessions', session['id']))
    if fresh != frozen:
        raise SystemExit('Snapshot and fresh replay disagree; not freezing.')
    path = ROOT/f"tests/fixtures/display-baseline-{frozen['date']}.json"
    path.write_text(json.dumps(frozen, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: frozen[k] for k in ('date', 'assigned', 'postponed', 'postponed_ids', 'original_levels', 'proposed_levels', 'heat', 'max_decision')}, ensure_ascii=False))


if __name__ == '__main__':
    build()
