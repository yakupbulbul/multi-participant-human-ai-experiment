# Multi-Participant Human-AI Experiment Platform

A small web app that simulates a **3-participant group decision experiment**. Three participants chat in real time for two rounds, vote on who should be the **Decision Maker** after each round, and see the final result. Participants are never told whether the others are humans or AI agents.

Built as a take-home assessment (Center for Humans and Machines, MPIB) within a 4-hour budget. The goal was a clean, working core flow rather than polish.

**Stack:** React (Vite, TypeScript) · FastAPI (Python) · PostgreSQL 16 · Docker Compose · nginx

## Run it

Requires Docker with Compose.

```bash
docker compose up --build
```

Open <http://localhost:3000>. No `.env` file is needed (defaults are in `docker-compose.yml`; see `.env.example` to override).

Stop with `Ctrl+C`; `docker compose down -v` also removes the database volume.

**One browser tab = one participant.** The join token is kept in `sessionStorage`, so several tabs in the same browser are different participants. Open as many tabs as there are humans in the current configuration (see below). A reload keeps your place.

## Switch the configuration (no code change)

Edit `participants` in [`config.yml`](config.yml), then restart only the backend:

```bash
docker compose restart backend
```

| Condition | `participants` | Tabs to open |
|---|---|---|
| 3 humans | `[human, human, human]` | 3 |
| 2 humans + 1 AI | `[human, human, ai]` | 2 |
| 1 human + 2 AI (default) | `[human, ai, ai]` | 1 |

Other settings in the same file: `round_seconds` (60), `vote_seconds` (20), `voting.rule` (`sum` or `last_round`), `ai.join_delay_s` (range of the AI "arrival" delay), `disconnect_grace_s` (30). The file is validated at startup (exactly 3 entries, only `human`/`ai`, at least one human, unknown keys rejected), and the backend refuses to start on an invalid file.

To play a quick session for a demo, set `round_seconds: 10` and `vote_seconds: 10`.

## Experiment flow and the decisions I made

The brief left these open. My choices, each with the reason:

| Topic | Choice | Why |
|---|---|---|
| Waiting room | Shows only "Waiting for participants (n/3)". AI participants "join" after a random delay through the same code path as humans. | No slot list or pre-filled slots that would reveal where the AI sit. |
| Rounds | 2 rounds of chat (60 s), each followed by a vote (20 s). A voting round ends early once all 3 have voted. | Matches the brief; the early finish keeps the demo fast. |
| Between-round feedback | After the round-1 vote, everyone sees the tally per player (not who voted for whom). It stays visible during round 2. | Gives round 2 something to discuss without exposing individual votes. |
| Final result | **Sum of both rounds.** Ties: more round-2 votes, then a seeded random pick (seed = session id, so it is reproducible). `voting.rule: last_round` switches to "round 2 decides". | Both votes count; the rule is one config line. The result screen says "decided by tie-break" neutrally. |
| Self-vote | Allowed. | Simplest rule; the brief does not forbid it. |
| Abstain | A participant who does not vote in time adds no vote. If nobody votes, the seeded random pick decides. | The experiment always ends with a result. |
| AI behaviour | **Scripted, no LLM.** About 10 short lines, random timing (2 to 9 s between messages), weighted-random votes (more active players are slightly more likely, self less likely). | Cheap, deterministic, runs with `docker compose up` and no API key. |
| Human disconnect | Reconnecting within `disconnect_grace_s` (30 s) restores the same seat and chat. If a human stays away longer, the session is **aborted** and everyone sees a neutral "session ended" screen. In the waiting room, leaving frees the slot. | Simple and predictable. Replacing the person with an AI would be better research design but was cut for time. |

### Keeping humans and AI indistinguishable

- The server never sends a participant's kind. Clients only see labels ("Player A" to "Player C"), which are shuffled per session so the label never leaks the config order. There are no ids in payloads.
- AI and human messages and votes go through the same two functions (`submit_message`, `submit_vote`), so the payload, the length limit and the database writes are identical.
- Every participant is rendered with the same components and styling. Your own messages differ only by alignment and a "(you)" label.
- `GET /api/health` does not expose the configuration.
- One automated test checks that no `kind`, `human`, `ai`, token hash or participant id appears in any payload, for all three conditions.

## Architecture

```
browser (React)  <--HTTP / WebSocket-->  nginx  --/api, /ws-->  FastAPI  <-->  PostgreSQL
                                        (frontend container)    (1 process)
```

Three services in `docker-compose.yml`: `db` (Postgres), `backend` (FastAPI), `frontend` (nginx serving the React build and proxying `/api` and `/ws`).

