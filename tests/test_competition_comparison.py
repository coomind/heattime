from copy import deepcopy
from datetime import date
import json
from types import SimpleNamespace

import pytest

from backend.repository import Repository
from backend.service import Service
from backend.schedule.optimizer import optimize
from scripts.compare_schedule_methods import candidates, compare_day, digest, input_digest, summarize, verify_assignments

ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def evidence():
    ledger = json.loads((ROOT/'docs/competition-evidence/frozen-solutions.json').read_text(encoding='utf-8'))
    results = json.loads((ROOT/'docs/competition-evidence/method-comparison.json').read_text(encoding='utf-8'))
    return ledger, results


@pytest.fixture(scope='module')
def service(tmp_path_factory):
    return Service(Repository(tmp_path_factory.mktemp('competition')/'fresh.sqlite3'))


@pytest.mark.parametrize('index', range(62))
def test_every_frozen_comparison_uses_identical_inputs_and_satisfies_original_constraints(index,evidence,service):
    ledger, result = evidence
    frozen, row = ledger['days'][index], result['days'][index]
    session = service.replay(date.fromisoformat(row['date']),mode='observed')
    assert input_digest(session) == frozen['input_sha256']
    baseline = SimpleNamespace(assignments=candidates(row['greedy_assignments']),
                               postponed=row['greedy_postponed_reasons'],elapsed_sec=row['greedy_elapsed_sec'])
    verified = compare_day(session,frozen,baseline)
    assert verified == row
    assert row['cp_assigned']+row['cp_postponed']==15
    assert row['greedy_assigned']+row['greedy_postponed']==15
    assert row['constraints_ok']
    assert set(row['common_match_ids']) == {r['match_id'] for r in frozen['assignments']} & {r['match_id'] for r in row['greedy_assignments']}


def test_published_totals_include_all_dates_and_both_favorable_and_unfavorable_exposure(evidence):
    ledger, result = evidence
    original = json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))
    assert [r['date'] for r in result['days']] == [r['date'] for r in original['days']]
    assert result['summary'] == summarize(result['days'])
    assert result['frozen_solutions_sha256'] == digest(ledger)
    assert result['original_sample_sha256'] == original['original_sample_sha256']
    for frozen,row in zip(ledger['days'],original['days']):
        assert frozen['date']==row['date']
        assert len(frozen['assignments'])==row['assigned']
        assert len(frozen['postponed'])==row['postponed']
        assert frozen['solver']==row['solver']


def test_greedy_comparator_is_the_unchanged_existing_fallback(evidence,service):
    ledger, result = evidence
    row = next(r for r in result['days'] if r['date']=='2026-07-10')
    session = service.replay(date(2026,7,10),mode='observed')
    t,m,v,r,settings,engine = Service.context(session)
    baseline = optimize(m,t,v,r,settings,engine,force_greedy=True)
    frozen = next(r for r in ledger['days'] if r['date']==row['date'])
    fresh = compare_day(session,frozen,baseline)
    assert {k:v for k,v in fresh.items() if k!='greedy_elapsed_sec'} == {k:v for k,v in row.items() if k!='greedy_elapsed_sec'}


@pytest.mark.parametrize('field,value', [('duration_min',1),('heat_score',-1),('action','none')])
def test_forged_assignment_duration_cost_or_action_is_rejected(field,value,evidence,service):
    ledger, _ = evidence
    frozen = next(r for r in ledger['days'] if r['date']=='2026-07-10')
    session = service.replay(date(2026,7,10),mode='observed')
    rows=deepcopy(frozen['assignments']);rows[0][field]=value
    with pytest.raises(ValueError,match='differs from current unchanged policy/score'):
        verify_assignments(rows,session)


def test_missing_postponement_coverage_is_rejected(evidence,service):
    ledger,result=evidence
    frozen=next(r for r in ledger['days'] if r['date']=='2026-08-06')
    row=next(r for r in result['days'] if r['date']==frozen['date'])
    session=service.replay(date(2026,8,6),mode='observed')
    baseline=SimpleNamespace(assignments=[],postponed=row['greedy_postponed_reasons'],elapsed_sec=0)
    with pytest.raises(ValueError,match='Coverage/postponement mismatch'):
        compare_day(session,{**frozen,'postponed':[]},baseline)


def test_saved_cooling_break_times_restore_as_aware_datetimes(evidence):
    ledger,_=evidence
    row=next(a for day in ledger['days'] for a in day['assignments'] if a['cooling_times'])
    restored=candidates([row])[0]
    assert [time.isoformat() for time in restored.cooling_times]==row['cooling_times']
    assert all(time.utcoffset() is not None for time in restored.cooling_times)
