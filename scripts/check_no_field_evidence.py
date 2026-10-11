"""Additional offline evidence checks; never replace existing checks or load credentials."""
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.analyze_without_field import summarize
from scripts.compare_schedule_methods import digest

def validate_analysis(data,ledger,ui):
    if data['ledger_sha256']!=digest(ledger) or data['original_sample_sha256']!=ledger['original_sample_sha256']:
        raise ValueError('원자료 지문 불일치')
    if len(data['days'])!=62 or [d['date'] for d in data['days']]!=[d['date'] for d in ledger['days']]:
        raise ValueError('전체 날짜 불일치')
    if data['summary']!=summarize(data['days']):raise ValueError('합산 불일치')
    for day,frozen in zip(data['days'],ledger['days'],strict=True):
        if day['input_sha256']!=frozen['input_sha256'] or day['cp']['assignments']!=frozen['assignments'] or day['cp_solver']!=frozen['solver']:
            raise ValueError('고정 해 불일치')
        names=[n for n in day['baselines'] if n!='best_of_four']
        if set(names)!={'existing_heat_first','earliest_input','earliest_reverse','weighted_critical'}:
            raise ValueError('비교 방식 불일치')
        selected=min(names,key=lambda n:(-day['baselines'][n]['assigned'],day['baselines'][n]['secondary_cost'],n))
        if day['baselines']['best_of_four']!={**day['baselines'][selected],'selected_method':selected}:
            raise ValueError('기준 선택 불일치')
        cp=day['cp']['assignments'];cp_ids={a['match_id'] for a in cp}
        if len(cp_ids)!=len(cp) or day['cp']['assigned']!=len(cp):raise ValueError('배정 수 불일치')
        for name,baseline in day['baselines'].items():
            ids={a['match_id'] for a in baseline['assignments']};common=ids&cp_ids;c=day['comparisons'][name]
            if len(ids)!=len(baseline['assignments']) or len(ids)!=baseline['assigned'] or baseline['assigned']+baseline['postponed']!=15:
                raise ValueError('배정 수 불일치')
            if c!={'common_match_ids':sorted(common),'cp_common_heat':sum(a['heat_score'] for a in cp if a['match_id'] in common),
                   'baseline_common_heat':sum(a['heat_score'] for a in baseline['assignments'] if a['match_id'] in common)}:
                raise ValueError('공통 경기 점수 불일치')
    compact={**data,'days':[{**d,'baselines':{k:{a:b for a,b in val.items() if a!='assignments'} for k,val in d['baselines'].items()}} for d in data['days']]}
    if ui!=compact:raise ValueError('화면 자료 불일치')

def run():
    def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
    checks=[]
    def check(name,passed):checks.append({'name':name,'passed':bool(passed)})
    try:
        validate_analysis(read('docs/competition-evidence/no-field-analysis.json'),read('docs/competition-evidence/frozen-solutions.json'),read('frontend/src/demo/no-field-analysis.json'))
        check('all dates, favourable baselines, common scores, frozen source and UI agree',True)
    except (ValueError,KeyError):check('all dates, favourable baselines, common scores, frozen source and UI agree',False)
    qa=(ROOT/'docs/presentation/qa.md').read_text(encoding='utf-8');counts={}
    for n in (14,15):
        match=re.search(rf'(?ms)^## {n}\. .*?\*\*30초 목표 답변\*\*\s*(.*?)(?=\n\*\*|\Z)',qa)
        counts[str(n)]=len(re.sub(r'\s+',' ',match.group(1).strip())) if match else 0
    check('new two answers fit unchanged 30-second rehearsal budget',all(0<n<=180 for n in counts.values()))
    proposal=(ROOT/'docs/submission/proposal.md').read_text(encoding='utf-8')
    # 2026-10-11 recalculation: best-of-four 552 vs CP-SAT 555, complete days 15 vs 15, common heat 148856->142674.
    data=read('docs/competition-evidence/no-field-analysis.json');strong=data['summary']['baselines']['best_of_four']
    reduction=round((1-strong['cp_common_heat']/strong['baseline_common_heat'])*100,2)
    check('summary numbers quoted in manuscripts match the regenerated analysis',
          (strong['assigned'],data['summary']['cp_assigned'],strong['complete_days'],strong['cp_equal_days'],strong['cp_fewer_days'],
           strong['equal_coverage_secondary_win_days'],strong['equal_coverage_secondary_loss_days'],strong['baseline_common_heat'],strong['cp_common_heat'],reduction)
          ==(552,555,15,59,0,49,0,148856,142674,4.15)
          and sum(d['cp']['assigned']==15 for d in data['days'])==15
          and {k:v['needs_review_days'] for k,v in data['summary']['scenarios'].items()}=={'wbgt_-1':36,'wbgt_+0':0,'wbgt_+1':38,'wbgt_+2':52,'missing_critical_hour':52}
          and all(v['applicable_days']==52 for v in data['summary']['scenarios'].values()))
    check('primary proposal uses stronger comparison and keeps the adverse comparison',
          all(t in proposal for t in ('552','555','15→15','4.15%','2.90%','148856','142674','49일 우세','+1℃38일','+2℃52일','0배정10일','현장 WBGT 실측 아님')))
    check('scenario limits and missing field evidence are explicit',all(t in proposal for t in ('실제 오차','재최적화','미검증','실측 자료')))
    return {'passed':all(c['passed'] for c in checks),'checks':checks,'qa_characters':counts}

if __name__=='__main__':
    result=run();print(json.dumps(result,ensure_ascii=True,indent=2));raise SystemExit(0 if result['passed'] else 1)
