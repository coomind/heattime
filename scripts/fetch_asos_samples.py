"""User-run ASOS downloader, solely based on docs/kma's supplied guide.

Importing does not read credentials, call the API, sleep, or create output files.
"""
import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from html import unescape
import json
import logging
import math
from pathlib import Path
import re
import sys
import time as clock
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus, unquote, urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
# Guide: 1.1 다.1.a Call Back URL. HTTPS support is not asserted by this guide.
ENDPOINT = 'http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList'
DEFAULT_STATION = '119'  # Guide attachment: 수원 / 수도권기상청.
FIELDS = (
    'tm rnum stnId stnNm ta taQcflg rn rnQcflg ws wsQcflg wd wdQcflg '
    'hm hmQcflg pv td pa paQcflg ps psQcflg ss ssQcflg icsr dsnw hr3Fhsc '
    'dc10Tca dc10LmcsCa clfmAbbrCd lcsCh vs gndSttCd dmstMtphNo ts tsQcflg '
    'm005Te m01Te m02Te m03Te'
).split()
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # Local memory guard, not a claimed API limit.


class FetchError(Exception):
    """Static exception text; selected body fields are redacted only at output."""
    def __init__(self, message, *, stage='응답 파싱', http_status=None, result_code=None,
                 result_msg=None, exception_class=None, key_missing=False):
        super().__init__(message)
        self.stage = stage
        self.http_status = http_status
        self.result_code = result_code
        self.result_msg = result_msg
        self.exception_class = exception_class or type(self).__name__
        self.key_missing = key_missing


class XmlResponse(bytes):
    """Bytes-compatible response retaining only the HTTP status, never headers/URL."""
    def __new__(cls, data, status):
        result = super().__new__(cls, data)
        result.http_status = status
        return result


def station_table():
    data = json.loads((ROOT / 'docs/kma/asos-stations.json').read_text(encoding='utf-8'))
    return {s['id']: s for s in data['stations']}


def read_api_key(path):
    """Only user-triggered main calls this with the project .env."""
    try:
        lines = path.read_text(encoding='utf-8-sig').splitlines()
    except OSError as error:
        raise FetchError('인증키 설정 파일을 읽지 못했습니다.', stage='키 로드',
                         exception_class=type(error).__name__,
                         key_missing=isinstance(error, FileNotFoundError)) from None
    values = []
    for line in lines:
        match = re.match(r'^\s*(?:export\s+)?KMA_API_KEY\s*=\s*(.*?)\s*$', line)
        if match:
            value = match[1]
            if value.startswith(('"', "'")):
                if len(value) < 2 or value[-1] != value[0]:
                    raise FetchError('KMA_API_KEY의 따옴표 설정을 확인하세요.', stage='키 로드')
                value = value[1:-1]
            values.append(value)
    if not values or (len(values) == 1 and not values[0]):
        raise FetchError('키를 찾지 못함', stage='키 로드', key_missing=True)
    if len(values) != 1 or any(c.isspace() for c in values[0]):
        raise FetchError('KMA_API_KEY는 비어 있지 않은 Decoding 키 한 개로 설정하세요.', stage='키 로드')
    return values[0]


def secret_variants(key):
    if not key:
        return set()
    values = {key, quote(key, safe=''), quote_plus(key, safe='')}
    # Also catch double encoding and lowercase percent escapes in unexpected echoes.
    values |= {quote(v, safe='') for v in list(values)}
    values |= {re.sub(r'%[0-9A-F]{2}', lambda m: m[0].lower(), v) for v in list(values)}
    return values


