import React from 'react';
import {stageWindow} from './stage-window.js';
const clock=min=>new Date(min*60000).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Seoul'});
const hourOf=t=>Number(String(t).slice(11,13));
function line(label,w,match,stageLabel,actualEnd){
  if(w.missing)return <li>{label}: 기상 자료가 빠진 시간대가 있어 단계를 정하지 않았습니다.</li>;
  const hours=w.hours.map(h=>hourOf(h.time)+'시').join(', ');
  const kick=w.hours[0];
  return <li><b>{label}</b> 단계 판정 창은 {clock(w.startMin)}~{clock(w.endMin)}입니다({w.duration}분{w.duration>w.base?', 쿨링브레이크 포함':''}{actualEnd&&actualEnd<w.endMin?', 단축 전 길이 기준':''}). 이 창에 걸친 {hours} 시간대 가운데 가장 높은 {w.level}단계({stageLabel(w.level)})를 경기 단계로 씁니다.
    {actualEnd&&actualEnd<w.endMin&&<> 실제 경기는 시간을 줄여 {clock(actualEnd)}에 끝납니다.</>}
    {kick&&kick.level!==w.level&&<> 킥오프 시각 칸({hourOf(kick.time)}시)은 {kick.level}단계({stageLabel(kick.level)})이지만, 창이 다음 시간대까지 걸쳐 경기 단계가 달라졌습니다.</>}</li>;
}
export default function StageWindowNote({session,detail,stageLabel}){
  const m=detail.match,cool=session.engine_settings?.cooling_min??3;
  const original=stageWindow(m,session.risks,m.venue_id,m.scheduled_start,cool);
  const a=session.proposal?.assignments?.find(x=>x.match_id===m.id);
  const proposed=a&&stageWindow(m,session.risks,a.venue_id,a.start,cool);
  return <section className="stage-window" aria-labelledby="stage-window-title">
    <h3 id="stage-window-title">경기 단계를 정한 방법</h3>
    <p>경기 단계는 킥오프부터 단축 전 경기 길이(하프 휴식 포함, 2단계면 쿨링브레이크 포함)까지 걸친 시간대 가운데 가장 높은 단계입니다. 그래서 히트맵 한 칸의 단계와 경기 단계가 다를 수 있습니다.</p>
    <ul>{line('원래 일정:',original,m,stageLabel)}{proposed&&line('제안 일정:',proposed,m,stageLabel,new Date(a.end).getTime()/60000)}</ul>
  </section>;
}
