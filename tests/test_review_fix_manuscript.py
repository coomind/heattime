import json,re
from pathlib import Path
from datetime import timedelta
from backend.schedule.demo import demo_tournament

ROOT=Path(__file__).resolve().parents[1]

def test_main_presentation_moves_statistics_to_appendix_and_discloses_selection_and_weather():
    s=(ROOT/'docs/presentation/slides.md').read_text(encoding='utf-8')
    main=s.split('## 부록 ·')[0]
    assert '29.36%' not in main and '62일 중 46일' not in main and '38.062' not in main
    # 2026-10-11 recalculation: the current figures (26.14%, 38.229, 47 incomplete days) also stay in the appendix.
    assert '26.14%' not in main and '62일 중 47일' not in main and '38.229' not in main
    # Demo date 2026-08-10 (2026-10-21 rule): 4 originally stopped, all 4 assigned, none postponed.
    assert '원래 중지 단계4경기 모두 제안 배정' in main and '31.6℃' in main and '운영시간 습도44~67%' in main
    # Postponement is shown on the 8/8 extreme scene (10 assigned / 5 postponed) in both the screen text and the script.
    assert '8월10일에는 연기 없음' in main and '8월8일(35.4℃)은10경기 배정/5경기 연기 제안' in main and '35.4℃였던8월8일에는10경기만 배정되고5경기가 연기 제안입니다' in main
    # The postponed 8/8 matches are named, not just counted.
    assert all(name in main for name in ('1조 2경기', '4조 1경기', '준결승 1', '준결승 2', '결승'))
    assert '39.79%' not in main and '2563' not in main.split('## 5 ·')[0]
    assert '연기 수 최소' in main and '원래 중지 경기의 배정 수 최대' in main
    assert '최적화가 언제나 단순 방식보다 낫다고 주장하지 않습니다' in main
    assert '구장 정리 간격을 어겨' in main and '8월4일' in main
    summary=json.loads((ROOT/'frontend/src/demo/review-fix-summary.json').read_text(encoding='utf-8'))
    result=json.loads((ROOT/'docs/competition-evidence/review-fix-results.json').read_text(encoding='utf-8'))
    assert summary['summary']==result['summary']

def test_reference_cleanup_violation_is_disclosed_not_a_feasible_baseline():
    _,_,matches,_=demo_tournament();by={m.id:m for m in matches}
    early,late=by['g1-1'],by['g4-1']
    nominal_end=early.scheduled_start+timedelta(minutes=early.duration_min+(early.halves-1)*early.half_break_min)
    assert early.venue_id==late.venue_id
    assert late.scheduled_start==nominal_end
    assert late.scheduled_start<nominal_end+timedelta(minutes=5)
    assert '유효한 일정/사람의 업무/건강 효과 비교가 아닙니다' in (ROOT/'frontend/src/App.jsx').read_text(encoding='utf-8')

def test_added_answers_fit_same_30_second_budget_and_do_not_claim_field_validation():
    qa=(ROOT/'docs/presentation/qa.md').read_text(encoding='utf-8')
    for i in (16,17,18):
        section=re.search(rf'(?ms)^## {i}\. .*?(?=^## |\Z)',qa).group(0)
        answer=section.split('**30초 목표 답변**',1)[1].split('**근거',1)[0].strip()
        assert len(re.sub(r'\s+',' ',answer))<=180
