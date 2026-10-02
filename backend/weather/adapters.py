"""Adapter boundary: live providers deliberately have no guessed wire schema."""
from datetime import date, datetime, timezone
import math
from typing import Protocol
from .grid import latlon_to_grid
from .models import Venue, WeatherPoint, ManualMeasurement, KST


class ForecastAdapter(Protocol):
    def fetch(self, venue: Venue, day: date) -> list[WeatherPoint]: ...


class ObservationAdapter(Protocol):
    def fetch(self, venue: Venue, station_id: str, day: date) -> list[WeatherPoint]: ...


class LiveIntegrationPending(RuntimeError):
    pass


class KmaForecastAdapter:
    def fetch(self, venue: Venue, day: date) -> list[WeatherPoint]:
        latlon_to_grid(venue.lat, venue.lon)
        # TODO: approved endpoint/auth, publication time, pagination, missing values,
        # response fields/units and error handling from official docs + data/samples/.
        raise LiveIntegrationPending("KMA integration pending official docs and redacted response samples")


class AsosObservationAdapter:
    def __init__(self, sample_path=None):
        self.sample_path = sample_path

    def fetch(self, venue: Venue, station_id: str, day: date) -> list[WeatherPoint]:
        if not station_id.strip():
            raise ValueError("Station id required")
        from .asos_samples import load_dataset
        try:
            dataset = load_dataset(self.sample_path)
        except FileNotFoundError:
            raise LiveIntegrationPending('ASOS observation sample not installed; no live request') from None
        if station_id != dataset.station_id:
            raise LiveIntegrationPending('No verified sample for this ASOS station; no live request')
        return dataset.fetch(venue, station_id, day)


def _mock_points(venue: Venue, day: date, source: str, station_id: str | None = None):
    fetched = datetime.now(timezone.utc)
    phase = sum(venue.id.encode("utf-8")) % 5 * 0.2
    result = []
    for hour in range(24):
        heat = math.cos((hour - 14) * math.pi / 12)
        daylight = max(0.0, math.sin((hour - 6) * math.pi / 12)) if 6 <= hour <= 18 else 0.0
        result.append(WeatherPoint(
            venue_id=venue.id, valid_time=datetime(day.year, day.month, day.day, hour, tzinfo=KST),
            source=source, ta_c=round(30 + 5 * heat + phase, 2),
            rh_pct=round(65 - 15 * heat, 2), ws_ms=round(1.5 + daylight, 2),
            sky_code=1 if source == "kma_fcst" else None,
            pty_code=0 if source == "kma_fcst" else None,
            solar_wm2=round(850 * daylight, 2) if source == "asos_obs" else None,
            fetched_at=fetched, is_mock=True, station_id=station_id))
    return result


class MockForecastAdapter:
    def fetch(self, venue: Venue, day: date) -> list[WeatherPoint]:
        latlon_to_grid(venue.lat, venue.lon)
        return _mock_points(venue, day, "kma_fcst")


class MockAsosAdapter:
    def fetch(self, venue: Venue, station_id: str, day: date) -> list[WeatherPoint]:
        if not station_id.strip():
            raise ValueError("Station id required")
        return _mock_points(venue, day, "asos_obs", station_id)


class ManualInputAdapter:
    def enter(self, venue_id: str, valid_time: datetime, wbgt_c: float, *, is_mock=False) -> ManualMeasurement:
        return ManualMeasurement(venue_id, valid_time, wbgt_c, datetime.now(timezone.utc), is_mock)
