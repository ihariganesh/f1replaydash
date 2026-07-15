from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import traceback
from typing import Any
from uuid import uuid4

from f1dash.services.session_service import SessionService


class PrecomputeService:
    """Runs background cache warmup jobs and tracks status in memory."""

    def __init__(self, session_service: SessionService) -> None:
        self._session_service = session_service
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="precompute")
        self._jobs: dict[str, dict[str, Any]] = {}

    def start_event_warmup(self, year: int, round_number: int, session_types: list[str]) -> str:
        job_id = str(uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "message": "Warmup job queued",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "year": year,
            "round": round_number,
            "session_types": session_types,
        }

        self._executor.submit(self._run_event_warmup, job_id, year, round_number, session_types)
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise KeyError(f"Unknown precompute job: {job_id}")
        return self._jobs[job_id]

    def _run_event_warmup(self, job_id: str, year: int, round_number: int, session_types: list[str]) -> None:
        try:
            self._update(job_id, status="running", message="Warmup in progress")

            for session_type in session_types:
                self._session_service.load_session(year, round_number, session_type)
                session_id = self._session_service.build_session_id(year, round_number, session_type)

                self._session_service.get_drivers(session_id)
                self._session_service.get_laps(session_id, limit=5000)
                self._session_service.get_gap_summaries(session_id)
                self._session_service.get_tyre_stints(session_id)
                self._session_service.get_pit_stops(session_id)

                drivers = self._session_service.get_drivers(session_id)
                if len(drivers) >= 2:
                    first = drivers[0]["driver_code"]
                    second = drivers[1]["driver_code"]
                    self._session_service.get_sector_comparison(session_id, first, second)
                    self._session_service.get_telemetry_comparison(session_id, first, second, sample_size=200)

            self._update(job_id, status="completed", message="Warmup completed")
        except Exception as exc:  # noqa: BLE001
            details = f"Warmup failed: {exc}\n{traceback.format_exc()}"
            self._update(job_id, status="failed", message=details)

    def _update(self, job_id: str, status: str, message: str) -> None:
        if job_id not in self._jobs:
            return
        self._jobs[job_id]["status"] = status
        self._jobs[job_id]["message"] = message
        self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
