# AGENTS.md

Rules for any AI coding agent working in this repository. Read this before changing anything.

## Project

Take-home assessment (Center for Humans and Machines, MPIB): a web app that simulates a 3-participant group decision-making experiment. Participants chat in real time for 2 rounds (about 1 minute each), vote for a Decision Maker after each round, and see the final result. Participants must not know whether the others are humans or AI agents.

Hard limit: the whole task is capped at 4 hours. Build a clean working core flow, not extra polish.

## Stack (fixed)

- Frontend: React (Vite, TypeScript, plain CSS with CSS variables, no UI library)
- Backend: Python, FastAPI, native WebSockets, SQLAlchemy 2.0 (async, asyncpg)
- Database: PostgreSQL 16 (schema created on startup with `create_all`, no Alembic)
- Containers: Docker Compose; the whole app starts with `docker compose up --build`
- Local Docker runtime is Colima (context `colima`)

## Non-negotiable rules

1. **Blind condition.** Nothing sent to a client may reveal whether a participant is human or AI. No `kind`/`ai`/`human` keys in any API or WebSocket payload, DOM attribute, class name or log shown to users. AI and human messages use the same code path, payload shape and styling. The waiting room shows only a generic "Waiting for participants (n/3)".
2. **Config drives the session.** `config.yml` decides the participant types (`human` / `ai`). All three conditions (3 humans, 2 humans + 1 AI, 1 human + 2 AI) must work by editing only `config.yml`. No code change, no rebuild of the frontend.
3. **Server is authoritative.** The backend owns the phase machine and timers. The client only renders `phase` and `ends_at`. On every WebSocket connect the server sends a full state snapshot.
4. **Rules live in the database.** One vote per participant per round is a `UNIQUE` constraint, not only application code. Use simple FKs, `UNIQUE` and `CHECK`. No composite FKs.
5. **Single backend process.** Run uvicorn with `--workers 1`. Session state and timers live in process memory.
6. **Dev-only routes** (`/api/dev/reset`) exist only when `DEV_MODE=1`.
7. **Keep it explainable.** The author presents the design in 5 minutes. Prefer the simple, obvious choice and add a one-line reason in the README. Do not add libraries, abstractions or features that are not in the plan.

## Build order and cut line

Follow the approved plan. Order: Docker skeleton, DB models, session engine, scripted AI, frontend (plain CSS first), identity/abort/reset, tests + README, style polish last.

Checkpoint at 2h30: the core flow must run end to end in the browser, unstyled, in at least one config. If it does not, start cutting.

Cut order (first to last): AI takeover of a disconnected human, LLM adapter, inter-round tally polish, stretch tests, style polish, reconnect-by-token.
Never cut: config switching for all 3 conditions, DB constraints, blind UI, snapshot on connect, README, AI log.

## Testing

Three must-have tests: (1) `decide()` rules and tie-break, (2) duplicate vote raises `IntegrityError`, (3) blind payload check plus a full 1H+2AI flow using `config.test.yml` (1-2 second rounds, real timers, no fake clock). Everything else is stretch.

## AI usage log (required by the assessment)

The repository must contain every prompt that directs the project, sent to AI assistants, with the **exact model and tool** used. This is kept in `ai_logs/prompts.md`.

- After every prompt that directs the work (including short approvals like "Yes, start step 3"), append an entry: date, tool, exact model name, prompt text verbatim. Side questions that do not direct the project are not logged. If a prompt was sent in another language, log an English translation and mark it "(translated from Turkish)" in the entry title.
- If the model or tool changes, say so in the entry header.
- Agents: remind the user at the end of each work block to update the log if you cannot append to it yourself.

## Style

- Python: type hints, small functions, no dead code. Pure functions for logic that must be tested (`decide()`).
- Frontend: one `useExperiment` hook over the WebSocket; screens switch on server `phase`. Design tokens as CSS variables.
- UI look (applied last): near-black background `rgb(9,10,11)`, off-white text, borders `rgba(255,255,255,.10)`, 18px card radius, Geist Sans/Mono, tight letter-spacing on headlines, pill buttons (off-white, black text), mono uppercase labels, one green accent. Same styling for every participant.
- Do not commit secrets. Keep `.env.example` current.
- Do not run `git commit` or `git push` unless the user asks.
