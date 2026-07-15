import { GapSummary, LapSummary } from "../types";
import { DriverSummary } from "../types";
import { TeamDriverComparison } from "../components/TeamDriverComparison";
import { TelemetryOverlay } from "../components/TelemetryOverlay";

interface QualifyingViewProps {
  sessionId: string;
  drivers: DriverSummary[];
  laps: LapSummary[];
  gaps: GapSummary[];
}

export function QualifyingView({ sessionId, drivers, laps, gaps }: QualifyingViewProps) {
  const topGap = gaps.slice(0, 5);
  return (
    <>
      <section className="panel">
        <h2>Qualifying View</h2>
        <p>Focus: one-lap pace and sector deltas.</p>
        <p>Lap samples: {laps.length}</p>
        <ul>
          {topGap.map((item) => (
            <li key={item.driver_code}>
              {item.driver_code}: +{item.gap_to_leader_seconds?.toFixed(3) ?? "-"}s
            </li>
          ))}
        </ul>
      </section>
      <TeamDriverComparison sessionId={sessionId} drivers={drivers} />
      <TelemetryOverlay sessionId={sessionId} drivers={drivers} />
    </>
  );
}
