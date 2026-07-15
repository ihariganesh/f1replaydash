import { DriverSummary, LapSummary } from "../types";
import { TeamDriverComparison } from "../components/TeamDriverComparison";
import { TelemetryOverlay } from "../components/TelemetryOverlay";
import { StrategyPanel } from "../components/StrategyPanel";

interface PracticeViewProps {
  sessionId: string;
  drivers: DriverSummary[];
  laps: LapSummary[];
}

export function PracticeView({ sessionId, drivers, laps }: PracticeViewProps) {
  return (
    <>
      <section className="panel">
        <h2>Practice View</h2>
        <p>Focus: long-run consistency and tyre behavior.</p>
        <p>Loaded drivers: {drivers.length}</p>
        <p>Visible laps: {laps.length}</p>
      </section>
      <TeamDriverComparison sessionId={sessionId} drivers={drivers} />
      <TelemetryOverlay sessionId={sessionId} drivers={drivers} laps={laps} />
      <StrategyPanel sessionId={sessionId} />
    </>
  );
}
