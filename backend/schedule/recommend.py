from dataclasses import dataclass
from datetime import timedelta
from backend.engine.settings import EngineSettings

class MissingRisk(ValueError): pass

@dataclass(frozen=True)
class Recommendation:
    match_id: str
    level: int
    action: str
    detail: str
    duration_min: int
    end: object
    cooling_times: list
    wbgt_c: float | None
    wbgt_low_c: float | None
    wbgt_high_c: float | None


def window_risks(risks,venue_id,start,end):
    hourly={r.valid_time:r for r in risks if r.venue_id==venue_id}
    hour=start.replace(minute=0,second=0,microsecond=0);selected=[]
    while hour<=end:
        if hour not in hourly: raise MissingRisk("기상 자료 누락: 배정 보류")
        selected.append(hourly[hour]);hour+=timedelta(hours=1)
    return selected


def recommend(match,risks,settings=None):
    settings=settings or EngineSettings()
    base=match.duration_min+(match.halves-1)*match.half_break_min
    duration=base;level=0;samples=[]
    for _ in range(3):
        end=match.scheduled_start+timedelta(minutes=duration)
        try:samples=window_risks(risks,match.venue_id,match.scheduled_start,end)
        except MissingRisk:return Recommendation(match.id,4,'postpone','자료 누락 · 운영자 확인 필요',duration,end,[],None,None,None)
        level=max(level,max(r.level for r in samples))
        new=base+settings.cooling_min*match.halves if level==2 else base
        if level>=3 or new==duration:break
        duration=new
    action={0:'none',1:'none',2:'cooling_break',3:'shorten',4:'postpone'}[level]
    detail={0:'수분 보충 안내',1:'정기 수분 보충',2:f'각 하프 중간 {settings.cooling_min}분 쿨링브레이크',3:'격렬한 운동 피함 · 경기시간 단축 또는 시간 이동',4:'해당 시간대 배정 금지 · 이동 또는 연기'}[level]
    play=match.duration_min
    if level==3:play=max(1,int(play*settings.shorten_ratio));duration=play+(match.halves-1)*match.half_break_min
    cooling=[match.scheduled_start+timedelta(minutes=h*(play/match.halves+match.half_break_min+settings.cooling_min)+play/match.halves/2) for h in range(match.halves)] if level==2 else []
    return Recommendation(match.id,level,action,detail,duration,match.scheduled_start+timedelta(minutes=duration),cooling,max(r.wbgt_c for r in samples),max(r.wbgt_low_c for r in samples),max(r.wbgt_high_c for r in samples))
