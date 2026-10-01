"""Precompute a synthetic demo locally. No credential loading or network calls."""
import base64
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.repository import Repository
from backend.service import Service
from backend.exports import records_pdf, records_csv


def build(output):
    work = ROOT/'data/output/snapshot-build'
    work.mkdir(parents=True, exist_ok=True)
    service = Service(Repository(work/f'{uuid4().hex}.sqlite3'))
    session = service.replay(date(2026, 8, 1))
    session['mode'] = 'snapshot'
    session['label'] = '시연 스냅샷 · 가상 예시 · mock 합성 기상 (실제 관측 아님)'
    service.repo.put('sessions', session['id'], session)
    service.optimize(session['id'])
    approved = service.decide(session['id'], 'accepted', '가상 예시 스냅샷 운영자',
                              '사전 계산된 가상 시연 · 실제 운영 판단 기록 아님')
    fingerprint = hashlib.sha256(json.dumps({k: approved[k] for k in
        ['weather', 'engine_settings', 'schedule_settings', 'policy']},
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result = {'version': 1, 'label': approved['label'], 'input_fingerprint': fingerprint,
              'approved': approved, 'pdf_base64': base64.b64encode(records_pdf(approved)).decode(),
              'csv_utf8': records_csv(approved).decode('utf-8-sig')}
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    return {'path': str(output), 'assignments': len(approved['proposal']['assignments']),
            'postponed': approved['proposal']['postponed_count'], 'is_mock': True}


if __name__ == '__main__':
    print(json.dumps(build(ROOT/'frontend/src/demo/snapshot.json'), ensure_ascii=False))
