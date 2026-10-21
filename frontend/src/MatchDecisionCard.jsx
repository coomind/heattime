import React from 'react';
import {round1} from './format.js';
import {breakdown} from './decision-breakdown.js';
import {stageWindow} from './stage-window.js';
import {matchName} from './labels.js';
// Top of the match detail: the decision value that set this match's stage, read from the engine's frozen
// hourly risks (the highest decision value inside the stage window), with its formula and the range for reference.
export function decisionHour(session,match,risks){
 const w=stageWindow(match,risks,match.venue_id,match.scheduled_start,session.engine_settings?.cooling_min??3);
 if(!w||w.missing||!w.hours?.length)return null;
 const times=new Set(w.hours.map(h=>h.time));
 return risks.filter(r=>r.venue_id===match.venue_id&&times.has(r.valid_time))
  .reduce((best,r)=>!best||r.decision_wbgt_c>best.decision_wbgt_c?r:best,null);
}
export default function MatchDecisionCard({session,match,risks,level,stageLabel,venueName}){
 const r=decisionHour(session,match,risks);
 if(!r)return <section className="card decision-card"><p className="dc-label">이 경기의 판정값</p><p>기상 자료가 빠진 시간대가 있어 판정값을 정하지 않았습니다. 운영자 확인이 필요합니다.</p></section>;
 const b=breakdown(r);const n=x=>Number(x).toFixed(3);
 return <section className="card decision-card" aria-labelledby="decision-card-title">
  <p className="dc-label" id="decision-card-title">{matchName(match.id)}의 판정값 ({r.valid_time.slice(11,16)} 시간대, {venueName})</p>
  <div className="dc-main"><span className="dc-value">{round1(r.decision_wbgt_c)}<span className="dc-unit">℃</span></span>
   <span className={'chip-stage dc-chip risk-'+level}>단계 {level} {stageLabel(level)}</span></div>
  <p className="dc-formula">관측 기반 추정 <span className="mono">{n(b.model)}</span> + 구장 보정 <span className="mono">{n(b.field)}</span>{b.surface||b.calibration?<> + 표면과 현장 보정 <span className="mono">{n(b.surface+b.calibration)}</span></>:null}{b.upper?<> + 상단 폭 <span className="mono">{n(b.upper)}</span></>:null} = <span className="mono">{n(b.unrounded)}</span> → 판정값 <span className="mono">{round1(r.decision_wbgt_c)}℃</span></p>
  <p className="dc-range">추정 범위 {round1(r.wbgt_low_c)}~{round1(r.wbgt_high_c)}℃ (참고용이며 판정에 쓰지 않습니다)</p>
 </section>;
}
