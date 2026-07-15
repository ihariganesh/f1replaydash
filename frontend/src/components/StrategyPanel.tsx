import { useEffect, useState } from "react";

import { getPitStops, getTyres } from "../api/client";
import { PitStopSummary, TyreStintSummary } from "../types";

interface StrategyPanelProps {
  sessionId: string;
}

export function StrategyPanel({ sessionId }: StrategyPanelProps) {
  const [tyres, setTyres] = useState<TyreStintSummary[]>([]);
  const [pitStops, setPitStops] = useState<PitStopSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStrategy() {
      if (!sessionId) {
        setTyres([]);
        setPitStops([]);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const [tyresData, pitData] = await Promise.all([getTyres(sessionId), getPitStops(sessionId)]);
        setTyres(tyresData);
        setPitStops(pitData);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }

    fetchStrategy();
  }, [sessionId]);

  return (
    <section className="panel">
      <h3>Tyre + Pit Strategy</h3>
      {loading ? <p>Loading strategy traces...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <h4>Tyre Stints</h4>
      <table>
        <thead>
          <tr>
            <th>Driver</th>
            <th>Stint</th>
            <th>Laps</th>
            <th>Compound</th>
            <th>Tyre Life Max</th>
          </tr>
        </thead>
        <tbody>
          {tyres.slice(0, 14).map((stint) => (
            <tr key={`${stint.driver_code}-${stint.stint}`}>
              <td>{stint.driver_code}</td>
              <td>{stint.stint}</td>
              <td>
                {stint.start_lap}-{stint.end_lap}
              </td>
              <td>{stint.compound ?? "-"}</td>
              <td>{stint.max_tyre_life ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>Pit Stop Events</h4>
      <table>
        <thead>
          <tr>
            <th>Driver</th>
            <th>Lap</th>
            <th>Pit In</th>
            <th>Pit Out</th>
            <th>Compound</th>
          </tr>
        </thead>
        <tbody>
          {pitStops.slice(0, 14).map((event, index) => (
            <tr key={`${event.driver_code}-${event.lap_number}-${index}`}>
              <td>{event.driver_code}</td>
              <td>{event.lap_number}</td>
              <td>{event.pit_in_time ?? "-"}</td>
              <td>{event.pit_out_time ?? "-"}</td>
              <td>{event.compound ?? "-"}</td>
            </tr>
          ))}
          {pitStops.length === 0 ? (
            <tr>
              <td colSpan={5}>No pit events in this dataset or session not loaded.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
