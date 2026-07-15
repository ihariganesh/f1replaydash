import { useEffect, useMemo, useState, useRef } from "react";

import { getTelemetryComparison } from "../api/client";
import { DriverSummary, LapSummary, TelemetryComparisonSummary, TelemetryPointSummary } from "../types";

export function TelemetryOverlay({
  sessionId,
  drivers,
  laps = [],
}: {
  sessionId: string;
  drivers: DriverSummary[];
  laps?: LapSummary[];
}) {
  const WIDTH = 800;
  const HEIGHT = 250;

  const defaultPair = useMemo(() => {
    if (drivers.length < 2) return { a: "", b: "" };
    return { a: drivers[0].driver_code, b: drivers[1].driver_code };
  }, [drivers]);

  const [driverA, setDriverA] = useState(defaultPair.a);
  const [driverB, setDriverB] = useState(defaultPair.b);
  const [selectedLap, setSelectedLap] = useState<number>(1);
  const [telemetry, setTelemetry] = useState<TelemetryComparisonSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Available laps
  const availableLaps = useMemo(() => {
    if (!laps) return [1];
    const nums = Array.from(new Set(laps.map((l) => l.lap_number))).sort((a, b) => a - b);
    return nums.length ? nums : [1];
  }, [laps]);

  // Replay state
  const [isPlaying, setIsPlaying] = useState(false);
  const [distance, setDistance] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const requestRef = useRef<number>();
  const lastTimeRef = useRef<number>();

  useEffect(() => {
    setDistance(0);
    setIsPlaying(false);
  }, [driverA, driverB, selectedLap]);

  const maxDistance = useMemo(() => {
    const points = [...(telemetry?.points_a ?? []), ...(telemetry?.points_b ?? [])];
    return points.reduce((max, point) => Math.max(max, point.distance ?? 0), 0);
  }, [telemetry]);

  const animate = (time: number) => {
    if (lastTimeRef.current !== undefined) {
      const deltaTime = time - lastTimeRef.current;
      const speedScale = 180 * playbackSpeed;
      setDistance((prev) => {
        const next = prev + (deltaTime / 1000) * speedScale;
        if (next >= maxDistance) {
          setIsPlaying(false);
          return maxDistance;
        }
        return next;
      });
    }
    lastTimeRef.current = time;
    requestRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    if (isPlaying) {
      lastTimeRef.current = performance.now();
      requestRef.current = requestAnimationFrame(animate);
    } else {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    }
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [isPlaying, maxDistance, playbackSpeed]);

  async function handleLoadTelemetry() {
    if (!sessionId || !driverA || !driverB || driverA === driverB) {
      setError("Pick two different drivers.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getTelemetryComparison(sessionId, driverA, driverB, 400, selectedLap);
      setTelemetry(data);
      setDistance(0);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const maxSpeed = useMemo(() => {
    const points = [...(telemetry?.points_a ?? []), ...(telemetry?.points_b ?? [])];
    return points.reduce((max, point) => Math.max(max, point.speed ?? 0), 0);
  }, [telemetry]);

  const speedPathA = toPath(telemetry?.points_a ?? [], maxDistance, maxSpeed, (point) => point.speed);
  const speedPathB = toPath(telemetry?.points_b ?? [], maxDistance, maxSpeed, (point) => point.speed);

  const currentA = useMemo(() => interpolate(telemetry?.points_a ?? [], distance), [telemetry?.points_a, distance]);
  const currentB = useMemo(() => interpolate(telemetry?.points_b ?? [], distance), [telemetry?.points_b, distance]);

  const summaryA = useMemo(() => buildSummary(telemetry?.points_a ?? []), [telemetry?.points_a]);
  const summaryB = useMemo(() => buildSummary(telemetry?.points_b ?? []), [telemetry?.points_b]);

  return (
    <section className="panel pitwall-telemetry-panel">
      <h3>Lap-by-Lap Telemetry Replay</h3>
      
      <div className="row" style={{ gap: "15px" }}>
        <label>
          Driver A
          <select value={driverA} onChange={(e) => setDriverA(e.target.value)}>
            {drivers.map((d) => <option key={d.driver_code} value={d.driver_code}>{d.driver_code}</option>)}
          </select>
        </label>
        <label>
          Driver B
          <select value={driverB} onChange={(e) => setDriverB(e.target.value)}>
            {drivers.map((d) => <option key={d.driver_code} value={d.driver_code}>{d.driver_code}</option>)}
          </select>
        </label>
        <label>
          Lap
          <select value={selectedLap} onChange={(e) => setSelectedLap(parseInt(e.target.value))}>
            {availableLaps.map((n) => <option key={n} value={n}>Lap {n}</option>)}
          </select>
        </label>
        <button onClick={handleLoadTelemetry} disabled={loading} className="primary">
          {loading ? "Loading..." : "Load Lap Data"}
        </button>
      </div>

      <div className="playback-controls row" style={{ margin: "20px 0", gap: "20px", alignItems: "center" }}>
        <button onClick={() => setIsPlaying(!isPlaying)} disabled={!telemetry}>
          {isPlaying ? "⏸ Pause" : "▶ Play Replay"}
        </button>
        <button onClick={() => { setIsPlaying(false); setDistance(0); }} disabled={!telemetry}>
          ⏹ Stop
        </button>
        
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "10px" }}>
          <input
            type="range"
            min={0}
            max={maxDistance || 1}
            value={distance}
            onChange={(e) => setDistance(parseFloat(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ minWidth: "60px" }}>{distance.toFixed(0)}m</span>
        </div>

        <select value={playbackSpeed} onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}>
          <option value={0.5}>0.5x</option>
          <option value={1}>1.0x</option>
          <option value={2}>2.0x</option>
          <option value={5}>5.0x</option>
        </select>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: "20px" }}>
        <div>
          <h4>Speed Sync</h4>
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="telemetry-chart">
            <rect x={0} y={0} width={WIDTH} height={HEIGHT} fill="#0f2231" />
            <path d={speedPathA} stroke="#ff7a18" strokeWidth={2} fill="none" opacity={0.3} />
            <path d={speedPathB} stroke="#6de0ff" strokeWidth={2} fill="none" opacity={0.3} />
            <line
              x1={maxDistance > 0 ? (distance / maxDistance) * WIDTH : 0}
              y1={0}
              x2={maxDistance > 0 ? (distance / maxDistance) * WIDTH : 0}
              y2={HEIGHT}
              stroke="white"
              strokeWidth={1}
            />
          </svg>
          
          <div className="live-metrics row" style={{ marginTop: "10px" }}>
            <div className="metric-card" style={{ borderLeft: "4px solid #ff7a18", padding: "10px", background: "#1a1d29" }}>
              <div style={{ fontWeight: "bold" }}>{driverA}</div>
              <div style={{ fontSize: "1.2em" }}>{currentA?.speed?.toFixed(0)} <small>km/h</small></div>
              <div style={{ fontSize: "0.8em", opacity: 0.7 }}>G{currentA?.n_gear} | {currentA?.throttle?.toFixed(0)}% Thr</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #6de0ff", padding: "10px", background: "#1a1d29" }}>
              <div style={{ fontWeight: "bold" }}>{driverB}</div>
              <div style={{ fontSize: "1.2em" }}>{currentB?.speed?.toFixed(0)} <small>km/h</small></div>
              <div style={{ fontSize: "0.8em", opacity: 0.7 }}>G{currentB?.n_gear} | {currentB?.throttle?.toFixed(0)}% Thr</div>
            </div>
          </div>
        </div>

        <div>
          <h4>Track Position</h4>
          <TrackMap telemetry={telemetry} distance={distance} driverA={driverA} driverB={driverB} />
        </div>
      </div>

      <div style={{ marginTop: "30px" }}>
        <h4>Lap {selectedLap} Summary</h4>
        <table>
          <thead>
            <tr><th>Channel</th><th>{driverA}</th><th>{driverB}</th></tr>
          </thead>
          <tbody>
            <tr><td>Max Speed</td><td>{summaryA.maxSpeed?.toFixed(1)}</td><td>{summaryB.maxSpeed?.toFixed(1)}</td></tr>
            <tr><td>Avg Speed</td><td>{summaryA.avgSpeed?.toFixed(1)}</td><td>{summaryB.avgSpeed?.toFixed(1)}</td></tr>
            <tr><td>Avg Throttle</td><td>{summaryA.avgThrottle?.toFixed(1)}%</td><td>{summaryB.avgThrottle?.toFixed(1)}%</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TrackMap({ telemetry, distance, driverA, driverB }: { telemetry: TelemetryComparisonSummary | null, distance: number, driverA: string, driverB: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !telemetry) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const points = telemetry.points_a;
    if (!points.length) return;

    const xValues = points.map(p => p.x ?? 0);
    const yValues = points.map(p => p.y ?? 0);
    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const yMin = Math.min(...yValues);
    const yMax = Math.max(...yValues);

    const padding = 40;
    const scale = Math.min(
      (canvas.width - padding * 2) / (xMax - xMin || 1),
      (canvas.height - padding * 2) / (yMax - yMin || 1)
    );

    const tx = (x?: number) => padding + ((x ?? 0) - xMin) * scale;
    const ty = (y?: number) => canvas.height - (padding + ((y ?? 0) - yMin) * scale);

    // Track
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 6;
    ctx.lineJoin = "round";
    ctx.beginPath();
    points.forEach((p, i) => {
      if (i === 0) ctx.moveTo(tx(p.x), ty(p.y));
      else ctx.lineTo(tx(p.x), ty(p.y));
    });
    ctx.stroke();

    const drawDriver = (pts: TelemetryPointSummary[], color: string, label: string) => {
      const pos = interpolate(pts, distance);
      if (!pos) return;
      const x = tx(pos.x);
      const y = ty(pos.y);
      ctx.shadowBlur = 15;
      ctx.shadowColor = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.fillStyle = "white";
      ctx.font = "bold 14px sans-serif";
      ctx.fillText(label, x + 15, y + 5);
    };

    drawDriver(telemetry.points_a, "#ff7a18", driverA);
    drawDriver(telemetry.points_b, "#6de0ff", driverB);

  }, [telemetry, distance, driverA, driverB]);

  return <canvas ref={canvasRef} width={400} height={400} style={{ background: "#0b0e14", borderRadius: "12px", width: "100%" }} />;
}

