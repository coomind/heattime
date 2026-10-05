"""Internal schema; these names are not claims about external API fields."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import math
from typing import Literal

KST = timezone(timedelta(hours=9))


def require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime required")


def finite_range(name: str, value: float, low: float, high: float) -> None:
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}")


@dataclass(frozen=True)
class Venue:
    id: str
    name: str
    lat: float
    lon: float
    surface: str = "natural_grass"
    shade: str = "none"
    field_offset_c: float = 2.5
    asos_station_id: str | None = None
    is_mock: bool = True
    has_lights: bool = False

    def __post_init__(self):
        if not self.id or not self.name:
            raise ValueError("Venue id/name required")
        finite_range("latitude", self.lat, -89.999, 89.999)
        finite_range("longitude", self.lon, -180, 180)
        finite_range("field offset", self.field_offset_c, -20, 20)
        if self.surface not in {"artificial_turf", "natural_grass", "dirt", "indoor"}:
            raise ValueError("Invalid surface")
        if self.shade not in {"none", "partial", "full"}:
            raise ValueError("Invalid shade")


@dataclass(frozen=True)
class WeatherPoint:
    venue_id: str
    valid_time: datetime
    source: Literal["kma_fcst", "asos_obs", "aws_obs"]
    ta_c: float
    rh_pct: float
    ws_ms: float
    sky_code: int | None
    pty_code: int | None
    solar_wm2: float | None
    fetched_at: datetime
    is_mock: bool
    station_id: str | None = None
    cloud_fraction: float | None = None
    rain_mm: float | None = None
    provenance: dict | None = None

    def __post_init__(self):
        require_aware(self.valid_time)
        require_aware(self.fetched_at)
        if not self.venue_id or self.source not in {"kma_fcst", "asos_obs", "aws_obs"}:
            raise ValueError("Invalid venue/source")
        finite_range("temperature", self.ta_c, -90, 65)
        finite_range("humidity", self.rh_pct, 0, 100)
        finite_range("wind", self.ws_ms, 0, 150)
        if self.solar_wm2 is not None:
            finite_range("solar irradiance", self.solar_wm2, 0, 1600)
        if self.cloud_fraction is not None:
            finite_range('observed cloud fraction', self.cloud_fraction, 0, 1)
        if self.rain_mm is not None:
            finite_range('observed precipitation', self.rain_mm, 0, 1000)
        # Code semantics must be checked against real samples before live ingestion.
        if self.sky_code is not None and self.sky_code not in {1, 3, 4}:
            raise ValueError("Invalid internal sky code")
        if self.pty_code is not None and (type(self.pty_code) is not int or self.pty_code < 0):
            raise ValueError("Invalid internal precipitation code")

    @property
    def data_label(self) -> str:
        if self.is_mock:
            return '가상 예시 · mock 합성 기상'
        if self.source in {'asos_obs', 'aws_obs'} and self.station_id:
            name = (self.provenance or {}).get('station_name', '')
            return f'기상청 관측 자료({name} {self.station_id}·{self.valid_time.astimezone(KST).date()})'
        return '기상 자료'


@dataclass(frozen=True)
class ManualMeasurement:
    # A measured WBGT is not air temperature and must not be stored as ta_c.
    venue_id: str
    valid_time: datetime
    wbgt_c: float
    entered_at: datetime
    is_mock: bool = False

    def __post_init__(self):
        require_aware(self.valid_time)
        require_aware(self.entered_at)
        if not self.venue_id:
            raise ValueError("Venue required")
        finite_range("measured WBGT", self.wbgt_c, -50, 65)
