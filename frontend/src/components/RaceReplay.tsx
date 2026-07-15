import { useEffect, useMemo, useState, useRef } from "react";
import { getSessionReplay, getPitStops } from "../api/client";
import { SessionReplaySummary, ReplayFrame, ReplayDriverSnapshot, PitStopSummary } from "../types";

interface RaceReplayProps {
  sessionId: string;
}

export function RaceReplay({ sessionId }: RaceReplayProps) {
  console.log("[REPLAY] Rendering component with sessionId:", sessionId);
  const [replayData, setReplayData] = useState<SessionReplaySummary | null>(null);
  const [pitStops, setPitStops] = useState<PitStopSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  
  const requestRef = useRef<number>();
  const lastTimeRef = useRef<number>();

  useEffect(() => {
    async function loadData() {
      if (!sessionId) return;
      console.log("[REPLAY] Loading replay data for:", sessionId);
      setLoading(true);
      setError(null);
      setReplayData(null);
      try {
        const [replay, stops] = await Promise.all([
          getSessionReplay(sessionId),
          getPitStops(sessionId)
        ]);
        console.log("[REPLAY] Data loaded:", replay.frames.length, "frames,", stops.length, "pit stops");
        setReplayData(replay);
        setPitStops(stops);
        setFrameIndex(0);
      } catch (err) {
        console.error("[REPLAY] Load failed:", err);
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [sessionId]);

  const animate = (time: number) => {
    if (lastTimeRef.current !== undefined && replayData) {
      const deltaTime = time - lastTimeRef.current;
      const framesPerSecond = 10 * playbackSpeed; // 10 FPS matching backend dt=0.1
      
      setFrameIndex((prev) => {
        const next = prev + (deltaTime / 1000) * framesPerSecond;
        if (next >= replayData.frames.length - 1) {
          setIsPlaying(false);
          return replayData.frames.length - 1;
        }
        return next;
      });
    }
    lastTimeRef.current = time;
    requestRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    if (isPlaying && replayData) {
      lastTimeRef.current = performance.now();
      requestRef.current = requestAnimationFrame(animate);
    } else {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    }
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [isPlaying, replayData, playbackSpeed]);

  const currentFrame = useMemo(() => {
    if (!replayData) return null;
    return replayData.frames[Math.floor(frameIndex)];
  }, [replayData, frameIndex]);

  if (!sessionId) return <div className="panel">Please load a session first.</div>;
  if (loading) return <div className="panel" style={{ minHeight: "400px", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <h2>Loading Race Replay...</h2>
  </div>;
  if (error) return <div className="panel error">Error: {error}</div>;
  if (!replayData) return <div className="panel">No replay data available for this session.</div>;

  return (
    <section className="panel race-replay-panel" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h3>🎥 Race Replay: {replayData.session_id}</h3>
        <div className="session-info">
          {currentFrame && (
            <span style={{ fontSize: "1.2rem", color: "#f5b400", fontWeight: "bold" }}>
              Time: {currentFrame.t.toFixed(1)}s
            </span>
          )}
        </div>
      </div>

      <div className="playback-controls row" style={{ padding: "15px", background: "#111827", borderRadius: "8px", gap: "20px" }}>
        <button onClick={() => setIsPlaying(!isPlaying)} className="primary" style={{ padding: "10px 20px" }}>
          {isPlaying ? "⏸ Pause" : "▶ Play Replay"}
        </button>
        <button onClick={() => { setIsPlaying(false); setFrameIndex(0); }}>
          ⏹ Reset
        </button>
        
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "15px" }}>
          <input
            type="range"
            min={0}
            max={replayData.frames.length - 1}
            step={1}
            value={Math.floor(frameIndex)}
            onChange={(e) => setFrameIndex(parseInt(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ minWidth: "120px", fontVariantNumeric: "tabular-nums" }}>
            Frame {Math.floor(frameIndex)} / {replayData.frames.length - 1}
          </span>
        </div>

        <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          Speed
          <select value={playbackSpeed} onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}>
            <option value={1}>1.0x</option>
            <option value={10}>10x</option>
            <option value={50}>50x</option>
            <option value={100}>100x</option>
          </select>
        </label>
      </div>

      <div style={{ flex: 1, position: "relative", height: "600px", minHeight: "600px", background: "#000", borderRadius: "8px", overflow: "hidden", border: "2px solid red" }}>
        <ReplayCanvas replayData={replayData} frameIndex={frameIndex} />
      </div>
    </section>
  );
}

function ReplayCanvas({ replayData, frameIndex }: { replayData: SessionReplaySummary, frameIndex: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const bounds = useMemo(() => {
    if (!replayData.track_layout || !replayData.track_layout.X.length) {
      return { xMin: -1, xMax: 1, yMin: -1, yMax: 1 };
    }
    const xValues = replayData.track_layout.X;
    const yValues = replayData.track_layout.Y;
    return {
      xMin: Math.min(...xValues),
      xMax: Math.max(...xValues),
      yMin: Math.min(...yValues),
      yMax: Math.max(...yValues)
    };
  }, [replayData.track_layout]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const updateSize = () => {
      const width = canvas.parentElement?.clientWidth || 800;
      const height = canvas.parentElement?.clientHeight || 600;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
    };

    updateSize();

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (!replayData.track_layout || !replayData.track_layout.X.length) {
      console.log("[REPLAY] No track layout data");
      ctx.fillStyle = "#ef4444";
      ctx.textAlign = "center";
      ctx.font = "20px Arial";
      ctx.fillText("No track layout data available", canvas.width / 2, canvas.height / 2);
      return;
    }

    const { xMin, xMax, yMin, yMax } = bounds;
    const padding = 60;
    const scale = Math.min(
      (canvas.width - padding * 2) / (xMax - xMin || 1),
      (canvas.height - padding * 2) / (yMax - yMin || 1)
    );

    const tx = (x: number) => padding + (x - xMin) * scale;
    const ty = (y: number) => canvas.height - (padding + (y - yMin) * scale);

    // 1. Draw Track
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 3;
    ctx.lineJoin = "round";
    ctx.beginPath();
    replayData.track_layout.X.forEach((x, i) => {
      const y = replayData.track_layout!.Y[i];
      if (i === 0) ctx.moveTo(tx(x), ty(y));
      else ctx.lineTo(tx(x), ty(y));
    });
    ctx.stroke();

    // 2. Draw Drivers
    const currentFrame = replayData.frames[Math.floor(frameIndex)];
    if (currentFrame) {
      Object.values(currentFrame.drivers).forEach((driver) => {
        const x = tx(driver.x);
        const y = ty(driver.y);
        
        const color = replayData.driver_colors?.[driver.code] || "#fff";
        
        ctx.shadowBlur = 15;
        ctx.shadowColor = color;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
        
        ctx.fillStyle = "white";
        ctx.font = "bold 14px monospace";
        const label = driver.is_pitting ? `${driver.code} (PIT)` : driver.code;
        ctx.fillText(label, x + 12, y + 5);

        if (driver.is_pitting) {
          ctx.strokeStyle = "#fbbf24";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(x, y, 12, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    }

  }, [replayData, frameIndex, bounds]);

  return <canvas ref={canvasRef} style={{ display: "block" }} />;
}
