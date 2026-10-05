import React from 'react';
import {scheduleChanges} from './schedule-changes.js';

const time=value=>new Date(value).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});
const actions={none:'수분 보충',cooling_break:'쿨링브레이크',shorten:'시간 단축',move:'시간 이동',postpone:'연기'};
export default function ScheduleChanges({session,onSelect,onEvidence}){
  const rows=scheduleChanges(session),venues=new Map(session.venues.map(row=>[row.id,row.name]));
  const action=session.decision?.operator_action;
  return <section className="card schedule-changes"><h2>경기별 자동 제안 변경 내역</h2>
    <p>가상 예시 · {action==='modified'?'수정 전 자동 제안입니다. 승인한 수정안은 운영 기록에서 확인하세요.':action==='rejected'?'거절된 자동 제안이며 적용되지 않았습니다.':action==='accepted'?'승인된 자동 제안입니다.':'아직 승인하지 않은 자동 제안입니다.'} 킥오프·구장·연기 사유를 경기별로 확인하세요.</p>
    <div className="table-scroll"><table aria-label="경기별 자동 제안 변경 내역"><thead><tr><th>경기 / 원래 상세</th><th>원래 일정(KST)</th><th>자동 제안(KST)</th><th>변경과 조치</th></tr></thead><tbody>{rows.map(row=><tr key={row.match.id}>
      <td><button className="chip" onClick={()=>onSelect(row.match.id)} aria-label={row.match.id+' 원래 경기 상세'}>{row.match.round} · {row.match.id}</button></td>
      <td>{time(row.match.scheduled_start)}<small>{venues.get(row.match.venue_id)}</small></td>
      <td>{row.proposal?<>{time(row.proposal.start)}<small>{venues.get(row.proposal.venue_id)}</small><small>권고 반영 종료 {time(row.proposal.end)}</small></>:<>연기<small>{row.postponedReason||'결과 없음 · 운영자 확인 필요'}</small></>}</td>
      <td>{row.proposal?<>{row.deltaMinutes===0?'킥오프 유지':Math.abs(row.deltaMinutes)+'분 '+(row.deltaMinutes<0?'앞당김':'늦춤')}{row.venueChanged&&<small>구장 이동</small>}{row.movedFromStop&&<small>원래 중지 단계 → 제안 배정</small>}<small>{actions[row.proposal.action]||row.proposal.action} · 제안 위험 단계 {row.proposal.level}</small></>:<>연기 사유 확인</>}<button className="chip" aria-label={row.match.id+' 자동 제안 근거'} onClick={()=>onEvidence(row.match.id,'proposed')}>자동 제안 근거</button>{session.decision&&<button className="chip" aria-label={row.match.id+' 승인 일정 근거'} onClick={()=>onEvidence(row.match.id,'approved')}>승인 일정 근거</button>}</td>
    </tr>)}</tbody></table></div>
    <p>배정은 안전 보장이 아닙니다. 위험 판정과 제약의 상세 근거를 확인한 뒤 운영자가 판단합니다. 수정안을 승인했을 때 이 표의 자동 제안 수치를 수정안 성과로 해석하지 않습니다.</p>
  </section>;
}
