// Display existing, validated proposal results without changing engine or policy inputs.
export function scheduleOutcome(matches, recommendations, proposal) {
  const matchIds = new Set(matches.map(match => match.id));
  const knownIds = rows => new Set(rows.map(row => row.match_id).filter(id => matchIds.has(id)));
  const assigned = knownIds(proposal.assignments);
  const postponed = knownIds(proposal.postponed);
  const originalStop = knownIds(recommendations.filter(row => row.level === 4));
  const common = new Set(proposal.common_match_ids.filter(id => assigned.has(id)));
  const scoreReduction = common.size ? proposal.original_heat_score - proposal.proposed_heat_score : null;
  return {
    total: matchIds.size,
    assigned: assigned.size,
    postponed: postponed.size,
    originalStop: originalStop.size,
    reassignedStop: [...originalStop].filter(id => assigned.has(id)).length,
    common: common.size,
    scoreReduction,
    reductionPercent: common.size && proposal.original_heat_score > 0
      ? scoreReduction / proposal.original_heat_score * 100 : null,
  };
}
