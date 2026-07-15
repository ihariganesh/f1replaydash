import { DriverSummary, GapSummary, LapSummary } from "../types";
import { RaceEventFeed } from "../components/RaceEventFeed";
import { TeamDriverComparison } from "../components/TeamDriverComparison";
import { StrategyPanel } from "../components/StrategyPanel";
import { TelemetryOverlay } from "../components/TelemetryOverlay";
import { TimingTower } from "../components/TimingTower";

interface RaceViewProps {
  sessionId: string;
  drivers: DriverSummary[];
  gaps: GapSummary[];
  laps: LapSummary[];
}

export function RaceView({ sessionId, drivers, gaps, laps }: RaceViewProps) {
  const leader = gaps.slice().sort((a, b) => (a.best_lap_seconds ?? 9999) - (b.best_lap_seconds ?? 9999))[0];

  return (
    <>
      <section className="panel race-ops-strip">
        <h2>Race Operations Console</h2>
        <p>
          Session {sessionId || "-"} | Leader {leader?.driver_code ?? "-"} | Best {leader?.best_lap_seconds?.toFixed(3) ?? "-"}s | Drivers {drivers.length} | Laps {laps.length}
        </p>
      </section>

      <section className="race-control-grid">
        <div className="race-left-column">
          <TimingTower drivers={drivers} gaps={gaps} />
        </div>

        <div className="race-center-column">
          <TelemetryOverlay sessionId={sessionId} drivers={drivers} laps={laps} />
          <TeamDriverComparison sessionId={sessionId} drivers={drivers} />
        </div>

        <div className="race-right-column">
          <StrategyPanel sessionId={sessionId} />
          <RaceEventFeed sessionId={sessionId} />
        </div>
      </section>
    </>
  );
}