def redact_diagnostic(value, key=None):
    """Redact before truncating, including encoded echoes and header-like lines."""
    if value is None:
        return '없음'
    text = unescape(str(value))
    variants = secret_variants(key)
    if key:
        decoded = key
        for _ in range(3):
            decoded = unquote(decoded)
            if decoded:
                variants |= secret_variants(decoded)
    # Remove whole URLs before key placeholders could split them at a space.
    for _ in range(4):
        text = re.sub(r'(?i)\b[a-z][a-z0-9+.-]*://[^\s<>"\']+', '[URL 마스킹]', text)
        text = unquote(text)
    text = re.sub(r'(?i)\b[a-z][a-z0-9+.-]*://[^\s<>"\']+', '[URL 마스킹]', text)
    for secret in sorted(variants, key=len, reverse=True):
        text = text.replace(secret, '[키 마스킹]')
    text = re.sub(r'(?i)\bservicekey\s*=\s*[^\s&<>"\']*', '[인증정보 마스킹]', text)
    # Do not surface echoed request lines/headers, even with an unrelated token.
    text = re.sub(r'(?im)^\s*(?:GET|POST|HEAD|PUT|DELETE|OPTIONS)\s+[^\r\n]*', '[요청 마스킹]', text)
    text = re.sub(r'(?im)^\s*[\"\']?[a-z][a-z0-9_-]*[\"\']?\s*:[^\r\n]*', '[헤더 형태 값 마스킹]', text)
    text = re.sub(r'(?i)\b(?:request[-_ ]*)?headers?\b[\"\']?\s*[:=][^\r\n]*', '[헤더 마스킹]', text)
    text = re.sub(r'(?i)\b(?:authorization|proxy-authorization|cookie|host|user-agent|connection|content-[a-z-]+|accept(?:-[a-z-]+)?|x-[a-z0-9_-]+)[\"\']?\s*[:=][^\r\n]*', '[헤더 마스킹]', text)
    text = ''.join(c if c.isprintable() else ' ' for c in text)
    return ' '.join(text.split())[:1000] or '없음'


def response_error_fields(data):
    """Inspect present error leaves only; do not infer an alternate API schema."""
    if not isinstance(data, (bytes, bytearray)) or len(data) > MAX_RESPONSE_BYTES or b'<!DOCTYPE' in data.upper():
        return None, None
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError, UnicodeError):
        # Diagnostic-only lookup of the documented names; normal ingestion stays XML.
        try:
            pending = [json.loads(data)]
        except (ValueError, UnicodeError, RecursionError):
            return None, None
        found = {}
        for _ in range(2048):
            if not pending:
                break
            node = pending.pop()
            if isinstance(node, dict):
                for name, value in node.items():
                    if name in {'resultCode', 'resultMsg'} and isinstance(value, (str, int, float)):
                        found.setdefault(name, str(value))
                    elif isinstance(value, (dict, list)):
                        pending.append(value)
            elif isinstance(node, list):
                pending.extend(node)
        return found.get('resultCode'), found.get('resultMsg')
    codes = []; messages = []; documented = {}
    for node in root.iter():
        if len(node) or node.text is None:
            continue
        name = node.tag.rsplit('}', 1)[-1]
        value = node.text.strip()
        if name in {'resultCode', 'resultMsg'}:
            documented[name] = value
        # Generic XML error diagnostics: use names actually present, not a schema claim.
        elif name.lower().endswith('code'):
            codes.append(value)
        elif name.lower().endswith(('msg', 'message')):
            messages.append(value)
    return (documented.get('resultCode') or ' / '.join(codes) or None,
            documented.get('resultMsg') or ' / '.join(messages) or None)


def response_failure(data, status, exception_class='FetchError'):
    code, message = response_error_fields(data)
    return FetchError('API 오류 응답입니다.', stage='HTTP 응답', http_status=status,
                      result_code=code, result_msg=message, exception_class=exception_class)


def print_failure(error, key=None):
    status = error.http_status
    status = status if isinstance(status, int) and 100 <= status <= 599 else '없음'
    print(f'실패 단계: {error.stage}', file=sys.stderr)
    print(f'HTTP 상태 코드: {status}', file=sys.stderr)
    print(f'resultCode: {redact_diagnostic(error.result_code, key)}', file=sys.stderr)
    print(f'resultMsg: {redact_diagnostic(error.result_msg, key)}', file=sys.stderr)
    print(f'예외 클래스: {redact_diagnostic(error.exception_class, key)}', file=sys.stderr)


def print_key_info(key, stream=None, missing=False):
    length = len(key) if key is not None else (0 if missing else '확인 불가')
    percent = ('예' if '%' in key else '아니오') if key is not None else ('아니오' if missing else '확인 불가')
    print(f"키 길이: {length} / '%' 문자 포함: {percent}", file=stream)


def assert_safe(text, key):
    if any(v in text for v in secret_variants(key)) or re.search(r'https?://|servicekey\s*=', text, re.I):
        raise FetchError('응답 또는 출력에 인증정보나 URL이 포함되어 저장하지 않았습니다.')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not forward the credential to an undocumented redirect.


