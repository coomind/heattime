"""AWS 1.1 minute observations. Contract: docs/kma/aws-minute-spec.md.

Only the user-triggered API path loads a credential. No response text, request
URL, headers, or exception message is emitted, persisted, or returned.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import math
import os
import threading
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from backend.weather.models import KST, WeatherPoint

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = 'https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min'
FIELDS = 'YYMMDDHHMI STN WD1 WS1 WDS WSS WD10 WS10 TA RE RN-15m RN-60m RN-12H RN-DAY HM PA PS TD'.split()
MAX_RESPONSE_BYTES = 1024 * 1024
DAILY_CALLS = 20000
DAILY_BYTES = 5_000_000_000
INTERVAL_SECONDS = 60


class LiveFailure(Exception):
    def __init__(self, stage, message, http_status=None, exception_class=None):
        super().__init__(message)
        self.details = {'stage': stage, 'message': message,
                        'http_status': http_status, 'exception_class': exception_class}


def load_key(root=ROOT):
    """Runtime only. Tests supply a temporary root or inject a separate loader."""
    value = os.environ.get('KMA_APIHUB_KEY', '').strip()
    if not value:
        try:
            with (Path(root) / '.env').open(encoding='utf-8-sig') as handle:
                for line in handle:
                    name, sep, text = line.strip().partition('=')
                    if sep and name.strip() == 'KMA_APIHUB_KEY':
                        value = text.strip().strip('"\'')
                        break
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError) as exc:
            raise LiveFailure('키 로드', '프로젝트 루트의 키 설정을 읽을 수 없습니다.', exception_class=type(exc).__name__) from None
    if not value:
        raise LiveFailure('키 로드', '키를 찾지 못함 · 프로젝트 루트 .env의 KMA_APIHUB_KEY를 확인하세요.')
    return value


class NoRedirect(HTTPRedirectHandler):
    # A redirect must never forward the credential-bearing query to another host.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_bytes(key, station):
    query = urlencode({'stn': station, 'disp': 0, 'help': 0, 'authKey': key})
    req = Request(ENDPOINT + '?' + query)
    try:
        with build_opener(NoRedirect()).open(req, timeout=10) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise LiveFailure('HTTP 응답', '응답 크기가 앱의 단일 응답 제한을 초과했습니다.', response.status)
            return body
    except HTTPError as exc:
        messages = {401: '인증키를 확인하세요.', 403: 'AWS 매분자료 1.1 활용신청을 확인하세요.'}
        raise LiveFailure('HTTP 응답', messages.get(exc.code, '기상청 응답이 정상 상태가 아닙니다.'), exc.code, type(exc).__name__) from None
    except LiveFailure:
        raise
    except Exception as exc:
        raise LiveFailure('네트워크 연결', '기상청에 연결하지 못했습니다.', exception_class=type(exc).__name__) from None


@dataclass(frozen=True)
class AwsObservation:
    station_id: int
    valid_time: datetime
    fetched_at: datetime
    ta_c: float
    rh_pct: float
    ws_ms: float
    station_pressure_hpa: float | None
    sea_level_pressure_hpa: float | None
    rain_60m_mm: float | None
    is_mock: bool = False

    def point(self, venue_id):
        return WeatherPoint(venue_id=venue_id, valid_time=self.valid_time, fetched_at=self.fetched_at,
            source='aws_obs', ta_c=self.ta_c, rh_pct=self.rh_pct, ws_ms=self.ws_ms,
            sky_code=None, pty_code=None, solar_wm2=None, is_mock=self.is_mock,
            station_id=str(self.station_id), rain_mm=self.rain_60m_mm,
            provenance={'service': 'AWS 매분자료 1.1', 'station_name': '수원' if self.station_id == 119 else '',
                'wind_field': 'WS10', 'wind_average_minutes': 10,
                'observed_station_pressure_hpa': self.station_pressure_hpa,
                'observed_sea_level_pressure_hpa': self.sea_level_pressure_hpa,
                'radiation_observed': False, 'cloud_observed': False})


def parse_observation(body, station, fetched_at):
    """Strict documented 18-column format. Never return untrusted text errors."""
    try:
        text = body.decode('utf-8-sig')
        header = False
        rows = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('#'):
                fields = stripped.lstrip('#').split()
                if fields and fields[0] in ('YYMMDDHHMI', 'TM'):
                    if fields[1:] != FIELDS[1:]:
                        raise ValueError()
                    header = True
                continue
            if not stripped:
                continue
            parts = stripped.split()
            if not header or len(parts) != 18 or len(parts[0]) != 12 or not parts[0].isdigit():
                raise ValueError()
            valid_time = datetime.strptime(parts[0], '%Y%m%d%H%M').replace(tzinfo=KST)
            stn = int(parts[1])
            values = [float(value) for value in parts[2:]]
            if not all(math.isfinite(value) for value in values):
                raise ValueError()
            if stn != station:
                continue
            def field(name):
                value = values[FIELDS.index(name)-2]
                return None if value <= -50 else value
            ta, rh, ws = field('TA'), field('HM'), field('WS10')
            if None in (ta, rh, ws):
                raise LiveFailure('응답 파싱', '최신 관측의 기온·습도·풍속 중 결측이 있습니다.')
            observation = AwsObservation(stn, valid_time, fetched_at, ta, rh, ws, field('PA'), field('PS'), field('RN-60m'))
            observation.point('validation')  # Existing internal ranges, including zero.
            if valid_time > fetched_at + timedelta(minutes=1):
                raise ValueError()
            rows.append(observation)
        if not header or not rows:
            raise LiveFailure('응답 파싱', '요청 지점의 관측 자료가 없습니다. 최신 시각 자료가 아직 제공되지 않았을 수 있습니다.')
        return max(rows, key=lambda row: row.valid_time)
    except LiveFailure:
        raise
    except Exception as exc:
        raise LiveFailure('응답 파싱', '공식 18개 필드·단위·시간 형식과 맞지 않는 응답입니다.', exception_class=type(exc).__name__) from None


class LiveProvider:
    """One request shared by venues; persistent local daily budget and cooldown."""
    def __init__(self, repo, key_loader=load_key, transport=request_bytes, clock=None):
        self.repo = repo
        self.key_loader = key_loader
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(KST))
        self.lock = threading.Lock()
        self.cache = {}
        self.last_errors = {}
        with repo.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS live_usage(day TEXT PRIMARY KEY,calls INTEGER NOT NULL,bytes INTEGER NOT NULL,last_attempt REAL NOT NULL)')

    def usage(self, now):
        with self.repo.connect() as conn:
            row = conn.execute('SELECT calls,bytes FROM live_usage WHERE day=?', (now.astimezone(KST).date().isoformat(),)).fetchone()
        return {'calls': row[0] if row else 0, 'bytes': row[1] if row else 0,
                'daily_call_limit': DAILY_CALLS, 'daily_byte_limit': DAILY_BYTES,
                'scope': '이 앱의 저장소 기준 · 계정 전체 사용량은 API허브에서 확인'}

    def get(self, station, mode='mock'):
        with self.lock:
            now = self.clock().astimezone(KST)
            if mode == 'mock':
                point = AwsObservation(station, now.replace(second=0,microsecond=0), now, 33, 60, 1.5, 1010, 1013, 0, True)
                return self.result('mock', point, now)
            if mode != 'api' or type(station) is not int or not 1 <= station <= 9999:
                raise ValueError('Invalid live mode/station')
            cached = self.cache.get(station)
            day = now.date().isoformat()
            error = None
            retry = 0
            try:
                # Checking the key never reserves a network call.
                key = self.key_loader()
                with self.repo.connect() as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    row = conn.execute('SELECT calls,bytes,last_attempt FROM live_usage WHERE day=?', (day,)).fetchone()
                    # Last previous day prevents midnight/restart bursts.
                    last = conn.execute('SELECT MAX(last_attempt) FROM live_usage').fetchone()[0]
                    retry = max(0, math.ceil(INTERVAL_SECONDS - (now.timestamp()-last))) if last is not None else 0
                    if retry:
                        previous_error=self.last_errors.get(station)
                        return self.result('error' if previous_error else ('cached' if cached else 'waiting'), cached, now, error=previous_error,retry_after=retry)
                    calls, size = row[:2] if row else (0, 0)
                    if calls >= DAILY_CALLS or size + MAX_RESPONSE_BYTES > DAILY_BYTES:
                        raise LiveFailure('호출 한도', '이 앱의 일일 호출·용량 제한에 도달했습니다. 다음 날 다시 시도하세요.')
                    # Reserve the entire bounded response; failures keep this
                    # conservative charge, successful reads replace it by size.
                    conn.execute('INSERT INTO live_usage VALUES(?,?,?,?) ON CONFLICT(day) DO UPDATE SET calls=excluded.calls,bytes=excluded.bytes,last_attempt=excluded.last_attempt', (day,calls+1,size+MAX_RESPONSE_BYTES,now.timestamp()))
                body = self.transport(key, station)
                # Never persist the body or key. Count the response before parsing.
                with self.repo.connect() as conn:
                    conn.execute('UPDATE live_usage SET bytes=bytes+? WHERE day=?', (min(len(body),MAX_RESPONSE_BYTES)-MAX_RESPONSE_BYTES,day))
                if len(body) > MAX_RESPONSE_BYTES:
                    raise LiveFailure('HTTP 응답', '응답 크기가 앱의 단일 응답 제한을 초과했습니다.')
                if key.encode() in body:
                    raise LiveFailure('응답 파싱', '응답에 인증 정보가 포함되어 처리를 중단했습니다.')
                cached = parse_observation(body, station, self.clock().astimezone(KST))
                self.cache[station] = cached
            except LiveFailure as exc:
                error = exc.details
            except Exception as exc:
                error = {'stage':'네트워크 연결', 'message':'관측 갱신에 실패했습니다.', 'http_status':None,'exception_class':type(exc).__name__}
            self.last_errors[station]=error
            return self.result('error' if error else 'ready', cached, self.clock().astimezone(KST), error=error, retry_after=retry)

    def result(self, status, observation, now, error=None, retry_after=0):
        return {'status':status, 'observation':asdict(observation) if observation else None,
                'checked_at':now, 'retry_after_seconds':retry_after,
                'error':error, 'usage':self.usage(now), 'refresh_interval_seconds':INTERVAL_SECONDS}
