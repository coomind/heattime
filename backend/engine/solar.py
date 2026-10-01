from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime
import pandas as pd
from pvlib.location import Location
from backend.weather.models import Venue, WeatherPoint, require_aware


@dataclass(frozen=True)
class SolarEstimate:
    zenith_deg: float
    clear_wm2: float
    estimated_wm2: float
    low_wm2: float
    high_wm2: float
    used_wm2: float
    source: str
    assumptions: list[str]


@lru_cache(maxsize=4096)
def geometry(lat: float, lon: float, time: datetime):
    require_aware(time)
    loc = Location(lat, lon, tz="Asia/Seoul", altitude=0)
    times = pd.DatetimeIndex([time])
    position = loc.get_solarposition(times)
    clear = loc.get_clearsky(times, model="ineichen", solar_position=position)
    return float(position.iloc[0].apparent_zenith), max(0, float(clear.iloc[0].ghi))


def estimate_solar(venue: Venue, point: WeatherPoint, rain_attenuation=0.5) -> SolarEstimate:
    zenith, clear = geometry(venue.lat, venue.lon, point.valid_time)
    assumptions = ["고도 0m 가정"]
    clouds = {1: 0.25, 3: 0.7, 4: 0.95}
    cloud = clouds.get(point.sky_code, 0.7)
    if point.sky_code is None:
        assumptions.append("하늘상태 누락: 운량 0.7 가정")
    estimated = clear * (1 - 0.75 * cloud ** 3.4)
    if point.pty_code not in (0, None):
        estimated *= rain_attenuation
    if zenith >= 90:
        estimated = 0.0
    used = point.solar_wm2 if point.solar_wm2 is not None else estimated
    source = "mock 합성 일사량" if point.is_mock and point.solar_wm2 is not None else (
        "관측 일사량" if point.solar_wm2 is not None else "일사량 추정")
    return SolarEstimate(zenith, clear, estimated, max(0, estimated * 0.75),
                         min(clear, estimated * 1.25), used, source, assumptions)