def request_xml(params, timeout=30):
    """Never print/store a request URL, raw response, or exception containing one."""
    status = None
    try:
        request = Request(ENDPOINT + '?' + urlencode(params), method='GET')
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            status = response.status
            data = response.read(MAX_RESPONSE_BYTES + 1)
        if status != 200:
            raise response_failure(data, status)
        if len(data) > MAX_RESPONSE_BYTES:
            raise FetchError('응답이 로컬 읽기 제한을 초과했습니다.', http_status=status)
        return XmlResponse(data, status)
    except HTTPError as error:
        try:
            data = error.read(MAX_RESPONSE_BYTES + 1)
        except Exception:
            data = b''
        finally:
            error.close()
        raise response_failure(data, error.code, type(error).__name__) from None
    except FetchError:
        raise
    except Exception as error:
        raise FetchError('API 통신에 실패했습니다.',
                         stage='네트워크 연결' if status is None else 'HTTP 응답',
                         http_status=status, exception_class=type(error).__name__) from None


@dataclass
class Page:
    number: int
    total: int
    records: list[dict]


def integer(node, field):
    try:
        value = int(node.findtext(field, '').strip())
        if value < 0:
            raise ValueError
        return value
    except (ValueError, AttributeError) as error:
        raise FetchError('응답 페이지 메타데이터 형식이 가이드와 다릅니다.',
                         exception_class=type(error).__name__) from None


def parse_page(data, key):
    if b'<!DOCTYPE' in data.upper():
        raise FetchError('지원하지 않는 XML 문서 선언입니다.')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise FetchError('응답이 가이드의 XML 형식과 다릅니다.',
                         exception_class=type(error).__name__) from None
    if root.tag != 'response' or root.find('header') is None:
        code, message = response_error_fields(data)
        if code is not None or message is not None:
            raise response_failure(data, getattr(data, 'http_status', None))
        raise FetchError('응답 구조가 가이드의 XML 예제와 다릅니다.')
    code = root.findtext('header/resultCode', '').strip()
    if code in {'03', '3'}:  # Guide error table: NODATA_ERROR.
        return Page(0, 0, [])
    if code not in {'00', '0'}:  # Table is 00; sample XML is 0.
        raise response_failure(data, getattr(data, 'http_status', None))
    body = root.find('body')
    if body is None or body.findtext('dataType', '').strip() != 'XML':
        raise FetchError('응답 body 또는 자료형이 가이드와 다릅니다.')
    records = []
    for item in body.findall('items/item'):
        row = {}
        for field in FIELDS:
            element = item.find(field)
            if element is not None:
                value = element.text or ''
                assert_safe(value, key)
                row[field] = value
        records.append(row)
    return Page(integer(body, 'pageNo'), integer(body, 'totalCount'), records)


def record_time(row):
    # Only the guide's field-table and XML-example formats. No timezone inference.
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H'):
        try:
            value = datetime.strptime(row.get('tm', ''), fmt)
            if value.minute == 0:
                return value
        except ValueError:
            pass
    raise FetchError('관측 일시가 가이드의 시간 표기와 다릅니다.')


