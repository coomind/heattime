import React,{useEffect,useState} from 'react';
import {round1} from './format.js';
import {occupiedMinutes,dayOf} from './gantt-geometry.js';
import {UPPER_BOUND_GROUPS} from './decision-breakdown.js';
import {matchName,matchShort,teamLabel} from './labels.js';

const ACTIONS={none:'통상 진행',cooling_break:'쿨링브레이크',shorten:'시간 단축',move:'시간 이동',postpone:'연기'};
const HOURS=Array.from({length:14},(_,i)=>i+7);
const DAY_START=7*60,SPAN=14*60;
const hm=t=>String(t).slice(11,16);
// Keep a marker inside the 07:00-21:00 lane even when it starts late (no overflow past the panel).
const laneBox=(start,len)=>{const left=Math.max(0,(start-DAY_START)/SPAN*100);const width=Math.min(Math.max(len/SPAN*100,3.2),100-left);return {left:Math.min(left,96.8)+'%',width:Math.max(width,3.2)+'%'};};
const minutes=t=>Number(String(t).slice(11,13))*60+Number(String(t).slice(14,16));
const venueShort=name=>{const m=/구장\s*([A-Z0-9]+)/.exec(name||'');return m?`구장 ${m[1]}`:(name||'').replace(/ · 가상 예시$/,'');};

function useNarrow(){
  const query='(max-width: 720px)';
  const [narrow,setNarrow]=useState(()=>typeof matchMedia==='function'&&matchMedia(query).matches);
  useEffect(()=>{if(typeof matchMedia!=='function')return;const m=matchMedia(query);const on=()=>setNarrow(m.matches);m.addEventListener('change',on);return()=>m.removeEventListener('change',on);},[]);
  return narrow;
}

export function postponeReason(p,session,postponedIds){
  if(p.reason.includes('선행 경기')){
    const m=session.matches.find(x=>x.id===p.match_id);
    const before=(m?.depends_on||[]).filter(id=>postponedIds.has(id)).map(matchName);
    return `앞선 경기${before.length?`(${before.join(', ')})`:''}가 연기되어 함께 연기합니다.`;
  }
  if(p.coverage_proven===false)return '제한 시간 안에 배정하지 못해 연기로 표시했습니다. 배정이 불가능하다는 증명은 아닙니다.';
  return '운동 중지 시간대를 피하면서 팀 휴식, 구장 정리, 일몰 전 종료 조건을 모두 지키는 시간이 없어 연기합니다.';
}

function Cell({r,venue,hour,stageLabel,upper,onOpen}){
  if(!r)return <div className="heat-cell nodata"><span className="stg">자료 없음</span><span className="cr">배정 보류</span></div>;
  return <button type="button" className={'heat-cell risk-'+r.level}
    title={`${r.level} ${stageLabel(r.level)} · 판정값 ${round1(r.decision_wbgt_c)}℃ · 추정 중앙 ${round1(r.wbgt_c)}℃ (범위 ${round1(r.wbgt_low_c)}~${round1(r.wbgt_high_c)}℃)`}
    onClick={()=>onOpen(venue.id,r.valid_time)}>
    <span className="stg">{r.level} {stageLabel(r.level)}</span>
    <span className="dv">{round1(r.decision_wbgt_c)}</span>
    <span className="cr">{upper?<>중앙 {round1(r.wbgt_c)}<br/>{round1(r.wbgt_low_c)}~{round1(r.wbgt_high_c)}</>:<>범위 {round1(r.wbgt_low_c)}~{round1(r.wbgt_high_c)}</>}</span>
    <span className="sr-only"> {venue.name} {hour}시 입력 근거</span>
  </button>;
}

