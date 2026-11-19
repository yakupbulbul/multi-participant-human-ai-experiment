// Shape of what the server sends. There is deliberately no participant kind anywhere.
export interface Message {
  id: number;
  round: number;
  sender: string; // "Player A" .. "Player C"
  content: string;
  ts: number;
  mine: boolean;
}

export interface Result {
  winner: string;
  totals: Record<string, number>;
  round_tallies: Record<string, Record<string, number>>;
  decided_by_tiebreak: boolean;
}

export type Phase = "waiting" | "round" | "vote" | "results" | "aborted";

export interface ServerState {
  type: "state";
  phase: Phase;
  round: number | null;
  ends_at: number | null; // epoch seconds (server clock)
  now: number; // server epoch seconds when this state was sent
  waiting: { count: number; total: number };
  you?: { label: string };
  players?: string[];
  messages?: Message[];
  feedback?: { round: number; tally: Record<string, number> } | null;
  result?: Result | null;
  voted?: boolean;
}
