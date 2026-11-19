import type { ServerState } from "../types";
import { useCountdown } from "../useExperiment";

// Blind rule: only a generic count. No slots, no per-participant status.
export default function Waiting({ state, clockOffsetMs }: { state: ServerState; clockOffsetMs: number }) {
  const left = useCountdown(state.ends_at, clockOffsetMs);
  const { count, total } = state.waiting;
  return (
    <>
      <p className="label">Waiting room</p>
      <h1>
        Waiting for participants ({count}/{total})
      </h1>
      <p className="muted">
        {state.ends_at ? `Everyone is here. Starting in ${left}s...` : "The experiment starts when all participants have joined."}
      </p>
    </>
  );
}
