"""Offline diagnostic/sensitivity analysis. No .env, collection, or policy writes.

The optional C probe uses upstream source at a pinned commit, without modifying
the installed library. Sensitivity variants exist only in this script's memory.
"""
import argparse
import ctypes
from dataclasses import asdict, replace
from datetime import datetime
import hashlib
from importlib.metadata import version
from functools import lru_cache
import json
import math
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lwbgt import Input, calculate
from backend.engine.policy import classify
from backend.engine.settings import EngineSettings
from backend.engine.wbgt import wind_at_2m
from backend.repository import Repository
from backend.service import Service
from backend.schedule.models import ScheduleSettings
from backend.schedule.optimizer import optimize, validate, Candidate
from backend.weather.asos_samples import load_dataset, numeric

UPSTREAM_COMMIT = 'e4b1298fcee27faa459f2eab0c2ef766ce2f34d7'
PUBLIC = ROOT/'docs/wbgt-sanity'
OUTPUT = ROOT/'data/output/wbgt-sanity'
RAW = ROOT/'data/samples/asos_119_20260701_20260831.json'
PRESSURE = PUBLIC/'pressure-evidence.json'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def pressure_evidence():
    """Only a fixed whitelist of meteorological fields can leave the raw sample."""
    data = load_dataset()
    if RAW.exists():
        raw = RAW.read_bytes()
        if hashlib.sha256(raw).hexdigest() != data.original_sha256:
            raise ValueError('Original sample fingerprint differs; audit withheld')
        fields = ('tm', 'pa', 'paQcflg', 'ps', 'psQcflg')
        evidence = {'original_sample_sha256': data.original_sha256,
                    'units': {'pa': 'hPa', 'ps': 'hPa'},
                    'records': [{k: r.get(k) for k in fields}
                                for r in json.loads(raw)['records']]}
        write_json(PRESSURE, evidence)
    else:
        evidence = json.loads(PRESSURE.read_text(encoding='utf-8'))
    if evidence['original_sample_sha256'] != data.original_sha256:
        raise ValueError('Pressure evidence has a different source')
    return {r['tm']: r for r in evidence['records']}


def stull_wet_bulb(ta_c, rh_percent):
    """Independent implementation of Stull Eq.4.19; comparison only, degC/%.

    Source: author-hosted Practical Meteorology, p95, Eq4.19. It estimates an
    aspirated wet bulb at sea-level pressure, NOT the radiated natural wet bulb.
    """
    return (ta_c * math.atan(.151977 * math.sqrt(rh_percent + 8.313659))
            + math.atan(ta_c + rh_percent) - math.atan(rh_percent - 1.676331)
            + .00391838 * rh_percent**1.5 * math.atan(.023101 * rh_percent)
            - 4.686035)


def shade_proxy(ta_c, rh_percent):
    return .7 * stull_wet_bulb(ta_c, rh_percent) + .3 * ta_c


