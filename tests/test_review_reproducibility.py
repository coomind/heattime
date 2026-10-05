import json
from pathlib import Path
import shlex
import subprocess
import zipfile
import scripts.build_ai_review_bundle as builder


def test_review_bundle_includes_runtime_mock_fixtures_and_can_bootstrap_service(tmp_path,monkeypatch):
    monkeypatch.setattr(builder,'ROOT',Path(__file__).resolve().parents[1])
    archive=builder.build()
    with zipfile.ZipFile(archive) as z:
        assert {'data/mock/venues.json','data/mock/matches.csv','.dockerignore','Dockerfile','render.yaml'} <= set(z.namelist())
        assert '.env' in z.read('.dockerignore').decode('utf-8')
        assert builder.ASOS_GUIDE in z.namelist()
        import hashlib
        assert hashlib.sha256(z.read(builder.ASOS_GUIDE)).hexdigest()==builder.ASOS_GUIDE_SHA256
        assert json.loads(z.read('data/mock/venues.json'))
        z.extractall(tmp_path)
    result=subprocess.run([__import__('sys').executable,'-c',
        'from backend.service import Service; from backend.repository import Repository; '
        's=Service(Repository("data/output/smoke.sqlite3")); '
        'assert len(s.repo.list("venues"))==3; assert len(s.repo.list("matches"))==15'],
        cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_all_local_docker_copy_inputs_are_tracked():
    root=Path(__file__).resolve().parents[1]
    tracked=set(builder.inventory(root)[0])
    for line in (root/'Dockerfile').read_text(encoding='utf-8').splitlines():
        if not line.startswith('COPY ') or '--from=' in line:continue
        for source in shlex.split(line)[1:-1]:
            assert any(name==source or name.startswith(source.rstrip('/')+'/') for name in tracked),source
            assert (root/source).exists(),source
