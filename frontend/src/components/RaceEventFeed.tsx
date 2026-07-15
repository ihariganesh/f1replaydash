import { useEffect, useMemo, useState } from "react";

import { getLaps, getPitStops } from "../api/client";
import { LapSummary, PitStopSummary } from "../types";

interface RaceEventFeedProps {
  sessionId: string;
}

interface FeedEvent {
  id: string;
  lap: number;
  label: string;
  detail: string;
}

export function RaceEventFeed({ sessionId }: RaceEventFeedProps) {
  const [pitStops, setPitStops] = useState<PitStopSummary[]>([]);
  const [laps, setLaps] = useState<LapSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadFeed() {
      if (!sessionId) {
        setPitStops([]);
        setLaps([]);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const [pitData, lapData] = await Promise.all([getPitStops(sessionId), getLaps(sessionId, 240)]);
        setPitStops(pitData);
        setLaps(lapData);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }

    loadFeed();
  }, [sessionId]);

  const events = useMemo(() => {
    const pitEvents: FeedEvent[] = pitStops.slice(0, 12).map((event, index) => ({
      id: `pit-${event.driver_code}-${event.lap_number}-${index}`,
      lap: event.lap_number,
      label: "PIT",
      detail: `${event.driver_code} pit window (compound ${event.compound ?? "?"})`,
    }));

    const paceEvents: FeedEvent[] = laps
      .filter((lap) => lap.lap_time_seconds !== undefined)
      .sort((a, b) => b.lap_number - a.lap_number)
      .slice(0, 12)
      .map((lap, index) => ({
        id: `lap-${lap.driver_code}-${lap.lap_number}-${index}`,
        lap: lap.lap_number,
        label: "LAP",
        detail: `${lap.driver_code} ${lap.lap_time_seconds?.toFixed(3)}s (S1 ${lap.sector1_seconds?.toFixed(3) ?? "-"})`,
      }));

    return [...pitEvents, ...paceEvents].sort((a, b) => b.lap - a.lap).slice(0, 20);
  }, [pitStops, laps]);

  return (
    <section className="panel event-feed-panel">
      <h3>Race Events / Radio Log</h3>
      {loading ? <p>Polling event stream...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <div className="event-feed-list">
        {events.map((event) => (
          <article key={event.id} className="event-row">
            <span className="event-lap">L{event.lap}</span>
            <span className="event-label">{event.label}</span>
            <span className="event-detail">{event.detail}</span>
          </article>
        ))}
        {events.length === 0 ? <p className="muted">No event feed available yet.</p> : null}
      </div>
    </section>
  );
}
