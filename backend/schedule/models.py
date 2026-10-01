from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from backend.weather.models import require_aware

class Tournament(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    sport: Literal["football"] = "football"
    date_start: date
    date_end: date
    age_group: Literal["U10","U12","U15","U18","adult","senior"] = "U12"
    policy_id: Literal["general","football"] = "general"
    is_mock: bool = True
    @model_validator(mode="after")
    def dates(self):
        if self.date_end < self.date_start: raise ValueError("Invalid dates")
        return self

class Team(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    tournament_id: str
    name: str = Field(min_length=1)
    contact: str = "가상 예시 · 모의 수신함"
    is_mock: bool = True

class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    tournament_id: str
    round: str
    team_a: str
    team_b: str
    venue_id: str
    scheduled_start: datetime
    duration_min: int = Field(default=40, ge=10, le=180)
    halves: int = Field(default=2, ge=1, le=4)
    half_break_min: int = Field(default=5, ge=0, le=30)
    depends_on: list[str] = Field(default_factory=list)
    status: Literal["scheduled","modified","postponed","done"] = "scheduled"
    @field_validator("scheduled_start")
    @classmethod
    def aware(cls,value): require_aware(value); return value
    @model_validator(mode="after")
    def valid(self):
        if self.team_a==self.team_b or self.id in self.depends_on: raise ValueError("Invalid participants/dependency")
        return self

class ScheduleSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot_min: Literal[10,15] = 15
    cleanup_min: int = Field(default=5,ge=0,le=30)
    open_hour: int = Field(default=7,ge=0,le=23)
    close_hour: int = Field(default=20,ge=1,le=24)
    rest_by_age: dict[str,int] = Field(default_factory=lambda:{"U10":60,"U12":60,"U15":60,"U18":45,"adult":30,"senior":60})
    heat_weight: int = Field(default=100,ge=1,le=10000)
    time_weight: int = Field(default=1,ge=0,le=1000)
    venue_penalty: int = Field(default=30,ge=0,le=10000)
    time_limit_sec: float = Field(default=10,gt=0,le=10)
    @model_validator(mode="after")
    def valid(self):
        if self.close_hour<=self.open_hour or any(v<0 for v in self.rest_by_age.values()): raise ValueError("Invalid hours/rest")
        return self


def default_schedule_settings():
    from pathlib import Path
    import yaml
    return ScheduleSettings(**yaml.safe_load((Path(__file__).parents[1]/"config/schedule.yaml").read_text(encoding="utf-8")))
