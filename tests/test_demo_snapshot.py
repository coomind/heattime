import base64
from io import BytesIO
import json
from pathlib import Path
from pypdf import PdfReader
from backend.service import Service
from backend.schedule.optimizer import Candidate, validate
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from datetime import datetime

ROOT = Path(__file__).parents[1]


def test_snapshot_provenance_defaults_and_constraints():
    bundle = json.loads((ROOT/'frontend/src/demo/snapshot.json').read_text(encoding='utf-8'))
    s = bundle['approved']
    assert s['mode'] == 'snapshot' and '시연 스냅샷' in s['label'] and '실제 관측 아님' in s['label']
    assert all(r['is_mock'] for r in s['risks']) and len(s['risks']) == 72
    assert s['engine_settings'] == EngineSettings().model_dump()
    assert s['schedule_settings'] == ScheduleSettings().model_dump()
    t, matches, venues, risks, settings, engine = Service.context(s)
    assignments = [Candidate(**{**a, 'start': datetime.fromisoformat(a['start']),
                    'end': datetime.fromisoformat(a['end'])}) for a in s['proposal']['assignments']]
    assert validate(assignments, matches, t, venues, risks, settings) == []
    assert len(assignments) + len(s['proposal']['postponed']) == 15
    assert s['decision']['assignments'] == s['proposal']['assignments']
    assert all(n['channel'] == 'mock' for n in s['notifications'])


def test_precomputed_pdf_has_snapshot_and_exact_notice():
    bundle = json.loads((ROOT/'frontend/src/demo/snapshot.json').read_text(encoding='utf-8'))
    reader = PdfReader(BytesIO(base64.b64decode(bundle['pdf_base64'])))
    text = ''.join(p.extract_text() for p in reader.pages)
    assert '시연 스냅샷' in text and '실제 운영 판단 기록 아님' in text
    assert all('본 자료는 의사결정 보조용 추정값' in p.extract_text() for p in reader.pages)
    assert '시연 스냅샷' in bundle['csv_utf8']
