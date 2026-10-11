"""Re-solve every predeclared 31 larger / 62 original case once to check reproducibility."""
from datetime import date
from pathlib import Path
from uuid import uuid4
from collections import Counter
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.repository import Repository
from backend.service import Service
from backend.schedule.optimizer import optimize,candidates_for
from scripts.analyze_tournament_scale import make_service,WINDOWS
from scripts.analyze_without_field import METHODS,greedy_variant,describe
from scripts.compare_schedule_methods import input_digest,json_row,verify_assignments


def run():
    folder=ROOT/'data/output/review-fix';folder.mkdir(parents=True,exist_ok=True)
    previous16=json.loads((ROOT/'docs/competition-evidence/tournament-scale-analysis.json').read_text(encoding='utf-8'))
    previous12=json.loads((ROOT/'docs/competition-evidence/frozen-solutions.json').read_text(encoding='utf-8'))
    scale=make_service(folder/(uuid4().hex+'.sqlite3'));original=Service(Repository(folder/(uuid4().hex+'.sqlite3')))
    cases=[]
    for size,service,old_rows,days in [(16,scale,previous16['cases'],WINDOWS),(12,original,previous12['days'],[date.fromisoformat(r['date']) for r in previous12['days']])]:
        for day,old in zip(days,old_rows,strict=True):
            s=service.replay(day,tournament_id='benchmark16' if size==16 else 'demo',mode='observed')
            if input_digest(s)!=old['input_sha256']:raise ValueError('Original input changed')
            t,m,v,r,settings,engine=Service.context(s)
            result=optimize(m,t,v,r,settings,engine)
            rows=[json_row(a) for a in result.assignments];verify_assignments(rows,s)
            options={match.id:candidates_for(match,t,v,r,settings,engine) for match in m}
            existing=optimize(m,t,v,r,settings,engine,force_greedy=True)
            baselines={'existing_heat_first':describe(existing.assignments,m,settings)}
            for method in METHODS:baselines[method]=describe(greedy_variant(m,t,v,r,settings,engine,method,options),m,settings)
            for baseline in baselines.values():verify_assignments(baseline['assignments'],s)
            best=min(baselines,key=lambda name:(-baselines[name]['assigned'],baselines[name]['secondary_cost'],name))
            previous=old['engine']['assigned'] if size==16 else len(old['assignments'])
            selected=describe(result.assignments,m,settings)
            common={a.match_id for a in result.assignments}&{a['match_id'] for a in baselines[best]['assignments']}
            record={'teams':size,'start':day.isoformat(),'end':t.date_end.isoformat(),'input_sha256':input_digest(s),
                'previous_assigned':previous,'selected':selected,'selected_method':result.selected_method,
                'cp_sat_status':result.cp_sat_status,'coverage_optimal':result.coverage_optimal,
                'solver':result.solver,'elapsed_sec':result.elapsed_sec,'solver_wall_sec':result.solver_wall_sec,
                'selection_candidates':result.selection_candidates,'postponed':result.postponed,
                'baselines':baselines,'best_baseline':best,'common_match_ids':sorted(common),
                'selected_common_heat':sum(a.heat_score for a in result.assignments if a.match_id in common),
                'baseline_common_heat':sum(a['heat_score'] for a in baselines[best]['assignments'] if a['match_id'] in common)}
            if selected['assigned']<baselines[best]['assigned']:raise ValueError('Selection below baseline')
            if size==12 and selected['assigned']<previous:raise ValueError('Original daily coverage regressed')
            cases.append(record)
            if size==12:
                from fastapi.encoders import jsonable_encoder
                s['proposal']={'id':uuid4().hex,**jsonable_encoder(result)};service.repo.put('sessions',s['id'],s)
                (folder/(day.isoformat()+'.json')).write_text(json.dumps(s,ensure_ascii=False),encoding='utf-8')
            print(json.dumps({'teams':size,'date':day.isoformat(),'previous':previous,'baseline':baselines[best]['assigned'],'selected':selected['assigned'],'method':result.selected_method,'status':result.cp_sat_status}),flush=True)
    summary={}
    for size in (12,16):
        rows=[c for c in cases if c['teams']==size]
        summary[str(size)]={'cases':len(rows),'previous_assigned':sum(c['previous_assigned'] for c in rows),
            'selected_assigned':sum(c['selected']['assigned'] for c in rows),'baseline_assigned':sum(c['baselines'][c['best_baseline']]['assigned'] for c in rows),
            'selected_complete':sum(c['selected']['postponed']==0 for c in rows),
            'statuses':dict(Counter(c['cp_sat_status'] for c in rows)),
            'selected_methods':dict(Counter(c['selected_method'] for c in rows)),
            'baseline_common_heat':sum(c['baseline_common_heat'] for c in rows),'selected_common_heat':sum(c['selected_common_heat'] for c in rows)}
    packet={'version':1,'scope':'2026-10-11 recalculation (solar interval alignment, 0.1C decision rounding, deterministic tie-break); every predeclared case re-solved once with the same inputs; no policy/operating/time-limit change',
        'historical_files':'Prior frozen evidence remains historical; never overwrite adverse results.',
        'original_sample_sha256':previous12['original_sample_sha256'],'summary':summary,'cases':cases}
    (ROOT/'docs/competition-evidence/review-fix-results.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (folder/'analysis.json').write_text(json.dumps(packet,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary),flush=True)
    return packet

if __name__=='__main__':run()
