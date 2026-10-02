"""Offline analysis of every verified observation day; no collection or .env."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.weather.asos_samples import load_dataset
from backend.repository import Repository
from backend.service import Service
from backend.schedule.optimizer import Candidate,validate


def candidate_order(row):
    return (row['postponed'], -row['salvaged'], -row['heat_reduction'], row['date'])


def analyze(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    data=load_dataset();db=output/f'analysis-{uuid4().hex}.sqlite3'
    service=Service(Repository(db));rows=[]
    for day in data.dates:
        session=service.replay(day,mode='observed');p=service.optimize(session['id'])
        t,m,v,r,settings,engine=service.context(session)
        assignments=[Candidate(**{**a,'start':datetime.fromisoformat(a['start']),'end':datetime.fromisoformat(a['end'])}) for a in p['assignments']]
        errors=validate(assignments,m,t,v,r,settings)
        if errors or not p['constraints_ok']:raise RuntimeError('Hard constraint validation failed')
        if set(p['common_match_ids'])!={a.match_id for a in assignments}:raise RuntimeError('Common match set mismatch')
        if len(assignments)+p['postponed_count']!=len(m) or any(not x['reason'] for x in p['postponed']):
            raise RuntimeError('Missing coverage/postponement evidence')
        assigned={a.match_id for a in assignments}
        salvaged=sum(rec['level']==4 and rec['match_id'] in assigned for rec in session['recommendations'])
        row={'date':day.isoformat(),'session_id':session['id'],'assigned':len(assignments),'postponed':p['postponed_count'],
             'common_count':len(p['common_match_ids']),'original_heat':p['original_heat_score'],'proposed_heat':p['proposed_heat_score'],
             'heat_reduction':p['original_heat_score']-p['proposed_heat_score'],'salvaged':salvaged,
             'original_stop_count':sum(rec['level']==4 for rec in session['recommendations']),
             'max_wbgt_c':max(risk.wbgt_c for risk in r),'max_decision_wbgt_c':max(risk.decision_wbgt_c for risk in r),
             'solver':p['solver'],'coverage_optimal':p['coverage_optimal'],'elapsed_sec':p['elapsed_sec'],
             'constraints_ok':not errors,'postponement_reasons':p['postponed'],
             'missing_solar_hours':session['observation_summary']['solar_missing_hours']}
        rows.append(row)
        (output/(day.isoformat()+'.json')).write_text(json.dumps(service.repo.get('sessions',session['id']),ensure_ascii=False),encoding='utf-8')
        print(json.dumps({k:row[k] for k in ('date','assigned','postponed','salvaged','solver','elapsed_sec')}),flush=True)
    candidates=sorted(rows,key=candidate_order)[:3]
    result={'station':data.station,'original_sample_sha256':data.original_sha256,'days':rows,'candidates':candidates,
            'selection_rule':'postponed ascending, salvaged descending, common heat reduction descending, date ascending',
            'note':'Salvaged = originally level4 but assigned after rescheduling; maximum WBGT across 24h and all virtual venues',
            'db':str(db)}
    public_result={k:v for k,v in result.items() if k!='db'}
    (ROOT/'docs/real-data/replay-results.json').write_text(json.dumps(public_result,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'data/output/real'))
    args=parser.parse_args();result=analyze(args.output)
    print(json.dumps({'candidates':result['candidates']},ensure_ascii=False),flush=True)
