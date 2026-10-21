"""Local review archive of tracked source/docs and normalized public observations.

Never opens .env, raw samples, local databases, runtime records or untracked files.
No upload, external messaging, code execution, dependency install or credential loading.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
# Verbatim table extract of the public KMA ASOS guide (the DOCX itself is no longer in the repository).
ASOS_GUIDE='docs/kma/asos-guide-extract.json'
ASOS_GUIDE_SHA256='5b51a81b9f1f401952605865c3fbce4c80f3f36c614b1b2f557cf2c9e6a72623'

def allowed(name):
    path=Path(name)
    if path.is_absolute() or '..' in path.parts:return False
    if any(part.lower().startswith('.env') for part in path.parts):return False
    if name==ASOS_GUIDE:return True
    if path.suffix.lower() in {'.sqlite3','.db','.pyc','.docx','.pdf','.pptx'}:return False
    if any(part in {'.git','.venv','node_modules','dist','__pycache__'} for part in path.parts):return False
    if name.startswith('data/'):
        return name in {'data/observations/asos_119_20260701_20260831.json',
                        'data/mock/venues.json','data/mock/matches.csv'}
    if name.startswith('docs/'):
        return path.suffix.lower() in {'.md','.json','.png','.txt'} or name=='docs/wbgt-sanity/regression-fixtures.zip'
    if name.startswith(('backend/','frontend/','scripts/','tests/')):return True
    return name in {'README.md','AGENTS.md','pyproject.toml','requirements.txt','.gitignore','.dockerignore','Dockerfile','render.yaml','vercel.json','docker-compose.yml'}

def inventory(root=None):
    root=Path(root or ROOT)
    # An extracted review ZIP has no Git metadata; its committed file manifest
    # supplies the same explicit inventory so its tests/build remain runnable.
    if (root/'REVIEW-MANIFEST.json').is_file() and not (root/'.git').exists():
        manifest=json.loads((root/'REVIEW-MANIFEST.json').read_text(encoding='utf-8'))
        return [entry['path'] for entry in manifest['files']],manifest['repository_commit']
    return (subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0'),
            subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip())

def build():
    tracked,revision=inventory()
    names=sorted(name for name in tracked if name and allowed(name))
    target=ROOT/'data/output/ai-review/HeatTime-AI-review.zip';target.parent.mkdir(parents=True,exist_ok=True)
    entries=[]
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names:
            payload=(ROOT/name).read_bytes()
            if name==ASOS_GUIDE and hashlib.sha256(payload).hexdigest()!=ASOS_GUIDE_SHA256:
                raise ValueError('ASOS guide extract fingerprint changed')
            entries.append({'path':name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
            archive.writestr(name,payload)
        manifest={'repository_commit':revision,'purpose':'Local independent AI review; not uploaded or independently certified.',
                  'excluded':'All .env files, raw API samples, local databases/runtime records, untracked files, other DOCX and generated PDF/PPTX. The fingerprint-verified table extract of the public ASOS guide is included for offline contract tests.',
                  'observation_scope':'Committed normalized public Suwon ASOS fields; observed inputs are not field WBGT.',
                  'files':entries}
        archive.writestr('REVIEW-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:raise ValueError('Archive integrity failure')
        for name in archive.namelist():
            if name!='REVIEW-MANIFEST.json' and not allowed(name):raise ValueError('Forbidden archive member')
        if 'docs/ai-review-pack.md' not in archive.namelist():raise ValueError('Review handoff missing')
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (target.parent/'manifest.json').write_text(json.dumps({**manifest,'archive_sha256':digest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(entries),'archive_bytes':target.stat().st_size,'sha256':digest,'commit':revision},ensure_ascii=True))
    return target

if __name__=='__main__':build()
