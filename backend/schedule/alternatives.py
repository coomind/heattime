"""Fixed deterministic alternatives using unchanged candidates and hard constraints."""
METHODS=('existing_heat_first','earliest_input','earliest_reverse','weighted_critical')


def secondary_cost(candidate,match,settings):
    return int(candidate.heat_score*settings.heat_weight+abs((candidate.start-match.scheduled_start).total_seconds()/60)*settings.time_weight+(candidate.venue_id!=match.venue_id)*settings.venue_penalty)


def greedy(matches,tournament,venues,risks,settings,options,method):
    from .optimizer import validate
    if method not in METHODS:raise ValueError('Unknown alternative')
    by={m.id:m for m in matches}
    def ancestors(mid):
        seen=set();pending=list(by[mid].depends_on)
        while pending:
            current=pending.pop()
            if current in seen:continue
            seen.add(current);pending+=by[current].depends_on
        return seen
    pending=list(reversed(matches)) if method=='earliest_reverse' else list(matches)
    if method=='weighted_critical':
        priority={m.id:sum(m.id in ancestors(other.id) for other in matches if other.id!=m.id) for m in matches}
        pending.sort(key=lambda m:(-priority[m.id],m.id))
    chosen=[]
    while pending:
        ids={m.id for m in pending};ready=[m for m in pending if not set(m.depends_on)&ids]
        if not ready:raise ValueError('Cyclic dependencies')
        for m in ready:
            if method=='existing_heat_first':key=lambda c:(c.heat_score,c.start,c.venue_id)
            elif method=='weighted_critical':key=lambda c:(secondary_cost(c,m,settings),c.start,c.venue_id)
            else:key=lambda c:(c.start,c.end,c.venue_id,c.heat_score)
            for candidate in sorted(options[m.id],key=key):
                if not validate(chosen+[candidate],matches,tournament,venues,risks,settings):
                    chosen.append(candidate);break
            pending.remove(m)
    return chosen


def choose_validated(plans,matches,tournament,venues,risks,settings):
    from .optimizer import validate
    by={m.id:m for m in matches};valid=[];records=[]
    for method,rows in plans:
        errors=validate(rows,matches,tournament,venues,risks,settings)
        if errors:raise RuntimeError('Invalid alternative: '+','.join(errors))
        cost=sum(secondary_cost(row,by[row.match_id],settings) for row in rows)
        records.append({'method':method,'assigned':len(rows),'secondary_cost':cost,'constraints_ok':True})
        valid.append(((-len(rows),cost,method!='cp_sat',method),method,rows))
    _,method,rows=min(valid,key=lambda item:item[0])
    return method,rows,records
