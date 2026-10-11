"""Offline ASOS samples. Wire fields/units: supplied guide + verified samples.

Time/solar interval evidence is recorded in docs/kma/asos-observation-evidence.md.
No authentication, endpoint calls, .env loading, or synthetic substitution.
"""
from datetime import date, datetime, timedelta
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
from .models import KST, WeatherPoint

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT/'data/observations/asos_119_20260701_20260831.json'
OBS_FIELDS = ('tm', 'stnId', 'ta', 'taQcflg', 'hm', 'hmQcflg', 'ws', 'wsQcflg',
              'icsr', 'dc10Tca', 'rn', 'rnQcflg')
UNITS = {'ta': 'degC', 'hm': '%', 'ws': 'm/s', 'icsr': 'MJ/m2', 'dc10Tca': 'tenths', 'rn': 'mm'}


def numeric(row, name, required=False):
    flag = row.get(name+'Qcflg')
    if flag not in (None, '', '0'):
        if flag not in ('1', '9'):
            raise ValueError('Unknown ASOS quality flag; no inferred meaning')
        if required:
            raise ValueError('Required ASOS weather has an error/missing quality flag')
        return None
    value = row.get(name)
    if value is None or str(value).strip() == '':
        if required:
            raise ValueError('Required ASOS weather is missing; replay withheld')
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError('Invalid ASOS numeric field') from None
    if not math.isfinite(result):
        raise ValueError('Nonfinite ASOS numeric field')
    return result


class SampleDataset:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.name.lower().startswith('.env'):
            raise ValueError('Credential files are not observation samples')
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw)
        self.station_id = str(payload['station']['id'])
        table = json.loads((ROOT/'docs/kma/asos-stations.json').read_text(encoding='utf-8'))
        station = next((s for s in table['stations'] if s['id'] == self.station_id), None)
        if station is None:
            raise ValueError('ASOS station not confirmed by the supplied guide')
        self.station = station
        self.start = date.fromisoformat(payload['start_date'])
        self.end = date.fromisoformat(payload['end_date'])
        self.fetched_at = datetime.fromisoformat(payload['retrieved_at'])
        if self.fetched_at.utcoffset() is None:
            raise ValueError('ASOS retrieval timestamp must contain its timezone')
        if payload.get('units', UNITS) != UNITS:
            raise ValueError('ASOS units differ from the verified sample contract')
        self.original_sha256 = payload.get('original_sha256', self.sha256)
        if len(self.original_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.original_sha256):
            raise ValueError('Invalid observation fingerprint')
        self.rows = {}
        for original in payload['records']:
            row = {k: original[k] for k in OBS_FIELDS if k in original}
            try:
                stamp = datetime.strptime(row['tm'], '%Y-%m-%d %H:%M').replace(tzinfo=KST)
            except (ValueError, KeyError, TypeError):
                raise ValueError('ASOS time must match the provided hourly sample') from None
            if stamp.minute or row.get('stnId') != self.station_id:
                raise ValueError('ASOS sample station/hour mismatch')
            if not self.start <= stamp.date() <= self.end or stamp in self.rows:
                raise ValueError('ASOS sample dates/duplicate timestamps are invalid')
            self.rows[stamp] = row
        if len(self.rows) != payload['count']:
            raise ValueError('ASOS sample count does not match its records')

    def normalized(self):
        return {'source': '기상청 ASOS 시간자료 조회서비스', 'station': self.station,
                'start_date': self.start.isoformat(), 'end_date': self.end.isoformat(),
                'retrieved_at': self.fetched_at.isoformat(), 'count': len(self.rows),
                'units': UNITS, 'original_sha256': self.original_sha256,
                'time_basis': 'KST', 'solar_interval': 'preceding one hour ending at tm',
                'evidence': 'docs/kma/asos-observation-evidence.md',
                'records': [self.rows[t] for t in sorted(self.rows)]}

    @property
    def dates(self):
        return sorted({t.date() for t in self.rows})

    def fetch(self, venue, station_id, day):
        if station_id != self.station_id:
            raise ValueError('Requested station has no matching observation sample')
        rows = [(t, r) for t, r in sorted(self.rows.items()) if t.date() == day]
        if len(rows) != 24 or {t.hour for t, _ in rows} != set(range(24)):
            raise ValueError('A complete 24-hour ASOS day is required; no mock substitution')
        points = []
        for stamp, row in rows:
            # Risk at hour h covers [h, h+1). icsr at tm is the preceding hour's energy,
            # so the interval-aligned solar/cloud/rain come from the row at h+1.
            end = stamp+timedelta(hours=1)
            solar_row = self.rows.get(end)
            energy = numeric(solar_row, 'icsr') if solar_row else None
            cloud = numeric(solar_row, 'dc10Tca') if solar_row else None
            rain = numeric(solar_row, 'rn') if solar_row else None
            if cloud is not None and not 0 <= cloud <= 10:
                raise ValueError('Observed ASOS cloud amount is outside 0..10')
            if rain is not None and rain < 0:
                raise ValueError('Negative ASOS precipitation is not treated as a known missing sentinel')
            provenance = {'station_name': self.station['name'], 'sample_sha256': self.sha256,
                'original_sample_sha256': self.original_sha256, 'time_basis': 'KST',
                'units': UNITS, 'solar_energy_mj_m2': energy,
                'solar_interval_start': stamp.isoformat(),
                'solar_interval_end': end.isoformat(),
                'solar_observation_tm': end.isoformat() if solar_row else None,
                'solar_interval_basis': 'risk hour [h, h+1) = icsr/cloud/rain reported at h+1',
                'solar_wm2_is_hour_mean': energy is not None,
                'quality_flags': {k: row.get(k) for k in ('taQcflg', 'hmQcflg', 'wsQcflg')}}
            points.append(WeatherPoint(venue.id, stamp, 'asos_obs', numeric(row, 'ta', True),
                numeric(row, 'hm', True), numeric(row, 'ws', True), None, None,
                None if energy is None else energy*1_000_000/3600, self.fetched_at, False,
                station_id, None if cloud is None else cloud/10, rain, provenance))
        return points


@lru_cache(maxsize=4)
def _cached_dataset(path, modified_ns, size):
    return SampleDataset(path)


def load_dataset(path=None):
    path = Path(path or DATASET)
    stat = path.stat()
    return _cached_dataset(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
