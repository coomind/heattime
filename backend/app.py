from datetime import date as CalendarDate,datetime
from pathlib import Path
from typing import Literal
import csv,io
from fastapi import FastAPI,HTTPException,Body
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from backend.repository import Repository
from backend.service import Service
from backend.exports import records_pdf,records_csv
from backend.engine.settings import EngineSettings
from backend.engine.policy import policies
from backend.schedule.models import ScheduleSettings,Match
from backend.schedule.optimizer import participants
from backend.weather.models import ManualMeasurement,Venue,KST

ROOT=Path(__file__).resolve().parents[1]
class ReplayRequest(BaseModel):
    date: CalendarDate = CalendarDate(2026,8,1)
    tournament_id: str = 'demo'
    region: Literal['suwon'] = 'suwon'
    mode: Literal['mock','observed'] = 'mock'
    engine_settings: EngineSettings = Field(default_factory=EngineSettings)
    schedule_settings: ScheduleSettings = Field(default_factory=ScheduleSettings)
class DecisionRequest(BaseModel):
    action: Literal['accepted','modified','rejected']
    operator_name: str = Field(default='가상 예시 운영자',min_length=1,max_length=100)
    reason: str = Field(min_length=1,max_length=1000)
    assignments: list[dict] | None = None
class CsvRequest(BaseModel):
    csv_text: str = Field(max_length=1000000)
class ManualRequest(BaseModel):
    venue_id: str
    valid_time: datetime
    wbgt_c: float
    is_mock: bool = True


