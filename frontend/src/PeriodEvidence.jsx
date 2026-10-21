import React,{useState} from 'react';

export default function PeriodEvidence(){
  const [data,setData]=useState(null),[error,setError]=useState(false),[loading,setLoading]=useState(false);
  async function load(event){
    if(!event.currentTarget.open||data||loading)return;
    setLoading(true);setError(false);
    try{
      const {default:url}=await import('./demo/period-evidence.json?url');
      const response=await fetch(url);
      if(!response.ok)throw new Error('자료 읽기 실패');
      setData(await response.json());
    }catch{setError(true);}finally{setLoading(false);}
  }
  const complete=data?.days.filter(row=>row.postponed===0).length;
  const zero=data?.days.filter(row=>row.assigned===0).length;
  const zeroDates=data?.days.filter(row=>row.assigned===0).map(row=>`${Number(row.date.slice(5,7))}/${Number(row.date.slice(8,10))}`).join('·');
  const stats=data?.comparison.summary;
  const scoreDelta=stats&&stats.cp_common_heat-stats.greedy_common_heat;
  return <details className="card period-evidence" onToggle={load}>
    <summary>62일 전체 재현 결과와 알고리즘 비교</summary>
    {loading&&<p role="status">저장된 검증 자료를 불러오고 있습니다…</p>}
    {error&&<p role="alert">검증 자료를 불러오지 못했습니다. 연결된 상태에서 시연 자료를 저장하고 다시 펼쳐주세요.</p>}
    {data&&<><p>2026-10-11 재계산(일사 구간 정렬·판정값 0.1℃ 반올림·동점 처리 고정) 결과입니다. 같은 입력을 다시 푼 93조건 재현성 검증은 위 재실행 결과에 따로 표시합니다.</p>
      <p className="evidence-label">기상청 관측 자료(수원 {data.station.id}·2026-07-01~2026-08-31) · 가상 U12 12팀·3구장·15경기 · 사전 계산</p>
      <p>기본값을 고정한 별도 분석입니다. 현재 선택한 대회·날짜·변경 설정의 새 계산 결과와 다릅니다. 현장 WBGT 실측이나 실제 대회 성과가 아닙니다.</p>
      <p className="evidence-assumptions">가정: {data.assumptions}. 추정 범위는 현장 검증된 신뢰구간이 아닙니다.</p>
      <h3>날짜별 전체 결과 · {data.days.length}일 모두 표시</h3>
      <div className="period-totals"><span>전부 배정 <b>{complete}일</b></span><span>일부 배정 <b>{data.days.length-complete-zero}일</b></span><span>0경기 배정 <b>{zero}일</b></span></div>
      <p>수원 관측 자료로 재현한 가상 12팀 대회에서는 {data.days.length}일 중 {data.days.length-complete}일에, 일정을 재배치해도 15경기 전부를 같은 날 배정할 수 없었습니다. 0경기 배정일은 {zero}일({zeroDates})입니다. 실제 대회 일반의 개최 불가 일수가 아닙니다.</p>
      <div className="table-scroll" tabIndex={0}><table aria-label="62일 전체 재현 결과"><thead><tr><th>날짜</th><th>배정 / 연기</th><th>원래 중지 중 배정</th><th>공통 경기 수</th><th>원래 → 제안 점수</th><th>결과 상태</th></tr></thead><tbody>
        {data.days.map(row=><tr key={row.date}><td>{row.date}</td><td>{row.assigned} / {row.postponed}</td><td>{row.salvaged} / {row.original_stop_count}</td><td>{row.common_count}</td><td>{row.common_count?`${row.original_heat.toLocaleString()} → ${row.proposed_heat.toLocaleString()}`:'비교할 공통 경기 없음'}</td><td>{row.solver}{!row.coverage_optimal?' · 최적성 미확정':''}</td></tr>)}
      </tbody></table></div>
      <details className="method-evidence"><summary>같은 제약의 탐욕 방식과 비교 · 별도 지표</summary>
        <h3>전역 조합 탐색의 장점과 비용</h3>
        <p>동일 관측·기본 설정·하드 제약으로 기존 탐욕 폴백을 실행하고, 위의 고정 CP-SAT 제안과 비교했습니다. 탐욕은 경기별 낮은 점수 후보부터 배정합니다. 사람의 수작업이나 경쟁 제품을 시험한 결과가 아닙니다.</p>
        <div className="period-totals"><span>배정 합계 <b>{stats.greedy_assigned} → {stats.cp_assigned}건</b></span><span>15경기 전부 배정 <b>{stats.greedy_complete_days} → {stats.cp_complete_days}일</b></span></div>
        <p>CP-SAT의 배정 수가 더 많은 날 {stats.more_assigned_days}일, 같은 날 {stats.same_assigned_days}일, 더 적은 날 {stats.fewer_assigned_days}일입니다. 합계는62개 가상 대회의 배정 건수입니다.</p>
        <p className="comparison-tradeoff">공통 경기의 열 노출 점수 합계는 {stats.greedy_common_heat.toLocaleString()} → {stats.cp_common_heat.toLocaleString()}로, CP-SAT가 {Math.abs(scoreDelta).toLocaleString()}점·{(Math.abs(scoreDelta)/stats.greedy_common_heat*100).toFixed(2)}% {scoreDelta>=0?'높습니다':'낮습니다'}. 연기를 먼저 줄이는 우선순위 때문에 점수가 항상 감소하지 않습니다. 건강 효과나 사고 감소율이 아닙니다.</p>
        <p>날짜별 공통 점수는 CP-SAT가 낮은 {stats.common_heat_lower_days}일 / 같은 {stats.common_heat_equal_days}일 / 높은 {stats.common_heat_higher_days}일입니다. 공통 경기 없는 {stats.no_common_days}일은 점수 비교에서 제외합니다.</p>
        <div className="table-scroll" tabIndex={0}><table aria-label="62일 알고리즘 비교"><thead><tr><th>날짜</th><th>탐욕 배정 / 연기</th><th>CP-SAT 배정 / 연기</th><th>공통 경기 수</th><th>탐욕 → CP-SAT 점수</th></tr></thead><tbody>{data.comparison.days.map(row=><tr key={row.date}><td>{row.date}</td><td>{row.greedy_assigned} / {row.greedy_postponed}</td><td>{row.cp_assigned} / {row.cp_postponed}</td><td>{row.common_count}</td><td>{row.common_count?`${row.greedy_common_heat.toLocaleString()} → ${row.cp_common_heat.toLocaleString()}`:'비교할 공통 경기 없음'}</td></tr>)}</tbody></table></div>
        <p>이 표의 공통 경기 집합은 탐욕과 CP-SAT의 교집합입니다. 위 표의 원래 일정→제안 일정 점수와 같은 비교가 아닙니다. 탐욕의 연기는 전역 배정 불가능 증명이 아닙니다.</p>
      </details>
    </>}
  </details>;
}
