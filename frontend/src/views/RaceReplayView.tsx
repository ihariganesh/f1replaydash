import { RaceReplay } from "../components/RaceReplay";

interface RaceReplayViewProps {
  sessionId: string;
}

export function RaceReplayView({ sessionId }: RaceReplayViewProps) {
  return (
    <div className="view-container">
      <RaceReplay sessionId={sessionId} />
    </div>
  );
}
