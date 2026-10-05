from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts.check_no_field_evidence import validate_analysis,run
from scripts.build_award_evidence import markdown

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def sources():
    return [json.loads((ROOT/p).read_text(encoding='utf-8')) for p in (
        'docs/competition-evidence/no-field-analysis.json','docs/competition-evidence/frozen-solutions.json','frontend/src/demo/no-field-analysis.json')]

@pytest.mark.parametrize('case',['hash','date','cp','summary','best','score','ui'])
def test_new_claims_reject_corrupted_evidence_without_reducing_old_checks(sources,case):
    d,l,u=deepcopy(sources)
    if case=='hash':d['ledger_sha256']='changed'
    if case=='date':d['days'].pop()
    if case=='cp':d['days'][0]['cp']['assignments'][0]['start']='2026-07-01T00:00:00+09:00'
    if case=='summary':d['summary']['cp_assigned']+=1
    if case=='best':d['days'][0]['baselines']['best_of_four']['selected_method']='bad'
    if case=='score':d['days'][0]['comparisons']['earliest_input']['cp_common_heat']+=1
    if case=='ui':u['days'][0]['cp']['assigned']+=1
    with pytest.raises(ValueError):validate_analysis(d,l,u)

def test_actual_new_claims_and_manuscripts_pass_all_additional_checks(sources):
    validate_analysis(*sources)
    assert run()['passed']

def test_proof_pack_presents_stronger_comparison_and_hypothetical_limits():
    data=json.loads((ROOT/'docs/competition-evidence/verified-claims.json').read_text(encoding='utf-8'))
    # Existing final manifest is regenerated after full validation; use actual new source for this rendering check.
    data['no_field_analysis']=json.loads((ROOT/'docs/competition-evidence/no-field-analysis.json').read_text(encoding='utf-8'))['summary']
    body=markdown(data)
    assert all(t in body for t in ('558','562','5.15%','14→16','1.39%','재최적화'))
