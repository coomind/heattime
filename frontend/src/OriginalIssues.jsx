import React,{useEffect,useState} from 'react';
// Hard-constraint issues of the author's original schedule, found by the backend validate() (offline: snapshot bundle).
export default function OriginalIssues({api,session}){
  const [data,setData]=useState(null),[error,setError]=useState('');
  useEffect(()=>{let live=true;api('/sessions/'+session.id+'/original-issues').then(d=>{if(live)setData(d);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[session.id]);
  if(error)return <p className="issues-error" role="alert">원래 일정의 제약 검사 결과를 불러오지 못했습니다. {error}</p>;
  if(!data)return <p className="issues-loading">원래 일정의 제약을 확인하고 있습니다.</p>;
  if(!data.full_errors.length)return <p>원래 일정은 기존 하드 제약 검사를 모두 통과합니다.</p>;
  const heat=data.singles.filter(x=>x.errors.includes('prohibited heat slot'));
  const otherSingles=data.singles.filter(x=>x.errors.some(e=>e!=='prohibited heat slot'));
  return <div className="original-issues" aria-labelledby="original-issues-title">
    <h3 id="original-issues-title">{data.note}</h3>
    <ul>
      {heat.length>0&&<li>{heat.length}경기가 운동 중지 단계 시간대에 배정되어 있습니다: {heat.map(x=>x.names[0]).join(', ')}.</li>}
      {otherSingles.map(x=><li key={x.match_ids.join()}>{x.names[0]}: {x.text.filter(t=>!t.startsWith('운동 중지')).join(', ')}.</li>)}
      {data.pairs.map(x=><li key={x.match_ids.join()}>{x.names[0]}({x.times[0]})와 {x.names[1]}({x.times[1]}): {x.text.join(', ')}.</li>)}
    </ul>
    <p className="fine">이 목록은 원래 일정과 제안의 점수 비교가 같은 조건의 비교가 아님을 알리기 위한 것입니다. 제안 일정은 같은 검사를 모두 통과했습니다.</p>
  </div>;
}
