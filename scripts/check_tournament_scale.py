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
    # 2026-10-21 recalculation (central-estimate decision rule): engine 710 vs favourable simple 701, no case below the
    # simple baseline, 10 OPTIMAL / 12 FEASIBLE / 9 fallback (CP-SAT UNKNOWN -> validated earliest_input).
    s=data['summary']
    FALLBACK='validated-greedy · CP-SAT UNKNOWN'
    check('regenerated summary values are the ones quoted in manuscripts',
          (s['engine_assigned'],s['baseline_assigned'],s['engine_complete_cases'],s['baseline_complete_cases'],s['engine_more_cases'],s['equal_cases'],s['engine_fewer_cases'])==(710,701,21,17,7,24,0)
          and s['statuses']=={'CP-SAT FEASIBLE':12,'CP-SAT OPTIMAL':10,FALLBACK:9} and (s['engine_common_heat'],s['baseline_common_heat'])==(181204,190575))
    rerun=json.loads((ROOT/'docs/competition-evidence/review-fix-results.json').read_text(encoding='utf-8'))['summary']['16']
    # The same-input rerun now reproduces 710 assignments, but 9 cases end as CP-SAT UNKNOWN and fall back to the
    # validated earliest_input alternative; that fallback count must be recorded, not hidden.
    check('same-input rerun difference is recorded, not hidden',rerun['previous_assigned']==710 and rerun['selected_assigned']==710 and rerun['baseline_assigned']==701
          and rerun['statuses']=={'UNKNOWN':9,'FEASIBLE':12,'OPTIMAL':10} and rerun['selected_methods']=={'earliest_input':9,'cp_sat':22})
    body=(ROOT/'docs/tournament-scale-report.md').read_text(encoding='utf-8')
    current=(ROOT/'docs/competition-evidence/judge-brief.md').read_text(encoding='utf-8')+(ROOT/'docs/submission/proposal.md').read_text(encoding='utf-8')
    # The 2026-10-06 report keeps its historical 596/598 figures and must point to the recalculations; current-facing
    # manuscripts must quote the regenerated JSON values and the fallback count.
    check('adverse results and non-optimal cases disclosed',all(t in body for t in ('FEASIBLE','최소 연기','일반화','596','598','recalc-2026-10-11.md','recalc-2026-10-21.md'))
          and all(t in current for t in (str(s['engine_assigned']),str(s['baseline_assigned']),str(rerun['selected_assigned']),
                                         f"{s['statuses']['CP-SAT FEASIBLE']}개 FEASIBLE",f"{s['statuses'][FALLBACK]}개 구간은 CP-SAT UNKNOWN",'우위로 확대하지 않')))
    return {'passed':all(r['passed'] for r in checks),'checks':checks}

if __name__=='__main__':
    result=run();print(json.dumps(result,ensure_ascii=True,indent=2));raise SystemExit(0 if result['passed'] else 1)
