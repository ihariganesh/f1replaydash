import {
  DriverSummary,
  EventSummary,
  GapSummary,
  LapSummary,
  PitStopSummary,
  PrecomputeJobResponse,
  SectorComparisonSummary,
  SessionLoadResponse,
  SessionType,
  SessionReplaySummary,
  MultiSessionComparisonSummary,
  TelemetryComparisonSummary,
  TyreStintSummary,
} from "../types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getSessions(year: number): Promise<EventSummary[]> {
  return request<EventSummary[]>(`/api/sessions?year=${year}`);
}

export function loadSession(
  year: number,
  round: number,
  sessionType: SessionType
): Promise<SessionLoadResponse> {
  return request<SessionLoadResponse>("/api/sessions/load", {
    method: "POST",
    body: JSON.stringify({ year, round, session_type: sessionType }),
  });
}

export function getDrivers(sessionId: string): Promise<DriverSummary[]> {
  return request<DriverSummary[]>(`/api/sessions/${sessionId}/drivers`);
}

export function getLaps(sessionId: string, limit = 100): Promise<LapSummary[]> {
  return request<LapSummary[]>(`/api/sessions/${sessionId}/laps?limit=${limit}`);
}

export function getGaps(sessionId: string): Promise<GapSummary[]> {
  return request<GapSummary[]>(`/api/sessions/${sessionId}/gaps`);
}

export function getTyres(sessionId: string): Promise<TyreStintSummary[]> {
  return request<TyreStintSummary[]>(`/api/sessions/${sessionId}/tyres`);
}

export function getPitStops(sessionId: string): Promise<PitStopSummary[]> {
  return request<PitStopSummary[]>(`/api/sessions/${sessionId}/pit-stops`);
}

export function getSectorComparison(
  sessionId: string,
  driverA: string,
  driverB: string
): Promise<SectorComparisonSummary> {
  return request<SectorComparisonSummary>(
    `/api/sessions/${sessionId}/compare/sectors?driver_a=${driverA}&driver_b=${driverB}`
  );
}

export function getReplayData(
  sessionId: string,
  drivers: string[],
  fps = 5
): Promise<any> {
  return request<any>(
    `/api/sessions/${sessionId}/replay?drivers=${drivers.join(",")}&fps=${fps}`
  );
}

export function getTelemetryComparison(
  sessionId: string,
  driverA: string,
  driverB: string,
  sampleSize = 220,
  lapNumber?: number
): Promise<TelemetryComparisonSummary> {
  let url = `/api/sessions/${sessionId}/compare/telemetry?driver_a=${driverA}&driver_b=${driverB}&sample_size=${sampleSize}`;
  if (lapNumber) {
    url += `&lap_number=${lapNumber}`;
  }
  return request<TelemetryComparisonSummary>(url);
}

export function getMultiSessionComparison(
  year: number,
  round: number,
  driverCode: string
): Promise<MultiSessionComparisonSummary> {
  return request<MultiSessionComparisonSummary>(
    `/api/events/${year}/${round}/compare?driver_code=${driverCode}`
  );
}

export function startPrecomputeJob(
  year: number,
  round: number
): Promise<PrecomputeJobResponse> {
  return request<PrecomputeJobResponse>(`/api/events/${year}/${round}/precompute`, {
    method: "POST",
  });
}

export function getPrecomputeJob(jobId: string): Promise<PrecomputeJobResponse> {
  return request<PrecomputeJobResponse>(`/api/precompute/${jobId}`);
}

export function getSessionReplay(sessionId: string): Promise<SessionReplaySummary> {
  return request<SessionReplaySummary>(`/api/sessions/${sessionId}/race-replay`);
}
