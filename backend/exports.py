from io import BytesIO,StringIO
import csv,json
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak


def records_csv(s):
    output=StringIO(newline='');writer=csv.writer(output)
    writer.writerow(['가상 예시','match_id','WBGT 추정','low','high','level','action','operator_action','reason'])
    recs={r['match_id']:r for r in s['recommendations']}
    for m in s['matches']:
        r=recs[m['id']];d=s['decision'] or {}
        writer.writerow([s['label'],m['id'],r['wbgt_c'],r['wbgt_low_c'],r['wbgt_high_c'],r['level'],r['action'],d.get('operator_action','미결정'),d.get('reason','')])
    return ('﻿'+output.getvalue()).encode('utf-8')


def records_pdf(s):
    pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
    buf=BytesIO();doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=38,leftMargin=38,topMargin=38,bottomMargin=42)
    style=ParagraphStyle('body',fontName='HYSMyeongJo-Medium',fontSize=10,leading=16,wordWrap='CJK')
    title=ParagraphStyle('title',parent=style,fontSize=19,leading=26,spaceAfter=14)
    story=[]
    def para(text,heading=False):story.extend([Paragraph(escape(str(text)),title if heading else style),Spacer(1,5)])
    para('히트타임 · 경기 운영 판단 기록',True);para(s['tournament']['name']);para(s['label'])
    para('정책: '+s['policy']['name']);para('출처: '+s['policy']['source_ref']);para(s['policy']['verification'])
    para('연령 보정은 설계 가정 · 전문가 자문 필요. 최종 판단은 운영자.')
    if s['decision']:
        d=s['decision'];para(f"운영자: {d['operator_name']} / 조치: {d['operator_action']} / 시각: {d['timestamp']}");para('사유: '+d['reason'])
    else:para('운영자 조치: 미결정')
    recs={r['match_id']:r for r in s['recommendations']}
    for m in s['matches']:
        story.append(PageBreak());r=recs[m['id']]
        para(m['round']+' · '+m['id'],True);para('가상 예시 · '+m['team_a']+' vs '+m['team_b'])
        para('원래 일정: '+m['scheduled_start']+' / 구장: '+m['venue_id'])
        para(f"WBGT 추정 {r['wbgt_c']}℃ / 범위 {r['wbgt_low_c']}~{r['wbgt_high_c']}℃ / 단계 {r['level']}")
        para('권고: '+r['detail'])
        risks=[x for x in s['risks'] if x['venue_id']==m['venue_id'] and x['valid_time'][:10]==m['scheduled_start'][:10]]
        for x in risks:
            inputs=x['inputs'];w=inputs['weather'];solar=inputs['solar']
            para(f"{x['valid_time']} | WBGT 추정 {x['wbgt_c']}℃ ({x['wbgt_low_c']}~{x['wbgt_high_c']}℃), 단계 {x['level']}, 판정값 {x['decision_wbgt_c']}℃")
            para(f"입력: 기온 {w['ta_c']}℃ / 습도 {w['rh_pct']}% / 풍속 {w['ws_ms']}m/s / 사용 일사 {solar['used_wm2']}W/m² / 자료 {w['source']} / 수집 {w['fetched_at']}")
            para('방법: '+x['method_version']+' / 해시: '+x['inputs_hash'])
        if s['decision']:
            a=next((a for a in s['decision']['assignments'] if a['match_id']==m['id']),None)
            p=next((p for p in s['decision']['postponed'] if p['match_id']==m['id']),None)
            para('운영 조치: '+(f"{a['start']} / {a['venue_id']} / {a['action']}" if a else ('연기: '+p['reason']) if p else s['decision']['operator_action']))
    def footer(canvas,doc):
        canvas.setFont('HYSMyeongJo-Medium',9);canvas.drawString(38,24,'본 자료는 의사결정 보조용 추정값');canvas.drawRightString(A4[0]-38,24,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
