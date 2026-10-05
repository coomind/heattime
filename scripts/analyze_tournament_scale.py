"""All 31 non-overlapping observed two-day windows, unchanged 16-team fixture.

Offline analysis only. No credentials, collection, application settings or snapshot edits.
Run each new solver case once and publish every result, including worse outcomes.
"""
from datetime import date,timedelta
from pathlib import Path
from statistics import median
from time import perf_counter
from uuid import uuid4
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.repository import Repository
from backend.service import Service
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from backend.schedule.optimizer import optimize,candidates_for
from backend.weather.asos_samples import load_dataset
from scripts.benchmark_schedule import tournament_16
from scripts.analyze_without_field import METHODS,greedy_variant,describe
from scripts.compare_schedule_methods import input_digest,verify_assignments,json_row

START=date(2026,7,1)
WINDOWS=tuple(START+timedelta(days=i) for i in range(0,62,2))
NAMES=('existing_heat_first',*METHODS)

def make_service(path):
    service=Service(Repository(path));t,teams,matches,venues=tournament_16()
    for kind,items in [('tournaments',[t]),('teams',teams),('matches',matches),('venues',venues)]:
        for item in items:service.repo.put(kind,item.id,item)
    return service

def summary(rows):
    cp_heat=sum(r['comparison']['engine_common_heat'] for r in rows)
    baseline_heat=sum(r['comparison']['baseline_common_heat'] for r in rows)
    return {'cases':len(rows),'matches_per_case':27,
            'engine_assigned':sum(r['engine']['assigned'] for r in rows),
            'baseline_assigned':sum(r['baselines'][r['selected_baseline']]['assigned'] for r in rows),
            'engine_complete_cases':sum(r['engine']['postponed']==0 for r in rows),
            'baseline_complete_cases':sum(r['baselines'][r['selected_baseline']]['postponed']==0 for r in rows),
            'engine_more_cases':sum(r['comparison']['assignment_gain']>0 for r in rows),
            'equal_cases':sum(r['comparison']['assignment_gain']==0 for r in rows),
            'engine_fewer_cases':sum(r['comparison']['assignment_gain']<0 for r in rows),
            'engine_common_heat':cp_heat,'baseline_common_heat':baseline_heat,
            'common_heat_reduction_pct':round((baseline_heat-cp_heat)/baseline_heat*100,4) if baseline_heat else None,
            'no_common_cases':sum(not r['comparison']['common_match_ids'] for r in rows),
            'statuses':{name:sum(r['solver']==name for r in rows) for name in sorted({r['solver'] for r in rows})},
            'median_optimize_sec':round(median(r['optimize_elapsed_sec'] for r in rows),4),
            'max_optimize_sec':max(r['optimize_elapsed_sec'] for r in rows)}

def analyze():
    dataset=load_dataset()
    if dataset.dates!=[START+timedelta(days=i) for i in range(62)]:raise ValueError('Expected complete July/August source dates')
    folder=ROOT/'data/output/scale';folder.mkdir(parents=True,exist_ok=True)
    service=make_service(folder/(uuid4().hex+'.sqlite3'));rows=[];started=perf_counter()
    for day in WINDOWS:
        replay_start=perf_counter();s=service.replay(day,tournament_id='benchmark16',mode='observed')
        replay_sec=perf_counter()-replay_start;t,m,v,r,settings,engine=Service.context(s)
        if settings!=ScheduleSettings() or engine!=EngineSettings():raise ValueError('Default settings changed')
        result=optimize(m,t,v,r,settings,engine)
        selected=verify_assignments([json_row(a) for a in result.assignments],s)
        options={match.id:candidates_for(match,t,v,r,settings,engine) for match in m}
        existing=optimize(m,t,v,r,settings,engine,force_greedy=True)
        baselines={'existing_heat_first':describe(verify_assignments([json_row(a) for a in existing.assignments],s),m,settings)}
        for method in METHODS:
            chosen=greedy_variant(m,t,v,r,settings,engine,method,options)
            verify_assignments([json_row(a) for a in chosen],s)
            baselines[method]=describe(chosen,m,settings)
        best=min(baselines,key=lambda n:(-baselines[n]['assigned'],baselines[n]['secondary_cost'],n))
        common={a.match_id for a in selected}&{a['match_id'] for a in baselines[best]['assignments']}
        record={'start':day.isoformat(),'end':t.date_end.isoformat(),'teams':len(s['teams']),
                'input_sha256':input_digest(s),'source_label':s['label'],'solver':result.solver,
                'coverage_optimal':result.coverage_optimal,'replay_elapsed_sec':round(replay_sec,4),
                'optimize_elapsed_sec':round(result.elapsed_sec,4),'preparation_sec':round(result.preparation_sec,4),
                'solver_wall_sec':round(result.solver_wall_sec,4),'engine':describe(selected,m,settings),
                'postponed':result.postponed,'baselines':baselines,'selected_baseline':best,
                'comparison':{'common_match_ids':sorted(common),'assignment_gain':len(selected)-baselines[best]['assigned'],
                              'engine_common_heat':sum(a.heat_score for a in selected if a.match_id in common),
                              'baseline_common_heat':sum(a['heat_score'] for a in baselines[best]['assignments'] if a['match_id'] in common)}}
        rows.append(record)
        print(json.dumps({k:record[k] for k in ('start','end','solver','optimize_elapsed_sec','comparison')},ensure_ascii=True),flush=True)
    packet={'version':1,'scope':'Existing virtual 16-team/27-match/2-day fixture; same Suwon observed source and defaults.',
            'selection':'Every non-overlapping two-day window from July 1 to August 31, fixed before solving. One engine run per case; no favourable rerun selection.',
            'limitation':'31 conditions of one second virtual bracket, not representative tournaments, measured WBGT, human/competitor performance, or winning odds.',
            'original_sample_sha256':dataset.original_sha256,'engine_settings':engine.model_dump(),'schedule_settings':settings.model_dump(),
            'elapsed_sec':round(perf_counter()-started,3),'summary':summary(rows),'cases':rows}
    (ROOT/'docs/competition-evidence/tournament-scale-analysis.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(packet['summary'],ensure_ascii=True),flush=True)
    return packet

if __name__=='__main__':analyze()
