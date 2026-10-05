"""Append-only exploratory evidence. Never feeds measurements into the engine."""
from datetime import datetime
from typing import Literal
from uuid import uuid4
from statistics import median
import csv
import hashlib
import io
import json
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from backend.exports import csv_safe
from backend.weather.models import KST, require_aware


class EvidenceBase(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    mode: Literal['mock', 'actual'] = 'mock'
    source_ref: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    observed_at: datetime
    notes: str = Field(default='', max_length=2000)

    @field_validator('observed_at')
    @classmethod
    def aware(cls, value):
        require_aware(value)
        if value > datetime.now(KST):
            raise ValueError('미래 시각을 수행 기록으로 저장할 수 없습니다.')
        return value


class Timing(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    preparation_min: float | None = Field(default=None, ge=0)
    change_min: float | None = Field(default=None, ge=0)
    documentation_min: float | None = Field(default=None, ge=0)
    completed: bool = True
    constraint_check: Literal['passed', 'failed', 'unchecked'] = 'unchecked'

    def total(self):
        times = [self.preparation_min, self.change_min, self.documentation_min]
        return sum(times) if self.completed and all(t is not None for t in times) else None


class WorkEvidence(EvidenceBase):
    participant_code: str = Field(pattern=r'^[A-Za-z0-9_-]{1,40}$')
    case_code: str = Field(pattern=r'^[A-Za-z0-9_-]{1,40}$')
    consent: bool = False
    order: Literal['current_first', 'heattime_first']
    same_conditions: bool = False
    current: Timing
    heattime: Timing
    negative_feedback: str = Field(default='', max_length=2000)
    purchase_response: str = Field(default='미확인', max_length=1000)

    @model_validator(mode='after')
    def actual_consent(self):
        if self.mode == 'actual' and not self.consent:
            raise ValueError('실제 운영자 기록은 익명 기록 동의가 필요합니다.')
        return self


class FieldEvidence(EvidenceBase):
    session_id: str = Field(min_length=1, max_length=100)
    venue_id: str = Field(min_length=1, max_length=100)
    reference_time: datetime
    measured_wbgt_c: float = Field(ge=-50, le=65)
    device_code: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    protocol_ref: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    measurement_height_m: float = Field(gt=0)
    placement: str = Field(min_length=1, max_length=500)
    calibration_status: Literal['documented', 'unknown'] = 'unknown'
    same_site: bool = False

    @field_validator('reference_time')
    @classmethod
    def reference_aware(cls, value):
        require_aware(value)
        return value


class ExclusionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator('reason')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('제외 사유를 기록하세요.')
        return value.strip()


def exclude_record(repo, kind, id, body):
    if kind not in {'work', 'field'}: raise KeyError(kind)
    with repo.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        repo.get('validation_' + kind, id, conn)
        code = kind + '_' + id
        if conn.execute("SELECT 1 FROM resources WHERE kind='validation_exclusions' AND id=?", (code,)).fetchone():
            raise HTTPException(409, '이미 제외한 기록입니다. 원자료와 제외 사유는 그대로 보존됩니다.')
        return repo.put('validation_exclusions', code, {'kind': kind, 'record_id': id,
                        'reason': body.reason, 'saved_at': datetime.now(KST).isoformat()}, conn)


def fingerprint(value):
    data = json.dumps(jsonable_encoder(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def save_work(repo, body):
    row = jsonable_encoder(body)
    reasons = []
    if body.mode == 'mock': reasons.append('가상 예시 · 실제 성과 제외')
    if not body.same_conditions: reasons.append('동일 대진·정책·운영 조건 미확인')
    if body.current.total() is None or body.heattime.total() is None:
        reasons.append('중단 또는 준비·변경·기록 시간 누락')
    if body.current.constraint_check != 'passed' or body.heattime.constraint_check != 'passed':
        reasons.append('두 방식의 하드 제약 통과 미확인')
    row.update(current_total_min=body.current.total(), heattime_total_min=body.heattime.total(),
               excluded_reasons=reasons, eligible=not reasons)
    with repo.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        for saved, in conn.execute("SELECT body FROM resources WHERE kind='validation_work'"):
            old = json.loads(saved)
            if all(old[k] == row[k] for k in ('mode', 'participant_code', 'case_code', 'order')):
                raise HTTPException(409, '같은 참여자·사례·순서의 기록이 이미 있습니다. 다른 반복은 별도 사례 코드로 남기세요.')
        return _store(repo, 'work', row, conn)


def save_field(repo, body):
    with repo.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        session = repo.get('validation_references' if body.session_id.startswith('live-') else 'sessions', body.session_id, conn)
        risk = next((r for r in session['risks'] if r['venue_id'] == body.venue_id
                     and datetime.fromisoformat(r['valid_time']) == body.reference_time), None)
        if risk is None: raise KeyError('대조할 추정 기록')
        row = jsonable_encoder(body)
        reasons = []
        if body.mode == 'mock': reasons.append('가상 예시 · 실제 현장 대조 제외')
        if risk['is_mock']: reasons.append('합성 기상 입력')
        if risk['inputs']['venue'].get('is_mock', True): reasons.append('가상 구장')
        if body.observed_at != body.reference_time: reasons.append('측정·추정 시각 불일치 · 보간하지 않음')
        if not body.same_site: reasons.append('동일 측정 위치 미확인')
        if body.calibration_status != 'documented': reasons.append('측정기 교정 근거 미확인')
        if risk['inputs'].get('calibration') is not None: reasons.append('실측 보정된 추정 · 순환 검증 제외')
        for saved, in conn.execute("SELECT body FROM resources WHERE kind='validation_field'"):
            old = json.loads(saved)
            if (old['mode'], old['venue_id'], datetime.fromisoformat(old['reference_time']), old['device_code']) == (
                    row['mode'], row['venue_id'], body.reference_time, row['device_code']):
                raise HTTPException(409, '같은 시각·구장·측정기의 대조 기록이 이미 있습니다.')
        v = risk['inputs']['venue']
        offset = v['field_offset_c'] + risk['inputs']['settings']['surface_offsets'].get(v['surface'], 0)
        row.update(frozen_risk=risk, reference_label=session['label'], reference_fingerprint=fingerprint(risk),
                   model_base_c=risk['wbgt_c'] - offset, error_c=risk['wbgt_c'] - body.measured_wbgt_c,
                   base_error_c=risk['wbgt_c'] - offset - body.measured_wbgt_c,
                   inside_range=risk['wbgt_low_c'] <= body.measured_wbgt_c <= risk['wbgt_high_c'],
                   excluded_reasons=reasons, eligible=not reasons)
        return _store(repo, 'field', row, conn)


def _store(repo, kind, row, conn):
    row.update(id=uuid4().hex, saved_at=datetime.now(KST).isoformat(), kind=kind)
    row['record_fingerprint'] = fingerprint(row)
    return repo.put('validation_' + kind, row['id'], row, conn)


def work_stats(rows, excluded=()):
    good = [r for r in rows if r['eligible'] and r['id'] not in excluded]
    differences = [r['current_total_min'] - r['heattime_total_min'] for r in good]
    return {'records': len(rows), 'actual_records': sum(r['mode'] == 'actual' for r in rows),
            'mock_records': sum(r['mode'] == 'mock' for r in rows), 'included_pairs': len(good),
            'excluded_actual': sum(r['mode'] == 'actual' and (not r['eligible'] or r['id'] in excluded) for r in rows),
            'participants': len({r['participant_code'] for r in good}),
            'median_saved_min': median(differences) if differences else None,
            'min_saved_min': min(differences) if differences else None,
            'max_saved_min': max(differences) if differences else None,
            'order_counts': {order: sum(r['order'] == order for r in good) for order in ('current_first', 'heattime_first')}}


def field_stats(rows, excluded=()):
    good = [r for r in rows if r['eligible'] and r['id'] not in excluded]
    def avg(values): return sum(values) / len(values) if values else None
    return {'records': len(rows), 'actual_records': sum(r['mode'] == 'actual' for r in rows),
            'mock_records': sum(r['mode'] == 'mock' for r in rows), 'included_pairs': len(good),
            'excluded_actual': sum(r['mode'] == 'actual' and (not r['eligible'] or r['id'] in excluded) for r in rows),
            'mae_c': avg([abs(r['error_c']) for r in good]), 'bias_c': avg([r['error_c'] for r in good]),
            'base_mae_c': avg([abs(r['base_error_c']) for r in good]),
            'base_bias_c': avg([r['base_error_c'] for r in good]),
            'range_inclusion_fraction': avg([int(r['inside_range']) for r in good])}


def evidence_summary(repo):
    work = repo.list('validation_work'); field = repo.list('validation_field')
    exclusions = repo.list('validation_exclusions'); excluded = {r['record_id'] for r in exclusions}
    return {'work': work_stats(work, excluded), 'field': field_stats(field, excluded), 'work_records': work, 'field_records': field,
            'exclusions': exclusions,
            'work_cases': {case: work_stats([r for r in work if r['case_code'] == case], excluded) for case in sorted({r['case_code'] for r in work})},
            'field_sites': {site: field_stats([r for r in field if r['venue_id'] == site], excluded) for site in sorted({r['venue_id'] for r in field})},
            'limitations': ['입력자의 수행 기록입니다. 제3자 확인이나 수상 가능성의 입증은 아닙니다.',
                            '준비·변경·기록을 모두 포함합니다. 음수 절감 시간도 그대로 표시합니다.',
                            '사례별·구장별 결과를 확인하세요. 반복 기록 수와 참여자 수는 다릅니다.',
                            '범위 포함 비율은 표본 내 관찰이며 검증된 신뢰구간·안전성 지표가 아닙니다.',
                            '정책·운영값·엔진 보정을 변경하거나 이 기록을 실측 보정에 사용하지 않습니다.']}


def evidence_csv(summary):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    exclusions = {r['record_id']: r for r in summary['exclusions']}
    writer.writerow(['kind', 'id', 'mode', 'source_ref', 'eligible', 'excluded_reasons', 'review_exclusion_json', 'record_fingerprint', 'record_json'])
    for row in summary['work_records'] + summary['field_records']:
        values = [row['kind'], row['id'], row['mode'], row['source_ref'], row['eligible'] and row['id'] not in exclusions,
                  '; '.join(row['excluded_reasons']), json.dumps(exclusions.get(row['id']), ensure_ascii=False),
                  row['record_fingerprint'], json.dumps(row, ensure_ascii=False, allow_nan=False)]
        writer.writerow([csv_safe(value) for value in values])
    return ('\ufeff' + output.getvalue()).encode('utf-8')
