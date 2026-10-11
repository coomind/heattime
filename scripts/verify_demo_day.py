"""Repeat the observed replay + rescheduling for a demo date; no network or .env.

Pass criterion (author decision 2026-10-11): every run proves CP-SAT OPTIMAL within
half of the solver time limit and all runs give the identical schedule.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.repository import Repository
from backend.service import Service

OUTPUT = ROOT/'docs/real-data/demo-day-check.json'


def schedule_key(proposal):
    rows = sorted((a['match_id'], a['venue_id'], a['start'], a['end'], a['action']) for a in proposal['assignments'])
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def check(day, runs=5, role='main'):
    folder = ROOT/'data/output/demo-day-check'; folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(runs):
        service = Service(Repository(folder/f'{uuid4().hex}.sqlite3'))
        session = service.replay(date.fromisoformat(day), mode='observed')
        proposal = service.optimize(session['id'])
        limit = session['schedule_settings']['time_limit_sec']
        rows.append({'run': index+1, 'cp_sat_status': proposal['cp_sat_status'], 'selected_method': proposal['selected_method'],
                     'solver_wall_sec': round(proposal['solver_wall_sec'], 3), 'elapsed_sec': round(proposal['elapsed_sec'], 3),
                     'assigned': len(proposal['assignments']), 'postponed': proposal['postponed_count'],
                     'original_heat': proposal['original_heat_score'], 'proposed_heat': proposal['proposed_heat_score'],
                     'schedule_sha256': schedule_key(proposal)})
        print(json.dumps(rows[-1]), flush=True)
    levels = {str(level): sum(r['level'] == level for r in session['recommendations']) for level in range(5)}
    passed = (all(r['cp_sat_status'] == 'OPTIMAL' and r['solver_wall_sec'] <= limit/2 for r in rows)
              and len({r['schedule_sha256'] for r in rows}) == 1)
    weather = session['weather']
    return {'date': day, 'role': role, 'runs': rows, 'passed': passed, 'time_limit_sec': limit,
            'criterion': 'every run CP-SAT OPTIMAL with solver wall time <= half the limit, identical schedules',
            'max_ta_c': max(w['ta_c'] for w in weather), 'original_levels': levels,
            'max_solver_wall_sec': max(r['solver_wall_sec'] for r in rows),
            'environment_note': 'Wall times are from this machine; other CPUs or loads can change OPTIMAL/FEASIBLE.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', action='append', required=True, help='YYYY-MM-DD[:role]; repeatable')
    parser.add_argument('--runs', type=int, default=5)
    args = parser.parse_args()
    existing = json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else {'checks': []}
    for item in args.date:
        day, _, role = item.partition(':')
        result = check(day, args.runs, role or 'main')
        existing['checks'] = [c for c in existing['checks'] if c['date'] != day] + [result]
        print(json.dumps({'date': day, 'passed': result['passed'], 'max_solver_wall_sec': result['max_solver_wall_sec']}), flush=True)
    OUTPUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
