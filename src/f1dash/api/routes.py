from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from f1dash.models.schemas import (
    DriverSummary,
    EventSummary,
    GapSummary,
    LapSummary,
    MultiSessionComparisonSummary,
    PitStopSummary,
    PrecomputeJobResponse,
    SectorComparisonSummary,
    SessionLoadRequest,
    SessionLoadResponse,
    SessionReplaySummary,
    TelemetryComparisonSummary,
    TyreStintSummary,
)
from f1dash.services import export_service, precompute_service, session_service

router = APIRouter(prefix="/api", tags=["f1dash"])


@router.get("/sessions", response_model=list[EventSummary])
def list_sessions(year: int = Query(..., ge=2018, le=2100)) -> list[EventSummary]:
    events = session_service.list_events(year)
    return [EventSummary.model_validate(event) for event in events]


@router.post("/sessions/load", response_model=SessionLoadResponse)
def load_session(payload: SessionLoadRequest) -> SessionLoadResponse:
    try:
        loaded = session_service.load_session(
            year=payload.year,
            round_number=payload.round,
            session_type=payload.session_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SessionLoadResponse.model_validate(loaded)


@router.get("/sessions/{session_id}/drivers", response_model=list[DriverSummary])
def get_drivers(session_id: str) -> list[DriverSummary]:
    try:
        drivers = session_service.get_drivers(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [DriverSummary.model_validate(driver) for driver in drivers]


@router.get("/sessions/{session_id}/laps", response_model=list[LapSummary])
def get_laps(
    session_id: str,
    driver_code: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=5000),
) -> list[LapSummary]:
    try:
        laps = session_service.get_laps(session_id, driver_code=driver_code, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    items: list[LapSummary] = []
    for _, row in laps.iterrows():
        lap_time = _to_seconds(row.get("LapTime", row.get("lap_time_seconds")))
        sector1 = _to_seconds(row.get("Sector1Time", row.get("sector1_seconds")))
        sector2 = _to_seconds(row.get("Sector2Time", row.get("sector2_seconds")))
        sector3 = _to_seconds(row.get("Sector3Time", row.get("sector3_seconds")))

        items.append(
            LapSummary(
                lap_number=int(row.get("LapNumber", row.get("lap_number", 0))),
                driver_code=str(row.get("Driver", row.get("driver_code", ""))),
                lap_time_seconds=lap_time,
                sector1_seconds=sector1,
                sector2_seconds=sector2,
                sector3_seconds=sector3,
                compound=row.get("Compound", row.get("compound")),
                tyre_life=(
                    float(row.get("TyreLife", row.get("tyre_life")))
                    if row.get("TyreLife", row.get("tyre_life")) is not None
                    else None
                ),
            )
        )
    return items


@router.get("/sessions/{session_id}/gaps", response_model=list[GapSummary])
def get_gaps(session_id: str) -> list[GapSummary]:
    try:
        gaps = session_service.get_gap_summaries(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [GapSummary.model_validate(item) for item in gaps]


@router.get("/sessions/{session_id}/tyres", response_model=list[TyreStintSummary])
def get_tyres(session_id: str) -> list[TyreStintSummary]:
    try:
        stints = session_service.get_tyre_stints(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [TyreStintSummary.model_validate(stint) for stint in stints]


@router.get("/sessions/{session_id}/pit-stops", response_model=list[PitStopSummary])
def get_pit_stops(session_id: str) -> list[PitStopSummary]:
    try:
        events = session_service.get_pit_stops(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [PitStopSummary.model_validate(event) for event in events]


@router.get("/sessions/{session_id}/race-replay", response_model=SessionReplaySummary)
def get_session_replay(session_id: str) -> SessionReplaySummary:
    try:
        replay = session_service.get_session_replay(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SessionReplaySummary.model_validate(replay)


@router.get("/sessions/{session_id}/compare/sectors", response_model=SectorComparisonSummary)
def get_sector_comparison(
    session_id: str,
    driver_a: str = Query(..., min_length=1, max_length=3),
    driver_b: str = Query(..., min_length=1, max_length=3),
) -> SectorComparisonSummary:
    try:
        comparison = session_service.get_sector_comparison(session_id, driver_a=driver_a, driver_b=driver_b)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SectorComparisonSummary.model_validate(comparison)


@router.get("/sessions/{session_id}/replay")
def get_session_replay_data(
    session_id: str,
    drivers: str = Query(..., description="Comma-separated driver codes"),
    fps: int = Query(default=5, ge=1, le=25),
) -> dict[str, Any]:
    driver_list = [d.strip().upper() for d in drivers.split(",") if d.strip()]
    try:
        return session_service.get_session_replay_data(session_id, driver_list, fps=fps)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/compare/telemetry", response_model=TelemetryComparisonSummary)
def get_telemetry_comparison(
    session_id: str,
    driver_a: str = Query(..., min_length=1, max_length=3),
    driver_b: str = Query(..., min_length=1, max_length=3),
    sample_size: int = Query(default=200, ge=50, le=1000),
    lap_number: int | None = Query(default=None, ge=1, le=100),
) -> TelemetryComparisonSummary:
    try:
        telemetry = session_service.get_telemetry_comparison(
            session_id,
            driver_a=driver_a,
            driver_b=driver_b,
            sample_size=sample_size,
            lap_number=lap_number,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return TelemetryComparisonSummary.model_validate(telemetry)


@router.get("/events/{year}/{round_number}/compare", response_model=MultiSessionComparisonSummary)
def get_multi_session_comparison(
    year: int,
    round_number: int,
    driver_code: str = Query(..., min_length=1, max_length=3),
    session_types: str = Query(default="FP1,FP2,Q,R"),
) -> MultiSessionComparisonSummary:
    parsed_session_types = [item.strip().upper() for item in session_types.split(",") if item.strip()]
    try:
        payload = session_service.get_multi_session_comparison(
            year=year,
            round_number=round_number,
            driver_code=driver_code,
            session_types=parsed_session_types,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MultiSessionComparisonSummary.model_validate(payload)


@router.post("/events/{year}/{round_number}/precompute", response_model=PrecomputeJobResponse)
def start_precompute_job(
    year: int,
    round_number: int,
    session_types: str = Query(default="FP1,FP2,Q,R"),
) -> PrecomputeJobResponse:
    parsed_session_types = [item.strip().upper() for item in session_types.split(",") if item.strip()]
    job_id = precompute_service.start_event_warmup(
        year=year,
        round_number=round_number,
        session_types=parsed_session_types,
    )
    return PrecomputeJobResponse(job_id=job_id, status="queued", message="Warmup job queued")


@router.get("/precompute/{job_id}", response_model=PrecomputeJobResponse)
def get_precompute_job(job_id: str) -> PrecomputeJobResponse:
    try:
        job = precompute_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PrecomputeJobResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        message=job.get("message"),
    )


@router.get("/sessions/{session_id}/export")
def export_session_dataset(
    session_id: str,
    dataset: str = Query(default="laps"),
    export_format: str = Query(default="csv", alias="format"),
    driver_code: str | None = Query(default=None),
):
    try:
        path = export_service.export_session_dataset(
            session_id=session_id,
            dataset=dataset,
            export_format=export_format,
            driver_code=driver_code,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_type = "text/csv" if export_format.lower() == "csv" else "application/octet-stream"
    return FileResponse(path=str(path), filename=path.name, media_type=media_type)


@router.get("/events/{year}/{round_number}/compare/export")
def export_multi_session_comparison(
    year: int,
    round_number: int,
    driver_code: str = Query(..., min_length=1, max_length=3),
    export_format: str = Query(default="csv", alias="format"),
):
    try:
        path = export_service.export_multi_session_comparison(
            year=year,
            round_number=round_number,
            driver_code=driver_code,
            export_format=export_format,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_type = "text/csv" if export_format.lower() == "csv" else "application/octet-stream"
    return FileResponse(path=str(path), filename=path.name, media_type=media_type)


def _to_seconds(value) -> float | None:
    if value is None:
        return None
    if hasattr(value, "total_seconds"):
        return round(float(value.total_seconds()), 3)
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None
