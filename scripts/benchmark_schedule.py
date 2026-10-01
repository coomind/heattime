"""16-team, two-day synthetic tournament; defaults and constraints unchanged."""
import argparse
from dataclasses import replace
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.weather.cli import demo_venues
from backend.weather.models import KST
from backend.weather.adapters import MockAsosAdapter
from backend.engine.wbgt import estimate_series
from backend.engine.settings import EngineSettings
from backend.schedule.models import Tournament, Team, Match, ScheduleSettings
from backend.schedule.optimizer import optimize, validate


def tournament_16():
    day = date(2026, 8, 1); second = day + timedelta(days=1)
    tournament = Tournament(id='benchmark16', name='16팀 2일 성능검증 · 가상 예시', date_start=day, date_end=second)
    teams = [Team(id=f'b{i+1}', tournament_id=tournament.id, name=f'벤치마크 팀{i+1} · 가상 예시') for i in range(16)]
    venues = demo_venues(); matches = []
    pairs = [(0,1),(2,3),(0,2),(1,3),(0,3),(1,2)]
    for group in range(4):
        for index, (a,b) in enumerate(pairs):
            matches.append(Match(id=f'b-g{group+1}-{index+1}', tournament_id=tournament.id,
                round=f'조별 {group+1}조', team_a=teams[group*4+a].id, team_b=teams[group*4+b].id,
                venue_id=venues[group%3].id,
                scheduled_start=datetime.combine(day, datetime.min.time(), KST)+timedelta(hours=8,minutes=index*90+group*15)))
    for i in range(2):
        dependencies=[m.id for m in matches if m.round in {f'조별 {i*2+1}조',f'조별 {i*2+2}조'}]
        matches.append(Match(id=f'b-semi{i+1}', tournament_id=tournament.id, round='준결승',
            team_a=f'winner:group{i*2+1}', team_b=f'winner:group{i*2+2}', venue_id=venues[i].id,
            scheduled_start=datetime.combine(second,datetime.min.time(),KST)+timedelta(hours=10),depends_on=dependencies))
    matches.append(Match(id='b-final',tournament_id=tournament.id,round='결승',team_a='winner:b-semi1',team_b='winner:b-semi2',
        venue_id=venues[0].id,scheduled_start=datetime.combine(second,datetime.min.time(),KST)+timedelta(hours=14),
        depends_on=['b-semi1','b-semi2']))
    return tournament, teams, matches, venues


def run(repeats=3, forced_greedy=False):
    tournament, teams, matches, venues = tournament_16()
    settings = ScheduleSettings(); engine = EngineSettings(); results = []
    for scenario in ['default_mock_hot','controlled_mild_mock']:
        started=perf_counter();risks=[]
        for venue in venues:
            points=[]
            for offset in range(2):
                day=tournament.date_start+timedelta(days=offset)
                rows=MockAsosAdapter().fetch(venue,venue.asos_station_id,day)
                # Benchmark weather fixture only. No production defaults or policies change.
                if scenario=='controlled_mild_mock':
                    rows=[replace(p,ta_c=22,rh_pct=45,ws_ms=3) for p in rows]
                points+=rows
            risks+=estimate_series(venue,points,tournament.age_group,tournament.policy_id,engine)
        engine_elapsed=perf_counter()-started
        for iteration in range(repeats):
            result=optimize(matches,tournament,venues,risks,settings,engine,force_greedy=forced_greedy)
            errors=validate(result.assignments,matches,tournament,venues,risks,settings)
            if errors:raise RuntimeError('Benchmark constraints failed')
            record={'scenario':scenario,'run':iteration+1,'teams':len(teams),'days':2,'matches':len(matches),
                'solver':result.solver,'coverage_optimal':result.coverage_optimal,'assigned':len(result.assignments),
                'postponed':result.postponed_count,'constraints_ok':not errors,
                'elapsed_sec':round(result.elapsed_sec,4),'preparation_sec':round(result.preparation_sec,4),
                'solver_wall_sec':round(result.solver_wall_sec,4),'engine_sec':round(engine_elapsed,4),
                'original_common_heat':result.original_heat_score,'proposed_common_heat':result.proposed_heat_score,
                'maximum_wbgt_c':max(r.wbgt_c for r in risks)}
            results.append(record);print(json.dumps(record),flush=True)
    summary=[]
    for scenario in {r['scenario'] for r in results}:
        rows=[r for r in results if r['scenario']==scenario]
        summary.append({'scenario':scenario,'median_elapsed_sec':round(statistics.median(r['elapsed_sec'] for r in rows),4),
                        'max_elapsed_sec':max(r['elapsed_sec'] for r in rows),
                        'statuses':sorted({r['solver'] for r in rows})})
    return {'label':'SYNTHETIC BENCHMARK - NOT REAL OBSERVATIONS','forced_greedy':forced_greedy,'engine_settings':engine.model_dump(),
            'schedule_settings':settings.model_dump(),'results':results,'summary':summary}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--force-fallback',action='store_true');args=parser.parse_args()
    result=run(repeats=1 if args.force_fallback else 3,forced_greedy=args.force_fallback)
    output=ROOT/('docs/overnight/b4-fallback-metrics.json' if args.force_fallback else 'docs/overnight/b4-metrics.json')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
