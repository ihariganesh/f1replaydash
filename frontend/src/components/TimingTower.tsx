import { DriverSummary, GapSummary } from "../types";

interface TimingTowerProps {
  drivers: DriverSummary[];
  gaps: GapSummary[];
}

interface TowerRow {
  position: number;
  driverCode: string;
  driverNumber?: string;
  teamName?: string;
  bestLap?: number;
  gap?: number;
}

export function TimingTower({ drivers, gaps }: TimingTowerProps) {
  const byCode = new Map(drivers.map((driver) => [driver.driver_code, driver]));

  const rows: TowerRow[] = gaps
    .slice()
    .sort((a, b) => (a.best_lap_seconds ?? 9_999) - (b.best_lap_seconds ?? 9_999))
    .map((gap, index) => {
      const meta = byCode.get(gap.driver_code);
      return {
        position: index + 1,
        driverCode: gap.driver_code,
        driverNumber: meta?.driver_number,
        teamName: meta?.team_name,
        bestLap: gap.best_lap_seconds,
        gap: gap.gap_to_leader_seconds,
      };
    });

  return (
    <section className="panel timing-tower-panel">
      <h3>Timing Tower</h3>
      <table className="timing-table">
        <thead>
          <tr>
            <th>P</th>
            <th>DRV</th>
            <th>GAP</th>
            <th>BEST</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.driverCode}>
              <td>{row.position}</td>
              <td>
                {row.driverCode}
                <span className="tower-driver-number">#{row.driverNumber ?? "--"}</span>
              </td>
              <td>{row.gap?.toFixed(3) ?? "LEADER"}</td>
              <td>{row.bestLap?.toFixed(3) ?? "-"}</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={4}>Load race gaps to populate tower.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