| Decision | Why | Trade-off |
|---|---|---|
| WebSocket for real time | True push for chat and timers. | A connection manager to write, versus simpler polling. |
| Server-authoritative phases and timers | The server owns the phase machine; clients only render `phase` and `ends_at` (corrected for clock skew). | More server code, but no client can drift or cheat. |
| Push the full state after every change | The first message on connect is the same as any update, so reload and reconnect need no special code. | A few KB per update; fine for 3 participants. |
| In-memory live state, persisted to Postgres | Fast and simple. Every message, vote and status change is also stored. | One backend process (`--workers 1`), and a restart loses a running session. |
| One live session at a time | No lobby or matchmaking to build. | No concurrent groups. A finished or aborted session is replaced by the next arrival. |
| `config.yml` mounted read-only | Switch conditions by editing one file. | Needs a backend restart (no hot reload). |
| SQLAlchemy 2.0 (async) + `create_all` on startup | Widely known, explicit constraints. No migration tooling to explain. | No Alembic. A schema change needs a manual migration or a volume reset. |

### UI

Plain CSS with design tokens as CSS variables (`frontend/src/styles.css`): near-black background, off-white text, 10%-white borders, 18px cards, one green accent, pill buttons, mono uppercase labels, small status dots, and Geist Sans / Geist Mono self-hosted through `@fontsource` (no CDN). Four screens (waiting room, chat round with timer, vote, results) plus a neutral notice screen. All participants use the same components and styling. Layout works down to a 375 px phone width.

### Data model

`sessions`, `participants`, `messages`, `votes`. Rules are enforced by the database, not only by code:

- one vote per participant per round: `UNIQUE (session_id, round, voter_id)`
- one participant per slot and per label in a session: `UNIQUE (session_id, slot)`, `UNIQUE (session_id, label)`
- rounds are 1 or 2, slots are 0 to 2, message length is 1 to 500, session status is one of waiting/running/finished/aborted
- a human participant always has a token: `CHECK (kind = 'ai' OR token_hash IS NOT NULL)`

A participant row is created only when that participant joins (humans and AI alike). Simple single-column foreign keys are used; "the voter belongs to this session" is checked in the service layer (`repo.py`), not by the database.

## Tests

Three must-have tests, run inside the backend container against a separate database (`experiment_test`), so they never touch the live data:

```bash
docker compose up -d
docker compose exec backend pytest -q
```

1. `test_voting.py`: `decide()` for both rules, tie-breaks (round 2, then seeded random, reproducible) and all-abstain.
2. `test_db_constraints.py`: a second vote by the same voter in the same round raises `IntegrityError`.
3. `test_flow_blind.py`: a full session for all three conditions with the 1-second rounds in `backend/tests/config.test.yml` (real timers), persisted rows checked, and no kind or id in any client payload.

Not automated: browser behaviour (I checked the screens by hand), disconnect and abort, and reload races. Those were exercised with ad hoc scripts during development.

## Known limitations

- **The lobby counter is simulated for AI.** The "n/3" count does not come from real arrivals for AI slots; AI "joins" are timed events from a random delay window. A careful participant could notice patterns (for example, arrivals faster than a person could navigate, or the same delay range in every run). Jittered delays and the shared join code path reduce this; the blind is not perfect.
- **Scripted AI text can be spotted** (about 10 lines). An LLM-backed agent would be harder to tell apart but needs an API key and was out of scope.
- **No consent or debrief screen.** A real study needs informed consent before the experiment and a debrief after it that discloses the AI participants.
- Single backend process and one live session; schema created on startup (no Alembic); same-session checks in the service layer rather than composite foreign keys.
- A long human disconnect aborts the session instead of handing the seat to an AI.
- `DEV_MODE=1` is on by default in `docker-compose.yml` to make demos easy: it enables `POST /api/dev/reset`, which aborts the live session. Set `DEV_MODE=0` to remove the route.

## What I cut because of the 4-hour limit

LLM-driven AI, AI takeover of a disconnected human, Alembic migrations, concurrent sessions, browser end-to-end tests.

## AI usage

All prompts and the exact model and tool are in [`ai_logs/prompts.md`](ai_logs/prompts.md). Tool: Claude Code (Claude desktop app). Model: `claude-sonnet-5-5`. Rules for the agent are in [`AGENTS.md`](AGENTS.md).

## Project layout

```
config.yml                 experiment configuration
docker-compose.yml         db + backend + frontend
backend/app/               FastAPI app
  config.py                load and validate config.yml
  models.py, db.py, repo.py   schema, engine, data access
  engine.py                live session: join, phases, timers, broadcast
  voting.py                pure decide() / tally()
  ai.py                    scripted AI participants
  main.py                  HTTP + WebSocket endpoints
backend/tests/             pytest suite
frontend/src/              React app: useExperiment hook, screens/
ai_logs/prompts.md         prompts, model and tool log
```
