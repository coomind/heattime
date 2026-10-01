from datetime import date,datetime,timedelta
from .models import Tournament,Team,Match
from backend.weather.models import KST
from backend.weather.cli import demo_venues

def demo_tournament(day=date(2026,8,1)):
    t=Tournament(id='demo',name='수원 유소년 축구대회 · 가상 예시',date_start=day,date_end=day)
    teams=[Team(id=f't{i+1}',tournament_id='demo',name=f'유소년 팀 {i+1} · 가상 예시') for i in range(12)]
    venues=demo_venues();matches=[];base=datetime.combine(day,datetime.min.time(),KST)
    for g in range(4):
        members=teams[g*3:g*3+3]
        for n,(a,b) in enumerate([(0,1),(1,2),(0,2)]):
            matches.append(Match(id=f'g{g+1}-{n+1}',tournament_id='demo',round=f'조별 {g+1}조',team_a=members[a].id,team_b=members[b].id,venue_id=venues[g%3].id,scheduled_start=base+timedelta(hours=10+n*2,minutes=g*15)))
    for n in range(2):
        deps=[m.id for m in matches if m.round in {f'조별 {n*2+1}조',f'조별 {n*2+2}조'}]
        matches.append(Match(id=f'semi{n+1}',tournament_id='demo',round='준결승',team_a=f'winner:group{n*2+1}',team_b=f'winner:group{n*2+2}',venue_id=venues[n].id,scheduled_start=base+timedelta(hours=16),depends_on=deps))
    matches.append(Match(id='final',tournament_id='demo',round='결승',team_a='winner:semi1',team_b='winner:semi2',venue_id=venues[0].id,scheduled_start=base+timedelta(hours=18),depends_on=['semi1','semi2']))
    return t,teams,matches,venues
