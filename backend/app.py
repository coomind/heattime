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
    expected_revision: str | None = Field(default=None,min_length=64,max_length=64)
class ManualRequest(BaseModel):
    venue_id: str
    valid_time: datetime
    wbgt_c: float
    is_mock: bool = True

class LiveRequest(BaseModel):
    mode: Literal['mock','api'] = 'mock'
    station_id: int = Field(default=119,ge=1,le=9999)
    tournament_id: str = 'demo'
    engine_settings: EngineSettings = Field(default_factory=EngineSettings)


def create_app(db_path=None):
    app=FastAPI(title='HeatTime · 의사결정 보조',version='0.4.0')
    repo=Repository(db_path or ROOT/'data/heattime.sqlite3');service=Service(repo)
    app.state.repo=repo;app.state.service=service
    from backend.weather.aws_live import LiveProvider
    app.state.live_provider=LiveProvider(repo)
    from backend.validation import WorkEvidence,FieldEvidence,save_work,save_field,evidence_summary,evidence_csv
    @app.get('/api/validation/summary')
    def validation_summary():return evidence_summary(repo)
    @app.post('/api/validation/work',status_code=201)
    def validation_work(body:WorkEvidence):return save_work(repo,body)
    @app.post('/api/validation/field',status_code=201)
    def validation_field(body:FieldEvidence):return save_field(repo,body)
    @app.api_route('/api/validation/{kind}',methods=['PUT','PATCH','DELETE'])
    def validation_readonly(kind:str):raise HTTPException(405,'검증 기록은 추가 저장만 지원합니다.')
    @app.get('/api/validation/export/{format}')
    def validation_export(format:str):
        summary=evidence_summary(repo)
        if format=='json':return summary
        if format!='csv':raise HTTPException(404,'Unknown export format')
        return Response(evidence_csv(summary),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="heattime-validation.csv"'})
    @app.post('/api/live-observations')
    def live_observations(body:LiveRequest):
        from dataclasses import asdict
        from backend.weather.aws_live import AwsObservation
        from backend.engine.wbgt import estimate
        tour=repo.get('tournaments',body.tournament_id)
        result=app.state.live_provider.get(body.station_id,body.mode)
        observation=result['observation']
        result['risks']=[]
        result['tournament_name']=tour['name']
        result['age_group']=tour['age_group']
        result['policy_id']=tour['policy_id']
        if observation:
            point=AwsObservation(**observation)
            for raw in repo.list('venues'):
                venue=Venue(**raw)
                risk=estimate(venue,point.point(venue.id),tour['age_group'],tour['policy_id'],body.engine_settings)
                result['risks'].append({'venue_name':venue.name,**asdict(risk)})
        # This endpoint does not update replay/approved records or optimize future games.
        return result
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
    @app.post('/api/tournaments/{id}/matches/csv-preview')
    def csv_preview(id:str,body:CsvRequest):
        from backend.csv_import import prepare_csv
        with repo.connect() as conn:
            conn.execute('BEGIN')
            return prepare_csv(repo,id,body.csv_text,conn)
    @app.get('/api/tournaments/{id}/matches/csv-template')
    def csv_template(id:str):
        from backend.csv_import import template_csv
        return Response(template_csv(repo,id),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="heattime-matches-template.csv"'})
    @app.post('/api/tournaments/{id}/matches/csv')
    def upload(id:str,body:CsvRequest):
        from backend.csv_import import prepare_csv
        with repo.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            checked=prepare_csv(repo,id,body.csv_text,conn)
            if checked['errors']:
                raise HTTPException(checked['errors'][0]['status'],detail={'errors':checked['errors']})
            if body.expected_revision and body.expected_revision!=checked['revision']:
                raise HTTPException(409,'확인 후 등록 자료가 변경되었습니다. CSV를 다시 확인하세요.')
            for row in checked['rows']:repo.put('matches',row['match']['id'],row['match'],conn)
        return {'imported':len(checked['rows'])}
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
