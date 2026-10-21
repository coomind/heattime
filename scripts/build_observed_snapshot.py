"""Freeze observed demo scenes from existing real replays; no fetching.

Scenes (backend/config/demo.yaml): the demo day, the hotter day with postponements, and the
hotter day replayed as a two-day tournament (same virtual tournament, one more day).
Single days reuse the 62-day replay session (no re-solve); the two-day scene is replayed and
solved once in its own database because the 62-day analysis only covers one-day tournaments.
"""
import base64
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.repository import Repository
from backend.service import Service
from backend.exports import records_pdf,records_csv
from backend.demo_config import demo_date, extreme_date

# (file prefix, date, two-day?, operator reason typed in the demo). Reasons are virtual examples.
SCENES={
    'demo':('observed-snapshot',None,False,'가상 시연입니다. 단축안을 검토하고 승인합니다.'),
    'extreme':('observed-snapshot-0808',None,False,'가상 시연입니다. 단축안과 연기 후보를 검토하고 승인합니다.'),
    'extreme-2day':('observed-snapshot-0808-2day',None,True,'가상 시연입니다. 이틀 일정 단축안을 검토하고 승인합니다.'),
}


def scene_date(key):
    return demo_date() if key=='demo' else extreme_date()


def two_day_service(day):
    """Fresh database whose virtual tournament 'demo' runs one extra day (same teams, venues, matches)."""
    folder=ROOT/'data/output/real';folder.mkdir(parents=True,exist_ok=True)
    service=Service(Repository(folder/f'two-day-{uuid4().hex}.sqlite3'))
    t=service.repo.get('tournaments','demo')
    end=date.fromisoformat(t['date_start'])+timedelta(days=1)
    t={**t,'date_end':end.isoformat(),'name':t['name'].replace(' · 가상 예시',' · 이틀 일정 · 가상 예시')}
    service.repo.put('tournaments','demo',service.validate_resource('tournaments',t))
    return service


def solved_session(key):
    prefix,_,two_day,reason=SCENES[key];day=scene_date(key)
    if two_day:
        service=two_day_service(day)
        session=service.replay(date.fromisoformat(day),mode='observed');service.optimize(session['id'])
        session=service.repo.get('sessions',session['id'])
    else:
        results=json.loads((ROOT/'data/output/real/results.json').read_text(encoding='utf-8'))
        candidate=next(d for d in results['days'] if d['date']==day)
        service=Service(Repository(results['db']))
        session=service.repo.get('sessions',candidate['session_id'])
        assert session['proposal']['original_heat_score']==candidate['original_heat']
        assert session['proposal']['proposed_heat_score']==candidate['proposed_heat']
    if session['decision'] is None:
        session['mode']='snapshot-observed'
        session['label']='관측 시연 스냅샷 · 사전 계산 · '+session['label']
        service.repo.put('sessions',session['id'],session)
        session=service.decide(session['id'],'accepted','가상 예시 스냅샷 운영자',reason)
    # The typed demo reason is short, so the record label carries the notice that this is not a real operation record
    # (shown on screen, on every PDF page header block and in every CSV row).
    if '실제 운영 판단 기록 아님' not in session['label']:
        session['label']=session['label'].replace('관측 시연 스냅샷 · 사전 계산 · ','관측 시연 스냅샷 · 사전 계산 · 실제 운영 판단 기록 아님 · ',1)
        assert '실제 운영 판단 기록 아님' in session['label']
    frozen=(session.get('decision') or {}).get('snapshot')
    if frozen and '실제 운영 판단 기록 아님' not in frozen.get('label',''):
        frozen['label']=session['label']  # the approved record keeps the same notice
    # Mock notification wording follows the current templates (readable names); schedule and decision unchanged.
    from backend.notifications import build_notifications
    from fastapi.encoders import jsonable_encoder
    session['notifications']=jsonable_encoder(build_notifications(session))
    service.repo.put('sessions',session['id'],session)
    assert session['data_origin']=='kma_observed' and all(not p['is_mock'] for p in session['weather'])
    return session


def build(key='demo'):
    prefix=SCENES[key][0];session=solved_session(key)
    fingerprint=hashlib.sha256(json.dumps({k:session[k] for k in
        ['weather','engine_settings','schedule_settings','policy']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    bundle={'version':1,'scene':key,'label':session['label'],'input_fingerprint':fingerprint,'approved':session}
    pdf=records_pdf(session)
    exports={'input_fingerprint':fingerprint,'pdf_base64':base64.b64encode(pdf).decode(),
             'csv_utf8':records_csv(session).decode('utf-8-sig')}
    output=ROOT/'frontend/src/demo'
    for name,item in [(f'{prefix}.json',bundle),(f'{prefix}-exports.json',exports)]:
        (output/name).write_text(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    (ROOT/f'data/output/real/{prefix}.pdf').write_bytes(pdf)
    p=session['proposal']
    print(json.dumps({'scene':key,'date':session['tournament']['date_start'],'end':session['tournament']['date_end'],
                      'assigned':len(p['assignments']),'postponed':p['postponed_count'],'fingerprint':fingerprint},ensure_ascii=False))
    return bundle


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--scene',choices=[*SCENES,'all'],default='all')
    args=parser.parse_args()
    for key in (SCENES if args.scene=='all' else [args.scene]):build(key)
