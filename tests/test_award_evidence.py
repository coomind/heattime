import json
import scripts.build_award_evidence as builder
import pytest
from scripts.build_award_evidence import junit_receipt, browser_receipt


@pytest.mark.parametrize('xml', ['<testsuites/>', '<testsuites><testcase><failure/></testcase></testsuites>',
                                '<testsuites><testcase><error/></testcase></testsuites>', '<testsuites><testcase><skipped/></testcase></testsuites>',
                                '<testsuites><testsuite failures="1"><testcase/></testsuite></testsuites>'])
def test_incomplete_junit_refused(tmp_path, xml):
    path=tmp_path/'test.xml';path.write_text(xml, encoding='utf-8')
    with pytest.raises(ValueError): junit_receipt(path)


def test_pytest_and_node_junit_shapes(tmp_path):
    path=tmp_path/'test.xml'
    path.write_text('<testsuites><testsuite time="2.5"><testcase/><testcase/></testsuite></testsuites>', encoding='utf-8')
    assert junit_receipt(path) == {'passed':2, 'failed':0, 'skipped':0, 'duration_seconds':2.5}
    path.write_text('<testsuites><testcase time="0.1"/><testcase time="0.2"/></testsuites>', encoding='utf-8')
    assert junit_receipt(path)['passed'] == 2
    assert junit_receipt(path)['duration_seconds'] == 0.3


@pytest.mark.parametrize('key', ['unexpected', 'flaky', 'skipped', 'expected'])
def test_unfinished_or_retried_browser_refused(tmp_path, key):
    stats={'expected':108, 'unexpected':0, 'flaky':0, 'skipped':0, 'duration':1000}
    stats[key]=0 if key=='expected' else 1
    path=tmp_path/'browser.json';path.write_text(json.dumps({'stats':stats}), encoding='utf-8')
    with pytest.raises(ValueError): browser_receipt(path)


def test_browser_duration_and_completed_count(tmp_path):
    stats={'expected':108, 'unexpected':0, 'flaky':0, 'skipped':0, 'duration':1234}
    path=tmp_path/'browser.json';path.write_text(json.dumps({'stats':stats}), encoding='utf-8')
    assert browser_receipt(path)['passed']==108
    assert browser_receipt(path)['duration_seconds']==1.234


def test_source_fingerprint_detects_code_change_but_never_opens_env(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    folder=tmp_path/'backend';folder.mkdir()
    (folder/'feature.py').write_text('version=1\n', encoding='utf-8')
    (folder/'.env').write_text('FAKE=not-a-key\n', encoding='utf-8')
    before=builder.source_fingerprint()
    (folder/'.env').write_text('FAKE=changed\n', encoding='utf-8')
    assert builder.source_fingerprint()==before
    (folder/'feature.py').write_text('version=2\n', encoding='utf-8')
    assert builder.source_fingerprint()!=before


def test_stale_source_stamp_rejected_before_receipt_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    output=tmp_path/'data/output';output.mkdir(parents=True)
    (output/'award-validation-source.json').write_text(json.dumps({'source_fingerprint':'old'}), encoding='utf-8')
    with pytest.raises(ValueError, match='코드'):
        builder.collect()


def test_collector_calls_presentation_check_without_writing_timing(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    monkeypatch.setattr(builder, 'source_fingerprint', lambda:'current')
    output=tmp_path/'data/output';output.mkdir(parents=True)
    (output/'award-validation-source.json').write_text(json.dumps({'source_fingerprint':'current'}), encoding='utf-8')
    for name in ('award-validation-pytest.xml', 'award-validation-node.xml', 'award-validation-playwright.json'):
        (output/name).write_text('newer receipt', encoding='utf-8')
    def check(*, write_timing):
        assert write_timing is False
        raise RuntimeError('validated checker interface')
    monkeypatch.setattr(builder,'check_presentation',check)
    with pytest.raises(RuntimeError, match='validated checker interface'):
        builder.collect()
