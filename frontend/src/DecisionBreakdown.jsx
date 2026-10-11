import React from 'react';
import {breakdown,counterLevel} from './decision-breakdown.js';
const n=x=>Number(x).toFixed(3);
export default function DecisionBreakdown({risks,policy}){
 return <details className="card" open><summary>판정값 분해 · 가정 비교</summary>
 <p>모든 값은 WBGT 추정입니다. 모델 추정 + 구장 보정 + 유소년 상단 폭 = 합계이며, 합계를 소수 첫째 자리로 반올림한 값이 판정값(추정)입니다. 성인은 중앙값을 사용하므로 상단 폭은0℃입니다. 현장·표면 보정이 있으면 별도로 표시합니다. 범위는 현장 검증된 신뢰구간이 아닙니다.</p>
 <p>보정0℃·중앙값 판정은 분석용 비교입니다. 설정·일정·운영자 승인을 바꾸지 않습니다. 같은 모델/기상과 현장 보정은 유지합니다. 표시 반올림값 기준이며 연령 단계 상향을 별도로 사용했다면 이 비교에서는 제외합니다.</p>
 <div className="table-scroll"><table aria-label="판정값 분해와 분석용 비교"><thead><tr><th>시각</th><th>모델 추정 ℃</th><th>구장 보정 ℃</th><th>표면/현장 보정 ℃</th><th>상단 폭 ℃</th><th>합계(반올림 전) ℃</th><th>판정값(추정) ℃ / 단계</th><th>보정0℃·중앙값 WBGT 추정 ℃ (범위) / 단계</th></tr></thead><tbody>{risks.map(r=>{const b=breakdown(r);return <tr key={r.venue_id+r.valid_time}><td>{r.valid_time.slice(11,16)}</td><td>{n(b.model)}</td><td>{n(b.field)}</td><td>{n(b.surface)} / {n(b.calibration)}</td><td>{n(b.upper)}</td><td>{n(b.unrounded)}</td><td>{Number(b.decision).toFixed(1)} / {r.level}</td><td>{n(b.counter)} ({n(b.counter-b.width)}~{n(b.counter+b.width)}) / {counterLevel(b.counter,policy,b.policyId)}</td></tr>})}</tbody></table></div></details>
}