export default function Dashboard({session,day,daySelect,stageLabel,openMatch,openInput,onOptimize,onCompare,busy}){
  const narrow=useNarrow();
  const recs=Object.fromEntries((session.recommendations||[]).map(r=>[r.match_id,r]));
  const proposal=session.proposal;
  const assigned=Object.fromEntries((proposal?.assignments||[]).map(a=>[a.match_id,a]));
  const postponed=proposal?.postponed||[];
  const postponedIds=new Set(postponed.map(p=>p.match_id));
  const upper=UPPER_BOUND_GROUPS.includes(session.tournament.age_group);
  const riskAt=(vid,h)=>session.risks.find(r=>r.venue_id===vid&&dayOf(r.valid_time)===day&&Number(r.valid_time.slice(11,13))===h);
  const dayMatches=session.matches.filter(m=>dayOf(m.scheduled_start)===day);
  const counts=[0,1,2,3,4].map(i=>(session.recommendations||[]).filter(r=>r.level===i).length);
  const stopIds=(session.recommendations||[]).filter(r=>r.level===4).map(r=>r.match_id);
  const rescued=stopIds.filter(id=>assigned[id]).length;
  const sameAcrossVenues=session.venues.length>1&&HOURS.every(h=>{const v=session.venues.map(x=>riskAt(x.id,h)?.decision_wbgt_c);return v.every(x=>x!==undefined&&x===v[0]);});
  const station=session.observation_summary?.station;
  const weather=session.weather||[];
  const open=session.schedule_settings?.open_hour??7,close=session.schedule_settings?.close_hour??20;
  const ops=weather.filter(w=>{const h=Number(w.valid_time.slice(11,13));return h>=open&&h<close;});
  const range=(xs,k)=>xs.length?`${Math.min(...xs.map(w=>w[k]))}~${Math.max(...xs.map(w=>w[k]))}`:'—';
  const originals=vid=>dayMatches.filter(m=>m.venue_id===vid);
  const proposals=vid=>(proposal?.assignments||[]).filter(a=>a.venue_id===vid&&dayOf(a.start)===day);
  const mark=(m,kind)=>{const id=kind==='orig'?m.id:m.match_id;const start=kind==='orig'?m.scheduled_start:m.start;
    const len=kind==='orig'?occupiedMinutes(m):(minutes(m.end)-minutes(m.start));
    return <button type="button" key={kind+id} className={'mk '+(kind==='orig'?'overlay-match':'proposed')}
      aria-label={`${matchShort(id)} (${matchName(id)} ${kind==='orig'?'원래':'제안'} 킥오프 ${hm(start)})`}
      style={narrow?undefined:laneBox(minutes(start),len)}
      title={`${matchName(id)} ${kind==='orig'?'원래':'제안'} ${hm(start)}`} onClick={()=>openMatch(id)}>{matchShort(id)}</button>;};

  const heatmap=narrow?
    <div className="heat-grid heat-v" style={{'--venues':session.venues.length}}>
      <span className="corner" style={{gridColumn:1,gridRow:1}} aria-hidden="true"></span>
      {HOURS.map((h,hi)=><span className="hour" key={'h'+h} style={{gridColumn:1,gridRow:hi+2}}>{h}:00</span>)}
      {session.venues.map((v,vi)=><div className="heat-row" key={v.id}>
        <div className="venue-label" style={{gridColumn:vi+2,gridRow:1}}>{venueShort(v.name)}<small>가상 예시</small></div>
        {HOURS.map((h,hi)=>{const r=riskAt(v.id,h);const o=originals(v.id).filter(m=>Number(m.scheduled_start.slice(11,13))===h);const p=proposals(v.id).filter(a=>Number(a.start.slice(11,13))===h);
          return <div className="vcell" key={h} style={{gridColumn:vi+2,gridRow:hi+2}}><Cell r={r} venue={v} hour={h} stageLabel={stageLabel} upper={upper} onOpen={openInput}/>
            {(o.length>0||p.length>0)&&<div className="kicks">{o.map(m=>mark(m,'orig'))}{p.map(a=>mark(a,'prop'))}</div>}</div>;})}
      </div>)}
    </div>:
    <div className="heat-grid heat-h">
      <div aria-hidden="true"></div>{HOURS.map(h=><div className="hour" key={h}>{h}:00</div>)}
      {session.venues.map(v=><div className="heat-row" key={v.id}>
        <div className="venue-label">{v.name.replace(/ · 가상 예시$/,'')}<small>가상 예시{v.surface==='artificial_turf'?' · 인조잔디 표면온도 주의':''}</small></div>
        {HOURS.map(h=><Cell key={h} r={riskAt(v.id,h)} venue={v} hour={h} stageLabel={stageLabel} upper={upper} onOpen={openInput}/>)}
        <div className="lanes"><div className="lane orig"><span className="lane-label">원래</span>{originals(v.id).map(m=>mark(m,'orig'))}</div>
          {proposal&&<div className="lane prop"><span className="lane-label">제안</span>{proposals(v.id).map(a=>mark(a,'prop'))}</div>}</div>
      </div>)}
    </div>;

  const listed=session.matches.filter(m=>!postponedIds.has(m.id));
  return <div className="dash">
    <section className="dash-panel decide wide" aria-labelledby="decide-title">
      {proposal?<>
        <div className="decide-head">
          <h2 id="decide-title">자동 재편성 제안</h2>
          <p className="fine">아직 승인하지 않은 제안입니다. 운영자가 근거를 확인한 뒤 승인하거나 고칩니다.</p>
          <div className="big">{proposal.assignments.length}경기 배정, {proposal.postponed_count}경기 연기</div>
          <div className="actions"><button type="button" className="primary" onClick={onCompare}>재편성 비교에서 검토</button></div>
        </div>
        <div className="decide-text">
          <p className="lead">원래 일정에서 운동 중지 단계였던 {stopIds.length}경기 중 {rescued}경기를 다른 시간이나 구장으로 옮겨 배정했습니다.</p>
          <p className="fine">같은 {proposal.common_match_ids.length}경기의 열 노출 점수는 {proposal.original_heat_score.toLocaleString('ko-KR')}점에서 {proposal.proposed_heat_score.toLocaleString('ko-KR')}점으로 내려갑니다. 일정 비교용 내부 점수이며 건강 효과를 뜻하지 않습니다.</p>
        </div>
        {postponed.length>0&&<div className="postponed-box" role="note"><h3>연기 제안 {postponed.length}경기</h3><ul>{postponed.map(p=>{const m=session.matches.find(x=>x.id===p.match_id);return <li key={p.match_id}><b>{matchName(p.match_id)}{m?` (${teamLabel(session,m.team_a)} 대 ${teamLabel(session,m.team_b)})`:''}</b><span>{postponeReason(p,session,postponedIds)}</span></li>;})}</ul></div>}
      </>:<>
        <div className="decide-head">
          <h2 id="decide-title">오늘 판단할 일</h2>
          <div className="big">{counts[4]}경기 운동 중지</div>
          <div className="actions"><button type="button" className="primary" disabled={busy} onClick={onOptimize}>재편성 실행</button></div>
        </div>
        <div className="decide-text"><p className="lead">원래 일정 {session.matches.length}경기 가운데 {counts[4]}경기가 운동 중지 단계, {counts[3]}경기가 엄중경계 단계에 걸칩니다. 재편성을 실행하면 같은 제약 안에서 시간과 구장을 다시 배정한 제안을 만듭니다.</p></div>
      </>}
    </section>
    <section className="dash-panel wide" aria-labelledby="heat-title">
      <h2 id="heat-title">구장 × 시간 위험도</h2>
      <div className="summary stage-counts" aria-label="원래 일정의 경기별 단계">{[0,1,2,3,4].map(i=><div className={'stat risk-'+i} key={i}><span>{i} {stageLabel(i)}</span><strong>{counts[i]}<small>경기</small></strong></div>)}</div>
      {daySelect}
      <p className="heat-legend">칸의 큰 숫자는 단계를 정하는 데 쓴 판정값(℃)입니다. {upper?`이 대회(${session.tournament.age_group})는 유소년 기준이라 WBGT 추정 범위의 상단값으로 판정하고, 작은 글씨로 추정 중앙값과 범위를 적었습니다.`:'WBGT 추정 중앙값으로 판정하고, 작은 글씨로 추정 범위를 적었습니다.'} 모든 값은 관측 기상으로 계산한 추정이며 현장 실측이 아닙니다.</p>
      <div className="timeline-scroll">{heatmap}</div>
      <p className="heat-legend"><b>원래</b>는 작성자가 정한 가상 일정의 킥오프, {proposal?<><b>제안</b>은 자동 재편성 제안의 킥오프입니다.</>:'제안 킥오프는 재편성을 실행하면 함께 표시됩니다.'}</p>
      {sameAcrossVenues&&<p className="same-note">세 구장의 값이 같은 이유: 모든 구장이 같은 관측소{station?`(${station.name} ${station.id})`:''} 자료를 쓰고, 표면 유형은 현재 판정에 반영하지 않기 때문입니다.</p>}
    </section>
    <section className="dash-panel dash-weather wide"><h2>그날의 관측 기상과 판정 가정</h2>
      <p>{weather.length?<>시간자료 최고기온 {Math.max(...weather.map(w=>w.ta_c)).toFixed(1)}℃, 습도 {range(weather,'rh_pct')}% (24시간), 운영시간 습도 {range(ops,'rh_pct')}%입니다. 관측 WBGT가 아니라 모델 추정과 보정값으로 판단합니다.</>:'기상 자료가 없습니다.'}</p></section>
    <section className="dash-panel wide" aria-labelledby="list-title">
      <h2 id="list-title">경기별 권고</h2>
      <p>{proposal?'큰 글씨는 원래 킥오프에서 제안 킥오프로의 변화입니다. 원래 일정의 단계와 권고는 오른쪽에 작게 적었습니다. 연기 제안 경기는 위 상자에 따로 있습니다.':'재편성 전에는 원래 일정의 킥오프와 단계별 권고만 보입니다.'}</p>
      <div className="mlist">
        <div className="head" aria-hidden="true"><span>경기</span><span>{proposal?'원래 → 제안 킥오프':'킥오프'}</span><span>{proposal?'제안 단계와 조치':'단계'}</span><span>원래 일정 권고</span></div>
        {listed.map(m=>{const r=recs[m.id];const a=assigned[m.id];
          return <button type="button" className="match-row" key={m.id} onClick={()=>openMatch(m.id)}>
            <span className="who"><b>{matchName(m.id)}</b><small>{teamLabel(session,m.team_a)} 대 {teamLabel(session,m.team_b)}</small></span>
            <span className="move">{a?<>{hm(m.scheduled_start)} → {hm(a.start)}<small>{venueShort(session.venues.find(v=>v.id===a.venue_id)?.name)}</small></>:<>{hm(m.scheduled_start)}<small>{venueShort(session.venues.find(v=>v.id===m.venue_id)?.name)}</small></>}</span>
            <span>{a?<span className={'chip-stage risk-'+a.level}>{a.level} {stageLabel(a.level)} · {ACTIONS[a.action]}</span>:<span className="chip-stage" style={{background:'var(--bg)'}}>재편성 전</span>}</span>
            <span className="orig">{r&&<><span className={'chip-stage risk-'+r.level}>{r.level} {stageLabel(r.level)}</span>{ACTIONS[r.action]} 권고 · WBGT 추정 {round1(r.wbgt_c)}℃ ({round1(r.wbgt_low_c)}~{round1(r.wbgt_high_c)}℃)</>}</span>
          </button>;})}
      </div>
    </section>
  </div>;
}
