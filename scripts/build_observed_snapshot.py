"""Freeze the highest ranked *existing* real replay; no re-solve or fetching."""
import base64
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.repository import Repository
from backend.service import Service
from backend.exports import records_pdf,records_csv


def build():
    results=json.loads((ROOT/'data/output/real/results.json').read_text(encoding='utf-8'))
    candidate=results['candidates'][0]
    service=Service(Repository(results['db']))
    session=service.repo.get('sessions',candidate['session_id'])
    if session['decision'] is None:
        session['mode']='snapshot-observed'
        session['label']='관측 시연 스냅샷 · 사전 계산 · '+session['label']
        service.repo.put('sessions',session['id'],session)
        session=service.decide(session['id'],'accepted','가상 예시 스냅샷 운영자',
            '기상청 관측 입력으로 사전 계산된 가상 시연 · 실제 운영 판단 기록 아님')
    assert session['data_origin']=='kma_observed' and all(not p['is_mock'] for p in session['weather'])
    assert session['proposal']['original_heat_score']==candidate['original_heat']
    assert session['proposal']['proposed_heat_score']==candidate['proposed_heat']
    fingerprint=hashlib.sha256(json.dumps({k:session[k] for k in
        ['weather','engine_settings','schedule_settings','policy']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    bundle={'version':1,'label':session['label'],'input_fingerprint':fingerprint,'approved':session}
    pdf=records_pdf(session)
    exports={'input_fingerprint':fingerprint,'pdf_base64':base64.b64encode(pdf).decode(),
             'csv_utf8':records_csv(session).decode('utf-8-sig')}
    output=ROOT/'frontend/src/demo'
    for name,item in [('observed-snapshot.json',bundle),('observed-snapshot-exports.json',exports)]:
        (output/name).write_text(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    (ROOT/'data/output/real/observed-snapshot.pdf').write_bytes(pdf)
    print(json.dumps({'date':candidate['date'],'assigned':candidate['assigned'],'postponed':candidate['postponed'],
                      'fingerprint':fingerprint},ensure_ascii=False))
    return bundle


if __name__=='__main__':build()
