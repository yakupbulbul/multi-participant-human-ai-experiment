import { useEffect, useRef, useState } from "react";
import type { ServerState } from "../types";
import { formatTime, useCountdown } from "../useExperiment";

interface Props {
  state: ServerState;
  clockOffsetMs: number;
  onSend: (content: string) => void;
}

export default function Round({ state, clockOffsetMs, onSend }: Props) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const left = useCountdown(state.ends_at, clockOffsetMs);
  const messages = (state.messages ?? []).filter((m) => m.round === state.round);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    onSend(text);
    setText("");
  };

  return (
    <>
      <div className="row">
        <p className="label">
          Round {state.round} / 2 · You are {state.you?.label}
        </p>
        <p className="timer">{formatTime(left)}</p>
      </div>
      <h1>Who should be the Decision Maker?</h1>
      {state.feedback && (
        <p className="muted">
          Round {state.feedback.round} votes:{" "}
          {Object.entries(state.feedback.tally)
            .map(([label, n]) => `${label} ${n}`)
            .join(" · ")}
        </p>
      )}
      <div className="messages" ref={listRef}>
        {messages.length === 0 && <p className="muted">No messages yet.</p>}
        {messages.map((m) => (
          <div key={m.id} className={m.mine ? "msg mine" : "msg"}>
            <span className="label">{m.mine ? `${m.sender} (you)` : m.sender}</span>
            <p>{m.content}</p>
          </div>
        ))}
      </div>
      <form className="row" onSubmit={submit}>
        <input value={text} maxLength={500} placeholder="Type a message" onChange={(e) => setText(e.target.value)} />
        <button type="submit">Send</button>
      </form>
    </>
  );
}
