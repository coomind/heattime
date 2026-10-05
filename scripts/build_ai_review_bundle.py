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

def allowed(name):
    path=Path(name)
    if any(part.lower().startswith('.env') for part in path.parts):return False
    if path.suffix.lower() in {'.sqlite3','.db','.pyc','.docx','.pdf','.pptx'}:return False
    if any(part in {'.git','.venv','node_modules','dist','__pycache__'} for part in path.parts):return False
    if name.startswith('data/'):
        return name=='data/observations/asos_119_20260701_20260831.json'
    if name.startswith('docs/'):
        return path.suffix.lower() in {'.md','.json','.png','.txt'}
    if name.startswith(('backend/','frontend/','scripts/','tests/')):return True
    return name in {'README.md','AGENTS.md','pyproject.toml','requirements.txt','.gitignore','Dockerfile','render.yaml','vercel.json','docker-compose.yml'}

def build():
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    names=sorted(name for name in tracked if name and allowed(name))
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    target=ROOT/'data/output/ai-review/HeatTime-AI-review.zip';target.parent.mkdir(parents=True,exist_ok=True)
    entries=[]
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names:
            payload=(ROOT/name).read_bytes()
            entries.append({'path':name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
            archive.writestr(name,payload)
        manifest={'repository_commit':revision,'purpose':'Local independent AI review; not uploaded or independently certified.',
                  'excluded':'All .env files, raw API samples, local databases/runtime records, untracked files, provided DOCX and generated PDF/PPTX.',
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
