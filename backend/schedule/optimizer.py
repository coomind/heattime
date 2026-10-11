"""CP-SAT optional intervals, shared constraint validator and greedy fallback."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from functools import lru_cache
import hashlib
import os
from time import perf_counter
import pandas as pd
from pvlib.solarposition import sun_rise_set_transit_spa
from ortools.sat.python import cp_model
from backend.weather.models import KST
from backend.engine.settings import EngineSettings
from .models import ScheduleSettings,default_schedule_settings
from .recommend import recommend,window_risks,MissingRisk

@dataclass(frozen=True)
class Candidate:
    match_id: str
    venue_id: str
    start: datetime
    end: datetime
    level: int
    heat_score: int
    duration_min: int
    cooling_times: list
    action: str

@dataclass
class OptimizationResult:
    assignments: list[Candidate]
    postponed: list[dict]
    solver: str
    original_heat_score: int
    proposed_heat_score: int
    constraints_ok: bool
    common_match_ids: list[str]
    postponed_count: int
    postponement_penalty: int
    secondary_cost_upper_bound: int
    coverage_optimal: bool
    elapsed_sec: float = 0.0
    preparation_sec: float = 0.0
    solver_wall_sec: float = 0.0
    selected_method: str = 'legacy'
    cp_sat_status: str = 'NOT_RUN'
    selection_candidates: list | None = None


def participants(matches):
    by={m.id:m for m in matches};cache={}
    def expand(mid,path=()):
        if mid in path:raise ValueError('Cyclic dependencies')
        if mid in cache:return cache[mid]
        if mid not in by:raise ValueError('Unknown predecessor')
        m=by[mid];teams={x for x in [m.team_a,m.team_b] if not x.startswith('winner:')}
        for d in m.depends_on:teams|=expand(d,path+(mid,))
        cache[mid]=teams;return teams
    for mid in by:expand(mid)
    return cache

@lru_cache(maxsize=512)
def sunset(day,lat,lon):
    times=pd.DatetimeIndex([datetime.combine(day,datetime.min.time(),KST)])
    return sun_rise_set_transit_spa(times,lat,lon).iloc[0].sunset.to_pydatetime(warn=False)


def heat_score(risks,venue,start,end):
    return int(sum(max(0,r.decision_wbgt_c-21)*max(0,(min(end,r.valid_time+timedelta(hours=1))-max(start,r.valid_time)).total_seconds()/60) for r in window_risks(risks,venue,start,end)))


def candidates_for(match,tournament,venues,risks,settings,engine):
    rows=[];day=tournament.date_start
    while day<=tournament.date_end:
        for v in venues:
            base=datetime.combine(day,datetime.min.time(),KST);start=base+timedelta(hours=settings.open_hour);close=base+timedelta(hours=settings.close_hour)
            if not v.has_lights:close=min(close,sunset(day,v.lat,v.lon))
            while start<close:
                rec=recommend(match.model_copy(update={'venue_id':v.id,'scheduled_start':start}),risks,engine)
                if rec.level<4 and rec.end+timedelta(minutes=settings.cleanup_min)<=close:
                    rows.append(Candidate(match.id,v.id,start,rec.end,rec.level,heat_score(risks,v.id,start,rec.end),rec.duration_min,rec.cooling_times,rec.action))
                start+=timedelta(minutes=settings.slot_min)
        day+=timedelta(days=1)
    return rows


def validate(assignments,matches,tournament,venues,risks,settings):
    errors=[];by={m.id:m for m in matches};vmap={v.id:v for v in venues};parts=participants(matches)
    rest=settings.rest_by_age[tournament.age_group];amap={a.match_id:a for a in assignments}
    if len(amap)!=len(assignments):errors.append('duplicate match')
    for a in assignments:
        v=vmap[a.venue_id];base=datetime.combine(a.start.date(),datetime.min.time(),KST)
        if not tournament.date_start<=a.start.date()<=tournament.date_end or a.end.date()!=a.start.date():errors.append('date range')
        close=base+timedelta(hours=settings.close_hour)
        if not v.has_lights:close=min(close,sunset(a.start.date(),v.lat,v.lon))
        if a.start<base+timedelta(hours=settings.open_hour) or a.end+timedelta(minutes=settings.cleanup_min)>close:errors.append('operating window/sunset')
        if a.start.minute%settings.slot_min:errors.append('slot alignment')
        try:
            if max(r.level for r in window_risks(risks,a.venue_id,a.start,a.end))>=4:errors.append('prohibited heat slot')
        except MissingRisk:errors.append('missing risk')
        for dep in by[a.match_id].depends_on:
            if dep not in amap or amap[dep].end>a.start:errors.append('dependency')
    for i,a in enumerate(assignments):
        for b in assignments[i+1:]:
            early,late=sorted([a,b],key=lambda r:r.start)
            if a.venue_id==b.venue_id and early.end+timedelta(minutes=settings.cleanup_min)>late.start:errors.append('venue overlap/cleanup')
            if parts[a.match_id]&parts[b.match_id] and early.end+timedelta(minutes=rest)>late.start:errors.append('team rest')
    return sorted(set(errors))


TIE_BREAK_RANGE=1000


def tie_break(candidate):
    """Fixed pseudo-random 0..999 per candidate, from its identity only.

    Scaled below one unit of the existing cost, so it never changes the
    postponement count or secondary cost; it only selects one schedule among
    equal-cost optima, making OPTIMAL results identical across runs/threads.
    """
    key=f"{candidate.match_id}|{candidate.venue_id}|{candidate.start.isoformat()}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4],'big')%TIE_BREAK_RANGE


class InfeasibleSchedule(ValueError):
    pass


def optimize(matches,tournament,venues,risks,settings=None,engine=None,force_greedy=False,required_match_ids=()):
    started=perf_counter();solver_wall_sec=0.0;preparation_sec=0.0
    settings=settings or default_schedule_settings();engine=engine or EngineSettings();parts=participants(matches)
    origin=datetime.combine(tournament.date_start,datetime.min.time(),KST);minute=lambda t:int((t-origin).total_seconds()/60)
    rows={m.id:candidates_for(m,tournament,venues,risks,settings,engine) for m in matches};original=0
    for m in matches:
        try:original+=heat_score(risks,m.venue_id,m.scheduled_start,recommend(m,risks,engine).end)
        except MissingRisk:pass
    chosen=[];name='greedy-fallback';penalty=0;coverage_optimal=False
    cp_status='NOT_RUN';selected_method='existing_heat_first';selection_records=[]
    unknown=set(required_match_ids)-{m.id for m in matches}
    if unknown:raise ValueError('Unknown forced match ids')
    from .alternatives import METHODS,greedy,choose_validated
    alternatives=[] if force_greedy or required_match_ids else [
        (method,greedy(matches,tournament,venues,risks,settings,rows,method)) for method in METHODS]
    if not force_greedy:
        model=cp_model.CpModel();vi={v.id:[] for v in venues};ti={t:[] for ts in parts.values() for t in ts}
        picks={};present={};starts={};ends={};objective=[];tie_terms=[];horizon=(tournament.date_end-tournament.date_start).days*1440+1440
        cost=lambda m,c:c.heat_score*settings.heat_weight+abs(minute(c.start)-minute(m.scheduled_start))*settings.time_weight+(c.venue_id!=m.venue_id)*settings.venue_penalty
        penalty=1+sum(max([cost(m,c) for c in rows[m.id]] or [0]) for m in matches)
        for m in matches:
            present[m.id]=model.new_bool_var('present_'+m.id);starts[m.id]=model.new_int_var(0,horizon,'start_'+m.id);ends[m.id]=model.new_int_var(0,horizon,'end_'+m.id);picks[m.id]=[]
            for index,c in enumerate(rows[m.id]):
                pick=model.new_bool_var(f'{m.id}_{index}');picks[m.id].append(pick);s,e=minute(c.start),minute(c.end)
                model.add(starts[m.id]==s).only_enforce_if(pick);model.add(ends[m.id]==e).only_enforce_if(pick)
                vi[c.venue_id].append(model.new_optional_interval_var(s,e-s+settings.cleanup_min,e+settings.cleanup_min,pick,'venue'))
                rest=settings.rest_by_age[tournament.age_group]
                for team in parts[m.id]:ti[team].append(model.new_optional_interval_var(s,e-s+rest,e+rest,pick,'team'))
                objective.append(cost(m,c)*pick);tie_terms.append(tie_break(c)*pick)
            model.add(sum(picks[m.id])==present[m.id]);objective.append(penalty*(1-present[m.id]))
        for required in required_match_ids:model.add(present[required]==1)
        for m in matches:
            for dep in m.depends_on:
                model.add(present[m.id]<=present[dep]);model.add(starts[m.id]>=ends[dep]).only_enforce_if(present[m.id])
        for intervals in list(vi.values())+list(ti.values()):model.add_no_overlap(intervals)
        if alternatives:
            _,hint,_=choose_validated(alternatives,matches,tournament,venues,risks,settings)
            hint_by={c.match_id:c for c in hint}
            for m in matches:
                candidate=hint_by.get(m.id)
                model.add_hint(present[m.id],int(candidate is not None))
                model.add_hint(starts[m.id],minute(candidate.start) if candidate else 0)
                model.add_hint(ends[m.id],minute(candidate.end) if candidate else 0)
                for c,pick in zip(rows[m.id],picks[m.id]):model.add_hint(pick,int(c==candidate))
        scale=TIE_BREAK_RANGE*len(matches)+1
        model.minimize(scale*sum(objective)+sum(tie_terms));solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=settings.time_limit_sec
        solver.parameters.num_search_workers=8;solver.parameters.random_seed=42
        preparation_sec=perf_counter()-started;solve_started=perf_counter();status=solver.solve(model)
        solver_wall_sec=perf_counter()-solve_started
        cp_status=solver.status_name(status)
        if status == cp_model.INFEASIBLE:
            raise InfeasibleSchedule("INFEASIBLE: forced match assignment violates hard constraints")
        coverage_optimal = status == cp_model.OPTIMAL
        if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
            name='CP-SAT '+solver.status_name(status);chosen=[c for m in matches for c,p in zip(rows[m.id],picks[m.id]) if solver.boolean_value(p)]
            selected_method='cp_sat'
    if name=='greedy-fallback':
        if preparation_sec==0.0:preparation_sec=perf_counter()-started
        if required_match_ids:raise TimeoutError('Forced feasibility not proven within solver time limit')
        chosen=greedy(matches,tournament,venues,risks,settings,rows,'existing_heat_first')
    if alternatives:
        plans=alternatives+([('cp_sat',chosen)] if selected_method=='cp_sat' else [])
        selected_method,chosen,selection_records=choose_validated(plans,matches,tournament,venues,risks,settings)
        if selected_method!='cp_sat':name='validated-greedy · CP-SAT '+cp_status
    errors=validate(chosen,matches,tournament,venues,risks,settings)
    if errors:raise RuntimeError('Invalid output: '+','.join(errors))
    ids={c.match_id for c in chosen};postponed=[]
    for m in matches:
        if m.id not in ids:
            reason=('선행 경기 연기' if any(d not in ids for d in m.depends_on) else '자료 누락 또는 중지·운영시간·휴식·구장·일몰 제약으로 배정 불가') if coverage_optimal else '제한 시간 내 배정하지 못함 · 불가능 증명 아님'
            postponed.append({'match_id':m.id,'reason':reason,'coverage_proven':coverage_optimal})
    # Both metrics use exactly the assigned/common match ids; postponements separate.
    original=0
    by_id={m.id:m for m in matches}
    for mid in ids:
        m=by_id[mid]
        try:original+=heat_score(risks,m.venue_id,m.scheduled_start,recommend(m,risks,engine).end)
        except MissingRisk:raise ValueError('Cannot compare exposure without original weather coverage')
    return OptimizationResult(chosen,postponed,name,original,sum(c.heat_score for c in chosen),not errors,
                              sorted(ids),len(postponed),penalty,max(0,penalty-1),coverage_optimal,
                              perf_counter()-started,preparation_sec,solver_wall_sec,selected_method,cp_status,selection_records)


def forced_feasibility(match_id,matches,tournament,venues,risks,settings=None,engine=None):
    """Force one match globally; UNKNOWN is not an infeasibility certificate."""
    try:
        result=optimize(matches,tournament,venues,risks,settings,engine,required_match_ids=[match_id])
        return {"match_id":match_id,"status":"FEASIBLE","assigned":len(result.assignments)}
    except InfeasibleSchedule:
        return {"match_id":match_id,"status":"INFEASIBLE"}
    except TimeoutError:
        return {"match_id":match_id,"status":"UNKNOWN"}
