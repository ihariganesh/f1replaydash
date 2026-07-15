import { useState } from "react";

import { getSessions, loadSession } from "../api/client";
import { EventSummary, SessionLoadResponse, SessionType } from "../types";

interface SessionLoaderProps {
  onLoaded: (session: SessionLoadResponse) => void;
}

export function SessionLoader({ onLoaded }: SessionLoaderProps) {
  const [year, setYear] = useState<number>(2024);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [selectedEventRound, setSelectedEventRound] = useState<number>(1);
  const [round, setRound] = useState<number>(1);
  const [sessionType, setSessionType] = useState<SessionType>("R");
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFetchEvents() {
    setError(null);
    setIsLoadingEvents(true);
    try {
      const data = await getSessions(year);
      const raceEvents = data.filter((event) => {
        const roundValue = Number(event.round_number ?? event.round);
        return Number.isFinite(roundValue) && roundValue > 0;
      });

      setEvents(raceEvents);
      if (raceEvents.length > 0) {
        const defaultRound = Number(raceEvents[0].round_number ?? raceEvents[0].round);
        setRound(defaultRound);
        setSelectedEventRound(defaultRound);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoadingEvents(false);
    }
  }

  async function handleLoadSession() {
    setError(null);
    setIsLoadingSession(true);
    try {
      const loaded = await loadSession(year, round, sessionType);
      onLoaded(loaded);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoadingSession(false);
    }
  }

  return (
    <section className="panel">
      <h2>Session Loader</h2>
      <div className="row">
        <label>
          Year
          <input
            type="number"
            value={year}
            min={2018}
            max={2100}
            onChange={(event) => setYear(Number(event.target.value))}
          />
        </label>
        <button onClick={handleFetchEvents} disabled={isLoadingEvents}>
          {isLoadingEvents ? "Loading events..." : "Fetch events"}
        </button>
      </div>

      <div className="row">
        <label>
          Grand Prix
          <select
            value={selectedEventRound}
            onChange={(event) => {
              const value = Number(event.target.value);
              setSelectedEventRound(value);
              setRound(value);
            }}
          >
            {events.map((event) => (
              <option
                key={`${event.event_name}-${event.round_number ?? event.round}`}
                value={Number(event.round_number ?? event.round)}
              >
                R{Number(event.round_number ?? event.round)} - {event.event_name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Session
          <select
            value={sessionType}
            onChange={(event) => setSessionType(event.target.value as SessionType)}
          >
            <option value="FP1">FP1</option>
            <option value="FP2">FP2</option>
            <option value="FP3">FP3</option>
            <option value="Q">Q</option>
            <option value="R">R</option>
          </select>
        </label>

        <button
          onClick={handleLoadSession}
          disabled={isLoadingSession || events.length === 0 || !Number.isFinite(round)}
        >
          {isLoadingSession ? "Loading session..." : "Load session"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
