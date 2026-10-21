from datetime import date
import copy
import pytest
from lwbgt import calculate
from backend.repository import Repository
from backend.service import Service
from backend.engine.policy import classify, round_decision
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from scripts.wbgt_sanity import engine_input,variant_context


@pytest.fixture(scope='module')
def session(tmp_path_factory):
    svc=Service(Repository(tmp_path_factory.mktemp('sanity')/'audit.sqlite3'))
    return svc.replay(date(2026,7,9),mode='observed')


def test_analysis_classifies_displayed_rounded_value(session):
    # Real near-boundary observation: 27.99959... is shown as 28.0, so it is stage 3
    # (user decision B-6: the displayed 0.1℃ value decides the stage).
    t,m,v,risks,settings,engine=variant_context(session,3.75,True,{})
    zero=next(r for r in risks if r.valid_time.hour==0)
    exact=calculate(engine_input(zero)).wbgt_c+3.75+1.5
    assert 27.95<=exact<28 and zero.decision_wbgt_c==28.0
    assert zero.level==classify(28.0)==3


@pytest.mark.parametrize('offset,upper,shifts',[(0,True,{}),(2.5,False,{}),(3.75,True,{}),
    (2.5,True,{'mock-suwon-a':-1,'mock-suwon-c':1})])
def test_sensitivity_keeps_policies_operating_values_and_raw_session(session,offset,upper,shifts):
    before=copy.deepcopy(session)
    t,m,v,risks,settings,engine=variant_context(session,offset,upper,shifts)
    assert session==before
    assert t.age_group=='U12' and settings==ScheduleSettings() and engine==EngineSettings()
    assert settings.rest_by_age['U12']==60 and settings.time_limit_sec==10
    for r in risks:
        native=calculate(engine_input(r))
        exact=native.wbgt_c+offset+shifts.get(r.venue_id,0)
        decision=round_decision(exact+(1.5 if upper else 0))
        assert r.level==classify(decision,t.policy_id)
        assert r.wbgt_c==round(exact,3)
        assert r.decision_wbgt_c==decision


def test_baseline_variant_preserves_every_record(session):
    old=Service.context(session)[3]
    new=variant_context(session,2.5,False,{})[3]  # baseline = 2.5C offset, central estimate decides (2026-10-21)
    assert old==new


def test_unknown_venue_shift_is_rejected(session):
    with pytest.raises(ValueError,match='Unknown hypothetical venue ids'):
        variant_context(session,2.5,True,{'invented-site':1})
