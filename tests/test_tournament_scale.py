from datetime import date,timedelta
from pathlib import Path
import json
import pytest
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from backend.service import Service
from backend.weather.asos_samples import load_dataset
from scripts.analyze_tournament_scale import WINDOWS,NAMES,make_service,summary
from scripts.analyze_without_field import secondary_cost
from scripts.compare_schedule_methods import input_digest,verify_assignments

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def packet():return json.loads((ROOT/'docs/competition-evidence/tournament-scale-analysis.json').read_text(encoding='utf-8'))

@pytest.fixture(scope='module')
def service(tmp_path_factory):return make_service(tmp_path_factory.mktemp('scale')/'test.sqlite3')

def test_all_31_windows_cover_every_source_day_once_with_original_defaults(packet):
    dates=[date.fromisoformat(r[k]) for r in packet['cases'] for k in ('start','end')]
    assert dates==[date(2026,7,1)+timedelta(days=i) for i in range(62)]
    assert len(set(dates))==62 and len(packet['cases'])==31
    assert packet['original_sample_sha256']==load_dataset().original_sha256
    assert packet['engine_settings']==EngineSettings().model_dump()
    assert packet['schedule_settings']==ScheduleSettings().model_dump()
    assert packet['summary']==summary(packet['cases'])
    from scripts.check_tournament_scale import run
    assert run()['passed']

@pytest.mark.parametrize('index',range(31))
def test_every_larger_case_preserves_inputs_constraints_scores_coverage_and_actual_status(index,packet,service):
    row=packet['cases'][index];s=service.replay(WINDOWS[index],tournament_id='benchmark16',mode='observed')
    assert input_digest(s)==row['input_sha256']
    assert len(s['teams'])==16 and len(s['matches'])==27
    assert len(s['weather'])==len(s['risks'])==144
    assert row['end']==s['tournament']['date_end'] and row['source_label']==s['label']
    t,m,v,r,settings,engine=Service.context(s);by={match.id:match for match in m}
    cp=verify_assignments(row['engine']['assignments'],s)
    assert set(row['baselines'])==set(NAMES)
    best=min(row['baselines'],key=lambda n:(-row['baselines'][n]['assigned'],row['baselines'][n]['secondary_cost'],n))
    assert row['selected_baseline']==best
    for result in [row['engine'],*row['baselines'].values()]:
        selected=verify_assignments(result['assignments'],s)
        assert len({a.match_id for a in selected})==len(selected)==result['assigned']
        assert result['assigned']+result['postponed']==27
        assert result['secondary_cost']==int(sum(secondary_cost(a,by[a.match_id],settings) for a in selected))
    ids={a.match_id for a in cp};postponed={p['match_id'] for p in row['postponed']}
    assert not ids&postponed and ids|postponed==set(by)
    assert len(postponed)==len(row['postponed'])==row['engine']['postponed']
    assert all(p['reason'] for p in row['postponed'])
    common=ids&{a['match_id'] for a in row['baselines'][best]['assignments']}
    assert row['comparison']=={'common_match_ids':sorted(common),
        'assignment_gain':row['engine']['assigned']-row['baselines'][best]['assigned'],
        'engine_common_heat':sum(a.heat_score for a in cp if a.match_id in common),
        'baseline_common_heat':sum(a['heat_score'] for a in row['baselines'][best]['assignments'] if a['match_id'] in common)}
    assert row['coverage_optimal']==(row['solver']=='CP-SAT OPTIMAL')
    assert row['optimize_elapsed_sec']>=row['solver_wall_sec'] and row['optimize_elapsed_sec']>=row['preparation_sec']
    if row['coverage_optimal']:
        assert row['engine']['assigned']>=row['baselines'][best]['assigned']
        if row['engine']['assigned']==row['baselines'][best]['assigned']:
            assert row['engine']['secondary_cost']<=row['baselines'][best]['secondary_cost']