class Downloader:
    def __init__(self, key, page_size=10, delay=0.2, transport=request_xml, sleep=clock.sleep):
        self.key = key
        self.page_size = page_size
        self.delay = delay
        self.transport = transport
        self.sleep = sleep
        self.calls = 0
        self.last_response = None

    def fetch(self, station, start, end):
        try:
            return self._fetch(station, start, end)
        except FetchError as error:
            self.attach_response(error)
            raise

    def attach_response(self, error):
        if self.last_response is not None:
            code, message = response_error_fields(self.last_response)
            if error.http_status is None:
                error.http_status = getattr(self.last_response, 'http_status', None)
            if error.result_code is None:
                error.result_code = code
            if error.result_msg is None:
                error.result_msg = message

    def read_page(self, station, start, end, page_number):
        self.last_response = None  # Never attach the previous page's status to a connection failure.
        if self.calls:
            self.sleep(self.delay)
        params = {'serviceKey': self.key, 'numOfRows': self.page_size, 'pageNo': page_number,
                  'dataType': 'XML', 'dataCd': 'ASOS', 'dateCd': 'HR',
                  'startDt': start.strftime('%Y%m%d'), 'startHh': '00',
                  'endDt': end.strftime('%Y%m%d'), 'endHh': '23', 'stnIds': station}
        try:
            self.last_response = self.transport(params)
        except FetchError:
            raise  # Preserve the transport's stage/status instead of hiding it.
        except Exception as error:
            raise FetchError('API 통신에 실패했습니다.', stage='네트워크 연결',
                             exception_class=type(error).__name__) from None
        self.calls += 1
        try:
            return parse_page(self.last_response, self.key)
        except FetchError as error:
            self.attach_response(error)
            raise

    def validate_row(self, row, station, start, end):
        stamp = record_time(row)
        if row.get('stnId', '').strip() != station:
            raise FetchError('요청 지점과 응답 지점이 다릅니다.')
        if not datetime.combine(start, time()) <= stamp <= datetime.combine(end, time(23)):
            raise FetchError('응답 일시가 요청 기간을 벗어났습니다.')
        return stamp

    def check(self, day):
        """Suwon only, exactly one request; never paginate or save partial samples."""
        try:
            page = self.read_page(DEFAULT_STATION, day, day, 1)
            if page.total == 0 and not page.records:
                return page
            if page.number != 1 or not page.records or len(page.records) > self.page_size or len(page.records) > page.total:
                raise FetchError('연결 점검 첫 페이지 형식이 가이드와 다릅니다.')
            seen = set()
            for row in page.records:
                stamp = self.validate_row(row, DEFAULT_STATION, day, day)
                if stamp in seen:
                    raise FetchError('연결 점검 응답에 중복 시간이 있습니다.')
                seen.add(stamp)
            return page
        except FetchError as error:
            self.attach_response(error)
            raise

    def _fetch(self, station, start, end):
        records = {}; total = None; page_number = 1
        while True:
            page = self.read_page(station, start, end, page_number)
            if total is None:
                total = page.total
            if page.total != total:
                raise FetchError('페이지 사이 총 건수가 바뀌어 완전한 결과를 확인하지 못했습니다.')
            if total == 0:
                if page.records:
                    raise FetchError('총 건수와 실제 응답 건수가 다릅니다.')
                return []
            if page.number != page_number or not page.records:
                raise FetchError('페이지 진행이 중단되어 전체 자료를 받지 못했습니다.')
            for row in page.records:
                stamp = self.validate_row(row, station, start, end)
                if stamp in records:
                    raise FetchError('중복 관측 시간이 반환되어 페이지 완료를 확인하지 못했습니다.')
                records[stamp] = row
            if len(records) > total:
                raise FetchError('총 건수보다 많은 관측이 반환되었습니다.')
            if len(records) == total:
                return [records[k] for k in sorted(records)]
            page_number += 1


def number(row, field):
    # Known QC error/missing flags only. Do not invent numeric missing sentinels.
    if row.get(field + 'Qcflg', '').strip() in {'1', '9'}:
        return None
    try:
        value = float(row.get(field, '').strip())
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def daily_summary(records, start, end):
    days = {}; current = start
    while current <= end:
        days[current] = []; current += timedelta(days=1)
    for row in records:
        days[record_time(row).date()].append(row)
    result = []
    for day, rows in days.items():
        temperatures = [n for r in rows if (n := number(r, 'ta')) is not None]
        humidities = [n for r in rows if (n := number(r, 'hm')) is not None]
        solar = sum(number(r, 'icsr') is not None for r in rows)
        result.append({'date': day.isoformat(), 'max_ta_c': max(temperatures) if temperatures else None,
                       'min_hm_pct': min(humidities) if humidities else None,
                       'received_hours': len(rows), 'missing_record_hours': 24 - len(rows),
                       'icsr_present': bool(solar), 'icsr_present_hours': solar,
                       'icsr_missing_hours': 24 - solar,
                       'icsr_blank_or_invalid_received_hours': len(rows) - solar})
    return result


def collect(downloader, station, start, end, solar_station=None):
    result = {station: downloader.fetch(station, start, end)}
    if solar_station and not any(number(r, 'icsr') is not None for r in result[station]):
        if solar_station != station:
            result[solar_station] = downloader.fetch(solar_station, start, end)
    return result


def save_samples(result, start, end, key, directory):
    table = station_table(); staged = []
    for station, records in result.items():
        payload = {'source': '기상청 ASOS 시간자료 조회서비스', 'guide': 'docs/kma/asos-spec.md',
                   'station': table[station], 'start_date': start.isoformat(), 'end_date': end.isoformat(),
                   'start_hour': '00', 'end_hour': '23', 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                   'count': len(records), 'records': records, 'daily_summary': daily_summary(records, start, end),
                   'notes': 'icsr는 MJ/m2 원문 값. 누적 구간·시간대·수치 결측 센티널은 가이드에 없음.'}
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
        assert_safe(encoded, key)  # Verify everything before creating any output.
        path = directory / f'asos_{station}_{start:%Y%m%d}_{end:%Y%m%d}.json'
        if path.exists():
            raise FetchError('동일 지점·기간의 샘플 파일이 이미 있습니다. 기존 파일을 별도 보관하세요.')
        staged.append((path, encoded))
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for path, encoded in staged:
            with path.open('x', encoding='utf-8') as output:
                written.append(path)
                output.write(encoded)
    except OSError:
        for path in written:
            path.unlink(missing_ok=True)
        raise FetchError('샘플 파일 저장에 실패했습니다.') from None
    return written


