"""Portable Korean records, generated from the frozen decision inputs."""
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from pathlib import Path
import csv, json
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.lib.colors import HexColor, white, black
from backend.decision_breakdown import explanation,breakdown
from backend.display_names import match_name, placeholder_name

DISCLAIMER = '본 자료는 의사결정 보조용 추정값'
# E-7: operator-facing Korean wording; internal ids stay in parentheses for traceability.
OPERATOR_ACTIONS = {'accepted': '제안 승인', 'modified': '수정안 승인', 'rejected': '제안 거절'}
MATCH_ACTIONS = {'none': '통상 진행', 'cooling_break': '쿨링브레이크', 'shorten': '시간 단축', 'move': '시간 이동', 'postpone': '연기'}
SURFACES = {'natural_grass': '천연잔디', 'artificial_turf': '인조잔디', 'dirt': '흙', 'indoor': '실내'}
SHADES = {'none': '없음', 'partial': '부분', 'full': '전체'}
SOURCES = {'asos_obs': '기상청 ASOS 관측', 'kma_fcst': '단기예보 형식', 'aws_obs': '기상청 AWS 관측'}


def verification_text(raw):
    """W-3: '원문 대조 필요 · 2026-10-01 … 대조 완료' read as a contradiction; state both facts explicitly."""
    head = '원문 대조 필요 · '
    if raw.startswith(head):
        return f"원문 대조: {raw[len(head):]} · 원문 개정 시 다시 대조 필요 · 국내 대회 적용 전 전문가 검토 필요"
    return raw


def display_label(label):
    return '통상 운영' if label == '거의 안전' else label


def stage_name(s, level):
    labels = (s.get('policy') or {}).get('labels') or []
    return display_label(labels[level]) if level is not None and 0 <= level < len(labels) else ''


def stage_display(policy):
    """JSON export note: display names next to the guideline's own labels (W-1)."""
    labels = (policy or {}).get('labels') or []
    return {'labels_display': [display_label(l) for l in labels],
            'note': 'policy.labels는 원 지침 단계명(출처: policy.source_ref)입니다. 화면·PDF·CSV는 labels_display를 쓰며, '
                    '0단계 "거의 안전"은 안전을 판정·보장하지 않도록 "통상 운영"으로 표시합니다(명세 2.5(D) 2026-10-11 변경).'}


def kst(value):
    """'2026-08-10T09:00:00+09:00' -> '2026-08-10 09:00 KST'."""
    if not value:
        return '—'
    text = value if isinstance(value, str) else value.isoformat()
    return text[:10] + ' ' + text[11:16] + ' KST'


def venue_name(s, venue_id):
    name = next((v['name'] for v in s.get('venues', []) if v['id'] == venue_id), None)
    return f"{name} ({venue_id})" if name else venue_id


def team_name(s, team_id):
    if team_id.startswith('winner:'):
        return placeholder_name(team_id)
    return next((t['name'] for t in s.get('teams', []) if t['id'] == team_id), team_id)


def record_context(session):
    return {**session, **(session.get('decision') or {}).get('snapshot', {})}


def match_context(s, m):
    rec = next(r for r in s['recommendations'] if r['match_id'] == m['id'])
    decision = s.get('decision') or {}
    assignment = next((a for a in decision.get('assignments', []) if a['match_id'] == m['id']), None)
    postponed = next((p for p in decision.get('postponed', []) if p['match_id'] == m['id']), None)
    windows = [('원래 일정', m['venue_id'], m['scheduled_start'], rec['end'])]
    if assignment:
        windows.append(('승인 일정', assignment['venue_id'], assignment['start'], assignment['end']))
    evidence = []
    for name, venue, start, end in windows:
        hour = datetime.fromisoformat(start).replace(minute=0, second=0, microsecond=0)
        finish = datetime.fromisoformat(end)
        while hour <= finish:
            risk = next((r for r in s['risks'] if r['venue_id'] == venue and datetime.fromisoformat(r['valid_time']) == hour), None)
            if risk:
                evidence.append((name, risk))
            hour += timedelta(hours=1)
    return rec, assignment, postponed, evidence


