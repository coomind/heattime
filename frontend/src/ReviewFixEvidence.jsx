import React from 'react';
import data from './demo/review-fix-summary.json';
export default function ReviewFixEvidence(){
 return <details className="card"><summary>재실행 재현성 검증 · 모든93조건</summary><p>동일 기본값·관측 입력·10초 탐색. 특정 가상 대진의 내부 검사이며 사람/건강/대회 일반의 우위가 아닙니다. 단순 대안 이상의 배정은 선택 규칙으로 확보한 성질입니다. 최적화의 독립 우위로 해석하지 않습니다.</p>
 <div className="table-scroll" tabIndex={0}><table aria-label="재실행 재현성 전체 대진 검증"><thead><tr><th>가상 대진</th><th>첫 실행</th><th>최선 단순 방식</th><th>재실행</th><th>재실행 CP-SAT 상태</th></tr></thead><tbody>{Object.entries(data.summary).map(([teams,r])=><tr key={teams}><td>{teams}팀 / {r.cases}조건</td><td>{r.previous_assigned}</td><td>{r.baseline_assigned}</td><td>{r.selected_assigned}</td><td>{Object.entries(r.statuses).map(([name,count])=>`${name} ${count}`).join(' / ')}</td></tr>)}</tbody></table></div>
 <p>같은 입력을 한 번 더 풀었을 때 배정 수가 달라진 조건: {data.regressions.length?data.regressions.map(r=>`${r.teams}팀 ${r.start}~${r.end}: ${r.previous_assigned}→${r.selected}배정 (${r.cp_sat_status})`).join(' / '):'없음'}. 동점 처리는 고정되어 OPTIMAL(최적 증명) 결과는 매번 같지만, 10초 안에 증명하지 못한 FEASIBLE 결과는 실행 환경에 따라 달라질 수 있습니다.</p></details>
}
