from copy import deepcopy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.plan_review import review

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('prefix',['snapshot','observed-snapshot'])
def test_api_and_offline_review_preserve_all_records_and_original_approval(tmp_path,prefix):
    bundle=json.loads((ROOT/f'frontend/src/demo/{prefix}.json').read_text(encoding='utf-8'))
    supplemental=json.loads((ROOT/f'frontend/src/demo/{prefix}-plan-review.json').read_text(encoding='utf-8'))
    s=bundle['approved'];app=create_app(tmp_path/'review.sqlite3');repo=app.state.repo
    repo.put('sessions',s['id'],s)
    with TestClient(app) as client:
        before=repo.list('sessions')
        for view in ('proposed','approved'):
            response=client.get(f"/api/sessions/{s['id']}/plan-review",params={'view':view})
            assert response.status_code==200
            assert response.json()==supplemental[view]==review(s,view)
        assert repo.list('sessions')==before
        assert client.get(f"/api/sessions/{s['id']}/plan-review?view=invalid").status_code==422
        assert client.get('/api/sessions/missing/plan-review').status_code==404
        assert client.post(f"/api/sessions/{s['id']}/plan-review",json={}).status_code==405
        changed=deepcopy(s);changed['risks']=[];changed['manual_history']=[]
        repo.put('sessions',s['id'],changed)
        assert client.get(f"/api/sessions/{s['id']}/plan-review?view=approved").json()==supplemental['approved']
        changed['decision']=None;repo.put('sessions',s['id'],changed)
        assert client.get(f"/api/sessions/{s['id']}/plan-review?view=approved").status_code==422
