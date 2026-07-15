from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SessionType = Literal["FP1", "FP2", "FP3", "Q", "R", "S", "SS"]


class EventSummary(BaseModel):
    year: int
    round: int = Field(alias="round_number")
    event_name: str
    country: str | None = None
    location: str | None = None
    event_date: datetime | None = None


class SessionLoadRequest(BaseModel):
    year: int
    round: int
    session_type: SessionType


class SessionLoadResponse(BaseModel):
    session_id: str
    event_name: str
    loaded_drivers: int
    loaded_laps: int
    data_updated_at: datetime


class DriverSummary(BaseModel):
    driver_code: str
    driver_number: str | None = None
    full_name: str | None = None
    team_name: str | None = None


class LapSummary(BaseModel):
    lap_number: int
    driver_code: str
    lap_time_seconds: float | None = None
    sector1_seconds: float | None = None
    sector2_seconds: float | None = None
    sector3_seconds: float | None = None
    compound: str | None = None
    tyre_life: float | None = None


class GapSummary(BaseModel):
    driver_code: str
    best_lap_seconds: float | None = None
    gap_to_leader_seconds: float | None = None


class TyreStintSummary(BaseModel):
    driver_code: str
    stint: int
    start_lap: int
    end_lap: int
    compound: str | None = None
    max_tyre_life: float | None = None


class PitStopSummary(BaseModel):
    driver_code: str
    lap_number: int
    pit_in_time: str | None = None
    pit_out_time: str | None = None
    pit_in_seconds: float | None = None
    pit_out_seconds: float | None = None
    stint: int | None = None
    compound: str | None = None


class SectorComparisonSummary(BaseModel):
    driver_a: str
    driver_b: str
    sector1_delta_seconds: float | None = None
    sector2_delta_seconds: float | None = None
    sector3_delta_seconds: float | None = None
    lap_delta_seconds: float | None = None


class TelemetryPointSummary(BaseModel):
    distance: float | None = None
    time_seconds: float | None = None
    speed: float | None = None
    throttle: float | None = None
    brake: float | None = None
    rpm: float | None = None
    n_gear: float | None = None


class TelemetryComparisonSummary(BaseModel):
    driver_a: str
    driver_b: str
    points_a: list[TelemetryPointSummary]
    points_b: list[TelemetryPointSummary]


class MultiSessionPoint(BaseModel):
    session_type: str
    session_id: str
    best_lap_seconds: float | None = None
    average_lap_seconds: float | None = None
    lap_count: int = 0
    position_by_best_lap: int | None = None


class MultiSessionComparisonSummary(BaseModel):
    year: int
    round: int
    driver_code: str
    event_name: str | None = None
    points: list[MultiSessionPoint]


class PrecomputeJobResponse(BaseModel):
    job_id: str
    status: str
    message: str | None = None


class ExportSummary(BaseModel):
    file_name: str
    format: str
    dataset: str


class ReplayDriverSnapshot(BaseModel):
    code: str
    x: float
    y: float
    dist: float
    lap: int
    position: int
    speed: float
    gear: int
    drs: int
    throttle: float
    brake: float
    is_pitting: bool = False


class ReplayFrame(BaseModel):
    t: float
    lap: int
    drivers: dict[str, ReplayDriverSnapshot]


class SessionReplaySummary(BaseModel):
    session_id: str
    total_laps: int
    frames: list[ReplayFrame]
    track_layout: dict[str, list[float]] | None = None
    driver_colors: dict[str, str] | None = None