def build_probe(source):
    source = Path(source).resolve()
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != UPSTREAM_COMMIT:
        raise ValueError('Unverified upstream source commit')
    subprocess.run(['git','-C',str(source),'diff','--quiet','HEAD','--','src/wbgt.c'],check=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    library = OUTPUT/'solar-probe.dll'
    subprocess.run(['gcc', '-shared', '-O2', '-std=gnu89', '-fno-fast-math',
                    '-ffp-contract=off', '-fno-strict-aliasing', '-static-libgcc',
                    '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                    str(source/'src/wbgt.c'), str(ROOT/'scripts/wbgt_solar_probe.c'),
                    '-lm', '-o', str(library)], check=True)
    return library


class Probe:
    def __init__(self, library):
        self.lib = ctypes.CDLL(str(Path(library).resolve()))
        self.lib.audit_solar.argtypes = ([ctypes.c_int]*7 + [ctypes.c_double]*3
                                        + [ctypes.POINTER(ctypes.c_double)])
        self.lib.audit_solar.restype = ctypes.c_int
        self.lib.calc_wbgt.argtypes = ([ctypes.c_int]*7 + [ctypes.c_double]*9
                                      + [ctypes.c_int] + [ctypes.POINTER(ctypes.c_float)]*5)
        self.lib.calc_wbgt.restype = ctypes.c_int

    def solar(self, item):
        values = (ctypes.c_double*7)()
        code = self.lib.audit_solar(item.year, item.month, item.day, item.hour,
            item.minute, item.gmt_offset_hours, item.averaging_minutes,
            item.latitude_deg_north, item.longitude_deg_east, item.solar_w_m2, values)
        if code: raise ValueError('Solar probe failed')
        return dict(zip(('effective_ghi_wm2', 'cos_zenith', 'direct_fraction',
                         'zenith_deg', 'direct_horizontal_wm2', 'diffuse_horizontal_wm2',
                         'direct_normal_wm2'), values))

    def outputs(self, item):
        floats = [ctypes.c_float() for _ in range(5)]
        code = self.lib.calc_wbgt(item.year, item.month, item.day, item.hour,
            item.minute, item.gmt_offset_hours, item.averaging_minutes,
            item.latitude_deg_north, item.longitude_deg_east, item.solar_w_m2,
            item.pressure_hpa, item.air_temperature_c, item.relative_humidity_percent,
            item.wind_speed_m_s, item.wind_height_m, item.vertical_temperature_difference_c,
            item.urban, *[ctypes.byref(v) for v in floats])
        if code: raise ValueError('Source calculation failed')
        return [v.value for v in floats]


def engine_input(risk):
    """Names explicitly reproduce production's positional arguments for audit."""
    w, v, settings = risk.inputs['weather'], risk.inputs['venue'], risk.inputs['settings']
    stamp = risk.valid_time
    solar = 0 if v['surface'] == 'indoor' or v['shade'] == 'full' else risk.inputs['solar']['used_wm2']
    return Input(year=stamp.year, month=stamp.month, day=stamp.day, hour=stamp.hour,
                 minute=stamp.minute, gmt_offset_hours=9, averaging_minutes=0, urban=1,
                 latitude_deg_north=v['lat'], longitude_deg_east=v['lon'], solar_w_m2=solar,
                 pressure_hpa=settings['pressure_hpa'], air_temperature_c=w['ta_c'],
                 relative_humidity_percent=max(w['rh_pct'], .01),
                 wind_speed_m_s=max(wind_at_2m(w['ws_ms'], settings['wind_exponent']), .13),
                 wind_height_m=2., vertical_temperature_difference_c=1.)


def fresh_sessions():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    service = Service(Repository(OUTPUT/f'audit-{uuid4().hex}.sqlite3'))
    existing = json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))
    sessions = []
    for day, expected in zip(load_dataset().dates, existing['days'], strict=True):
        session = service.replay(day, mode='observed')
        assert session['engine_settings'] == EngineSettings().model_dump()
        assert session['schedule_settings'] == ScheduleSettings().model_dump()
        assert max(r['wbgt_c'] for r in session['risks']) == expected['max_wbgt_c']
        # The original, proven coverage result is retained as evidence, not solved again.
        evidence_path = ROOT/'data/output/real'/(day.isoformat()+'.json')
        if evidence_path.exists():
            cached = json.loads(evidence_path.read_text(encoding='utf-8'))
            assert [(r['inputs_hash'], r['wbgt_c']) for r in cached['risks']] == [
                (r['inputs_hash'], r['wbgt_c']) for r in session['risks']]
        sessions.append(session)
        print(f"physics {day.isoformat()} verified", flush=True)
    write_json(OUTPUT/'fresh-sessions.json', sessions)
    return sessions


