from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from f1dash.services.session_service import SessionService


class ExportService:
    """Exports normalized session datasets into CSV or Parquet files."""

    def __init__(self, session_service: SessionService, export_dir: str) -> None:
        self._session_service = session_service
        self._export_dir = Path(export_dir)
        self._export_dir.mkdir(parents=True, exist_ok=True)

    def export_session_dataset(
        self,
        session_id: str,
        dataset: str,
        export_format: str,
        driver_code: str | None = None,
    ) -> Path:
        dataset_key = dataset.lower()
        export_key = export_format.lower()

        if dataset_key == "laps":
            frame = self._to_df(self._session_service.get_laps(session_id, driver_code=driver_code, limit=5000))
        elif dataset_key == "gaps":
            frame = self._to_df(self._session_service.get_gap_summaries(session_id))
        elif dataset_key == "tyres":
            frame = self._to_df(self._session_service.get_tyre_stints(session_id))
        elif dataset_key == "pit_stops":
            frame = self._to_df(self._session_service.get_pit_stops(session_id))
        else:
            raise KeyError(f"Unsupported dataset: {dataset}")

        return self._write(frame, session_id=session_id, dataset=dataset_key, export_format=export_key)

    def export_multi_session_comparison(
        self,
        year: int,
        round_number: int,
        driver_code: str,
        export_format: str,
    ) -> Path:
        comparison = self._session_service.get_multi_session_comparison(year, round_number, driver_code)
        frame = self._to_df(comparison.get("points", []))
        session_id = f"{year}-{round_number}-trend-{driver_code.upper()}"
        return self._write(frame, session_id=session_id, dataset="multi_session", export_format=export_format)

    def _write(self, frame: pd.DataFrame, session_id: str, dataset: str, export_format: str) -> Path:
        safe_session = session_id.replace("/", "-")
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        if export_format == "csv":
            path = self._export_dir / f"{safe_session}-{dataset}-{ts}.csv"
            frame.to_csv(path, index=False)
            return path

        if export_format == "parquet":
            path = self._export_dir / f"{safe_session}-{dataset}-{ts}.parquet"
            frame.to_parquet(path, index=False)
            return path

        raise KeyError(f"Unsupported export format: {export_format}")

    @staticmethod
    def _to_df(data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data.copy()
        return pd.DataFrame(data)
