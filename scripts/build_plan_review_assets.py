"""Supplement existing offline snapshots without modifying their inputs or decisions."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.plan_review import review

def build():
    folder=ROOT/'frontend/src/demo'
    for prefix in ('snapshot','observed-snapshot'):
        bundle=json.loads((folder/f'{prefix}.json').read_text(encoding='utf-8'))
        s=bundle['approved']
        data={'input_fingerprint':bundle['input_fingerprint'],'session_id':s['id'],
              'proposed':review(s),'approved':review(s,'approved')}
        (folder/f'{prefix}-plan-review.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        print(prefix, data['proposed']['assigned'])

if __name__=='__main__':build()
