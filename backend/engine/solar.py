from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime, timedelta
import numpy as np
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


CLOUDS = {1: 0.25, 3: 0.7, 4: 0.95}


def interval_clear_means(lat: float, lon: float, starts, step_seconds=60):
    """Clear-sky GHI mean over [start, start+1h), midpoint integration.

    Shared by the engine (observed replay) and the observed solar comparison so
    both use the same hour interval as the ASOS icsr energy.
    """
    if step_seconds <= 0 or 3600 % step_seconds:
        raise ValueError('Integration step must divide an hour')
    n = 3600 // step_seconds
    times = pd.DatetimeIndex([start+timedelta(seconds=(j+.5)*step_seconds) for start in starts for j in range(n)])
    loc = Location(lat, lon, tz="Asia/Seoul", altitude=0)
    pos = loc.get_solarposition(times)
    clear = loc.get_clearsky(times, model="ineichen", solar_position=pos)
    ghi = np.maximum(0, clear.ghi.to_numpy()).reshape(len(starts), n)
    ghi[pos.apparent_zenith.to_numpy().reshape(len(starts), n) >= 90] = 0
    return ghi.mean(axis=1)


@lru_cache(maxsize=4096)
def interval_clear_mean(lat: float, lon: float, start: datetime) -> float:
    require_aware(start)
    return float(interval_clear_means(lat, lon, [start])[0])


def estimate_solar(venue: Venue, point: WeatherPoint, rain_attenuation=0.5) -> SolarEstimate:
    interval = (point.provenance or {}).get('solar_interval_start')
    if interval:
        start = datetime.fromisoformat(interval)
        zenith, _ = geometry(venue.lat, venue.lon, start+timedelta(minutes=30))
        clear = interval_clear_mean(venue.lat, venue.lon, start)
    else:
        zenith, clear = geometry(venue.lat, venue.lon, point.valid_time)
    assumptions = ["고도 0m 가정"]
    cloud = point.cloud_fraction if point.cloud_fraction is not None else CLOUDS.get(point.sky_code, 0.7)
    if point.cloud_fraction is not None:
        assumptions.append('ASOS 전운량(10분위)/10 사용; 예보 SKY 코드로 변환하지 않음')
    elif point.sky_code is None:
        assumptions.append("하늘상태 누락: 운량 0.7 가정")
    estimated = clear * (1 - 0.75 * cloud ** 3.4)
    if point.pty_code not in (0, None) or (point.rain_mm is not None and point.rain_mm > 0):
        estimated *= rain_attenuation
    if interval:
        assumptions.append('일사는 위험 구간 [정시, 정시+1h)의 시간평균: 관측은 다음 정시 icsr(직전 1시간 에너지)/3600초, '
                           '결측 시 같은 구간 맑은 하늘 평균에 다음 정시 운량·강수를 적용한 추정')
    elif zenith >= 90:
        estimated = 0.0
    used = point.solar_wm2 if point.solar_wm2 is not None else estimated
    source = "mock 합성 일사량" if point.is_mock and point.solar_wm2 is not None else (
        "관측 일사량" if point.solar_wm2 is not None else "일사량 추정")
    return SolarEstimate(zenith, clear, estimated, max(0, estimated * 0.75),
                         min(clear, estimated * 1.25), used, source, assumptions)
