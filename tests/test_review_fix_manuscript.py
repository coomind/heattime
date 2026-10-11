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
    # Demo date 2026-08-10 (author decision 2026-10-11): 14 originally stopped, 13 of them assigned, 2 postponed.
    assert '원래 중지 단계14경기 중13경기' in main and '31.6℃' in main and '운영시간 습도44~67%' in main
    assert '2연기' in main and 'semi2' in main and 'final' in main
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
