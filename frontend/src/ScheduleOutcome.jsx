import React from 'react';
import {scheduleOutcome} from './schedule-outcome.js';

export default function ScheduleOutcome({session}) {
  const outcome = scheduleOutcome(session.matches, session.recommendations, session.proposal);
  const action = session.decision?.operator_action;
  const status = {
    accepted: '제안 승인됨 · 승인 기록은 아래에서 확인하세요.',
    modified: '수정안 승인됨 · 아래 수치는 수정 전 자동 제안입니다. 승인한 수정안은 운영 기록에서 확인하세요.',
    rejected: '제안 거절됨 · 아래 자동 제안은 적용되지 않았습니다.',
  }[action] || '승인 전 제안 · 아직 적용되지 않았습니다.';
  const change = outcome.scoreReduction === null ? '비교할 공통 경기 없음'
    : outcome.scoreReduction === 0 ? '점수 변화 없음'
    : outcome.reductionPercent === null ? '변화율 계산 불가'
    : `${Math.abs(outcome.reductionPercent).toFixed(2)}% ${outcome.scoreReduction > 0 ? '감소' : '증가'}`;
  return <section className="card outcome-summary" aria-labelledby="outcome-heading">
    <div className="section-head"><h2 id="outcome-heading">자동 제안 요약</h2><span className="outcome-state">{status}</span></div>
    <div className="outcome-grid">
      <div><span>전체 {outcome.total}경기 중 배정</span><strong>{outcome.assigned}<small>경기</small></strong></div>
      <div><span>별도 연기</span><strong>{outcome.postponed}<small>경기</small></strong></div>
      <div><span>원래 중지 단계 {outcome.originalStop}경기 중 제안 배정</span><strong>{outcome.reassignedStop}<small>경기</small></strong></div>
      <div><span>공통 {outcome.common}경기 열 노출 점수</span><strong className="outcome-change">{change}</strong>
        {outcome.scoreReduction !== null && <small>{Math.abs(outcome.scoreReduction).toLocaleString('ko-KR')}점 {outcome.scoreReduction > 0 ? '감소' : outcome.scoreReduction < 0 ? '증가' : '변화'}</small>}
      </div>
    </div>
    <p>기존 판정·운영 제약을 적용한 가상 대회의 제안 결과입니다. 점수 변화는 건강 효과나 사고 감소율이 아닙니다. 운영자가 근거와 연기 사유를 확인한 뒤 판단합니다.</p>
  </section>;
}