function buildSummary(points: TelemetryPointSummary[]) {
  if (!points.length) return { maxSpeed: 0, avgSpeed: 0, avgThrottle: 0, maxRpm: 0 };
  const speeds = points.map(p => p.speed ?? 0);
  const throttles = points.map(p => p.throttle ?? 0);
  return {
    maxSpeed: Math.max(...speeds),
    avgSpeed: speeds.reduce((a, b) => a + b, 0) / speeds.length,
    avgThrottle: throttles.reduce((a, b) => a + b, 0) / throttles.length,
    maxRpm: Math.max(...points.map(p => p.rpm ?? 0)),
  };
}

function toPath(points: TelemetryPointSummary[], maxDist: number, maxVal: number, getValue: (p: TelemetryPointSummary) => number | undefined) {
  if (!points.length || maxDist === 0) return "";
  const WIDTH = 800;
  const HEIGHT = 250;
  return points.map((p, i) => {
    const x = ((p.distance ?? 0) / maxDist) * WIDTH;
    const y = HEIGHT - ((getValue(p) ?? 0) / (maxVal || 1)) * HEIGHT;
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
}

function interpolate(points: TelemetryPointSummary[], dist: number): TelemetryPointSummary | null {
  if (!points.length) return null;
  let low = 0;
  let high = points.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const pDist = points[mid].distance ?? 0;
    if (pDist < dist) low = mid + 1;
    else if (pDist > dist) high = mid - 1;
    else return points[mid];
  }
  if (low >= points.length) return points[points.length - 1];
  if (high < 0) return points[0];
  
  const p1 = points[high];
  const p2 = points[low];
  const t = (dist - (p1.distance ?? 0)) / ((p2.distance ?? 0) - (p1.distance ?? 0) || 1);
  
  return {
    distance: dist,
    speed: (p1.speed ?? 0) + t * ((p2.speed ?? 0) - (p1.speed ?? 0)),
    throttle: (p1.throttle ?? 0) + t * ((p2.throttle ?? 0) - (p1.throttle ?? 0)),
    n_gear: p1.n_gear,
    x: (p1.x ?? 0) + t * ((p2.x ?? 0) - (p1.x ?? 0)),
    y: (p1.y ?? 0) + t * ((p2.y ?? 0) - (p1.y ?? 0)),
  };
}
