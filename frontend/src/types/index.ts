export type SessionType = "FP1" | "FP2" | "FP3" | "Q" | "R";

export interface EventSummary {
  year: number;
  round?: number;
  round_number?: number;
  event_name: string;
  country?: string;
  location?: string;
  event_date?: string;
}

export interface SessionLoadResponse {
  session_id: string;
  event_name: string;
  loaded_drivers: number;
  loaded_laps: number;
  data_updated_at: string;
}

export interface DriverSummary {
  driver_code: string;
  driver_number?: string;
  full_name?: string;
  team_name?: string;
}

export interface LapSummary {
  lap_number: number;
  driver_code: string;
  lap_time_seconds?: number;
  sector1_seconds?: number;
  sector2_seconds?: number;
  sector3_seconds?: number;
  compound?: string;
  tyre_life?: number;
}

export interface GapSummary {
  driver_code: string;
  best_lap_seconds?: number;
  gap_to_leader_seconds?: number;
}

export interface TyreStintSummary {
  driver_code: string;
  stint: number;
  start_lap: number;
  end_lap: number;
  compound?: string;
  max_tyre_life?: number;
}

export interface PitStopSummary {
  driver_code: string;
  lap_number: number;
  pit_in_time?: string;
  pit_out_time?: string;
  pit_in_seconds?: number;
  pit_out_seconds?: number;
  stint?: number;
  compound?: string;
}

export interface SectorComparisonSummary {
  driver_a: string;
  driver_b: string;
  sector1_delta_seconds?: number;
  sector2_delta_seconds?: number;
  sector3_delta_seconds?: number;
  lap_delta_seconds?: number;
}

export interface TelemetryPointSummary {
  distance?: number;
  time_seconds?: number;
  speed?: number;
  throttle?: number;
  brake?: number;
  rpm?: number;
  n_gear?: number;
  x?: number;
  y?: number;
}

export interface TelemetryComparisonSummary {
  driver_a: string;
  driver_b: string;
  points_a: TelemetryPointSummary[];
  points_b: TelemetryPointSummary[];
}

export interface MultiSessionPoint {
  session_type: string;
  session_id: string;
  best_lap_seconds?: number;
  average_lap_seconds?: number;
  lap_count: number;
  position_by_best_lap?: number;
}

export interface MultiSessionComparisonSummary {
  year: number;
  round: number;
  driver_code: string;
  event_name?: string;
  points: MultiSessionPoint[];
}

export interface PrecomputeJobResponse {
  job_id: string;
  status: string;
  message?: string;
}

export interface ReplayDriverSnapshot {
  code: string;
  x: number;
  y: number;
  dist: number;
  lap: number;
  position: number;
  speed: number;
  gear: number;
  drs: number;
  throttle: number;
  brake: number;
  is_pitting?: boolean;
}

export interface ReplayFrame {
  t: number;
  lap: number;
  drivers: Record<string, ReplayDriverSnapshot>;
}

export interface SessionReplaySummary {
  session_id: string;
  total_laps: number;
  frames: ReplayFrame[];
  track_layout?: {
    X: number[];
    Y: number[];
  };
}
