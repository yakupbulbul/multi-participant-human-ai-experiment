import type { Result } from "../types";
import { leaveSession } from "../useExperiment";

export default function Results({ result, you }: { result: Result; you?: string }) {
  const rows = Object.entries(result.totals).sort((a, b) => b[1] - a[1]);
  return (
    <>
      <p className="label">Final result</p>
      <h1>{result.winner} is the Decision Maker</h1>
      {result.winner === you && <p className="muted">That is you.</p>}
      {result.decided_by_tiebreak && <p className="muted">The vote was tied and decided by tie-break.</p>}
      <div className="cards">
        {rows.map(([label, n]) => (
          <div key={label} className={label === result.winner ? "vote-card selected" : "vote-card"}>
            <span className="name">{label}</span>
            <span className="label">
              {n} {n === 1 ? "vote" : "votes"}
            </span>
          </div>
        ))}
      </div>
      <p className="muted">
        Per round:{" "}
        {Object.entries(result.round_tallies)
          .map(([r, t]) => `R${r} ${Object.entries(t).map(([l, n]) => `${l.replace("Player ", "")}:${n}`).join(" ")}`)
          .join(" | ")}
      </p>
      <button onClick={leaveSession}>Join a new session</button>
    </>
  );
}
