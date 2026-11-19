import { useCallback, useEffect, useRef, useState } from "react";
import type { ServerState } from "./types";

// The server is authoritative: this hook only keeps the latest full state it pushed.
// The token lives in sessionStorage (per tab), so several tabs in one browser can be different participants.
const TOKEN_KEY = "token";

export function useExperiment() {
  const [state, setState] = useState<ServerState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clockOffsetMs, setClockOffsetMs] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let stopped = false;
    let retry: number | undefined;

    const connect = () => {
      const token = sessionStorage.getItem(TOKEN_KEY);
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const query = token ? `?token=${encodeURIComponent(token)}` : "";
      const ws = new WebSocket(`${proto}://${location.host}/ws/session${query}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const m = JSON.parse(e.data);
        if (m.type === "welcome") {
          sessionStorage.setItem(TOKEN_KEY, m.token);
        } else if (m.type === "error") {
          stopped = true; // the server will not let us in: do not retry
          setError(m.code);
        } else {
          setClockOffsetMs(m.now * 1000 - Date.now());
          setState(m);
        }
      };
      // A dropped connection reconnects with the same token and gets a full snapshot back.
      ws.onclose = () => {
        if (!stopped) retry = window.setTimeout(connect, 1000);
      };
    };

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      wsRef.current?.close();
    };
  }, []);

  const send = useCallback((payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify(payload));
  }, []);

  const sendMessage = useCallback((content: string) => send({ type: "message", content }), [send]);
  const sendVote = useCallback((candidate: string) => send({ type: "vote", candidate }), [send]);

  return { state, error, clockOffsetMs, sendMessage, sendVote };
}

/** Whole seconds left until `endsAt` (server epoch seconds), corrected for clock skew. */
export function useCountdown(endsAt: number | null | undefined, clockOffsetMs: number): number {
  const [left, setLeft] = useState(0);
  useEffect(() => {
    if (!endsAt) {
      setLeft(0);
      return;
    }
    const tick = () => setLeft(Math.max(0, Math.ceil(endsAt - (Date.now() + clockOffsetMs) / 1000)));
    tick();
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, [endsAt, clockOffsetMs]);
  return left;
}

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function leaveSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  location.reload();
}