def csv_safe(value):
    """Neutralize spreadsheet formulas; plain numbers (including negatives) stay numeric."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value) if value is not None else ''
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


# f: Korean column names people read; ids stay in their own columns for traceability.
CSV_HEADER = ['자료 구분(가상 예시)', '경기 ID', '경기', '근거 구간', '구장 ID', '시각', 'WBGT 추정', 'WBGT 추정 하한', 'WBGT 추정 상한',
              '단계', '단계명', '판정값(추정)', '기온(℃)', '습도(%)', '풍속(m/s)', '사용 일사(W/m²)', '일사 자료',
              '일사 추정(W/m²)', '일사 추정 하한', '일사 추정 상한', '기상 자료', '합성 기상 여부', '수집 시각',
              '산정 방법', '입력 해시', '정책', '정책 출처', '원래 일정 권고',
              '운영자 조치', '운영자', '판단 시각', '판단 사유', '적용 킥오프', '적용 구장 ID',
              '적용 조치', '쿨링브레이크 시각', '연기 사유', '입력 전체(JSON)', '고지']


# i: stage colours of design A plus hatch density, so stages stay distinct in black-and-white print.
STAGE_FILL = ['#e2efe5', '#f3edc4', '#ffd59f', '#ec9b7b', '#6b1f2e']
STAGE_HATCH = [None, (7, False), (4, False), (4, True), None]  # (spacing pt, cross-hatch)


def _hatch(d, x, y, w, h, level):
    spec = STAGE_HATCH[level]
    if not spec:
        return
    gap, cross = spec
    ink = HexColor('#3a2a22')
    k = -h
    while k < w:
        x0, y0, x1, y1 = x + max(k, 0), y + max(-k, 0), x + min(k + h, w), y + min(h, w - k)
        d.add(Line(x0, y0, x1, y1, strokeColor=ink, strokeWidth=0.45))
        if cross:
            d.add(Line(x + w - (x0 - x), y0, x + w - (x1 - x), y1, strokeColor=ink, strokeWidth=0.45))
        k += gap


def stage_grid(s, width, font, unit_font):
    """Venue x hour table: stage number, decision value; fill + hatch by stage."""
    day = s['tournament']['date_start']
    hours = list(range(7, 21))
    venues = s.get('venues', [])
    label_w, row_h, head_h, legend_h = 92, 30, 14, 34
    cell_w = (width - label_w) / len(hours)
    height = head_h + row_h * len(venues) + legend_h
    d = Drawing(width, height)
    top = height - head_h
    for i, h in enumerate(hours):
        d.add(String(label_w + i * cell_w + 2, top + 3, f'{h}시', fontName=font, fontSize=7))
    for r, v in enumerate(venues):
        y = top - (r + 1) * row_h
        d.add(String(0, y + row_h / 2 - 3, v['name'].replace(' · 가상 예시', ''), fontName=font, fontSize=7))
        for i, h in enumerate(hours):
            risk = next((x for x in s['risks'] if x['venue_id'] == v['id'] and x['valid_time'].startswith(f'{day}T{h:02d}')), None)
            x = label_w + i * cell_w
            if risk is None:
                d.add(Rect(x, y, cell_w - 1, row_h - 1, fillColor=white, strokeColor=black, strokeWidth=0.3))
                d.add(String(x + 2, y + 4, '자료 없음', fontName=font, fontSize=5.5))
                continue
            level = risk['level']
            d.add(Rect(x, y, cell_w - 1, row_h - 1, fillColor=HexColor(STAGE_FILL[level]), strokeColor=black, strokeWidth=0.3))
            _hatch(d, x, y, cell_w - 1, row_h - 1, level)
            ink = white if level == 4 else black
            d.add(Rect(x + 1.5, y + 1.5, cell_w - 4, 18, fillColor=HexColor('#6b1f2e') if level == 4 else white, strokeColor=None))
            d.add(String(x + 3, y + 12, f"{level}단계", fontName=font, fontSize=6, fillColor=ink))
            d.add(String(x + 3, y + 3.5, f"{risk['decision_wbgt_c']:.1f}", fontName=font, fontSize=6.5, fillColor=ink))
    y = 2
    for level in range(5):
        x = level * (width / 5)
        d.add(Rect(x, y, 14, 12, fillColor=HexColor(STAGE_FILL[level]), strokeColor=black, strokeWidth=0.3))
        _hatch(d, x, y, 14, 12, level)
        d.add(String(x + 18, y + 3, f"{level} {stage_name(s, level)}", fontName=font, fontSize=7))
    return d


def records_csv(session):
    s = record_context(session)
    output = StringIO(newline=''); writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    d = s.get('decision') or {}
    for m in s['matches']:
        rec, a, p, evidence = match_context(s, m)
        for name, r in evidence or [('자료 누락', {})]:
            inputs = r.get('inputs', {}); w = inputs.get('weather', {}); solar = inputs.get('solar', {})
            row = [s['label'], m['id'], match_name(m['id']), name, r.get('venue_id'), r.get('valid_time'), r.get('wbgt_c'),
                   r.get('wbgt_low_c'), r.get('wbgt_high_c'), r.get('level'), stage_name(s, r.get('level')), r.get('decision_wbgt_c'),
                   w.get('ta_c'), w.get('rh_pct'), w.get('ws_ms'), solar.get('used_wm2'), solar.get('source'),
                   solar.get('estimated_wm2'), solar.get('low_wm2'), solar.get('high_wm2'), w.get('source'),
                   w.get('is_mock'), w.get('fetched_at'), r.get('method_version'), r.get('inputs_hash'),
                   s['policy']['name'], s['policy']['source_ref'], rec['detail'], d.get('operator_action', '미결정'),
                   d.get('operator_name'), d.get('timestamp'), d.get('reason'), (a or {}).get('start'),
                   (a or {}).get('venue_id'), (a or {}).get('action'), json.dumps((a or {}).get('cooling_times', []), ensure_ascii=False),
                   (p or {}).get('reason'), json.dumps(inputs, ensure_ascii=False), DISCLAIMER]
            writer.writerow([csv_safe(v) for v in row])
    return ('\ufeff' + output.getvalue()).encode('utf-8')


def records_pdf(session):
    s = record_context(session)
    font = 'HeatTimeNanum'
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(Path(__file__).parent / 'assets/fonts/NanumGothic-Regular.ttf')))
    # NanumGothic lacks U+2103: otherwise Celsius silently becomes .notdef/NUL.
    # Matplotlib's bundled DejaVu Sans provides the unit glyph (its own license).
    unit_font='HeatTimeUnits'
    if unit_font not in pdfmetrics.getRegisteredFontNames():
        from matplotlib import get_data_path
        pdfmetrics.registerFont(TTFont(unit_font,str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf')))
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=38, leftMargin=38, topMargin=36, bottomMargin=44,
                            title='HeatTime 운영 판단 기록', author='HeatTime')
    style = ParagraphStyle('body', fontName=font, fontSize=9, leading=14, wordWrap='CJK')
    title = ParagraphStyle('title', parent=style, fontSize=17, leading=24, spaceAfter=12)
    story = []
    def para(text, heading=False):
        safe=escape(str(text)).replace('℃',f'<font name="{unit_font}">℃</font>')
        story.extend([Paragraph(safe, title if heading else style), Spacer(1, 4)])
    para('히트타임 · 경기 운영 판단 기록', True)
    para(s['tournament']['name']); para(s['label']); para('세션: ' + s['id'])
    para(f"대회 일자 {s['tournament']['date_start']}~{s['tournament']['date_end']} / 연령 {s['tournament']['age_group']}")
    para('정책: ' + s['policy']['name']); para('출처: ' + s['policy']['source_ref']); para(verification_text(s['policy']['verification']))
    source_labels = s['policy'].get('labels')
    if source_labels:
        # W-1: stage 0 is shown as '통상 운영'; the guideline's own label stays visible with its source.
        para('단계 표시: ' + ' · '.join(f"{i} {display_label(l)}" for i, l in enumerate(source_labels))
             + ' / 원 지침 단계명(출처 표기): ' + ' · '.join(f"{i} {l}" for i, l in enumerate(source_labels)))
    para('연령 보정은 설계 가정 · 전문가 자문 필요. 최종 판단은 운영자.')
    para('WBGT 설정: ' + json.dumps(s['engine_settings'], ensure_ascii=False))
    para('경기 운영 설정: ' + json.dumps(s['schedule_settings'], ensure_ascii=False))
    d = s.get('decision')
    if d:
        para(f"운영자 {d['operator_name']} / 조치 {OPERATOR_ACTIONS.get(d['operator_action'], d['operator_action'])} / 시각 {kst(d['timestamp'])}")
        para('판단 사유: ' + d['reason']); para('판단 시점 입력을 고정 보존한 기록입니다.')
    else:
        para('운영자 조치: 미결정 · 제안은 승인된 일정이 아닙니다.')
    if s.get('proposal'):
        p = s['proposal']
        para(f"공통 {len(p['common_match_ids'])}경기 열 노출 점수 {p['original_heat_score']} → {p['proposed_heat_score']} / 연기 {p['postponed_count']}경기 별도 집계")
        para(f"선택 방법 {p.get('selected_method','과거 고정 제안')} / CP-SAT 상태 {p.get('cp_sat_status',p['solver'])} / 최소 연기 증명 {'확인' if p['coverage_optimal'] else '미확정 · 불가능 증명 아님'}")
    if s.get('data_origin')=='kma_observed':
        para('전체 입력과 알림은 함께 내려받는 JSON에 보존됩니다. 기상청 관측 시간자료를 사용하며 대회·팀·구장은 가상 예시입니다. 현장 WBGT 정확도 검증은 별도입니다.')
        para('일사: 정시 h의 위험 구간 [h, h+1)에는 같은 구간을 덮는 h+1시 관측(icsr, 직전 1시간 에너지 MJ/m²)을 시간평균 W/m²로 변환해 사용. 결측 일사는 같은 구간의 기존 모델 추정을 쓰며 관측0으로 대체하지 않습니다.')
        para(f"관측 일사 결측 {s['observation_summary']['solar_missing_hours']}시간(동일 관측소 기준, 구장 수만큼 중복 집계하지 않음)")
        para('관측 원본 SHA256: '+s['observation_summary']['original_sample_sha256'])
    else:
        para('전체 입력과 알림은 함께 내려받는 JSON에 보존됩니다. 기상은 합성(가상 예시) 입력이고 대회·팀·구장도 가상 예시입니다. 비교 일사량은 합성 예시이며 실제 관측 정확도 검증은 보류입니다.')
    story.append(PageBreak())
    para('구장 × 시간 단계표', True)
    para('칸마다 단계 번호와 판정값(℃, WBGT 추정에서 정한 값)을 적었습니다. 단계는 색과 함께 빗금 밀도로도 구분하므로 흑백으로 인쇄해도 읽을 수 있습니다. 0단계는 빗금 없음, 1단계는 성긴 빗금, 2단계는 촘촘한 빗금, 3단계는 교차 빗금, 4단계는 진한 단색입니다.')
    story.append(stage_grid(s, A4[0] - 76, font, unit_font))
    for m in s['matches']:
        story.append(PageBreak()); rec, a, p, evidence = match_context(s, m)
        para(m['round'] + ' · ' + match_name(m['id']) + f" ({m['id']})", True)
        para('가상 예시 · ' + team_name(s, m['team_a']) + ' vs ' + team_name(s, m['team_b']))
        para('원래 일정: ' + kst(m['scheduled_start']) + ' / 구장: ' + venue_name(s, m['venue_id']))
        if rec['wbgt_c'] is None:
            para(f"WBGT 추정: 기상 자료 누락 · 산정하지 않음 / 단계 {rec['level']} {stage_name(s, rec['level'])} (자료 누락 시 배정 보류) · 운영자 확인 필요")
        else:
            para(f"WBGT 추정 {rec['wbgt_c']}℃ / 범위 {rec['wbgt_low_c']}~{rec['wbgt_high_c']}℃ / 단계 {rec['level']} {stage_name(s, rec['level'])}")
        para('원래 일정 권고: ' + rec['detail'])
        if a:
            para(f"운영 조치: {kst(a['start'])}~{kst(a['end'])[11:]} / {venue_name(s, a['venue_id'])} / {MATCH_ACTIONS.get(a['action'], a['action'])}")
            para('쿨링브레이크 시각: ' + (', '.join(kst(t)[11:] for t in a['cooling_times']) or '계획 없음'))
        elif p:
            para('운영 조치: 연기 / 사유: ' + p['reason'])
        else:
            para('운영 조치: ' + OPERATOR_ACTIONS.get((d or {}).get('operator_action'), '미결정'))
        for name, r in evidence:
            block_start=len(story)
            inputs = r['inputs']; w = inputs['weather']; solar = inputs['solar']; venue = inputs['venue']
            para(f"{name} 근거 {kst(r['valid_time'])} / {venue_name(s, r['venue_id'])} / WBGT 추정 {r['wbgt_c']}℃ (범위 {r['wbgt_low_c']}~{r['wbgt_high_c']}℃), 단계 {r['level']} {stage_name(s, r['level'])}, 판정값(추정) {r['decision_wbgt_c']}℃(위 추정·범위에서 정한 값, 소수 첫째 자리)")
            para(explanation(r))
            comparison=breakdown(r)
            width=inputs['settings']['uncertainty_c']
            para(f"분석용 보정0℃·중앙값 WBGT 추정: {comparison['counterfactual_c']:.3f}℃ (범위 {comparison['counterfactual_c']-width:.3f}~{comparison['counterfactual_c']+width:.3f}℃) / 단계 {comparison['counterfactual_level']}. 설정/승인 변경 없음.")
            para(f"입력 기온 {w['ta_c']}℃ / 습도 {w['rh_pct']}% / 풍속 {w['ws_ms']}m/s / 보정 풍속 {inputs['wind_2m_ms']:.3f}m/s")
            para(f"사용 일사 {solar['used_wm2']:.1f}W/m² ({solar['source']}) / 일사량 추정 {solar['estimated_wm2']:.1f}W/m² (범위 {solar['low_wm2']:.1f}~{solar['high_wm2']:.1f}W/m²)")
            para(f"자료 {SOURCES.get(w['source'], w['source'])} / {'합성 기상(가상 예시)' if w['is_mock'] else '실제 관측 기상(가상 예시 아님)'} / 수집 시각 {w['fetched_at']}")
            if not w['is_mock'] and w.get('provenance'):
                provenance=w['provenance']
                para(f"기상청 관측 자료({provenance['station_name']} {w['station_id']}·{r['valid_time'][:10]})")
                if provenance['solar_energy_mj_m2'] is None:
                    para('일사 관측 에너지 결측 · 모델 추정 사용')
                else:
                    para(f"일사 관측 에너지 {provenance['solar_energy_mj_m2']}MJ/m² / 구간 {provenance['solar_interval_start']}~{provenance['solar_interval_end']}")
            calibration = inputs['calibration']
            para(f"구장 보정 {venue['field_offset_c']}℃ / 표면 {SURFACES.get(venue['surface'], venue['surface'])} / 그늘 {SHADES.get(venue['shade'], venue['shade'])} / "
                 + (f"현장 보정 {calibration[0]:+.3f}℃(폭 {calibration[1]:.3f}℃)" if calibration else '현장 보정 없음'))
            para('가정: ' + ', '.join(inputs['assumptions']))
            para('산정 방법: ' + r['method_version']); para('입력 해시: ' + r['inputs_hash'])
            block=story[block_start:];del story[block_start:];story.append(KeepTogether(block))
        if not evidence:
            para('근거 자료 누락 · 운영자 확인 필요')
    def footer(canvas, page):
        canvas.setFont(font, 9); canvas.drawString(38, 24, DISCLAIMER)
        canvas.drawRightString(A4[0] - 38, 24, str(page.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
