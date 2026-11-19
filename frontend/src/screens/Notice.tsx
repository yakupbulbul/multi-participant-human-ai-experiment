import { leaveSession } from "../useExperiment";

export default function Notice({ title, text }: { title: string; text: string }) {
  return (
    <>
      <p className="label">Notice</p>
      <h1>{title}</h1>
      <p className="muted">{text}</p>
      <button onClick={leaveSession}>Try again</button>
    </>
  );
}
