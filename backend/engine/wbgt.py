"""Liljegren via lwbgt; explicit fallback and recorded input assumptions."""
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
from lwbgt import Input, calculate
from backend.weather.models import Venue, WeatherPoint, ManualMeasurement, KST
from .solar import estimate_solar
from .policy import risk_level
from .settings import EngineSettings


@dataclass(frozen=True)
class RiskEstimate:
    venue_id: str
    valid_time: datetime
    wbgt_c: float
    wbgt_low_c: float
    wbgt_high_c: float
    level: int
    decision_wbgt_c: float
    method_version: str
    inputs_hash: str
    is_mock: bool
    inputs: dict
    label: str = "WBGT 추정 · 의사결정 보조"


def wind_at_2m(speed: float, exponent=0.2):
    return speed * (2 / 10) ** exponent


def simple_wbgt(ta, rh, wind, solar):
    # Stull (2011) wet-bulb approximation, outside nominal domain disclosed.
    wet = (ta * math.atan(0.151977 * math.sqrt(rh + 8.313659)) + math.atan(ta + rh)
           - math.atan(rh - 1.676331) + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh) - 4.686035)
    return 0.7 * wet + 0.3 * ta + 0.002 * solar / math.sqrt(max(wind, 0.5))


def estimate(venue: Venue, point: WeatherPoint, age_group="U12", policy_id="general",
             settings: EngineSettings | None = None, calibration: tuple[float, float] | None = None,
             force_fallback=False) -> RiskEstimate:
    settings = settings or EngineSettings()
    solar = estimate_solar(venue, point, settings.rain_attenuation)
    # Indoor/full shade excludes direct solar; partial shade conservatively retains full irradiance.
    irradiance = 0 if venue.surface == "indoor" or venue.shade == "full" else solar.used_wm2
    speed = wind_at_2m(point.ws_ms, settings.wind_exponent)
    t = point.valid_time.astimezone(KST)
    assumptions = solar.assumptions + [f"기압 {settings.pressure_hpa} hPa 해수면 스크리닝 가정", "풍속 10m 입력 가정"]
    method = "liljegren-lwbgt-1.0.1"
    fallback_reason = None
    try:
        if force_fallback:
            raise ValueError("Explicit fallback request")
        output = calculate(Input(t.year,t.month,t.day,t.hour,t.minute,9,0,1,
            venue.lat,venue.lon,irradiance,settings.pressure_hpa,point.ta_c,
            max(point.rh_pct, 0.01),max(speed, 0.13),2.0,1.0))
        if output.status != 0 or not math.isfinite(output.wbgt_c):
            raise ValueError(f"Liljegren status={output.status}")
        value = output.wbgt_c
    except (ValueError, RuntimeError, OSError) as exc:
        value = simple_wbgt(point.ta_c, point.rh_pct, speed, irradiance)
        method = "simple-stull-solar-v1 · 간이 추정"
        fallback_reason = str(exc)
    value += venue.field_offset_c + settings.surface_offsets.get(venue.surface, 0)
    width = settings.uncertainty_c
    if calibration:
        value += calibration[0]
        width = max(width, calibration[1])
    low, high = value - width, value + width
    level, decision = risk_level(value, high, age_group, policy_id, settings.age_escalation)
    inputs = {"weather": asdict(point), "venue": asdict(venue), "settings":settings.model_dump(),
              "solar":asdict(solar), "wind_2m_ms":speed, "policy_id":policy_id,"age_group":age_group,
              "calibration":calibration,"assumptions":assumptions,"fallback_reason":fallback_reason}
    digest = hashlib.sha256(json.dumps(inputs,default=str,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return RiskEstimate(venue.id,t,round(value,3),round(low,3),round(high,3),level,
                        decision,method,digest,point.is_mock,inputs)


def estimate_series(venue, points, age_group="U12", policy_id="general", settings=None, manual=()):
    points = sorted(points, key=lambda p:p.valid_time)
    measurements = sorted((m for m in manual if m.venue_id == venue.id), key=lambda m:m.valid_time)
    raw = [estimate(venue,p,age_group,policy_id,settings) for p in points]
    calibrations = []
    for m in measurements:
        compatible = [r for r in raw if r.is_mock == m.is_mock and r.valid_time <= m.valid_time]
        if not compatible:
            continue
        reference = compatible[-1]
        if (m.valid_time - reference.valid_time).total_seconds() > 3600:
            continue
        residual = m.wbgt_c - reference.wbgt_c
        calibrations.append((m.valid_time,residual,abs(residual),m.is_mock))
    result = []
    for p,r in zip(points,raw):
        applicable = [c for c in calibrations if c[0] <= p.valid_time and c[3] == p.is_mock]
        result.append(estimate(venue,p,age_group,policy_id,settings,applicable[-1][1:3]) if applicable else r)
    return result
