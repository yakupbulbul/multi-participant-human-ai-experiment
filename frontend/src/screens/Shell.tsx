import type { ReactNode } from "react";

// Same frame for every screen and every participant.
export default function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="page">
      <header className="topbar">
        <span className="label">
          <span className="dot" /> Group decision experiment
        </span>
      </header>
      <main className="card">{children}</main>
    </div>
  );
}
