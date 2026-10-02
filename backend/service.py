from dataclasses import asdict,replace
from datetime import date,datetime,timedelta
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from backend.weather.cli import ROOT
from backend.weather.models import Venue,ManualMeasurement,WeatherPoint,KST
from backend.weather.adapters import MockAsosAdapter,AsosObservationAdapter
from backend.weather.asos_samples import load_dataset
from backend.weather.storage import WeatherStore
from backend.engine.settings import EngineSettings
from backend.engine.wbgt import estimate_series,RiskEstimate
from backend.engine.policy import policies
from backend.schedule.models import Tournament,Team,Match,ScheduleSettings
from backend.schedule.demo import demo_tournament
from backend.schedule.recommend import recommend
from backend.schedule.optimizer import optimize,Candidate,validate,candidates_for,participants
from backend.notifications import build_notifications

class Service:
    def __init__(self,repo):
        self.repo=repo;self.weather=WeatherStore(repo.path)
        if not repo.list('tournaments'):
            t,teams,matches,venues=demo_tournament()
            for kind,items in [('tournaments',[t]),('teams',teams),('matches',matches),('venues',venues)]:
                for item in items:repo.put(kind,item.id,item)
    def validate_resource(self,kind,payload):
        types={'venues':Venue,'tournaments':Tournament,'teams':Team,'matches':Match}
        if kind not in types:raise ValueError('Unknown resource kind')
        try:item=Venue(**payload) if kind=='venues' else types[kind].model_validate(payload)
        except TypeError as exc:raise ValueError('Invalid resource fields') from exc
        if kind=='venues':
            from backend.weather.grid import latlon_to_grid
            latlon_to_grid(item.lat,item.lon)
        if kind in {'teams','matches'}:
            t=Tournament(**self.repo.get('tournaments',item.tournament_id))
            if kind=='matches':
                self.repo.get('venues',item.venue_id)
                if not t.date_start<=item.scheduled_start.astimezone(KST).date()<=t.date_end:raise ValueError('Match date outside tournament')
                for tid in [item.team_a,item.team_b]:
                    if not tid.startswith('winner:'):
                        team=self.repo.get('teams',tid)
                        if team['tournament_id']!=item.tournament_id:raise ValueError('Team belongs to different tournament')
                    elif not item.depends_on:raise ValueError('Winner placeholder needs predecessors')
                ms=[Match(**m) for m in self.repo.list('matches') if m['tournament_id']==item.tournament_id and m['id']!=item.id]+[item]
                participants(ms)
        return jsonable_encoder(item)
    def replay(self,day,tournament_id='demo',engine=None,schedule=None,mode='mock'):
        if mode not in ('mock','observed'):raise ValueError('Unknown replay mode')
        engine=engine or EngineSettings();schedule=schedule or ScheduleSettings()
        t=Tournament(**self.repo.get('tournaments',tournament_id))
        delta=day-t.date_start
        t=t.model_copy(update={'date_start':day,'date_end':t.date_end+delta})
        matches=[Match(**m).model_copy(update={'scheduled_start':datetime.fromisoformat(m['scheduled_start'])+delta}) for m in self.repo.list('matches') if m['tournament_id']==t.id]
        if not matches:raise ValueError('Tournament has no matches')
        ids={m.venue_id for m in matches}
        venues=[Venue(**v) for v in self.repo.list('venues') if v['id'] in ids]
        dataset=load_dataset() if mode=='observed' else None
        if dataset:
            venues=[replace(v,asos_station_id=dataset.station_id) for v in venues]
        teams=[Team(**team) for team in self.repo.list('teams') if team['tournament_id']==t.id]
        all_points=[];risks=[];self.weather.save_venues(venues)
        manual=[]
        with self.weather.connect() as conn:
            for row in conn.execute('SELECT venue_id,valid_time,wbgt_c,entered_at,is_mock FROM manual_measurements'):
                manual.append(ManualMeasurement(row['venue_id'],datetime.fromisoformat(row['valid_time']),row['wbgt_c'],datetime.fromisoformat(row['entered_at']),bool(row['is_mock'])))
        for v in venues:
            points=[];current=t.date_start
            while current<=t.date_end:
                adapter=AsosObservationAdapter() if dataset else MockAsosAdapter()
                points+=adapter.fetch(v,v.asos_station_id or 'mock-station',current)
                current+=timedelta(days=1)
            all_points+=points
            risks+=estimate_series(v,points,t.age_group,t.policy_id,engine,manual)
        self.weather.save_weather(all_points)
        label=('기상청 관측 자료('+dataset.station['name']+' '+dataset.station_id+'·'+day.isoformat()+
               (('~'+t.date_end.isoformat()) if t.date_end!=day else '')+') · 가상 대회·팀·구장' if dataset else
               '가상 예시 · mock 합성 기상 재현 (실제 관측 아님)')
        session={'id':uuid4().hex,'created_at':datetime.now(KST),'label':label,
                 'mode':mode,'data_origin':'kma_observed' if dataset else 'synthetic',
                 'observation_summary':{'station':dataset.station,'original_sample_sha256':dataset.original_sha256,
                     'solar_missing_hours':sum(p.solar_wm2 is None for p in all_points)//len(venues),
                     'note':'동일 수원 지점 자료를 가상 구장에 공유; 현장 WBGT 실측이 아님'} if dataset else None,
                 'tournament':t,'teams':teams,'venues':venues,'matches':matches,'weather':all_points,'risks':risks,
                 'engine_settings':engine,'schedule_settings':schedule,'policy':policies()[t.policy_id],
                 'recommendations':[recommend(m,risks,engine) for m in matches],'proposal':None,'decision':None,'notifications':[]}
        return self.repo.put('sessions',session['id'],session)
    @staticmethod
    def context(s):
        t=Tournament(**s['tournament']);matches=[Match(**m) for m in s['matches']];venues=[Venue(**v) for v in s['venues']]
        risks=[RiskEstimate(**{**r,'valid_time':datetime.fromisoformat(r['valid_time'])}) for r in s['risks']]
        return t,matches,venues,risks,ScheduleSettings(**s['schedule_settings']),EngineSettings(**s['engine_settings'])
    def optimize(self,id):
        s=self.repo.get('sessions',id)
        if s['decision'] is not None:raise ValueError('Session decision already recorded; create a new replay to reconsider')
        t,matches,venues,risks,settings,engine=self.context(s)
        result=optimize(matches,t,venues,risks,settings,engine)
        s['proposal']={'id':uuid4().hex,**jsonable_encoder(result)}
        self.repo.put('sessions',id,s);return s['proposal']
    def decide(self,id,action,operator,reason,assignments=None):
        # Immediate transaction prevents duplicate approvals and notification duplication.
        with self.repo.connect() as conn:
            conn.execute('BEGIN IMMEDIATE');s=self.repo.get('sessions',id,conn)
            if s['decision'] is not None:raise ValueError('Decision already recorded')
            if not s['proposal']:raise ValueError('Optimize before deciding')
            t,matches,venues,risks,settings,engine=self.context(s)
            proposal=s['proposal'];selected=proposal['assignments']
            if action=='modified':
                if not assignments:raise ValueError('Modified assignments required')
                by={m.id:m for m in matches};selected=[]
                for row in assignments:
                    if row['match_id'] not in by:raise ValueError('Unknown match')
                    start=datetime.fromisoformat(row['start']);valid=candidates_for(by[row['match_id']],t,venues,risks,settings,engine)
                    candidate=next((c for c in valid if c.start==start and c.venue_id==row['venue_id']),None)
                    if not candidate:raise ValueError('Requested modified slot violates risk or operating constraints')
                    selected.append(jsonable_encoder(candidate))
                if {a['match_id'] for a in selected}!={a['match_id'] for a in proposal['assignments']}:raise ValueError('Modification must preserve proposed match coverage')
            candidates=[Candidate(**{**a,'start':datetime.fromisoformat(a['start']),'end':datetime.fromisoformat(a['end'])}) for a in selected]
            errors=validate(candidates,matches,t,venues,risks,settings)
            if errors:raise ValueError('Invalid proposal: '+','.join(errors))
            decision={'timestamp':datetime.now(KST),'operator_action':action,'operator_name':operator,'reason':reason,
                      'proposal_id':proposal['id'],'snapshot':{k:s[k] for k in ['label','mode','data_origin','observation_summary','tournament','venues','teams','matches','weather','risks','policy','recommendations','engine_settings','schedule_settings']},
                      'assignments':selected if action!='rejected' else [],'postponed':proposal['postponed'] if action!='rejected' else []}
            s['decision']=jsonable_encoder(decision)
            s['notifications']=build_notifications(s)
            self.repo.put('sessions',id,s,conn);self.repo.put('decisions',uuid4().hex,s['decision'],conn)
        return self.repo.get('sessions',id)
