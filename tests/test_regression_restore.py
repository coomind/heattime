import json
from pathlib import Path
import shutil
import zipfile
import scripts.prepare_regression_evidence as fixtures
import scripts.build_ai_review_bundle as builder

def test_historical_fixtures_restore_all_details_and_preserve_existing_local_file(tmp_path):
    source=Path(__file__).resolve().parents[1]/'docs/wbgt-sanity/regression-fixtures.zip'
    target=tmp_path/'docs/wbgt-sanity/regression-fixtures.zip';target.parent.mkdir(parents=True)
    shutil.copyfile(source,target)
    with zipfile.ZipFile(source) as z:
        assert len(z.namelist())==559 and z.testzip() is None
        assert len(json.loads(z.read('fresh-sessions.json')))==62
    assert fixtures.restore(tmp_path)==559
    existing=tmp_path/'data/output/wbgt-sanity/fresh-sessions.json';before=existing.read_bytes()
    assert fixtures.restore(tmp_path)==0 and existing.read_bytes()==before
    assert builder.allowed('docs/wbgt-sanity/regression-fixtures.zip')
    assert not builder.allowed('docs/private.zip')

def test_extracted_review_inventory_needs_no_git_and_still_excludes_secrets(tmp_path,monkeypatch):
    (tmp_path/'REVIEW-MANIFEST.json').write_text(json.dumps({'files':[{'path':'data/mock/venues.json'},{'path':'.env'}],'repository_commit':'fixture-commit'}),encoding='utf-8')
    def forbidden(*a,**k):raise AssertionError('Extracted review must not need Git')
    monkeypatch.setattr(builder.subprocess,'check_output',forbidden)
    names,revision=builder.inventory(tmp_path)
    assert revision=='fixture-commit'
    assert [n for n in names if builder.allowed(n)]==['data/mock/venues.json']
