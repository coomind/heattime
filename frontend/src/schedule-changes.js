export function scheduleChanges(session){
  if(!session.proposal)return [];
  const assigned=new Map(session.proposal.assignments.map(row=>[row.match_id,row]));
  const postponed=new Map(session.proposal.postponed.map(row=>[row.match_id,row]));
  const original=new Map(session.recommendations.map(row=>[row.match_id,row]));
  return [...session.matches].sort((a,b)=>new Date(a.scheduled_start)-new Date(b.scheduled_start)||a.id.localeCompare(b.id)).map(match=>{
    const proposal=assigned.get(match.id),before=original.get(match.id);
    const delta=proposal?(new Date(proposal.start)-new Date(match.scheduled_start))/60000:null;
    return {match,proposal,originalLevel:before?.level,postponedReason:postponed.get(match.id)?.reason,
      deltaMinutes:delta,venueChanged:proposal?proposal.venue_id!==match.venue_id:false,
      movedFromStop:before?.level===4&&proposal?.level<4};
  });
}
