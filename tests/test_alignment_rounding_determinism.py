"""D-1 solar interval alignment, B-6 displayed-value classification, reproducible schedules."""
from dataclasses import replace
from datetime import date, timedelta
import pytest
from backend.engine.policy import classify, policies, risk_level, round_decision
from backend.engine.solar import estimate_solar
from backend.engine.validate_solar import interval_estimates
from backend.repository import Repository
from backend.schedule.optimizer import Candidate, TIE_BREAK_RANGE, tie_break
from backend.service import Service
from backend.weather.asos_samples import load_dataset
from backend.weather.cli import demo_venues

V = demo_venues()[0]


@pytest.mark.parametrize('value,shown', [(27.95, 28.0), (27.949999, 27.9), (27.9499996, 28.0),
                                          (27.993, 28.0), (28.04999, 28.0), (30.428, 30.4), (0.05, 0.1)])
def test_round_decision_half_up_matches_frontend_rule(value, shown):
    assert round_decision(value) == shown


def test_stage_follows_displayed_one_decimal_value():
    # 27.993 is shown as 28.0, so the general policy (>=28) must say stage 3.
    # 2026-10-21 rule: the central estimate (first argument) decides; the upper bound is carried but not used.
    assert risk_level(27.993, 29.493, 'U12') == (3, 28.0)
    assert risk_level(27.949, 29.449, 'U12') == (2, 27.9)
    # Football uses strict exceedance on the same displayed value.
    assert risk_level(28.04, 28.04, 'adult', 'football') == (2, 28.0)
    assert risk_level(28.05, 28.05, 'adult', 'football') == (4, 28.1)
    for value in (20.95, 24.95, 27.95, 30.95):
        level, decision = risk_level(value, value, 'adult')
        assert level == classify(decision) and decision == round_decision(value)


def test_policy_boundaries_unchanged():
    assert policies()['general']['boundaries'] == [21, 25, 28, 31]
    assert (policies()['football']['cooling_above'], policies()['football']['postpone_above']) == (26, 28)


def test_risk_hour_uses_solar_interval_that_overlaps_the_match_window():
    data = load_dataset()
    points = data.fetch(V, '119', date(2026, 7, 10))
    for p in points[:-1]:
        start = p.valid_time
        assert p.provenance['solar_interval_start'] == start.isoformat()
        assert p.provenance['solar_interval_end'] == (start + timedelta(hours=1)).isoformat()
        row = data.rows[start + timedelta(hours=1)]
        if row.get('icsr') not in (None, ''):
            assert p.solar_wm2 == pytest.approx(float(row['icsr']) * 1_000_000 / 3600)
        else:
            assert p.solar_wm2 is None


def test_engine_estimate_and_comparison_use_the_same_interval():
    points = load_dataset().fetch(V, '119', date(2026, 7, 10))
    compared = interval_estimates(V, points)
    for p, value in zip(points, compared):
        assert estimate_solar(V, p).estimated_wm2 == pytest.approx(value, abs=1e-6)
    missing = [p for p in points if p.solar_wm2 is None]
    assert all(estimate_solar(V, p).used_wm2 == estimate_solar(V, p).estimated_wm2 for p in missing)


def test_tie_break_is_stable_and_below_one_cost_unit():
    from datetime import datetime
    from backend.weather.models import KST
    c = Candidate('g1-1', 'mock-suwon-a', datetime(2026, 7, 10, 7, 15, tzinfo=KST),
                  datetime(2026, 7, 10, 7, 50, tzinfo=KST), 3, 100, 35, [], 'shorten')
    assert tie_break(c) == tie_break(replace(c, heat_score=999)) and 0 <= tie_break(c) < TIE_BREAK_RANGE


def test_same_observed_input_gives_identical_schedule(tmp_path):
    svc = Service(Repository(tmp_path / 'det.sqlite3'))
    session = svc.replay(date(2026, 7, 10), mode='observed')
    first = svc.optimize(session['id'])
    second = svc.optimize(session['id'])
    assert first['cp_sat_status'] == 'OPTIMAL'
    key = lambda p: [(a['match_id'], a['venue_id'], a['start'], a['end']) for a in p['assignments']]
    assert key(first) == key(second)
    assert first['postponed'] == second['postponed']
    assert first['proposed_heat_score'] == second['proposed_heat_score']
