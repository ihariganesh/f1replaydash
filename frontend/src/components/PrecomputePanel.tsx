import { useMemo, useState } from "react";

import { getPrecomputeJob, startPrecomputeJob } from "../api/client";
import { PrecomputeJobResponse } from "../types";

interface PrecomputePanelProps {
  sessionId: string;
}

export function PrecomputePanel({ sessionId }: PrecomputePanelProps) {
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

  const [job, setJob] = useState<PrecomputeJobResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    if (!parsed.year || !parsed.round) {
      setError("Load a session before starting precompute.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const started = await startPrecomputeJob(parsed.year, parsed.round);
      setJob(started);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshStatus() {
    if (!job) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const updated = await getPrecomputeJob(job.job_id);
      setJob(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Background Precompute</h2>
      <p>Warm telemetry, strategy, and comparison caches for FP1/FP2/Q/R in the background.</p>
      <div className="row">
        <button onClick={handleStart} disabled={loading || !sessionId}>
          {loading ? "Starting..." : "Start warmup job"}
        </button>
        <button onClick={handleRefreshStatus} disabled={loading || !job}>
          Refresh job status
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}
      {job ? (
        <p>
          Job {job.job_id}: {job.status} {job.message ? `- ${job.message}` : ""}
        </p>
      ) : (
        <p>No job started yet.</p>
      )}
    </section>
  );
}
