from datetime import datetime, timedelta
from types import SimpleNamespace
from scripts.benchmark_schedule import tournament_16
from backend.schedule.optimizer import participants, optimize
from backend.schedule.models import ScheduleSettings
from backend.weather.models import KST


def test_benchmark_is_16_teams_two_days_and_unchanged_operating_values():
    t, teams, matches, venues = tournament_16()
    assert len(teams) == 16 and t.date_end-t.date_start == timedelta(days=1)
    assert len(matches) == 27 and len(venues) == 3
    assert participants(matches)['b-final'] == {team.id for team in teams}
    assert all(m.duration_min == 40 and m.half_break_min == 5 for m in matches)
    settings = ScheduleSettings()
    assert settings.time_limit_sec == 10 and settings.rest_by_age['U12'] == 60
    assert settings.open_hour == 7 and settings.close_hour == 20 and settings.cleanup_min == 5


def test_timing_metadata_does_not_change_allocation_or_constraints():
    t, teams, matches, venues = tournament_16()
    risks=[]
    for venue in venues:
        for hour in range(48):
            risks.append(SimpleNamespace(venue_id=venue.id,valid_time=datetime(2026,8,1,tzinfo=KST)+timedelta(hours=hour),
                wbgt_c=23.5,wbgt_low_c=22,wbgt_high_c=25,decision_wbgt_c=25,level=2))
    result = optimize(matches[:1],t,venues,risks)
    assert len(result.assignments) == 1 and not result.postponed and result.constraints_ok
    assert result.elapsed_sec > 0 and result.preparation_sec > 0 and result.solver_wall_sec > 0
    assert result.elapsed_sec >= result.preparation_sec + result.solver_wall_sec
