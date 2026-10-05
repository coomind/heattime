"""Offline integrity checks of the additional bracket; preserve older evidence checks."""
from datetime import date,timedelta
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.analyze_tournament_scale import WINDOWS,NAMES,summary
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings

def run():
    data=json.loads((ROOT/'docs/competition-evidence/tournament-scale-analysis.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'docs/competition-evidence/frozen-solutions.json').read_text(encoding='utf-8'))
    checks=[]
    def check(name,condition):checks.append({'name':name,'passed':bool(condition)})
    rows=data['cases']
    check('all predeclared two-day windows, original source and defaults retained',
          [r['start'] for r in rows]==[d.isoformat() for d in WINDOWS]
          and all(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])==timedelta(days=1) for r in rows)
          and data['original_sample_sha256']==old['original_sample_sha256']
          and data['engine_settings']==EngineSettings().model_dump() and data['schedule_settings']==ScheduleSettings().model_dump())
    check('summary and favourable baseline selection agree',data['summary']==summary(rows)
          and all(set(r['baselines'])==set(NAMES) and r['selected_baseline']==min(r['baselines'],key=lambda n:(-r['baselines'][n]['assigned'],r['baselines'][n]['secondary_cost'],n)) for r in rows))
    check('every comparison uses its actual common games and complete coverage counts',all(
        r['engine']['assigned']+r['engine']['postponed']==27
        and all(b['assigned']+b['postponed']==27 for b in r['baselines'].values())
        and r['comparison']['common_match_ids']==sorted({a['match_id'] for a in r['engine']['assignments']}&{a['match_id'] for a in r['baselines'][r['selected_baseline']]['assignments']})
        and r['comparison']['assignment_gain']==r['engine']['assigned']-r['baselines'][r['selected_baseline']]['assigned']
        for r in rows))
    body=(ROOT/'docs/tournament-scale-report.md').read_text(encoding='utf-8')
    check('adverse results and non-optimal cases disclosed',all(t in body for t in ('596','598','16 / 27','26 / 27','FEASIBLE','최소 연기','일반화')))
    return {'passed':all(r['passed'] for r in checks),'checks':checks}

if __name__=='__main__':
    result=run();print(json.dumps(result,ensure_ascii=True,indent=2));raise SystemExit(0 if result['passed'] else 1)
