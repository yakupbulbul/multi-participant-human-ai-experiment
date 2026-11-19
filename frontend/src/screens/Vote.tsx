import { useState } from "react";
import type { ServerState } from "../types";
import { formatTime, useCountdown } from "../useExperiment";

interface Props {
  state: ServerState;
  clockOffsetMs: number;
  onVote: (candidate: string) => void;
}

// Rendered with key={round}, so the local choice resets for each voting round.
export default function Vote({ state, clockOffsetMs, onVote }: Props) {
  const [choice, setChoice] = useState<string | null>(null);
  const left = useCountdown(state.ends_at, clockOffsetMs);
  const done = choice !== null || state.voted === true;

  return (
    <>
      <div className="row">
        <p className="label">
          Vote {state.round} / 2 · You are {state.you?.label}
        </p>
        <p className="timer">{formatTime(left)}</p>
      </div>
      <h1>Vote for the Decision Maker</h1>
      <div className="cards">
        {(state.players ?? []).map((label) => (
          <button
            key={label}
            className={choice === label ? "vote-card selected" : "vote-card"}
            disabled={done}
            onClick={() => {
              setChoice(label);
              onVote(label);
            }}
          >
            <span className="name">{label}</span>
            {label === state.you?.label && <span className="label">you</span>}
          </button>
        ))}
      </div>
      <p className="muted">{done ? "Vote submitted. Waiting for the others..." : "Choose one participant."}</p>
    </>
  );
}