def peak_traces(sessions, probe, pressure, source=None):
    peaks = []
    for s in sessions:
        risks = Service.context(s)[3]
        peak = sorted(risks, key=lambda r: (-r.wbgt_c, r.valid_time, r.venue_id))[0]
        peaks.append(peak)
    selected = sorted(peaks, key=lambda r: (-r.wbgt_c, r.valid_time))[:5]
    selected += [r for r in peaks if r.valid_time.date().isoformat() == '2026-07-10']
    rows = []
    for risk in selected:
        item = engine_input(risk)
        out = calculate(item)
        if out.status: raise ValueError('Library failure, not a valid physical peak')
        p = pressure[risk.valid_time.strftime('%Y-%m-%d %H:%M')]
        actual = [out.estimated_wind_speed_m_s, out.globe_temperature_c, out.natural_wet_bulb_c,
                  out.psychrometric_wet_bulb_c, out.wbgt_c]
        diff = max(abs(a-b) for a,b in zip(actual, probe.outputs(item), strict=True))
        if diff > .0001: raise ValueError('Source probe differs from installed library')
        offset = risk.inputs['venue']['field_offset_c']
        assert risk.inputs['calibration'] is None
        assert risk.inputs['settings']['surface_offsets'][risk.inputs['venue']['surface']] == 0
        assert round(out.wbgt_c + offset, 3) == risk.wbgt_c
        wet = stull_wet_bulb(item.air_temperature_c, item.relative_humidity_percent)
        radiated_wet = .7 * (out.natural_wet_bulb_c - out.psychrometric_wet_bulb_c)
        wet_method = .7 * (out.psychrometric_wet_bulb_c - wet)
        globe = .2 * (out.globe_temperature_c - item.air_temperature_c)
        row = {'date':risk.valid_time.date().isoformat(), 'time_kst':risk.valid_time.isoformat(),
               'venue_id':risk.venue_id, 'input':asdict(item), 'pressure_observed':p,
               'solar_raw_mj_m2':risk.inputs['weather']['provenance']['solar_energy_mj_m2'],
               'solar_source':risk.inputs['solar']['source'],
               'wind_observed_ms':risk.inputs['weather']['ws_ms'],
               'wind_height_factor':(2/10)**risk.inputs['settings']['wind_exponent'],
               'wind_adjusted_ms':risk.inputs['wind_2m_ms'],
               'native_solar':probe.solar(item), 'result':asdict(out),
               'source_output_max_abs_diff_c':diff, 'field_offset_c':offset,
               'central_c':risk.wbgt_c, 'low_c':risk.wbgt_low_c, 'upper_c':risk.wbgt_high_c,
               'stull_wet_c':wet, 'shade_proxy_c':shade_proxy(item.air_temperature_c,item.relative_humidity_percent),
               'difference_components_c':{'natural_wet_radiation':radiated_wet,
                                         'wet_formula':wet_method, 'globe_vs_air':globe,
                                         'field_offset':offset},
               'counterfactuals':{}}
        changes = {'observed_station_pressure':{'pressure_hpa':numeric(p,'pa',True)},
                   'solar_interval_60min':{'averaging_minutes':60},
                   'unadjusted_10m_wind_as_2m':{'wind_speed_m_s':row['wind_observed_ms']},
                   'no_shortwave':{'solar_w_m2':0}}
        for name, change in changes.items():
            alt = calculate(replace(item, **change))
            if alt.status: raise ValueError('Counterfactual library failure')
            row['counterfactuals'][name] = {'wbgt_station_c':alt.wbgt_c,
                'delta_station_c':alt.wbgt_c-out.wbgt_c,
                'tnw_c':alt.natural_wet_bulb_c,'tg_c':alt.globe_temperature_c}
        rows.append(row)
    result = {'library_version':version('lwbgt'), 'upstream_commit':UPSTREAM_COMMIT,
              'original_sample_sha256':load_dataset().original_sha256,
              'source_sha256':hashlib.sha256((Path(source or OUTPUT/'lwbgt-source')/'src/wbgt.c').read_bytes()).hexdigest(),
              'all_62_day_maxima_verified':True, 'rows':rows}
    write_json(PUBLIC/'peak-traces.json', result)
    return result


