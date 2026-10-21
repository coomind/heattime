import React from 'react';
import {round1} from './format.js';
import {breakdown,counterLevel} from './decision-breakdown.js';
const n=x=>Number(x).toFixed(3);
const NAMES=['통상 운영','주의','경계','엄중경계','운동 중지'];
const chip=(level,policy)=>{const raw=policy?.labels?.[level];return <span className={'chip-stage risk-'+level}>단계 {level} {raw&&raw!=='거의 안전'?raw:NAMES[level]}</span>;};
// (나) rule: observed-weather estimate + venue offset = central estimate = decision value (rounded to 0.1℃).
// The hours the match touches are shown first; the whole day stays available below. The range is
// reference only, and the comparison box re-classifies the same frozen numbers (no setting change).
function Formula({rows,label,anyUpper,anyExtra,policy}){
 return <div className="table-scroll" tabIndex={0}><table aria-label={label}><thead><tr><th>시각</th><th className="num">관측 기반 추정 ℃</th><th className="num">구장 보정 ℃</th>{anyExtra&&<th className="num">표면 또는 현장 보정 ℃</th>}{anyUpper&&<th className="num">상단 폭 ℃</th>}<th className="num">중앙 추정 ℃</th><th className="num">판정값 ℃</th><th>단계</th><th className="num">추정 범위 ℃ (참고)</th></tr></thead>
 <tbody>{rows.map(({r,b})=><tr key={r.venue_id+r.valid_time}><td>{r.valid_time.slice(11,16)}</td><td className="num">{n(b.model)}</td><td className="num">+{n(b.field)}</td>{anyExtra&&<td className="num">{n(b.surface)} / {n(b.calibration)}</td>}{anyUpper&&<td className="num">+{n(b.upper)}</td>}<td className="num">{n(r.wbgt_c)}</td><td className="num">{Number(b.decision).toFixed(1)}</td><td>{chip(r.level,policy)}</td><td className="num">{round1(r.wbgt_low_c)}~{round1(r.wbgt_high_c)}</td></tr>)}</tbody></table></div>;
}
export default function DecisionBreakdown({risks,policy,focus}){
 const all=risks.map(r=>({r,b:breakdown(r)}));
 const picked=focus?.length?all.filter(x=>focus.includes(x.r.valid_time)):all;
 const anyUpper=all.some(x=>x.b.upper>0),anyExtra=all.some(x=>x.b.surface||x.b.calibration);
 const width=all.length?Number(all[0].b.width).toFixed(1):'1.5';
 return <details className="more decision-breakdown"><summary>판정값이 나온 과정(표와 분석용 비교)</summary>
 <p>판정값은 <b>관측 기반 추정 + 구장 보정 = 중앙 추정</b>을 소수 첫째 자리로 반올림한 값이며, 이 값으로 단계를 정합니다. 모든 값은 WBGT 추정이고 현장 실측이 아닙니다.{anyUpper?' 이 대회는 범위 상단으로 판정하도록 설정되어 상단 폭을 더했습니다.':''}</p>
 {picked.length<all.length&&<p className="fine">아래 표는 이 경기의 단계 판정 창에 걸친 시간입니다. 하루 전체 값은 맨 아래에서 펼쳐 볼 수 있습니다.</p>}
 <Formula rows={picked} label="판정값 계산식" anyUpper={anyUpper} anyExtra={anyExtra} policy={policy}/>
 <p className="fine">추정 범위는 중앙 추정 ±{width}℃입니다. 불확실성을 보여 주려는 표시이며 판정에 쓰지 않고, 현장에서 검증한 신뢰구간도 아닙니다.</p>
 <div className="compare-box"><h4>분석용 비교: 기준을 바꾸면 단계가 어떻게 달라지는가</h4>
  <p>같은 기상과 추정값을 다른 기준으로 다시 분류만 한 결과입니다. 설정, 일정, 운영자 승인은 바꾸지 않습니다.</p>
  <div className="table-scroll" tabIndex={0}><table aria-label="판정 기준 비교"><thead><tr><th>시각</th><th>지금 기준(중앙 추정)</th><th>범위 상단으로 판정하면</th><th>구장 보정 없이 판정하면</th></tr></thead>
  <tbody>{picked.map(({r,b})=><tr key={r.venue_id+r.valid_time}><td>{r.valid_time.slice(11,16)}</td><td><span className="num-inline">{Number(b.decision).toFixed(1)}℃</span> {chip(r.level,policy)}</td><td><span className="num-inline">{round1(r.wbgt_high_c)}℃</span> {chip(counterLevel(r.wbgt_high_c,policy,b.policyId),policy)}</td><td><span className="num-inline">{round1(b.counter)}℃</span> {chip(counterLevel(b.counter,policy,b.policyId),policy)}</td></tr>)}</tbody></table></div>
 </div>
 {picked.length<all.length&&<details className="day-formula"><summary>하루 전체 계산식 보기({all.length}시간)</summary><Formula rows={all} label="하루 전체 판정값 계산식" anyUpper={anyUpper} anyExtra={anyExtra} policy={policy}/></details>}
 </details>
}
