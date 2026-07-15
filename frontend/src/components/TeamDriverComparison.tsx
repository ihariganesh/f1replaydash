import { useEffect, useMemo, useState } from "react";

import { getSectorComparison } from "../api/client";
import { DriverSummary, SectorComparisonSummary } from "../types";

interface TeamDriverComparisonProps {
  sessionId: string;
  drivers: DriverSummary[];
}

export function TeamDriverComparison({ sessionId, drivers }: TeamDriverComparisonProps) {
  const defaultPair = useMemo(() => {
    if (drivers.length < 2) {
      return { a: "", b: "" };
    }
    return { a: drivers[0].driver_code, b: drivers[1].driver_code };
  }, [drivers]);

  const [driverA, setDriverA] = useState<string>(defaultPair.a);
  const [driverB, setDriverB] = useState<string>(defaultPair.b);
  const [comparison, setComparison] = useState<SectorComparisonSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setDriverA(defaultPair.a);
    setDriverB(defaultPair.b);
    setComparison(null);
  }, [defaultPair.a, defaultPair.b]);

  async function handleCompare() {
    if (!sessionId || !driverA || !driverB || driverA === driverB) {
      setError("Pick two different drivers.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getSectorComparison(sessionId, driverA, driverB);
      setComparison(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h3>Team/Driver Sector Delta</h3>
      <div className="row">
        <label>
          Driver A
          <select value={driverA} onChange={(event) => setDriverA(event.target.value)}>
            {drivers.map((driver) => (
              <option key={driver.driver_code} value={driver.driver_code}>
                {driver.driver_code} #{driver.driver_number ?? "--"} {driver.full_name ?? ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          Driver B
          <select value={driverB} onChange={(event) => setDriverB(event.target.value)}>
            {drivers.map((driver) => (
              <option key={driver.driver_code} value={driver.driver_code}>
                {driver.driver_code} #{driver.driver_number ?? "--"} {driver.full_name ?? ""}
              </option>
            ))}
          </select>
        </label>
        <button onClick={handleCompare} disabled={loading || drivers.length < 2}>
          {loading ? "Comparing..." : "Compare Sectors"}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {comparison ? (
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>{comparison.driver_a}</th>
              <th>{comparison.driver_b}</th>
              <th>Delta (A-B)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Sector 1</td>
              <td>-</td>
              <td>-</td>
              <td>{comparison.sector1_delta_seconds?.toFixed(3) ?? "-"}</td>
            </tr>
            <tr>
              <td>Sector 2</td>
              <td>-</td>
              <td>-</td>
              <td>{comparison.sector2_delta_seconds?.toFixed(3) ?? "-"}</td>
            </tr>
            <tr>
              <td>Sector 3</td>
              <td>-</td>
              <td>-</td>
              <td>{comparison.sector3_delta_seconds?.toFixed(3) ?? "-"}</td>
            </tr>
            <tr>
              <td>Total Lap</td>
              <td>-</td>
              <td>-</td>
              <td>{comparison.lap_delta_seconds?.toFixed(3) ?? "-"}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p>Load two drivers to generate a sector delta table.</p>
      )}
    </section>
  );
}