def peak_tables(result):
    rows=result['rows']
    headers=[r['time_kst'][:16].replace('T',' ')+' '+r['venue_id'].removeprefix('mock-suwon-').upper() for r in rows]
    lines=['# 최고값 계산 단계 표', '',
           '모두 KST. A/B/C는 가상 구장. 관측 입력은 수원119 공유. WBGT·Tnw·Tg는 추정값이며 현장 실측이 아니다.', '',
           '| 단계·항목(단위) | '+' | '.join(headers)+' |',
           '|---|'+'---:|'*len(rows)]
    metrics=[
        ('1 관측 기온(℃)',lambda r:r['input']['air_temperature_c']),
        ('1 관측 상대습도(%)',lambda r:r['input']['relative_humidity_percent']),
        ('1 관측 풍속(m/s; 10m 입력 가정)',lambda r:r['wind_observed_ms']),
        ('1 관측 현지기압 pa(hPa)',lambda r:numeric(r['pressure_observed'],'pa',True)),
        ('1 관측 해면기압 ps(hPa)',lambda r:numeric(r['pressure_observed'],'ps',True)),
        ('1 실제 엔진 기압(hPa; 관측 대신 고정 가정)',lambda r:r['input']['pressure_hpa']),
        ('1 관측 일사 원값(이전 1시간 MJ/m²)',lambda r:r['solar_raw_mj_m2']),
        ('2 일사 변환값(시간평균 W/m²)',lambda r:r['input']['solar_w_m2']),
        ('2 풍속 높이 계수((2/10)^0.2)',lambda r:r['wind_height_factor']),
        ('2 높이 보정 후 풍속(m/s)',lambda r:r['wind_adjusted_ms']),
        ('2 최소 0.13 처리 후 라이브러리 풍속(m/s)',lambda r:r['input']['wind_speed_m_s']),
        ('3 내부 제한 후 실제 사용 GHI(W/m²)',lambda r:r['native_solar']['effective_ghi_wm2']),
        ('3 라이브러리 태양 천정각(도)',lambda r:r['native_solar']['zenith_deg']),
        ('3 직달 비율(수평면 기준)',lambda r:r['native_solar']['direct_fraction']),
        ('3 직달 수평면 일사(W/m²)',lambda r:r['native_solar']['direct_horizontal_wm2']),
        ('3 산란 수평면 일사 DHI(W/m²)',lambda r:r['native_solar']['diffuse_horizontal_wm2']),
        ('3 직달 법선면 일사 DNI(W/m²)',lambda r:r['native_solar']['direct_normal_wm2']),
        ('4 자연습구 Tnw(℃; 추정)',lambda r:r['result']['natural_wet_bulb_c']),
        ('4 통풍습구 Tpsy(℃; 추정)',lambda r:r['result']['psychrometric_wet_bulb_c']),
        ('4 흑구 Tg(℃; 추정)',lambda r:r['result']['globe_temperature_c']),
        ('4 관측 입력 기준 WBGT(℃; 경기장 보정 전 추정)',lambda r:r['result']['wbgt_c']),
        ('5 경기장 보정(℃)',lambda r:r['field_offset_c']),
        ('5 최종 중앙값(℃; 추정)',lambda r:r['central_c']),
        ('5 하단값(℃; 추정)',lambda r:r['low_c']),
        ('5 상단값(℃; 추정·유소년 판정값)',lambda r:r['upper_c']),
        ('비교 Stull 통풍습구 근사(℃)',lambda r:r['stull_wet_c']),
        ('비교 그늘 근사 0.7Tw+0.3Ta(℃)',lambda r:r['shade_proxy_c']),
    ]
    for label,get in metrics:
        lines.append('| '+label+' | '+' | '.join(f'{get(r):.6f}' for r in rows)+' |')
    lines += ['', '직달·산란은 관측된 분리값이 아니라 lwbgt 내부 경험식의 추정 분리값이다. 직접 컴파일한 동일 버전 C 계산의 5개 출력은 설치 DLL과 여섯 시각 모두 완전히 같았다.', '',
              '## 그늘 근사 대비 성분별 차이', '',
              '| 시각(KST) | 자연습구 복사 0.7(Tnw−Tpsy) | 습구 식 차이 0.7(Tpsy−Tw근사) | 흑구 0.2(Tg−Ta) | 경기장 보정 | 총 차이(반올림 전) |',
              '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        c=r['difference_components_c']
        lines.append('| '+r['time_kst'][:16].replace('T',' ')+' | '+' | '.join(f'{x:.6f}' for x in [*c.values(),sum(c.values())])+' |')
    lines += ['', '## 분석용 단일 입력 변경: 보정 전 WBGT 차이(℃)', '',
              '| 시각(KST) | 현지기압 pa 사용 | 이전 60분 중심 태양 위치 | 높이 보정 생략(잘못된 높이 가정 비교) | 일사 0 |',
              '|---|---:|---:|---:|---:|']
    for r in rows:
        lines.append('| '+r['time_kst'][:16].replace('T',' ')+' | '+' | '.join(
            f'{x["delta_station_c"]:+.6f}' for x in r['counterfactuals'].values())+' |')
    lines += ['', '각 비교는 나머지 입력을 고정했다. 엔진·기본 정책·운영값에는 반영하지 않았다. 소수점 6자리는 추적용이며 정확도 0.000001℃를 의미하지 않는다.', '']
    (PUBLIC/'peak-tables.md').write_text('\n'.join(lines),encoding='utf-8')


# These inputs are hypothetical sensitivity cases, not new policy/operating defaults.
SCENARIOS = {
    'baseline': (2.5, True, {}),
    'offset_0': (0., True, {}),
    'offset_1.25': (1.25, True, {}),
    'offset_3.75': (3.75, True, {}),
    'central_only': (2.5, False, {}),
    'offset_0_central': (0., False, {}),
    'site_lower_1': (2.5, True, {'*':-1.}),
    'site_upper_1': (2.5, True, {'*':1.}),
    'site_heterogeneous_1': (2.5, True, {'mock-suwon-a':-1., 'mock-suwon-b':0., 'mock-suwon-c':1.}),
    'site_heterogeneous_reverse_1': (2.5, True, {'mock-suwon-a':1., 'mock-suwon-b':0., 'mock-suwon-c':-1.}),
}


def variant_context(session, offset, upper, shifts):
    t,m,v,risks,settings,engine = Service.context(session)
    assert t.age_group == 'U12' and not engine.age_escalation
    unknown = set(shifts)-{'*'}-{x.id for x in v}
    if unknown: raise ValueError(f'Unknown hypothetical venue ids: {sorted(unknown)}')
    changed = []
    for r in risks:
        if r.inputs['calibration'] is not None:
            raise ValueError('This sensitivity protocol requires uncalibrated observations')
        native = unrounded_native_wbgt(engine_input(r))
        central = native + offset + shifts.get(r.venue_id,shifts.get('*',0.))
        central += engine.surface_offsets[r.inputs['venue']['surface']]
        low, high = central-engine.uncertainty_c, central+engine.uncertainty_c
        decision = high if upper else central
        # Match production: classify full precision, then round displayed numbers.
        changed.append(replace(r,wbgt_c=round(central,3),wbgt_low_c=round(low,3),wbgt_high_c=round(high,3),
                               level=classify(decision,t.policy_id),decision_wbgt_c=round(decision,3)))
    # Venue offset is descriptive; rescheduling uses the changed risks. No engine re-estimation.
    return t,m,[replace(x,field_offset_c=offset) for x in v],changed,settings,engine


@lru_cache(maxsize=8192)
def unrounded_native_wbgt(item):
    output=calculate(item)
    if output.status or not math.isfinite(output.wbgt_c):
        raise ValueError('Sensitivity requires successful primary-engine outputs')
    return output.wbgt_c


def sensitivity(sessions):
    prior = json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))['days']
    result = {'original_sample_sha256':load_dataset().original_sha256,
              'analysis_only':True,'settings':ScheduleSettings().model_dump(), 'scenarios':[]}
    for name,(offset,upper,shifts) in SCENARIOS.items():
        rows = []
        for s, baseline in zip(sessions, prior, strict=True):
            day = s['tournament']['date_start']
            if name == 'baseline':
                row = {k:baseline[k] for k in ('date','assigned','postponed','solver','coverage_optimal')}
                row['full_coverage_proven'] = baseline['postponed']==0 or baseline['coverage_optimal']
            else:
                t,m,v,r,settings,engine = variant_context(s,offset,upper,shifts)
                opt = optimize(m,t,v,r,settings,engine)
                if validate(opt.assignments,m,t,v,r,settings) or not opt.constraints_ok:
                    raise RuntimeError('Sensitivity hard constraints failed')
                if len(opt.assignments)+opt.postponed_count != 15:
                    raise RuntimeError('Sensitivity match accounting failed')
                assert opt.postponement_penalty > opt.secondary_cost_upper_bound
                row = {'date':day,'assigned':len(opt.assignments),'postponed':opt.postponed_count,
                       'solver':opt.solver,'coverage_optimal':opt.coverage_optimal,
                       'full_coverage_proven':opt.postponed_count==0 or opt.coverage_optimal,
                       'elapsed_sec':opt.elapsed_sec, 'constraints_ok':True}
                write_json(OUTPUT/name/(day+'.json'),{'analysis_only':True,'assumptions':{
                    'field_offset_c':offset,'decision_uses_upper':upper,'hypothetical_site_shift_c':shifts},
                    'summary':row,'proposal':asdict(opt) | {'assignments':[
                        asdict(a) | {'start':a.start.isoformat(),'end':a.end.isoformat(),
                                    'cooling_times':[x.isoformat() for x in a.cooling_times]}
                        for a in opt.assignments]}})
            rows.append(row)
            print(f"{name} {day} {row['assigned']}/15 {row['solver']}",flush=True)
        summary = {'complete_days':sum(x['assigned']==15 for x in rows),
                   'incomplete_days':sum(x['assigned']<15 for x in rows),
                   'zero_assignment_days':sum(x['assigned']==0 for x in rows),
                   'assigned_total':sum(x['assigned'] for x in rows),
                   'postponed_total':sum(x['postponed'] for x in rows),
                   'unproven_incomplete_days':[x['date'] for x in rows if not x['full_coverage_proven']]}
        result['scenarios'].append({'name':name,'field_offset_c':offset,'decision_uses_upper':upper,
             'hypothetical_site_shift_c':shifts,'summary':summary,'days':rows})
        write_json(PUBLIC/'sensitivity-results.json', result)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['traces','sensitivity','tables'],required=True)
    parser.add_argument('--source',type=Path,default=OUTPUT/'lwbgt-source')
    args=parser.parse_args()
    if args.mode == 'traces':
        probe=Probe(build_probe(args.source))
        result=peak_traces(fresh_sessions(),probe,pressure_evidence(),args.source)
        peak_tables(result)
        for row in result['rows']:
            print(json.dumps(row,ensure_ascii=False),flush=True)
    elif args.mode == 'sensitivity':
        sessions=json.loads((OUTPUT/'fresh-sessions.json').read_text(encoding='utf-8'))
        result=sensitivity(sessions)
        print(json.dumps([x['summary']|{'name':x['name']} for x in result['scenarios']],ensure_ascii=False))
    else:
        peak_tables(json.loads((PUBLIC/'peak-traces.json').read_text(encoding='utf-8')))
