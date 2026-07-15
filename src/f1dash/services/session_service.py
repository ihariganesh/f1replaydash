from datetime import datetime, timedelta
import json
import sys
from pathlib import Path
from typing import Any

import fastf1
import numpy as np
import pandas as pd

from f1dash.services.cache_service import CacheService
from f1dash.services.metrics_service import calculate_best_lap_gaps


class SessionService:
    """Loads and serves FastF1 sessions from an in-memory registry."""

    def __init__(
        self,
        cache_dir: str,
        snapshot_dir: str,
        cache_service: CacheService | None = None,
        cache_ttl_seconds: int = 900,
    ) -> None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        self._sessions: dict[str, Any] = {}
        self._loaded_at: dict[str, datetime] = {}
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._snapshot_dir = Path(snapshot_dir)
        self._cache = cache_service
        self._cache_ttl_seconds = cache_ttl_seconds

    @staticmethod
    def build_session_id(year: int, round_number: int, session_type: str) -> str:
        return f"{year}-{round_number}-{session_type.upper()}"

    def list_events(self, year: int) -> list[dict[str, Any]]:
        schedule = fastf1.get_event_schedule(year)
        events: list[dict[str, Any]] = []
        for _, row in schedule.iterrows():
            events.append(
                {
                    "year": year,
                    "round_number": int(row.get("RoundNumber", 0)),
                    "event_name": row.get("EventName"),
                    "country": row.get("Country"),
                    "location": row.get("Location"),
                    "event_date": row.get("EventDate"),
                }
            )
        return events

    def load_session(self, year: int, round_number: int, session_type: str) -> dict[str, Any]:
        session_id = self.build_session_id(year, round_number, session_type)

        if session_id in self._sessions:
            session = self._sessions[session_id]
            return self._build_load_response(session_id, session)

        snapshot = self._load_snapshot(session_id)
        if snapshot is not None:
            if self._snapshot_has_numeric_drivers(snapshot):
                session = fastf1.get_session(year, round_number, session_type)
                session.load(laps=True, telemetry=True, weather=False, messages=False)

                self._sessions[session_id] = session
                self._loaded_at[session_id] = datetime.utcnow()
                refreshed_snapshot = self._build_snapshot_from_session(session_id, session)
                self._snapshots[session_id] = refreshed_snapshot
                self._persist_snapshot(session_id, refreshed_snapshot)
                return self._build_load_response(session_id, session)

            self._snapshots[session_id] = snapshot
            return {
                "session_id": session_id,
                "event_name": snapshot.get("event_name", session_id),
                "loaded_drivers": len(snapshot.get("drivers", [])),
                "loaded_laps": len(snapshot.get("laps", [])),
                "data_updated_at": self.get_loaded_at(session_id),
            }

        session = fastf1.get_session(year, round_number, session_type)
        session.load(laps=True, telemetry=True, weather=False, messages=False)

        self._sessions[session_id] = session
        self._loaded_at[session_id] = datetime.utcnow()
        snapshot = self._build_snapshot_from_session(session_id, session)
        self._snapshots[session_id] = snapshot
        self._persist_snapshot(session_id, snapshot)

        return self._build_load_response(session_id, session)

    def get_loaded_session(self, session_id: str):
        if session_id not in self._sessions:
            self._load_fastf1_session_from_session_id(session_id)

        if session_id not in self._sessions:
            raise KeyError(f"Session not loaded: {session_id}")

        return self._sessions[session_id]

    def get_loaded_at(self, session_id: str) -> datetime:
        if session_id not in self._loaded_at:
            return datetime.utcnow()
        return self._loaded_at[session_id]

    def get_drivers(self, session_id: str) -> list[dict[str, Any]]:
        cached = self._cache_get(f"f1dash:{session_id}:drivers")
        if cached is not None:
            return cached

        snapshot = self._snapshots.get(session_id)
        if snapshot:
            drivers = snapshot.get("drivers", [])
            self._cache_set(f"f1dash:{session_id}:drivers", drivers)
            return drivers

        session = self.get_loaded_session(session_id)
        drivers: list[dict[str, Any]] = []

        for driver_code in session.drivers:
            info = session.get_driver(driver_code)
            drivers.append(
                {
                    "driver_code": self._driver_abbreviation(info, fallback=driver_code),
                    "driver_number": str(driver_code),
                    "full_name": info.get("FullName") if info is not None else None,
                    "team_name": info.get("TeamName") if info is not None else None,
                }
            )

        drivers.sort(key=lambda item: item["driver_code"])
        self._cache_set(f"f1dash:{session_id}:drivers", drivers)
        return drivers

    def get_laps(self, session_id: str, driver_code: str | None = None, limit: int = 100) -> pd.DataFrame:
        snapshot = self._snapshots.get(session_id)
        if snapshot:
            laps_df = pd.DataFrame(snapshot.get("laps", []))
            if laps_df.empty:
                return laps_df

            if driver_code:
                laps_df = laps_df[laps_df["driver_code"] == driver_code.upper()]

            laps_df = laps_df.sort_values(by=["driver_code", "lap_number"], ascending=[True, True])
            if limit > 0:
                laps_df = laps_df.tail(limit)
            return laps_df

        session = self.get_loaded_session(session_id)
        laps = session.laps.copy()

        if driver_code:
            laps = laps.pick_drivers(driver_code.upper())

        laps = laps.sort_values(by=["Driver", "LapNumber"], ascending=[True, True])

        if limit > 0:
            laps = laps.tail(limit)

        return laps

    def get_gap_summaries(self, session_id: str) -> list[dict[str, Any]]:
        cached = self._cache_get(f"f1dash:{session_id}:gaps")
        if cached is not None:
            return cached

        snapshot = self._snapshots.get(session_id)
        if snapshot:
            gaps = snapshot.get("gaps", [])
            self._cache_set(f"f1dash:{session_id}:gaps", gaps)
            return gaps

        laps = self.get_laps(session_id=session_id, driver_code=None, limit=5000)
        gaps_df = calculate_best_lap_gaps(laps)
        gaps: list[dict[str, Any]] = []
        for _, row in gaps_df.iterrows():
            gaps.append(
                {
                    "driver_code": str(row.get("Driver", "")),
                    "best_lap_seconds": self._to_float(row.get("best_lap_seconds")),
                    "gap_to_leader_seconds": self._to_float(row.get("gap_to_leader_seconds")),
                }
            )

        self._cache_set(f"f1dash:{session_id}:gaps", gaps)
        return gaps

    def get_tyre_stints(self, session_id: str) -> list[dict[str, Any]]:
        cached = self._cache_get(f"f1dash:{session_id}:tyres")
        if cached is not None:
            return cached

        snapshot = self._snapshots.get(session_id)
        if snapshot:
            tyres = snapshot.get("tyres", [])
            self._cache_set(f"f1dash:{session_id}:tyres", tyres)
            return tyres

        session = self.get_loaded_session(session_id)
        tyres = self._compute_tyre_stints(session.laps.copy())
        self._cache_set(f"f1dash:{session_id}:tyres", tyres)
        return tyres

    def get_pit_stops(self, session_id: str) -> list[dict[str, Any]]:
        cached = self._cache_get(f"f1dash:{session_id}:pitstops")
        if cached is not None:
            return cached

        snapshot = self._snapshots.get(session_id)
        if snapshot:
            pit_stops = snapshot.get("pit_stops", [])
            self._cache_set(f"f1dash:{session_id}:pitstops", pit_stops)
            return pit_stops

        session = self.get_loaded_session(session_id)
        pit_stops = self._compute_pit_stops(session.laps.copy())
        self._cache_set(f"f1dash:{session_id}:pitstops", pit_stops)
        return pit_stops

    def get_session_replay_data(
        self,
        session_id: str,
        driver_codes: list[str],
        fps: int = 5,
    ) -> dict[str, Any]:
        """
        Generates a synchronized bundle of telemetry 'frames' for smooth replay.
        FPS is lower than the desktop version (5-10) to keep JSON payload manageable for web.
        """
        cache_key = f"f1dash:{session_id}:replay:{','.join(sorted(driver_codes))}:{fps}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        session = self.get_loaded_session(session_id)
        
        # 1. Get Session Duration
        all_laps = session.laps.pick_drivers(driver_codes)
        if all_laps.empty:
            return {"fps": fps, "frames": [], "drivers": []}

        start_time = all_laps["Time"].min()
        end_time = all_laps["Time"].max()
        duration_seconds = (end_time - start_time).total_seconds()
        
        # 2. Generate Time Axis (Frames)
        num_frames = int(duration_seconds * fps)
        # Limit frames for web safety (max 2 hours at 5fps ~ 36k frames)
        num_frames = min(num_frames, 40000)
        
        time_steps = [start_time + pd.Timedelta(seconds=i/fps) for i in range(num_frames)]
        
        # 3. Interpolate Driver Data
        driver_data = {}
        for code in driver_codes:
            try:
                # Get raw telemetry
                tel = session.get_driver(code).get_telemetry()
                pos = session.get_driver(code).get_pos_data()
                # Merge
                merged = pd.merge_asof(tel, pos[["Time", "X", "Y"]], on="Time", direction="nearest")
                
                # Resample to our fixed FPS grid
                # We use reindex/interpolate for smooth movement
                merged.set_index("Time", inplace=True)
                # Remove duplicates in index
                merged = merged[~merged.index.duplicated(keep='first')]
                
                # Reindex to our target time steps
                resampled = merged.reindex(time_steps).interpolate(method="linear")
                
                driver_data[code] = {
                    "x": resampled["X"].tolist(),
                    "y": resampled["Y"].tolist(),
                    "speed": resampled["Speed"].tolist(),
                    "gear": resampled["nGear"].fillna(0).astype(int).tolist(),
                    "drs": (resampled["DRS"] >= 10).tolist()
                }
            except: continue

        payload = {
            "fps": fps,
            "duration": duration_seconds,
            "driver_data": driver_data,
            "drivers": list(driver_data.keys())
        }
        self._cache_set(cache_key, payload)
        return payload

    def get_sector_comparison(
        self,
        session_id: str,
        driver_a: str,
        driver_b: str,
    ) -> dict[str, Any]:
        cache_key = f"f1dash:{session_id}:sectors:{driver_a}:{driver_b}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        laps = self.get_laps(session_id=session_id, limit=5000)
        normalized = self._normalize_laps_from_any(laps)

        a_best = self._pick_best_lap(normalized, driver_a)
        b_best = self._pick_best_lap(normalized, driver_a)
        if not a_best or not b_best:
            raise KeyError("One or both drivers do not have valid lap data in this session")

        comparison = {
            "driver_a": driver_a.upper(),
            "driver_b": driver_b.upper(),
            "sector1_delta_seconds": self._delta(a_best.get("sector1_seconds"), b_best.get("sector1_seconds")),
            "sector2_delta_seconds": self._delta(a_best.get("sector2_seconds"), b_best.get("sector2_seconds")),
            "sector3_delta_seconds": self._delta(a_best.get("sector3_seconds"), b_best.get("sector3_seconds")),
            "lap_delta_seconds": self._delta(a_best.get("lap_time_seconds"), b_best.get("lap_time_seconds")),
        }

        self._cache_set(cache_key, comparison)
        return comparison

    def get_telemetry_comparison(
        self,
        session_id: str,
        driver_a: str,
        driver_b: str,
        sample_size: int,
        lap_number: int | None = None,
    ) -> dict[str, Any]:
        cache_key = f"f1dash:{session_id}:telemetry:{driver_a}:{driver_b}:{sample_size}:{lap_number}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        session = self.get_loaded_session(session_id)
        telemetry_a = self._extract_driver_telemetry(session, driver_a, sample_size, lap_number=lap_number)
        telemetry_b = self._extract_driver_telemetry(session, driver_b, sample_size, lap_number=lap_number)

        payload = {
            "driver_a": driver_a.upper(),
            "driver_b": driver_b.upper(),
            "points_a": telemetry_a,
            "points_b": telemetry_b,
        }
        self._cache_set(cache_key, payload)
        return payload

    def get_session_replay(self, session_id: str) -> dict[str, Any]:
        print(f"[REPLAY] Generating replay for {session_id}...", flush=True)
        session = self.get_loaded_session(session_id)
        
        # 1. Get track layout from fastest lap
        track_layout = None
        try:
            fastest_lap = session.laps.pick_fastest()
            ref_tel = fastest_lap.get_telemetry()
            track_layout = {'X': ref_tel['X'].tolist(), 'Y': ref_tel['Y'].tolist()}
            print(f"[REPLAY] Track layout extracted: {len(track_layout['X'])} points", flush=True)
        except Exception as e:
            print(f"[REPLAY] Failed to extract track layout: {e}", flush=True)

        # 2. Get all drivers telemetry
        drivers = session.drivers
        driver_data = {}
        global_t_min = float('inf')
        global_t_max = float('-inf')

        for driver_no in drivers:
            try:
                driver_info = session.get_driver(driver_no)
                code = self._driver_abbreviation(driver_info, fallback=driver_no)
                
                laps_driver = session.laps.pick_drivers(driver_no)
                if laps_driver.empty:
                    continue
                
                # Use a single call to get telemetry for the whole session for this driver
                tel = laps_driver.get_telemetry()
                if tel.empty or 'X' not in tel.columns:
                    continue
                
                # Cleanup NaNs
                tel = tel.dropna(subset=['X', 'Y', 'SessionTime'])
                if tel.empty: continue

                t = tel["SessionTime"].dt.total_seconds().to_numpy()
                driver_data[code] = {
                    "t": t,
                    "x": tel["X"].to_numpy(),
                    "y": tel["Y"].to_numpy(),
                    "speed": tel["Speed"].to_numpy(),
                    "gear": tel["nGear"].to_numpy().astype(int),
                    "drs": tel["DRS"].to_numpy().astype(int),
                    "throttle": tel["Throttle"].to_numpy(),
                    "brake": tel["Brake"].to_numpy()
                }
                
                global_t_min = min(global_t_min, t.min())
                global_t_max = max(global_t_max, t.max())
            except Exception as e:
                print(f"[REPLAY] Error for driver {driver_no}: {e}", flush=True)
                continue

        print(f"[REPLAY] Telemetry extracted for {len(driver_data)} drivers", flush=True)
        if not driver_data:
            raise KeyError(f"No telemetry data available for session: {session_id}")

        # 3. Build timeline and resample
        dt = 0.1 # 10 FPS for smooth video-like replay
        timeline = np.arange(global_t_min, global_t_max, dt)
        print(f"[REPLAY] Building {len(timeline)} frames...", flush=True)
        
        # Pre-group pit stops by driver
        pit_stops_all = self._compute_pit_stops(session.laps.copy())
        pit_stops_by_driver = {}
        for ps in pit_stops_all:
            d_code = ps["driver_code"]
            if d_code not in pit_stops_by_driver: pit_stops_by_driver[d_code] = []
            pit_stops_by_driver[d_code].append(ps)
        
        frames = []
        for i, t_val in enumerate(timeline):
            frame_drivers = {}
            for code, data in driver_data.items():
                # Use interpolation for smooth movement
                x_val = np.interp(t_val, data["t"], data["x"])
                y_val = np.interp(t_val, data["t"], data["y"])
                speed_val = np.interp(t_val, data["t"], data["speed"])
                throttle_val = np.interp(t_val, data["t"], data["throttle"])
                brake_val = np.interp(t_val, data["t"], data["brake"])
                
                # Nearest neighbor for discrete values
                idx = np.searchsorted(data["t"], t_val)
                if idx >= len(data["t"]): idx = len(data["t"]) - 1
                
                is_pitting = False
                for ps in pit_stops_by_driver.get(code, []):
                    in_s = ps.get("pit_in_seconds")
                    out_s = ps.get("pit_out_seconds")
                    if in_s is not None and out_s is not None:
                        if in_s <= t_val <= out_s:
                            is_pitting = True
                            break
                
                frame_drivers[code] = {
                    "code": code,
                    "x": float(x_val),
                    "y": float(y_val),
                    "dist": 0.0,
                    "lap": 0,
                    "position": 0,
                    "speed": float(speed_val),
                    "gear": int(data["gear"][idx]),
                    "drs": int(data["drs"][idx]),
                    "throttle": float(throttle_val),
                    "brake": float(data["brake"][idx]),
                    "is_pitting": is_pitting
                }
            
            frames.append({
                "t": round(float(t_val - global_t_min), 3),
                "lap": 0,
                "drivers": frame_drivers
            })

        payload = {
            "session_id": session_id,
            "total_laps": int(session.laps["LapNumber"].max()) if not session.laps.empty else 0,
            "frames": frames,
            "track_layout": track_layout,
            "driver_colors": {
                code: f"#{color}" if isinstance(color, str) else f"#{color:06x}"
                for code, color in self._get_driver_colors(session).items()
            }
        }
        
        return payload

    def _get_driver_colors(self, session) -> dict[str, str]:
        import fastf1.plotting
        try:
            colors = fastf1.plotting.get_driver_color_mapping(session)
            result = {}
            for d_no, color in colors.items():
                info = session.get_driver(d_no)
                code = self._driver_abbreviation(info, fallback=d_no)
                result[code] = color
            return result
        except:
            return {
                self._driver_abbreviation(session.get_driver(d), fallback=d): "#ffffff"
                for d in session.drivers
            }

    def get_multi_session_comparison(
        self,
        year: int,
        round_number: int,
        driver_code: str,
        session_types: list[str] | None = None,
    ) -> dict[str, Any]:
        selected_session_types = session_types or ["FP1", "FP2", "Q", "R"]
        normalized_driver = driver_code.upper()
        event_name: str | None = None
        points: list[dict[str, Any]] = []

        for session_type in selected_session_types:
            loaded = self.load_session(year, round_number, session_type)
            session_id = loaded["session_id"]
            if event_name is None:
                event_name = loaded.get("event_name")

            laps = self.get_laps(session_id, driver_code=normalized_driver, limit=5000)
            normalized_laps = self._normalize_laps_from_any(laps)
            best_lap, average_lap = self._compute_driver_lap_summary(normalized_laps, normalized_driver)

            gap_rows = self.get_gap_summaries(session_id)
            position = self._get_driver_position(gap_rows, normalized_driver)

            points.append(
                {
                    "session_type": session_type,
                    "session_id": session_id,
                    "best_lap_seconds": best_lap,
                    "average_lap_seconds": average_lap,
                    "lap_count": len(normalized_laps),
                    "position_by_best_lap": position,
                }
            )

        return {
            "year": year,
            "round": round_number,
            "driver_code": normalized_driver,
            "event_name": event_name,
            "points": points,
        }

    def _build_load_response(self, session_id: str, session) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "event_name": session.event["EventName"],
            "loaded_drivers": len(session.drivers),
            "loaded_laps": len(session.laps),
            "data_updated_at": self.get_loaded_at(session_id),
        }

    def _extract_driver_telemetry(
        self,
        session,
        driver_code: str,
        sample_size: int,
        lap_number: int | None = None,
    ) -> list[dict[str, Any]]:
        laps = session.laps.pick_drivers(driver_code.upper())
        if laps.empty:
            return []

        if lap_number is not None:
            target_lap = laps[laps["LapNumber"] == lap_number]
            if target_lap.empty:
                return []
            lap = target_lap.iloc[0]
        else:
            lap = laps.pick_quicklaps().pick_fastest() if not laps.pick_quicklaps().empty else laps.iloc[0]

        telemetry = lap.get_car_data().add_distance()
        pos = lap.get_pos_data()
        telemetry = pd.merge_asof(telemetry, pos[["Time", "X", "Y"]], on="Time", direction="nearest")
        
        telemetry = telemetry[["Time", "Distance", "Speed", "Throttle", "Brake", "RPM", "nGear", "X", "Y"]].dropna()

        if telemetry.empty:
            return []

        sampled = telemetry
        if sample_size > 0 and len(telemetry) > sample_size:
            step = max(1, len(telemetry) // sample_size)
            sampled = telemetry.iloc[::step].head(sample_size)

        points: list[dict[str, Any]] = []
        for _, row in sampled.iterrows():
            points.append(
                {
                    "distance": self._to_float(row.get("Distance")),
                    "time_seconds": self._to_lap_seconds(row.get("Time")),
                    "speed": self._to_float(row.get("Speed")),
                    "throttle": self._to_float(row.get("Throttle")),
                    "brake": self._to_float(row.get("Brake")),
                    "rpm": self._to_float(row.get("RPM")),
                    "n_gear": self._to_float(row.get("nGear")),
                    "x": self._to_float(row.get("X")),
                    "y": self._to_float(row.get("Y")),
                }
            )
        return points

    def _compute_tyre_stints(self, laps: pd.DataFrame) -> list[dict[str, Any]]:
        if laps.empty:
            return []

        grouped = (
            laps.dropna(subset=["Driver", "Stint", "LapNumber"])
            .groupby(["Driver", "Stint"], as_index=False)
            .agg(
                start_lap=("LapNumber", "min"),
                end_lap=("LapNumber", "max"),
                compound=("Compound", "first"),
                max_tyre_life=("TyreLife", "max"),
            )
            .sort_values(by=["Driver", "Stint"])
        )

        stints: list[dict[str, Any]] = []
        for _, row in grouped.iterrows():
            stints.append(
                {
                    "driver_code": str(row.get("Driver", "")),
                    "stint": int(row.get("Stint", 0)),
                    "start_lap": int(row.get("start_lap", 0)),
                    "end_lap": int(row.get("end_lap", 0)),
                    "compound": row.get("compound"),
                    "max_tyre_life": self._to_float(row.get("max_tyre_life")),
                }
            )
        return stints

    def _compute_pit_stops(self, laps: pd.DataFrame) -> list[dict[str, Any]]:
        if laps.empty:
            return []

        pit_laps = laps[(laps["PitInTime"].notna()) | (laps["PitOutTime"].notna())]
        if pit_laps.empty:
            return []

        events: list[dict[str, Any]] = []
        for _, row in pit_laps.iterrows():
            events.append(
                {
                    "driver_code": str(row.get("Driver", "")),
                    "lap_number": int(row.get("LapNumber", 0)),
                    "pit_in_time": str(row.get("PitInTime")) if row.get("PitInTime") is not None else None,
                    "pit_out_time": str(row.get("PitOutTime")) if row.get("PitOutTime") is not None else None,
                    "pit_in_seconds": self._to_lap_seconds(row.get("PitInTime")),
                    "pit_out_seconds": self._to_lap_seconds(row.get("PitOutTime")),
                    "stint": int(row.get("Stint", 0)) if row.get("Stint") is not None else None,
                    "compound": row.get("Compound"),
                }
            )
        return events

    def _build_snapshot_from_session(self, session_id: str, session) -> dict[str, Any]:
        laps_df = session.laps.copy().sort_values(by=["Driver", "LapNumber"], ascending=[True, True])
        alias_map = self._build_driver_alias_map(session)

        laps = self._normalize_laps_from_any(laps_df)
        for lap in laps:
            lap["driver_code"] = self._normalize_driver_code(lap.get("driver_code"), alias_map)

        gaps_df = calculate_best_lap_gaps(laps_df)
        gaps = [
            {
                "driver_code": self._normalize_driver_code(str(row.get("Driver", "")), alias_map),
                "best_lap_seconds": self._to_float(row.get("best_lap_seconds")),
                "gap_to_leader_seconds": self._to_float(row.get("gap_to_leader_seconds")),
            }
            for _, row in gaps_df.iterrows()
        ]

        drivers = self.get_drivers_from_session(session)
        tyres = self._compute_tyre_stints(laps_df)
        pit_stops = self._compute_pit_stops(laps_df)

        return {
            "session_id": session_id,
            "event_name": str(session.event["EventName"]),
            "generated_at": datetime.utcnow().isoformat(),
            "drivers": drivers,
            "laps": laps,
            "gaps": gaps,
            "tyres": tyres,
            "pit_stops": pit_stops,
        }

    def get_drivers_from_session(self, session) -> list[dict[str, Any]]:
        drivers: list[dict[str, Any]] = []
        for driver_code in session.drivers:
            info = session.get_driver(driver_code)
            drivers.append(
                {
                    "driver_code": self._driver_abbreviation(info, fallback=driver_code),
                    "driver_number": str(driver_code),
                    "full_name": info.get("FullName") if info is not None else None,
                    "team_name": info.get("TeamName") if info is not None else None,
                }
            )
        drivers.sort(key=lambda item: item["driver_code"])
        return drivers

    def _normalize_laps_from_any(self, laps: pd.DataFrame) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if laps.empty:
            return normalized

        uses_fastf1_columns = "Driver" in laps.columns
        for _, row in laps.iterrows():
            lap_number = int(row.get("LapNumber", row.get("lap_number", 0)))
            driver = str(row.get("Driver", row.get("driver_code", "")))

            normalized.append(
                {
                    "lap_number": lap_number,
                    "driver_code": driver,
                    "lap_time_seconds": self._to_lap_seconds(row.get("LapTime", row.get("lap_time_seconds"))),
                    "sector1_seconds": self._to_lap_seconds(row.get("Sector1Time", row.get("sector1_seconds"))),
                    "sector2_seconds": self._to_lap_seconds(row.get("Sector2Time", row.get("sector2_seconds"))),
                    "sector3_seconds": self._to_lap_seconds(row.get("Sector3Time", row.get("sector3_seconds"))),
                    "compound": row.get("Compound", row.get("compound")) if uses_fastf1_columns else row.get("compound"),
                    "tyre_life": self._to_float(row.get("TyreLife", row.get("tyre_life"))),
                }
            )
        return normalized

    @staticmethod
    def _compute_driver_lap_summary(
        normalized_laps: list[dict[str, Any]],
        driver_code: str,
    ) -> tuple[float | None, float | None]:
        lap_values = [
            lap.get("lap_time_seconds")
            for lap in normalized_laps
            if lap.get("driver_code") == driver_code and lap.get("lap_time_seconds") is not None
        ]
        if not lap_values:
            return None, None

        best = round(min(lap_values), 3)
        average = round(sum(lap_values) / len(lap_values), 3)
        return best, average

    @staticmethod
    def _get_driver_position(gap_rows: list[dict[str, Any]], driver_code: str) -> int | None:
        ordered = sorted(
            [row for row in gap_rows if row.get("best_lap_seconds") is not None],
            key=lambda row: row["best_lap_seconds"],
        )
        for index, row in enumerate(ordered, start=1):
            if row.get("driver_code") == driver_code:
                return index
        return None

    @staticmethod
    def _pick_best_lap(laps: list[dict[str, Any]], driver_code: str) -> dict[str, Any] | None:
        filtered = [
            lap
            for lap in laps
            if lap.get("driver_code") == driver_code.upper() and lap.get("lap_time_seconds") is not None
        ]
        if not filtered:
            return None
        filtered.sort(key=lambda lap: lap["lap_time_seconds"])
        return filtered[0]

    @staticmethod
    def _delta(value_a: float | None, value_b: float | None) -> float | None:
        if value_a is None or value_b is None:
            return None
        return round(value_a - value_b, 3)

    @staticmethod
    def _to_lap_seconds(value: Any) -> float | None:
        if value is None:
            return None
        if hasattr(value, "total_seconds"):
            return round(float(value.total_seconds()), 3)
        return SessionService._to_float(value)

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return round(float(value), 3)
        except (TypeError, ValueError):
            return None

    def _cache_get(self, key: str) -> Any | None:
        if not self._cache:
            return None
        return self._cache.get_json(key)

    def _cache_set(self, key: str, value: Any) -> None:
        if not self._cache:
            return
        self._cache.set_json(key, value, self._cache_ttl_seconds)

    def _snapshot_file(self, session_id: str) -> Path:
        return self._snapshot_dir / f"{session_id}.json"

    def _load_snapshot(self, session_id: str) -> dict[str, Any] | None:
        if session_id in self._snapshots:
            return self._snapshots[session_id]

        path = self._snapshot_file(session_id)
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _persist_snapshot(self, session_id: str, payload: dict[str, Any]) -> None:
        path = self._snapshot_file(session_id)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file)

    def _load_fastf1_session_from_session_id(self, session_id: str) -> None:
        parts = session_id.split("-")
        if len(parts) != 3:
            return

        year, round_number, session_type = parts
        session = fastf1.get_session(int(year), int(round_number), session_type)
        session.load(laps=True, telemetry=True, weather=False, messages=False)

        self._sessions[session_id] = session
        self._loaded_at[session_id] = datetime.utcnow()
        if session_id not in self._snapshots:
            snapshot = self._build_snapshot_from_session(session_id, session)
            self._snapshots[session_id] = snapshot
            self._persist_snapshot(session_id, snapshot)

    @staticmethod
    def _driver_abbreviation(info: Any, fallback: Any) -> str:
        if info is not None:
            abbreviation = info.get("Abbreviation")
            if abbreviation:
                return str(abbreviation).upper()
        return str(fallback).upper()

    def _build_driver_alias_map(self, session) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for driver_number in session.drivers:
            info = session.get_driver(driver_number)
            code = self._driver_abbreviation(info, fallback=driver_number)
            aliases[str(driver_number).upper()] = code
            aliases[code] = code
        return aliases

    @staticmethod
    def _normalize_driver_code(raw_code: Any, aliases: dict[str, str]) -> str:
        if raw_code is None:
            return ""
        key = str(raw_code).upper()
        return aliases.get(key, key)

    @staticmethod
    def _snapshot_has_numeric_drivers(snapshot: dict[str, Any]) -> bool:
        drivers = snapshot.get("drivers", [])
        if not drivers:
            return False

        for driver in drivers:
            code = str(driver.get("driver_code", ""))
            if code.isdigit() or len(code) < 3:
                return True
        return False
