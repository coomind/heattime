from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path
import socket
import pytest
from backend.weather.asos_samples import DATASET, OBS_FIELDS, SampleDataset, load_dataset, numeric
from backend.weather.adapters import AsosObservationAdapter, LiveIntegrationPending
from backend.weather.cli import demo_venues
from backend.weather.storage import WeatherStore
from backend.engine.solar import estimate_solar


@pytest.fixture(autouse=True)
def no_credentials_or_network(monkeypatch):
    original = Path.open
    def guarded(path, *args, **kwargs):
        if path.name == '.env':
            raise AssertionError('Credentials must not be read')
        return original(path, *args, **kwargs)
    def blocked(*args, **kwargs):
        raise AssertionError('No API connection in observation replay')
    monkeypatch.setattr(Path, 'open', guarded)
    monkeypatch.setattr(socket, 'create_connection', blocked)


def test_verified_sample_contract_and_all_days():
    dataset = load_dataset()
    assert dataset.original_sha256 == '3ec05108b47e104a4811a19bea81921c2d6e64e0008f8d3aa84a990605136ddf'
    assert dataset.station == {'id': '119', 'name': '수원', 'office': '수도권기상청'}
    assert len(dataset.rows) == 1488 and len(dataset.dates) == 62
    points = [p for day in dataset.dates for p in dataset.fetch(demo_venues()[0], '119', day)]
    assert sum(p.solar_wm2 is None for p in points) == 561
    assert sum(p.solar_wm2 is not None for p in points) == 927
    assert any(p.solar_wm2 == 0 for p in points)
    # Raw sample: 2 empty cloud rows. Risk hour h uses the h+1 row, so the final
    # hour (08-31 23:00) has no interval row and is also None.
    assert sum(numeric(r, 'dc10Tca') is None for r in dataset.rows.values()) == 2
    assert sum(p.cloud_fraction is None for p in points) == 3
    assert points[-1].provenance['solar_observation_tm'] is None and points[-1].solar_wm2 is None
    assert all(not p.is_mock and p.source == 'asos_obs' for p in points)
    assert all(p.valid_time.utcoffset() == timedelta(hours=9) for p in points)
    assert all(set(row) <= set(OBS_FIELDS) for row in dataset.rows.values())


def test_hour_energy_conversion_provenance_and_storage(tmp_path):
    venue = demo_venues()[0]
    points = AsosObservationAdapter().fetch(venue, '119', date(2026, 7, 1))
    noon = points[12]
    # Risk hour 12:00 covers [12:00, 13:00): icsr reported at 13:00 (its preceding hour).
    following = load_dataset().rows[noon.valid_time + timedelta(hours=1)]
    assert noon.solar_wm2 == pytest.approx(float(following['icsr']) * 1_000_000 / 3600)
    assert noon.cloud_fraction == pytest.approx(float(following['dc10Tca']) / 10)
    assert noon.provenance['solar_interval_start'] == '2026-07-01T12:00:00+09:00'
    assert noon.provenance['solar_interval_end'] == '2026-07-01T13:00:00+09:00'
    assert noon.provenance['solar_observation_tm'] == '2026-07-01T13:00:00+09:00'
    assert noon.provenance['units']['icsr'] == 'MJ/m2'
    assert noon.provenance['solar_wm2_is_hour_mean']
    assert noon.data_label == '기상청 관측 자료(수원 119·2026-07-01)'
    row = load_dataset().rows[noon.valid_time]
    assert (noon.ta_c, noon.rh_pct, noon.ws_ms) == tuple(float(row[k]) for k in ('ta', 'hm', 'ws'))
    store = WeatherStore(tmp_path / 'weather.sqlite3')
    store.save_venues([venue]); store.save_weather(points)
    restored = store.load_weather(source='asos_obs', is_mock=False)
    assert restored == points
    assert store.load_weather(source='asos_obs', is_mock=True) == []


def test_observed_cloud_used_without_invented_forecast_codes():
    venue = demo_venues()[0]
    point = AsosObservationAdapter().fetch(venue, '119', date(2026, 7, 1))[12]
    estimate = estimate_solar(venue, point)
    expected = estimate.clear_wm2 * (1 - .75 * point.cloud_fraction ** 3.4)
    if point.rain_mm is not None and point.rain_mm > 0:
        expected *= .5
    assert estimate.estimated_wm2 == pytest.approx(expected)
    assert point.sky_code is None and point.pty_code is None
    assert estimate.used_wm2 == point.solar_wm2
    assert any('시간평균' in a for a in estimate.assumptions)


@pytest.mark.parametrize('mutation', ['duplicate', 'time', 'count', 'units', 'missing', 'quality'])
def test_invalid_observations_never_fabricate_values(tmp_path, mutation):
    payload = json.loads(DATASET.read_text(encoding='utf-8'))
    if mutation == 'duplicate': payload['records'][1] = payload['records'][0]
    if mutation == 'time': payload['records'][0]['tm'] = '2026-07-01 00:30'
    if mutation == 'count': payload['count'] -= 1
    if mutation == 'units': payload['units']['icsr'] = 'W/m2'
    if mutation == 'missing': payload['records'][0]['ta'] = ''
    if mutation == 'quality': payload['records'][0]['taQcflg'] = '1'
    path = tmp_path / 'sample.json'; path.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError):
        SampleDataset(path).fetch(demo_venues()[0], '119', date(2026, 7, 1))


def test_unavailable_day_and_station_do_not_fall_back():
    adapter = AsosObservationAdapter(); venue = demo_venues()[0]
    with pytest.raises(ValueError): adapter.fetch(venue, '119', date(2026, 9, 1))
    with pytest.raises(LiveIntegrationPending): adapter.fetch(venue, '108', date(2026, 7, 1))
