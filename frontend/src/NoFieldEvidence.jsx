import React,{useState} from 'react';
const names={existing_heat_first:'기존 열 노출 우선',earliest_input:'이른 시간 우선',earliest_reverse:'이른 시간 우선(역순)',weighted_critical:'선행 경기와 가중 비용 우선',best_of_four:'4종 중 날짜별 가장 유리한 결과'};
export default function NoFieldEvidence(){
 const [data,setData]=useState(null),[error,setError]=useState(false);
 async function load(e){if(!e.currentTarget.open||data)return;setError(false);try{const {default:url}=await import('./demo/no-field-analysis.json?url');const r=await fetch(url);if(!r.ok)throw Error();setData(await r.json());}catch{setError(true);}}
 const best=data?.summary.baselines.best_of_four;
 const zeroDays=data?data.days.filter(d=>d.cp.assigned===0).length:0;
 const statuses=data?Object.entries(data.days.reduce((a,d)=>{a[d.cp_solver]=(a[d.cp_solver]||0)+1;return a;},{})).map(([k,v])=>`${k} ${v}일`).join(', '):'';
 return <details className="card no-field-evidence" onToggle={load}><summary>실측 없이 확인한 기술 근거: 더 강한 비교와 조건 변화</summary>
 {error&&<p role="alert">검증 자료를 불러오지 못했습니다.</p>}
 {data&&<><p>2026-10-21 기준으로 다시 계산한 고정 제안을 비교합니다. 지금 화면에서 바꾼 설정으로 새로 계산한 결과는 아닙니다.</p><p>{data.label}. 62일 모두 같은 기본값과 하드 제약을 썼습니다.</p><h3>유리하게 선택한 단순 방식과도 비교</h3><p>{data.baseline_rule} 사람이 짠 일정, 경쟁 제품, 실제 업무 시간과 비교한 결과는 아닙니다.</p>
 <p>강한 단순 기준 대비 배정 {best.assigned} → {data.summary.cp_assigned}건, 완전 배정 {best.complete_days} → {data.days.filter(d=>d.cp.postponed===0).length}일. 공통 경기 열 노출 점수 {best.baseline_common_heat.toLocaleString()} → {best.cp_common_heat.toLocaleString()} ({((best.baseline_common_heat-best.cp_common_heat)/best.baseline_common_heat*100).toFixed(2)}% 감소). 건강 효과나 실제 살린 경기 수가 아닙니다.</p>
 <div className="table-scroll" tabIndex={0}><table aria-label="단순 방식4종 전체 비교"><thead><tr><th>단순 방식</th><th>배정/연기 합계</th><th>15경기 전부 배정</th><th>같은 배정 수에서 CP-SAT 비용 승/패 일수</th></tr></thead><tbody>{Object.entries(data.summary.baselines).map(([k,r])=><tr key={k}><td>{names[k]}</td><td>{r.assigned} / {r.postponed}</td><td>{r.complete_days}일</td><td>{r.equal_coverage_secondary_win_days} / {r.equal_coverage_secondary_loss_days}일</td></tr>)}</tbody></table></div>
 <p>배정 수가 같은 날은 열 노출, 시간 이동, 구장 이동을 합친 기존 가중 비용으로 비교합니다. 공통 열 노출은 날짜마다 두 방식이 함께 배정한 경기만 더한 값이라, 원래 일정에서 제안 일정으로 바뀐 점수와는 다른 비교입니다. 이 분석에 쓴 CP-SAT 결과 상태는 {statuses}입니다(Windows 개발 PC). 10초 안에 최적을 증명하지 못한 날은 실행 환경에 따라 결과가 달라질 수 있습니다.</p>
 <h3>고정 일정의 취약 조건도 공개</h3><p>{data.scenario_rule} 배정이 0경기인 {zeroDays}일은 검사할 일정이 없어 대상에서 뺐습니다.</p><div className="table-scroll" tabIndex={0}><table aria-label={`${data.days.length-zeroDays}일 고정 일정 조건 변화`}><thead><tr><th>가정</th><th>대상 일수</th><th>같은 선택의 제약 통과</th><th>권고·제약 재검토 일수</th></tr></thead><tbody>{Object.entries(data.summary.scenarios).map(([k,r])=><tr key={k}><td>{k==='missing_critical_hour'?'주의 지점 1시간 누락':k.replace('wbgt_','WBGT ')+'℃'}</td><td>{r.applicable_days}</td><td>{r.same_choices_valid_days}</td><td>{r.needs_review_days}</td></tr>)}</tbody></table></div>
 <p>온도가 낮아져도 경기 단축이 풀리거나 쿨링브레이크가 붙으면 종료 시각과 휴식 조건이 바뀔 수 있습니다. 재검토 일수는 재배치한 뒤에도 개최할 수 없는 날의 수가 아닙니다. 실제 WBGT 정확도, 구매 수요, 현장 효과는 검증하지 않았습니다.</p>
 <details><summary>62일 강한 기준 비교 원자료</summary><div className="table-scroll" tabIndex={0}><table aria-label="62일 강한 기준 비교"><thead><tr><th>날짜</th><th>단순 방식 배정</th><th>CP-SAT 배정</th><th>공통 경기</th><th>단순 → CP-SAT 열 노출</th></tr></thead><tbody>{data.days.map(d=><tr key={d.date}><td>{d.date}</td><td>{d.baselines.best_of_four.assigned}</td><td>{d.cp.assigned}</td><td>{d.comparisons.best_of_four.common_match_ids.length}</td><td>{d.comparisons.best_of_four.common_match_ids.length?d.comparisons.best_of_four.baseline_common_heat+' → '+d.comparisons.best_of_four.cp_common_heat:'공통 경기 없음'}</td></tr>)}</tbody></table></div></details>
 </>}
 </details>;
}