def summary_text(result, start, end):
    table = station_table(); lines = []
    for station, records in result.items():
        lines.append(f"지점 {station} {table[station]['name']} · {len(records)}시간 자료")
        for day in daily_summary(records, start, end):
            temp = '결측' if day['max_ta_c'] is None else f"{day['max_ta_c']:g}℃"
            humidity = '결측' if day['min_hm_pct'] is None else f"{day['min_hm_pct']:g}%"
            solar = '있음' if day['icsr_present'] else '없음'
            lines.append(f"{day['date']} 최고기온 {temp} / 최저습도 {humidity} / 일사 값 {solar} "
                         f"(결측 {day['icsr_missing_hours']}시간, 자료 미수신 {day['missing_record_hours']}시간)")
    return '\n'.join(lines)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, '인자 형식이 올바르지 않습니다. --help를 확인하세요.\n')


def parser():
    p = SafeParser(description='사용자가 직접 실행하는 ASOS 시간자료 수집. 요청 URL/키를 기록하지 않음.')
    p.add_argument('--station', choices=list(station_table()), default=DEFAULT_STATION, help='가이드 표 지점번호, 기본119 수원')
    p.add_argument('--start', type=date.fromisoformat, default=date(2026, 7, 1), help='YYYY-MM-DD')
    p.add_argument('--end', type=date.fromisoformat, default=date(2026, 8, 31), help='YYYY-MM-DD')
    p.add_argument('--page-size', type=int, default=10, help='기본10(가이드 기본값), 최대 허용값은 문서에 없음')
    p.add_argument('--delay', type=float, default=0.2, help='호출 사이 대기 초, 기본0.2')
    p.add_argument('--solar-station', choices=list(station_table()), help='일사가 전부 결측이면 함께 받을 사용자 확인 지점. 관측 여부·거리는 TODO')
    p.add_argument('--check', action='store_true', help='수원119, --start 하루, 첫1페이지만 연결 점검. 저장·추가 지점 조회 없음')
    return p


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    # Do not permit library request logs to include a credential-bearing URL.
    for name in ('urllib', 'urllib3', 'httpx', 'httpcore'):
        logging.getLogger(name).disabled = True
    key = None; stage = '키 로드'; downloader = None
    try:
        args = parser().parse_args(argv)
        if args.check:
            args.station = DEFAULT_STATION
            args.end = args.start
            args.page_size = 10  # Guide default; one page, not one request per hour.
        if args.start > args.end or args.page_size < 1 or not math.isfinite(args.delay) or args.delay < 0.1:
            raise FetchError('기간·페이지 크기·대기 값을 확인하세요. 대기는 최소0.1초입니다.')
        key = read_api_key(ROOT / '.env')
        print_key_info(key)
        stage = '네트워크 연결'
        downloader = Downloader(key, args.page_size, args.delay)
        if args.check:
            checked = downloader.check(args.start)
            print(f'연결 점검 완료: 수원119 / {args.start.isoformat()} / 첫1페이지 / {len(checked.records)}건 (저장하지 않음)')
            return 0
        result = collect(downloader, args.station, args.start, args.end, args.solar_station)
        stage = '응답 파싱'
        output = summary_text(result, args.start, args.end)
        assert_safe(output, key)
        paths = save_samples(result, args.start, args.end, key, ROOT / 'data/samples')
        print(output)
        print(f'저장 완료: {len(paths)}개 지점 파일 (data/samples/)')
        if not any(number(r, 'icsr') is not None for r in result[args.station]):
            print('기본 지점의 일사 값이 전부 결측입니다. 가까운 일사 관측 지점은 가이드로 확인할 수 없어 TODO입니다.')
    except FetchError as error:
        if error.key_missing:
            print('키를 찾지 못함', file=sys.stderr)
        if key is None:
            print_key_info(None, sys.stderr, missing=error.key_missing)
        print_failure(error, key)
        return 1
    except KeyboardInterrupt:
        print('사용자가 수집을 중단했습니다.', file=sys.stderr)
        return 130
    except Exception as error:
        if key is None:
            print_key_info(None, sys.stderr)
        if downloader is not None and downloader.last_response is not None:
            stage = '응답 파싱'
        diagnostic = FetchError('수집 처리에 실패했습니다.', stage=stage,
                                exception_class=type(error).__name__)
        if downloader is not None:
            downloader.attach_response(diagnostic)
        print_failure(diagnostic, key)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
