"""Render page 1 of the pre-generated 8/10 operation record PDF (the same bytes the demo downloads) to PNG."""
import base64
import json
from pathlib import Path
import pymupdf as fitz  # PyMuPDF (dev dependency)

ROOT = Path(__file__).resolve().parents[2]
pdf = base64.b64decode(json.loads((ROOT/'frontend/src/demo/observed-snapshot-exports.json').read_text(encoding='utf-8'))['pdf_base64'])
out = ROOT/'recordings/assets'; out.mkdir(parents=True, exist_ok=True)
page = fitz.open(stream=pdf, filetype='pdf')[0]
page.get_pixmap(dpi=170).save(out/'pdf-page1.png')
print(out/'pdf-page1.png')
