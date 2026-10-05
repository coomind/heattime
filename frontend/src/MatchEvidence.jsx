import React from 'react';
import DecisionBreakdown from './DecisionBreakdown.jsx';
import {capturedRiskRows} from './decision-breakdown.js';
const states={unapproved:'아직 승인하지 않은 자동 제안',accepted_proposal:'승인된 자동 제안',superseded_proposal:'수정 전 자동 제안 · 실제 적용 일정과 다릅니다',rejected_proposal:'거절된 자동 제안 · 적용되지 않았습니다',approved:'승인 시점의 적용 일정',rejected:'제안 거절 · 적용 일정 없음'};
const time=v=>v?new Date(v).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}):'없음';
const value=v=>v===null||v===undefined?'자료 없음':Number(v).toFixed(3);
export default function MatchEvidence({evidence,onInput,capturedRisks}){
 const e=evidence,c=e.constraints,r=e.recommendation;
 return <section className="card match-evidence"><h2>{e.match.round} · {e.match.id} · 일정 근거</h2>
  <p className="evidence-assumptions">{states[e.state]} · 가상 예시 대회 · {e.label}</p>
  {!e.assignment?<p className="postponed">{e.postponed_reason?'연기 — '+e.postponed_reason:'적용한 배정이 없습니다.'}</p>:<>
   <div className="evidence-grid"><div><b>원래 일정</b><p>{time(e.match.scheduled_start)}</p><p>WBGT 추정 {value(e.original.wbgt_c)}℃<br/>범위 {value(e.original.wbgt_low_c)}~{value(e.original.wbgt_high_c)}℃</p></div>
   <div><b>{e.view==='approved'?'승인 일정':'자동 제안'}</b><p>{time(e.assignment.start)} → {time(e.assignment.end)}<br/>{e.venue_name}</p><p>WBGT 추정 {value(r.wbgt_c)}℃<br/>범위 {value(r.wbgt_low_c)}~{value(r.wbgt_high_c)}℃ · 위험 단계 {r.level}</p><p>{r.detail} · 권고 반영 {r.duration_min}분<br/>쿨링브레이크 {e.assignment.cooling_times.map(time).join(', ')||'없음'}</p></div></div>
   <h3>경기 운영 제약의 실제 확인값</h3><p>기존 설정과 검사 결과를 표시합니다. 단축 전 계획 구간도 권고 산정에서 보수적으로 확인할 수 있습니다.</p>
   <p>운영 {time(c.open)}~{time(c.close)} · {c.has_lights?'조명 있음': '조명 없음 · 일몰 '+time(c.sunset)}<br/>적용 마감 {time(c.effective_close)} · 종료+정리 {c.cleanup_min}분 = {time(c.end_with_cleanup)} · {c.operating_ok?'충족':'운영자 확인 필요'}</p>
   <div className="table-scroll"><table aria-label="경기별 제약 근거"><thead><tr><th>조건</th><th>관련 경기·팀</th><th>실제값 / 기준</th><th>확인</th></tr></thead><tbody>
    {c.rest.map(row=><tr key={'rest-'+row.match_id}><td>{row.possible_participants?'진출 가능 팀 휴식':'팀 휴식'}</td><td>{row.match_id} · {row.team_names.join(', ')}</td><td>{row.gap_min}분 / 최소 {row.required_min}분</td><td>{row.ok?'충족':'미충족'}</td></tr>)}
    {c.cleanup.map(row=><tr key={'cleanup-'+row.match_id}><td>같은 구장 정리</td><td>{row.match_id}</td><td>{row.gap_min}분 / 최소 {row.required_min}분</td><td>{row.ok?'충족':'미충족'}</td></tr>)}
    {c.dependencies.map(row=><tr key={'dep-'+row.match_id}><td>선행 경기</td><td>{row.match_id}</td><td>종료 {time(row.end)}</td><td>{row.ok?'충족':'미충족'}</td></tr>)}
   </tbody></table></div>
   <p>{c.schedule_errors.length?'제약 확인: '+c.schedule_errors.join(', '):'이 일정의 기존 하드 제약 검사 통과'} · {e.solver}{!e.coverage_optimal&&' · 최적성/최소 연기 증명 미확정'}</p>
   <DecisionBreakdown risks={capturedRiskRows(e.risks,capturedRisks)} policy={e.policy}/><details><summary>제안 구장의 시간별 WBGT 추정과 범위</summary><div className="table-scroll"><table aria-label="제안 구장 시간자료"><thead><tr><th>KST 시각</th><th>중앙값 / 범위 ℃</th><th>판정값 / 단계</th></tr></thead><tbody>{e.risks.map(risk=><tr key={risk.valid_time}><td>{time(risk.valid_time)}</td><td>추정 {value(risk.wbgt_c)} / {value(risk.wbgt_low_c)}~{value(risk.wbgt_high_c)}</td><td>{value(risk.decision_wbgt_c)} / {risk.level}{onInput&&<button className="chip" onClick={()=>onInput(risk.venue_id,risk.valid_time,e.view)}>입력 근거</button>}</td></tr>)}</tbody></table></div></details>
  </>}
  <p>제약 충족은 안전 보장이 아닙니다. 이 표는 특정 제약이 연기의 유일한 원인임을 증명하지 않습니다. 최종 판단은 운영자가 합니다.</p>
 </section>;
}
