import React from 'react';
import data from './demo/review-fix-summary.json';
export default function ReviewFixEvidence(){
 return <details className="card"><summary>재실행 재현성 검증(93개 조건 전부)</summary><p>같은 기본값과 관측 입력으로 10초 탐색을 한 번 더 실행했습니다. 특정 가상 대진의 내부 검사이며, 사람이 짠 일정보다 낫다거나 건강 효과가 있다는 뜻이 아닙니다. 단순 대안보다 적게 배정하지 않는 것은 선택 규칙으로 보장한 성질이므로, 최적화가 따로 우월하다는 근거로 해석하지 않습니다.</p>
 <div className="table-scroll" tabIndex={0}><table aria-label="재실행 재현성 전체 대진 검증"><thead><tr><th>가상 대진</th><th>첫 실행</th><th>최선 단순 방식</th><th>재실행</th><th>재실행 CP-SAT 상태</th></tr></thead><tbody>{Object.entries(data.summary).map(([teams,r])=><tr key={teams}><td>{teams}팀 / {r.cases}조건</td><td>{r.previous_assigned}</td><td>{r.baseline_assigned}</td><td>{r.selected_assigned}</td><td>{Object.entries(r.statuses).map(([name,count])=>`${name} ${count}`).join(' / ')}</td></tr>)}</tbody></table></div>
 <p>같은 입력을 한 번 더 풀었을 때 배정 수가 달라진 조건: {data.regressions.length?data.regressions.map(r=>`${r.teams}팀 ${r.start}~${r.end}에서 ${r.previous_assigned}경기에서 ${r.selected}경기 배정으로 바뀜(${r.cp_sat_status})`).join(', '):'없음'}. 동점 처리는 고정되어 OPTIMAL(최적 증명) 결과는 매번 같지만, 10초 안에 증명하지 못한 FEASIBLE 결과는 실행 환경에 따라 달라질 수 있습니다.</p></details>
}
