"""Restore committed historical virtual regression fixtures; no solve/network/env."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def restore(root=ROOT):
    target=root/'data/output/wbgt-sanity';count=0
    with zipfile.ZipFile(root/'docs/wbgt-sanity/regression-fixtures.zip') as z:
        if z.testzip() is not None:raise ValueError('Damaged regression fixture archive')
        for entry in z.infolist():
            relative=Path(entry.filename)
            if relative.is_absolute() or '..' in relative.parts or relative.suffix!='.json':raise ValueError('Unexpected fixture path')
            path=target/relative
            if not path.exists():
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(entry));count+=1
    print({'restored_files':count,'scope':'historical virtual sensitivity regression inputs only'})
    return count

if __name__=='__main__':restore()
