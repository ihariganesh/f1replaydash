import { useMemo, useState } from "react";

interface ExportPanelProps {
  sessionId: string;
}

export function ExportPanel({ sessionId }: ExportPanelProps) {
  const [dataset, setDataset] = useState("laps");
  const [format, setFormat] = useState("csv");
  const [driverCode, setDriverCode] = useState("VER");

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

  function buildSessionExportUrl(): string {
    if (!sessionId) {
      return "#";
    }

    const base = `/api/sessions/${sessionId}/export?dataset=${dataset}&format=${format}`;
    return dataset === "laps" && driverCode ? `${base}&driver_code=${driverCode}` : base;
  }

  function buildTrendExportUrl(): string {
    if (!parsed.year || !parsed.round) {
      return "#";
    }
    return `/api/events/${parsed.year}/${parsed.round}/compare/export?driver_code=${driverCode}&format=${format}`;
  }

  return (
    <section className="panel">
      <h2>Data Engineer Export Workflow</h2>
      <p>Download normalized datasets and trend outputs as CSV/Parquet for portfolio notebooks and pipelines.</p>
      <div className="row">
        <label>
          Dataset
          <select value={dataset} onChange={(event) => setDataset(event.target.value)}>
            <option value="laps">laps</option>
            <option value="gaps">gaps</option>
            <option value="tyres">tyres</option>
            <option value="pit_stops">pit_stops</option>
          </select>
        </label>
        <label>
          Format
          <select value={format} onChange={(event) => setFormat(event.target.value)}>
            <option value="csv">csv</option>
            <option value="parquet">parquet</option>
          </select>
        </label>
        <label>
          Driver
          <input value={driverCode} maxLength={3} onChange={(event) => setDriverCode(event.target.value.toUpperCase())} />
        </label>
      </div>

      <div className="row">
        <a className="link-button" href={buildSessionExportUrl()} target="_blank" rel="noreferrer">
          Export session dataset
        </a>
        <a className="link-button" href={buildTrendExportUrl()} target="_blank" rel="noreferrer">
          Export multi-session trend
        </a>
      </div>
    </section>
  );
}
