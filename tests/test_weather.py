from dataclasses import replace
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3
import pytest
from backend.weather.grid import latlon_to_grid, grid_to_latlon
from backend.weather.cli import demo_venues, run
from backend.weather.adapters import (MockForecastAdapter, MockAsosAdapter, ManualInputAdapter,
                                     KmaForecastAdapter, AsosObservationAdapter, LiveIntegrationPending)
from backend.weather.storage import WeatherStore

DAY = date(2026, 8, 1)
CASES = json.loads((Path(__file__).parent / "grid_reference.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES)
def test_grid_matches_executed_official_reference(case):
    assert latlon_to_grid(case["lat"], case["lon"]) == (case["x"], case["y"])


@pytest.mark.parametrize("xy", [(1,1),(43,136),(61,120),(98,76),(149,253)])
def test_grid_centres_roundtrip(xy):
    assert latlon_to_grid(*grid_to_latlon(*xy)) == xy


@pytest.mark.parametrize("lat,lon", [(90,127),(float("nan"),127),(37,float("inf")),(0,0)])
def test_invalid_coordinates_rejected(lat,lon):
    with pytest.raises(ValueError):
        latlon_to_grid(lat,lon)


@pytest.mark.parametrize("xy", [(0,120),(61,254),(61.0,120)])
def test_invalid_grid_rejected(xy):
    with pytest.raises(ValueError):
        grid_to_latlon(*xy)


@pytest.mark.parametrize("provider,source", [("forecast","kma_fcst"),("asos","asos_obs")])
def test_three_venues_full_day_sqlite_and_idempotence(tmp_path,provider,source):
    db = tmp_path / "weather.sqlite3"
    assert run(DAY,db,provider)["stored_for_day"] == 72
    assert run(DAY,db,provider)["stored_for_day"] == 72
    store = WeatherStore(db)
    points = store.load_weather(source=source,is_mock=True)
    for venue in demo_venues():
        subset = [p for p in points if p.venue_id == venue.id]
        assert len(subset) == 24
        assert [p.valid_time.hour for p in subset] == list(range(24))
        assert all(p.valid_time.date() == DAY and p.valid_time.utcoffset().total_seconds() == 32400 for p in subset)
        assert all("가상 예시" in p.data_label for p in subset)
        assert all((p.solar_wm2 is not None) == (provider == "asos") for p in subset)
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM weather_points").fetchone()[0] == 72
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_forecast_observation_and_real_mock_kept_separate(tmp_path):
    store = WeatherStore(tmp_path / "weather.sqlite3")
    venue = demo_venues()[0]
    store.save_venues([venue])
    fcst = MockForecastAdapter().fetch(venue,DAY)
    obs = MockAsosAdapter().fetch(venue,"mock-station",DAY)
    store.save_weather(fcst + obs + [replace(fcst[0],is_mock=False)])
    assert len(store.load_weather(source="kma_fcst",is_mock=True)) == 24
    assert len(store.load_weather(source="asos_obs",is_mock=True)) == 24
    assert len(store.load_weather(source="kma_fcst",is_mock=False)) == 1


def test_equivalent_timezones_do_not_duplicate(tmp_path):
    store = WeatherStore(tmp_path / "weather.sqlite3")
    venue = demo_venues()[0]
    store.save_venues([venue])
    p = MockForecastAdapter().fetch(venue,DAY)[0]
    store.save_weather([p,replace(p,valid_time=p.valid_time.astimezone(timezone.utc))])
    assert len(store.load_weather(source="kma_fcst",is_mock=True)) == 1


def test_failed_batch_rolls_back(tmp_path):
    store = WeatherStore(tmp_path / "weather.sqlite3")
    venue = demo_venues()[0]
    store.save_venues([venue])
    p = MockForecastAdapter().fetch(venue,DAY)[0]
    with pytest.raises(sqlite3.IntegrityError):
        store.save_weather([p,replace(p,venue_id="unknown")])
    assert store.load_weather(source="kma_fcst",is_mock=True) == []


def test_manual_wbgt_persisted_without_fabricated_air_temperature(tmp_path):
    store = WeatherStore(tmp_path / "weather.sqlite3")
    venue = demo_venues()[0]
    store.save_venues([venue])
    time = datetime(2026,8,1,5,tzinfo=timezone.utc)
    m = ManualInputAdapter().enter(venue.id,time,31.2,is_mock=True)
    row_id = store.save_manual(m)
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM manual_measurements WHERE id=?",[row_id]).fetchone()
        assert row["wbgt_c"] == 31.2
        assert row["valid_time"] == "2026-08-01T14:00:00+09:00"
        assert conn.execute("SELECT COUNT(*) FROM weather_points").fetchone()[0] == 0


@pytest.mark.parametrize("changes", [{"rh_pct":101},{"ws_ms":-1},{"ta_c":float("nan")},
                                     {"solar_wm2":-1},{"valid_time":datetime(2026,8,1)}])
def test_invalid_weather_rejected(changes):
    p = MockForecastAdapter().fetch(demo_venues()[0],DAY)[0]
    with pytest.raises(ValueError):
        replace(p,**changes)


def test_live_adapters_fail_explicitly_without_network(monkeypatch):
    import socket
    def blocked(*args, **kwargs):
        raise AssertionError("Network should not be used")
    monkeypatch.setattr(socket,"socket",blocked)
    venue = demo_venues()[0]
    with pytest.raises(LiveIntegrationPending):
        KmaForecastAdapter().fetch(venue,DAY)
    with pytest.raises(LiveIntegrationPending):
        AsosObservationAdapter().fetch(venue,"user-confirmed-station",DAY)


def test_mock_run_never_reads_env_or_network(tmp_path,monkeypatch):
    import builtins, socket
    original = builtins.open
    original_path = Path.open
    def guarded(file,*args,**kwargs):
        if Path(file).name == ".env":
            raise AssertionError(".env must not be read")
        return original(file,*args,**kwargs)
    def guarded_path(self,*args,**kwargs):
        if self.name == ".env":
            raise AssertionError(".env must not be read")
        return original_path(self,*args,**kwargs)
    def blocked(*args,**kwargs):
        raise AssertionError("No network in mock mode")
    monkeypatch.setattr(builtins,"open",guarded)
    monkeypatch.setattr(Path,"open",guarded_path)
    monkeypatch.setattr(socket,"socket",blocked)
    assert run(DAY,tmp_path / "offline.sqlite3","forecast")["stored_for_day"] == 72
