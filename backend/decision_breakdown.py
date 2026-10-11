"""Read-only explanation from rounded frozen risks; never changes policy or inputs."""
from .engine.policy import classify, policies, round_decision


def breakdown(risk):
    r=risk;inputs=r['inputs'];venue=inputs['venue'];settings=inputs['settings']
    field=venue['field_offset_c'];surface=settings['surface_offsets'].get(venue['surface'],0)
    calibration=(inputs.get('calibration') or (0,0))[0]
    native=round(r['wbgt_c']-field-surface-calibration,3)
    conservative=inputs.get('age_group') in policies()['age']['upper_bound_groups']
    upper=round(r['wbgt_high_c']-r['wbgt_c'],3) if conservative else 0.0
    unrounded=round(r['wbgt_c']+upper,3)
    # Counterfactual keeps the captured model/weather/calibration and drops only
    # field/surface offsets and use of the uncertainty upper bound.
    counter=round(r['wbgt_c']-field-surface,3)
    return {'model_c':native,'field_offset_c':field,'surface_offset_c':surface,
        'calibration_c':calibration,'upper_width_c':upper,'decision_unrounded_c':unrounded,
        'decision_c':r['decision_wbgt_c'],
        'level':r['level'],'counterfactual_c':counter,
        'counterfactual_decision_c':round_decision(counter),
        'counterfactual_level':classify(round_decision(counter),inputs['policy_id']),
        'age_escalation':settings['age_escalation'],
        'note':'분석용 비교 · 보정0℃·중앙값 판정 · 설정/승인 변경 없음 · 표시 반올림값 기준 · 현장 실측 아님'}


def explanation(risk):
    b=breakdown(risk)
    text=f"모델 추정 {b['model_c']:.3f}℃ + 구장 보정 {b['field_offset_c']:+.3f}℃"
    if b['surface_offset_c']:text+=f" + 표면 보정 {b['surface_offset_c']:+.3f}℃"
    if b['calibration_c']:text+=f" + 현장 보정 {b['calibration_c']:+.3f}℃"
    text+=(f" + 판정 상단 폭 {b['upper_width_c']:.3f}℃ = {b['decision_unrounded_c']:.3f}℃"
           f" → 판정값(소수 첫째 자리 반올림) {b['decision_c']:.1f}℃ / 단계 {b['level']}")
    if b['age_escalation']:text+=' 연령 단계 상향은 숫자에 더하지 않고 별도로 적용됨.'
    return text
