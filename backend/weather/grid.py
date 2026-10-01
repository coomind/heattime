"""KMA LCC DFS transform, independently ported from official convertDfsGrid.
Source: https://www.weather.go.kr/w/resources/js/fn.js (2026-10-01).
Official domain: nx 1..149, ny 1..253. Coordinates returned at grid centre.
"""
import math

RE, GRID = 6371.00877, 5.0
SLAT1, SLAT2 = math.radians(30), math.radians(60)
OLON, OLAT = math.radians(126), math.radians(38)
XO, YO = 43, 136
SN = math.log(math.cos(SLAT1) / math.cos(SLAT2)) / math.log(
    math.tan(math.pi / 4 + SLAT2 / 2) / math.tan(math.pi / 4 + SLAT1 / 2))
SF = math.tan(math.pi / 4 + SLAT1 / 2) ** SN * math.cos(SLAT1) / SN
RO = (RE / GRID) * SF / math.tan(math.pi / 4 + OLAT / 2) ** SN


def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    if not (math.isfinite(lat) and math.isfinite(lon)) or not (-90 < lat < 90 and -180 <= lon <= 180):
        raise ValueError("Invalid latitude/longitude")
    ra = (RE / GRID) * SF / math.tan(math.pi / 4 + math.radians(lat) / 2) ** SN
    theta = math.radians(lon) - OLON
    if theta > math.pi:
        theta -= 2 * math.pi
    if theta < -math.pi:
        theta += 2 * math.pi
    theta *= SN
    nx = math.floor(ra * math.sin(theta) + XO + 0.5)
    ny = math.floor(RO - ra * math.cos(theta) + YO + 0.5)
    _validate_grid(nx, ny)
    return nx, ny


def _validate_grid(nx: int, ny: int) -> None:
    if type(nx) is not int or type(ny) is not int or not (1 <= nx <= 149 and 1 <= ny <= 253):
        raise ValueError("Outside KMA forecast grid: nx 1..149, ny 1..253")


def grid_to_latlon(nx: int, ny: int) -> tuple[float, float]:
    _validate_grid(nx, ny)
    xn, yn = nx - XO, RO - ny + YO
    ra = math.hypot(xn, yn)
    lat = 2 * math.atan(((RE / GRID) * SF / ra) ** (1 / SN)) - math.pi / 2
    lon = math.atan2(xn, yn) / SN + OLON
    return math.degrees(lat), math.degrees(lon)
