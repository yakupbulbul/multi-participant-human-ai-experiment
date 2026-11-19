import Notice from "./screens/Notice";
import Results from "./screens/Results";
import Round from "./screens/Round";
import Shell from "./screens/Shell";
import Vote from "./screens/Vote";
import Waiting from "./screens/Waiting";
import { useExperiment } from "./useExperiment";

// The server decides the phase; this component only maps phase -> screen.
export default function App() {
  const { state, error, clockOffsetMs, sendMessage, sendVote } = useExperiment();

  let screen;
  if (error === "session_in_progress") {
    screen = <Notice title="An experiment is already running" text="Please try again in a few minutes." />;
  } else if (!state) {
    screen = <p className="muted">Connecting...</p>;
  } else if (state.phase === "waiting") {
    screen = <Waiting state={state} clockOffsetMs={clockOffsetMs} />;
  } else if (state.phase === "round") {
    screen = <Round key={state.round} state={state} clockOffsetMs={clockOffsetMs} onSend={sendMessage} />;
  } else if (state.phase === "vote") {
    screen = <Vote key={state.round} state={state} clockOffsetMs={clockOffsetMs} onVote={sendVote} />;
  } else if (state.phase === "results" && state.result) {
    screen = <Results result={state.result} you={state.you?.label} />;
  } else {
    screen = <Notice title="The session ended" text="The experiment was stopped before it finished." />;
  }

  return <Shell>{screen}</Shell>;
}
