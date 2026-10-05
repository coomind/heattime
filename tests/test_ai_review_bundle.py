import json
from pathlib import Path
import zipfile
import scripts.build_ai_review_bundle as builder

def test_review_archive_never_opens_tracked_credentials_raw_samples_or_runtime_records(tmp_path,monkeypatch):
    files={'docs/ai-review-pack.md':'Review only.','backend/public.py':'public=True\n',
           '.env':'FAKE_CREDENTIAL=fixture-only','.env.example':'FAKE=fixture-only',
           'data/samples/secret.json':'private fixture','data/output/records.json':'private fixture',
           'data/private.sqlite3':'private fixture'}
    for name,body in files.items():
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    monkeypatch.setattr(builder.subprocess,'check_output',lambda args,**kwargs:
                        ('\0'.join(files)+'\0').encode() if args[1]=='ls-files' else b'fixture-commit\n')
    read=Path.read_bytes
    def guard(path):
        name=path.relative_to(tmp_path).as_posix()
        if name in files and name not in {'docs/ai-review-pack.md','backend/public.py'}:
            raise AssertionError('Forbidden file must not be opened')
        return read(path)
    monkeypatch.setattr(Path,'read_bytes',guard)
    archive=builder.build()
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())=={'docs/ai-review-pack.md','backend/public.py','REVIEW-MANIFEST.json'}
        manifest=json.loads(z.read('REVIEW-MANIFEST.json'))
        assert manifest['repository_commit']=='fixture-commit'
        assert {r['path'] for r in manifest['files']}=={'docs/ai-review-pack.md','backend/public.py'}
        assert z.testzip() is None