def create_app(db_path=None):
    app=FastAPI(title='HeatTime · 의사결정 보조',version='0.4.0')
    repo=Repository(db_path or ROOT/'data/heattime.sqlite3');service=Service(repo)
    app.state.repo=repo;app.state.service=service
    @app.exception_handler(KeyError)
    async def missing(request,exc):return Response('Resource not found',status_code=404)
    @app.exception_handler(ValueError)
    async def invalid(request,exc):return Response(str(exc),status_code=422)
    @app.get('/api/health')
    def health():return {'status':'ok','mode':'mock','label':'가상 예시'}
    @app.get('/api/policies')
    def policy():return policies()
    @app.get('/api/settings')
    def settings():return {'engine':EngineSettings(),'schedule':ScheduleSettings(),'age_note':policies()['age']['note']}
    @app.get('/api/observations')
    def observations():
        from backend.weather.asos_samples import load_dataset
        try:data=load_dataset()
        except FileNotFoundError:return {'available':False,'dates':[]}
        results=ROOT/'docs/real-data/replay-results.json'
        recommended=None
        if results.exists():
            import json
            saved=json.loads(results.read_text(encoding='utf-8'))
            if saved['original_sample_sha256']==data.original_sha256:
                recommended=saved['candidates'][0]['date']
        return {'available':True,'station':data.station,'dates':[d.isoformat() for d in data.dates],'recommended_date':recommended,
                'label':'기상청 관측 자료(수원 119)','solar_interval':'이전1시간 에너지 → 시간평균 W/m²'}
    @app.post('/api/replays')
    def replay(body:ReplayRequest):return service.replay(body.date,body.tournament_id,body.engine_settings,body.schedule_settings,body.mode)
    @app.get('/api/sessions/{id}')
    def session(id:str):return repo.get('sessions',id)
    @app.get('/api/sessions/{id}/risks')
    def risks(id:str):return repo.get('sessions',id)['risks']
    @app.get('/api/sessions/{id}/recommendations')
    def recommendations(id:str):return repo.get('sessions',id)['recommendations']
    @app.get('/api/sessions/{id}/matches/{match_id}')
    def detail(id:str,match_id:str):
        s=repo.get('sessions',id);m=next((m for m in s['matches'] if m['id']==match_id),None)
        if not m:raise KeyError(match_id)
        return {'match':m,'risks':[r for r in s['risks'] if r['venue_id']==m['venue_id']],
                'recommendation':next(r for r in s['recommendations'] if r['match_id']==match_id),'policy':s['policy']}
    @app.post('/api/sessions/{id}/optimize')
    def optimize(id:str):return service.optimize(id)
    @app.get('/api/sessions/{id}/matches/{match_id}/evidence')
    def evidence(id:str,match_id:str,view:Literal['proposed','approved']='proposed'):
        from backend.evidence import schedule_evidence
        return schedule_evidence(repo.get('sessions',id),match_id,view)
    @app.post('/api/sessions/{id}/decision')
    def decision(id:str,body:DecisionRequest):return service.decide(id,body.action,body.operator_name,body.reason,body.assignments)
    @app.get('/api/sessions/{id}/notifications')
    def notifications(id:str):return repo.get('sessions',id)['notifications']
    @app.get('/api/sessions/{id}/records')
    def records(id:str):return repo.get('sessions',id)['decision']
    @app.get('/api/sessions/{id}/export/{format}')
    def export(id:str,format:str):
        s=repo.get('sessions',id)
        if format=='pdf':data=records_pdf(s);media='application/pdf'
        elif format=='csv':data=records_csv(s);media='text/csv; charset=utf-8'
        elif format=='json':return s
        else:raise HTTPException(404,'Unknown export format')
        return Response(data,media_type=media,headers={'Content-Disposition':f'attachment; filename="heattime-{id}.{format}"'})
    @app.get('/api/team-view/{id}')
    def team_view(id:str):
        s=repo.get('sessions',id)
        return {k:s.get(k) for k in ['label','mode','data_origin','observation_summary','tournament','decision','teams','venues','matches']}
    @app.post('/api/manual')
    def manual(body:ManualRequest):
        venue=repo.get('venues',body.venue_id);m=ManualMeasurement(body.venue_id,body.valid_time,body.wbgt_c,datetime.now(KST),body.is_mock)
        service.weather.save_venues([Venue(**venue)])
        return {'id':service.weather.save_manual(m),'label':'현장 WBGT 실측 입력','next':'새 재현 실행에서 보정 반영'}
    @app.get('/api/manual')
    def manual_history():
        with service.weather.connect() as conn:
            return [{**dict(row),'is_mock':bool(row['is_mock'])} for row in conn.execute('SELECT id,venue_id,valid_time,wbgt_c,entered_at,is_mock FROM manual_measurements ORDER BY valid_time,id')]
    @app.get('/api/sessions/{id}/input-evidence')
    def input_detail(id:str,venue_id:str,valid_time:str,view:Literal['original','proposed','approved']='original'):
        from backend.input_evidence import input_evidence
        return input_evidence(repo.get('sessions',id),venue_id,valid_time,view)
    @app.post('/api/tournaments/{id}/matches/csv')
    def upload(id:str,body:CsvRequest):
        t=repo.get('tournaments',id);rows=[]
        reader=csv.DictReader(io.StringIO(body.csv_text.lstrip('\ufeff')),strict=True)
        try:
            if reader.fieldnames and len(reader.fieldnames)!=len(set(reader.fieldnames)):
                raise ValueError('CSV 열 이름이 중복되었습니다.')
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f'CSV {reader.line_num}행의 열 수가 헤더와 다릅니다.')
                row['tournament_id']=id;row['depends_on']=[d.strip() for d in row.get('depends_on','').split(';') if d.strip()]
                for k in ['duration_min','halves','half_break_min']:
                    if not row.get(k):row.pop(k,None)
                rows.append(Match.model_validate(row))
        except csv.Error as exc:
            raise ValueError(f'CSV {reader.line_num}행의 형식이 올바르지 않습니다. 따옴표를 확인하세요.') from exc
        if not rows or len({r.id for r in rows})!=len(rows):raise ValueError('Empty CSV or duplicate ids')
        existing=[Match(**m) for m in repo.list('matches') if m['tournament_id']==id and m['id'] not in {r.id for r in rows}]
        participants(existing+rows)
        for m in rows:
            repo.get('venues',m.venue_id)
            if not CalendarDate.fromisoformat(t['date_start'])<=m.scheduled_start.astimezone(KST).date()<=CalendarDate.fromisoformat(t['date_end']):raise ValueError('CSV match outside dates')
            for tid in [m.team_a,m.team_b]:
                if not tid.startswith('winner:') and repo.get('teams',tid)['tournament_id']!=id:raise ValueError('Invalid CSV team')
        with repo.connect() as conn:
            # Check global ids under the write lock before importing any row.
            conn.execute('BEGIN IMMEDIATE')
            for m in rows:
                try:stored=repo.get('matches',m.id,conn)
                except KeyError:continue
                if stored['tournament_id']!=id:
                    raise HTTPException(409,f'경기 ID {m.id}는 다른 대회에서 사용 중입니다.')
            for m in rows:repo.put('matches',m.id,m,conn)
        return {'imported':len(rows)}
    kinds={'venues','tournaments','teams','matches'}
    @app.get('/api/{kind}')
    def list_resources(kind:str):
        if kind not in kinds:raise KeyError(kind)
        return repo.list(kind)
    @app.get('/api/{kind}/{id}')
    def get_resource(kind:str,id:str):
        if kind not in kinds:raise KeyError(kind)
        return repo.get(kind,id)
    @app.post('/api/{kind}',status_code=201)
    def create_resource(kind:str,body:dict=Body(...)):
        item=service.validate_resource(kind,body)
        if any(r['id']==item['id'] for r in repo.list(kind)):raise HTTPException(409,'Duplicate id')
        return repo.put(kind,item['id'],item)
    @app.put('/api/{kind}/{id}')
    def update_resource(kind:str,id:str,body:dict=Body(...)):
        repo.get(kind,id)
        if body.get('id')!=id:raise ValueError('Id cannot change')
        item=service.validate_resource(kind,body)
        if kind=='tournaments':
            for m in repo.list('matches'):
                if m['tournament_id']==id and not item['date_start']<=m['scheduled_start'][:10]<=item['date_end']:raise ValueError('Existing match outside updated dates')
        return repo.put(kind,id,item)
    @app.delete('/api/{kind}/{id}',status_code=204)
    def delete_resource(kind:str,id:str):
        if kind not in kinds:raise KeyError(kind)
        repo.get(kind,id);matches=repo.list('matches')
        used=(kind=='venues' and any(m['venue_id']==id for m in matches)) or (kind=='teams' and any(id in [m['team_a'],m['team_b']] for m in matches)) or (kind=='matches' and any(id in m['depends_on'] for m in matches)) or (kind=='tournaments' and (any(m['tournament_id']==id for m in matches) or any(t['tournament_id']==id for t in repo.list('teams'))))
        if used:raise HTTPException(409,'Referenced resource cannot be deleted')
        repo.delete(kind,id)
    dist=ROOT/'frontend/dist'
    if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app
