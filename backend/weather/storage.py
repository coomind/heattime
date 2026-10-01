"""SQLite persistence with provenance, timezone normalisation and atomic upserts."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import sqlite3
from .grid import latlon_to_grid
from .models import Venue, WeatherPoint, ManualMeasurement, KST

SCHEMA = """
CREATE TABLE IF NOT EXISTS venues (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
 kma_nx INTEGER NOT NULL, kma_ny INTEGER NOT NULL, surface TEXT NOT NULL,
 shade TEXT NOT NULL, field_offset_c REAL NOT NULL, asos_station_id TEXT,
 is_mock INTEGER NOT NULL CHECK(is_mock IN (0,1)));
CREATE TABLE IF NOT EXISTS weather_points (
 venue_id TEXT NOT NULL REFERENCES venues(id), valid_time TEXT NOT NULL,
 source TEXT NOT NULL CHECK(source IN ('kma_fcst','asos_obs')),
 ta_c REAL NOT NULL, rh_pct REAL NOT NULL CHECK(rh_pct BETWEEN 0 AND 100),
 ws_ms REAL NOT NULL CHECK(ws_ms >= 0), sky_code INTEGER, pty_code INTEGER,
 solar_wm2 REAL CHECK(solar_wm2 >= 0), fetched_at TEXT NOT NULL,
 is_mock INTEGER NOT NULL CHECK(is_mock IN (0,1)), station_id TEXT,
 PRIMARY KEY(venue_id,valid_time,source,is_mock));
CREATE TABLE IF NOT EXISTS manual_measurements (
 id INTEGER PRIMARY KEY AUTOINCREMENT, venue_id TEXT NOT NULL REFERENCES venues(id),
 valid_time TEXT NOT NULL, wbgt_c REAL NOT NULL, entered_at TEXT NOT NULL,
 is_mock INTEGER NOT NULL CHECK(is_mock IN (0,1)));
"""


class WeatherStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save_venues(self, venues: list[Venue]):
        with self.connect() as conn:
            for venue in venues:
                values = asdict(venue)
                values["kma_nx"], values["kma_ny"] = latlon_to_grid(venue.lat, venue.lon)
                self._upsert(conn, "venues", values, ["id"])

    @staticmethod
    def _upsert(conn, table, values, keys):
        # table/column identifiers are internal constants only, never user input.
        columns = list(values)
        updates = ','.join(f'{c}=excluded.{c}' for c in columns if c not in keys)
        sql = (f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
               f"ON CONFLICT ({','.join(keys)}) DO UPDATE SET {updates}")
        conn.execute(sql, list(values.values()))

    def save_weather(self, points: list[WeatherPoint]):
        with self.connect() as conn:
            for point in points:
                values = asdict(point)
                values["valid_time"] = point.valid_time.astimezone(KST).isoformat()
                values["fetched_at"] = point.fetched_at.astimezone(KST).isoformat()
                self._upsert(conn, "weather_points", values, ["venue_id", "valid_time", "source", "is_mock"])

    def load_weather(self, *, source: str, is_mock: bool, venue_id: str | None = None) -> list[WeatherPoint]:
        sql = "SELECT * FROM weather_points WHERE source=? AND is_mock=?"
        params = [source, int(is_mock)]
        if venue_id is not None:
            sql += " AND venue_id=?"
            params.append(venue_id)
        with self.connect() as conn:
            rows = conn.execute(sql + " ORDER BY venue_id,valid_time", params).fetchall()
        result = []
        for row in rows:
            values = dict(row)
            for key in ["valid_time", "fetched_at"]:
                values[key] = datetime.fromisoformat(values[key])
            values["is_mock"] = bool(values["is_mock"])
            result.append(WeatherPoint(**values))
        return result

    def save_manual(self, measurement: ManualMeasurement) -> int:
        values = asdict(measurement)
        for key in ["valid_time", "entered_at"]:
            values[key] = values[key].astimezone(KST).isoformat()
        with self.connect() as conn:
            columns = list(values)
            cursor = conn.execute(
                f"INSERT INTO manual_measurements ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                list(values.values()))
            return cursor.lastrowid
