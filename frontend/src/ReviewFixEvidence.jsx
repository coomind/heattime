import React from 'react';
import data from './demo/review-fix-summary.json';
export default function ReviewFixEvidence(){
 return <details className="card"><summary>수정 후 결과 선택 검증 · 모든93조건</summary><p>동일 기본값·관측 입력·10초 탐색. 특정 가상 대진의 내부 검사이며 사람/건강/대회 일반의 우위가 아닙니다. 단순 대안 이상의 배정은 선택 규칙으로 확보한 성질입니다. 최적화의 독립 우위로 해석하지 않습니다.</p>
 <div className="table-scroll"><table aria-label="수정 후 전체 대진 검증"><thead><tr><th>가상 대진</th><th>과거 엔진</th><th>최선 단순 방식</th><th>수정 후 선택</th><th>CP-SAT 상태</th></tr></thead><tbody>{Object.entries(data.summary).map(([teams,r])=><tr key={teams}><td>{teams}팀 / {r.cases}조건</td><td>{r.previous_assigned}</td><td>{r.baseline_assigned}</td><td>{r.selected_assigned}</td><td>{Object.entries(r.statuses).map(([name,count])=>`${name} ${count}`).join(' / ')}</td></tr>)}</tbody></table></div>
 <p>두 열세 구간 수정: {data.regressions.map(r=>`${r.start}~${r.end}: ${r.previous_assigned}→${r.selected}배정 (${r.cp_sat_status})`).join(' / ')}. FEASIBLE은 최소 연기/비용 최적성 증명이 아닙니다. 아래 이전 분석과 버전/교집합을 구분합니다.</p></details>
}
