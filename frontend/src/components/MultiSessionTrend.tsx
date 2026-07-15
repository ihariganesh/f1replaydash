import { useMemo, useState } from "react";

import { getMultiSessionComparison } from "../api/client";
import { MultiSessionComparisonSummary } from "../types";

interface MultiSessionTrendProps {
  sessionId: string;
}

const CHART_WIDTH = 860;
const CHART_HEIGHT = 220;

function buildLinePath(values: Array<number | undefined>, maxValue: number, minValue: number): string {
  const valid = values.map((value) => value ?? NaN);
  const range = Math.max(0.001, maxValue - minValue);
  const stepX = CHART_WIDTH / Math.max(1, values.length - 1);

  return valid
    .map((value, index) => {
      if (Number.isNaN(value)) {
        return "";
      }
      const x = index * stepX;
      const y = CHART_HEIGHT - ((value - minValue) / range) * CHART_HEIGHT;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .filter(Boolean)
    .join(" ");
}

export function MultiSessionTrend({ sessionId }: MultiSessionTrendProps) {
  const [driverCode, setDriverCode] = useState("VER");
  const [comparison, setComparison] = useState<MultiSessionComparisonSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsed = useMemo(() => {
    const parts = sessionId.split("-");
    if (parts.length !== 3) {
      return { year: undefined, round: undefined };
    }
    const year = Number(parts[0]);
    const round = Number(parts[1]);
    if (Number.isNaN(year) || Number.isNaN(round)) {
      return { year: undefined, round: undefined };
    }
    return { year, round };
  }, [sessionId]);

  async function handleLoad() {
    if (!parsed.year || !parsed.round) {
      setError("Load a valid session first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getMultiSessionComparison(parsed.year, parsed.round, driverCode);
      setComparison(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const bestValues = comparison?.points.map((point) => point.best_lap_seconds) ?? [];
  const avgValues = comparison?.points.map((point) => point.average_lap_seconds) ?? [];
  const allValues = [...bestValues, ...avgValues].filter((value): value is number => value !== undefined);
  const maxValue = allValues.length > 0 ? Math.max(...allValues) : 1;
  const minValue = allValues.length > 0 ? Math.min(...allValues) : 0;

  const bestPath = buildLinePath(bestValues, maxValue, minValue);
  const avgPath = buildLinePath(avgValues, maxValue, minValue);

  return (
    <section className="panel">
      <h2>Multi-Session Trend (FP1 vs FP2 vs Q vs R)</h2>
      <div className="row">
        <label>
          Driver Code
          <input
            value={driverCode}
            maxLength={3}
            onChange={(event) => setDriverCode(event.target.value.toUpperCase())}
          />
        </label>
        <button onClick={handleLoad} disabled={loading || !sessionId}>
          {loading ? "Loading trend..." : "Load trend"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} className="telemetry-chart" role="img" aria-label="Multi-session trend chart">
        <rect x={0} y={0} width={CHART_WIDTH} height={CHART_HEIGHT} fill="#0f2231" />
        <path d={bestPath} stroke="#ff7a18" strokeWidth={2.2} fill="none" />
        <path d={avgPath} stroke="#7eff9f" strokeWidth={2.2} fill="none" />
      </svg>

      {comparison ? (
        <table>
          <thead>
            <tr>
              <th>Session</th>
              <th>Best Lap</th>
              <th>Average Lap</th>
              <th>Laps</th>
              <th>Rank by Best</th>
            </tr>
          </thead>
          <tbody>
            {comparison.points.map((point) => (
              <tr key={point.session_id}>
                <td>{point.session_type}</td>
                <td>{point.best_lap_seconds?.toFixed(3) ?? "-"}</td>
                <td>{point.average_lap_seconds?.toFixed(3) ?? "-"}</td>
                <td>{point.lap_count}</td>
                <td>{point.position_by_best_lap ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Trend table appears after loading a driver.</p>
      )}
      <p className="muted">Orange: best lap trend | Green: average lap trend</p>
    </section>
  );
}
