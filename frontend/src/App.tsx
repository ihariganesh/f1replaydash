import { useMemo, useState } from "react";

import { getDrivers, getGaps, getLaps } from "./api/client";
import { ExportPanel } from "./components/ExportPanel";
import { MultiSessionTrend } from "./components/MultiSessionTrend";
import { PrecomputePanel } from "./components/PrecomputePanel";
import { SessionLoader } from "./components/SessionLoader";
import { DriverSummary, GapSummary, LapSummary, SessionLoadResponse } from "./types";
import { PracticeView } from "./views/PracticeView";
import { QualifyingView } from "./views/QualifyingView";
import { RaceView } from "./views/RaceView";
import { RaceReplayView } from "./views/RaceReplayView";

type ViewMode = "practice" | "qualifying" | "race" | "replay";


export function App() {
  const [view, setView] = useState<ViewMode>("practice");
  const [activeSession, setActiveSession] = useState<SessionLoadResponse | null>(null);
  const [drivers, setDrivers] = useState<DriverSummary[]>([]);
  const [laps, setLaps] = useState<LapSummary[]>([]);
  const [gaps, setGaps] = useState<GapSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function hydrateSessionData(session: SessionLoadResponse) {
    setIsRefreshing(true);
    setError(null);
    try {
      const [driversData, lapsData, gapsData] = await Promise.all([
        getDrivers(session.session_id),
        getLaps(session.session_id, 150),
        getGaps(session.session_id),
      ]);
      setDrivers(driversData);
      setLaps(lapsData);
      setGaps(gapsData);
      setActiveSession(session);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsRefreshing(false);
    }
  }

  const currentView = useMemo(() => {
    if (view === "qualifying") {
      return (
        <QualifyingView
          sessionId={activeSession?.session_id ?? ""}
          drivers={drivers}
          laps={laps}
          gaps={gaps}
        />
      );
    }

    if (view === "race") {
      return (
        <RaceView
          sessionId={activeSession?.session_id ?? ""}
          drivers={drivers}
          gaps={gaps}
          laps={laps}
        />
      );
    }

    if (view === "replay") {
      console.log("[APP] Rendering RaceReplayView with sessionId:", activeSession?.session_id);
      return <RaceReplayView sessionId={activeSession?.session_id ?? ""} />;
    }

    return <PracticeView sessionId={activeSession?.session_id ?? ""} drivers={drivers} laps={laps} />;

  }, [activeSession?.session_id, drivers, gaps, laps, view]);

  return (
    <main className="app-shell">
      <header className="hero">
        <h1>F1 Dash Pit Wall</h1>
        <p>Build and learn race engineering analytics with FastF1.</p>
      </header>

      <SessionLoader onLoaded={hydrateSessionData} />

      <section className="panel">
        <h2>View Switcher</h2>
        <div className="row">
          <button onClick={() => setView("practice")}>Practice</button>
          <button onClick={() => setView("qualifying")}>Qualifying</button>
          <button onClick={() => setView("race")}>Race</button>
          <button onClick={() => setView("replay")}>Race Replay</button>
          <button onClick={() => activeSession && hydrateSessionData(activeSession)} disabled={!activeSession || isRefreshing}>

            {isRefreshing ? "Refreshing..." : "Refresh data"}
          </button>
        </div>
        {activeSession ? (
          <p>
            Active: {activeSession.session_id} ({activeSession.event_name})
          </p>
        ) : (
          <p>No active session loaded.</p>
        )}
        {error ? <p className="error">{error}</p> : null}
      </section>

      {currentView}

      <MultiSessionTrend sessionId={activeSession?.session_id ?? ""} />
      <PrecomputePanel sessionId={activeSession?.session_id ?? ""} />
      <ExportPanel sessionId={activeSession?.session_id ?? ""} />
    </main>
  );
}
