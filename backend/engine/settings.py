from pydantic import BaseModel, Field, ConfigDict


class EngineSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    uncertainty_c: float = Field(default=1.5, ge=0, le=10)
    rain_attenuation: float = Field(default=0.5, ge=0, le=1)
    wind_exponent: float = Field(default=0.2, ge=0, le=1)
    pressure_hpa: float = Field(default=1013.25, ge=600, le=1100)
    # Pressure not in P1 schema: explicit sea-level screening assumption.
    surface_offsets: dict[str, float] = Field(default_factory=lambda: {
        "natural_grass": 0, "artificial_turf": 0, "dirt": 0, "indoor": 0})
    age_escalation: bool = False
    cooling_min: int = Field(default=3, ge=1, le=15)
    shorten_ratio: float = Field(default=0.75, gt=0, le=1)
