import React,{useState,useRef,useEffect} from 'react';
const names=id=>id==='missing_critical_hour'?'주의 지점 1시간 누락':id==='wbgt_+0'?'원래 추정값':`WBGT ${id.replace('wbgt_','')}℃`;
export default function PlanReview({api,session}){
 const [data,setData]=useState(null),[view,setView]=useState('proposed'),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const token=useRef(0),opened=useRef(false);
 useEffect(()=>{token.current++;setData(null);setError('');setBusy(false);},[session.id,session.proposal?.id,session.decision?.timestamp]);
 async function load(selected=view){const id=++token.current;setBusy(true);setError('');try{const value=await api('/sessions/'+session.id+'/plan-review?view='+selected);if(token.current===id)setData(value);}catch(e){if(token.current===id){setError(e.message);setData(null);}}finally{if(token.current===id)setBusy(false);}}
 return <details className="card plan-review" onToggle={e=>{opened.current=e.currentTarget.open;if(opened.current&&!data&&!busy)load();}}><summary>조건 변화 검토 · 추정 상승과 자료 누락</summary>
 <p>일정의 킥오프·구장을 고정하고 기존 권고와 제약을 다시 확인합니다. 가상 변화량은 실제 오차 범위나 확률이 아닙니다. 제안·승인·실제 날씨는 바뀌지 않습니다.</p>
 <label>검토할 일정<select value={view} onChange={e=>{setView(e.target.value);setData(null);if(opened.current)load(e.target.value);}}><option value="proposed">자동 제안</option><option value="approved" disabled={!session.decision||session.decision.operator_action==='rejected'}>승인된 일정</option></select></label>
 {busy&&<p role="status">조건을 검토하고 있습니다…</p>}{error&&<p className="error" role="alert">{error}</p>}
 {data&&<><h3>{data.plan_state}</h3><p>{data.label} · 기존 배정 {data.assigned} / 연기 {data.postponed}경기</p><p>{data.limitation}</p>
 {!data.assigned?<p>기존 배정0경기 · 검사할 일정이 없어 시나리오는 적용 대상이 아닙니다.</p>:<><div className="table-scroll"><table aria-label="고정 일정 조건 변화"><thead><tr><th>가정</th><th>중지 단계 경기</th><th>자료 누락 경기</th><th>단계·권고 변경</th><th>다시 확인한 제약</th></tr></thead><tbody>{[...data.scenarios,data.missing_case].map(r=><tr key={r.id}><td>{names(r.id)}</td><td>{r.blocked_match_ids.length}</td><td>{r.missing_match_ids.length}</td><td>{r.changed_match_ids.length}</td><td>{r.constraint_errors.length?r.constraint_errors.join(' · '):'통과'}{r.needs_review?' · 운영자 재검토':''}</td></tr>)}</tbody></table></div>
 <p>온도가 낮아져도 단축 해제·쿨링브레이크로 종료 시각이 바뀌면 휴식·일몰 등을 재검토해야 합니다. 여기서 배정 가능 수를 다시 풀거나 연기 결정을 내리지 않습니다.</p>
 <details><summary>경기별 중지 기준과 판정값의 차이</summary><p>{data.age_group} · 중지 조건: 판정값 {data.stop_comparison} {data.threshold_c}℃. 차이는 실제 측정 오차·여유 시간·안전성 지표가 아닙니다.</p><div className="table-scroll"><table aria-label="경기별 중지 기준 차이"><thead><tr><th>경기</th><th>참고 시각</th><th>WBGT 추정·범위</th><th>판정값</th><th>기준과 차이</th></tr></thead><tbody>{data.matches.map(r=><tr key={r.match_id}><td>{r.match_id}</td><td>{r.valid_time.slice(11,16)}</td><td>{r.wbgt_c.toFixed(3)}℃ · {r.wbgt_low_c.toFixed(3)}~{r.wbgt_high_c.toFixed(3)}℃</td><td>{r.decision_wbgt_c.toFixed(3)}℃</td><td>{r.stop_margin_c.toFixed(3)}℃</td></tr>)}</tbody></table></div></details></>}
 <details><summary>시나리오별 경기와 오류 상세</summary><pre>{JSON.stringify({변화:data.scenarios,누락:data.missing_case},null,2)}</pre></details></>}
 </details>;
}
