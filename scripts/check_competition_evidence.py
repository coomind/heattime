"""Offline cross-check of new comparison claims, UI evidence and Q&A; no secrets or network."""
import hashlib
import json
import re
from pathlib import Path

from compare_schedule_methods import summarize, digest
from check_submission import run as check_submission

ROOT=Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))


def run():
    original=read('docs/real-data/replay-results.json')
    result=read('docs/competition-evidence/method-comparison.json')
    ledger=read('docs/competition-evidence/frozen-solutions.json')
    ui=read('frontend/src/demo/period-evidence.json')
    summary=result['summary'];checks=[]
    def check(name,passed):checks.append({'name':name,'passed':bool(passed)})
    check('all dates, frozen outputs and original provenance agree',
          [r['date'] for r in original['days']]==[r['date'] for r in ledger['days']]==[r['date'] for r in result['days']]
          and original['original_sample_sha256']==ledger['original_sample_sha256']==result['original_sample_sha256']==ui['original_sample_sha256']
          and result['frozen_solutions_sha256']==digest(ledger)
          and all((o['assigned'],o['postponed'],o['solver'])==(r['cp_assigned'],r['cp_postponed'],r['cp_solver']) for o,r in zip(original['days'],result['days'])))
    check('reported summary covers all days and common-game scores',summary==summarize(result['days'])
          and all(r['cp_assigned']+r['cp_postponed']==r['greedy_assigned']+r['greedy_postponed']==15 for r in result['days']))
    hashes={p.name:hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest() for p in
            (ROOT/'docs/real-data/replay-results.json',ROOT/'docs/competition-evidence/method-comparison.json')}
    check('UI provenance matches normalized committed source text',ui['source_sha256']==hashes
          and ui['comparison']['summary']==summary and len(ui['days'])==len(ui['comparison']['days'])==62)
    texts={p:p.read_text(encoding='utf-8') for folder in ('docs/competition-evidence','docs/submission','docs/presentation') for p in (ROOT/folder).glob('*.md')}
    table=(ROOT/'docs/competition-evidence/method-comparison.md').read_text(encoding='utf-8')
    check('comparison manuscript includes both coverage benefit and heat cost',
          (summary['greedy_assigned'],summary['cp_assigned'],summary['assignment_gain'],summary['greedy_complete_days'],summary['cp_complete_days'])==(506,562,56,0,16)
          and (summary['greedy_common_heat'],summary['cp_common_heat'])==(130617,132430)
          and all(token in table for token in ('506','562','+56','0일','16일','130617','132430','1.39%','11 / 26 / 22','25 / 37 / 0')))
    qa=(ROOT/'docs/presentation/qa.md').read_text(encoding='utf-8')
    answer=re.search(r'(?ms)^## 13\. .*?\*\*30초 목표 답변\*\*\s*(.*?)(?=\n\*\*|\Z)',qa)
    length=len(re.sub(r'\s+',' ',answer.group(1).strip())) if answer else 0
    check('new answer fits unchanged rehearsal budget and discloses adverse result',0<length<=180
          and all(token in answer.group(1) for token in ('56건','1.39%','높았습니다','사람의 수작업','경쟁 제품')))
    slides=(ROOT/'docs/presentation/slides.md').read_text(encoding='utf-8')
    check('algorithm comparison remains outside unchanged main presentation',all(token not in slides for token in ('506','562','1.39%'))
          and '본 발표420초에 추가하지 않는다' in qa)
    missing=[]
    for path,body in texts.items():
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',body):
            if '://' not in target and not target.startswith('#') and not (path.parent/target.split('#')[0]).is_file():missing.append(f'{path.name}: {target}')
    check('evidence, submission and presentation links resolve',not missing)
    old=check_submission()
    check('existing ten submission and sixteen presentation checks retained',old['passed'] and len(old['checks'])==10)
    return {'passed':all(row['passed'] for row in checks),'checks':checks,'qa13_characters':length,'missing_links':missing}


if __name__=='__main__':
    result=run();print(json.dumps(result,ensure_ascii=True,indent=2));raise SystemExit(0 if result['passed'] else 1)
