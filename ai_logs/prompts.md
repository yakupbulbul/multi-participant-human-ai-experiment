# AI usage log

Required by the assessment: all prompts sent to AI assistants, with the exact model and tool.

## Tools and models

| Tool | Model (exact) | Notes |
|---|---|---|
| Claude Code (Claude desktop app, Code tab) | `claude-sonnet-5-5` | Confirmed by the author on 2026-11-19. Used for the whole session below. |

## How to read this log

- Entries are in order. Each has date, tool, model, and the prompt text verbatim.
- Prompts are the author's own messages. Assistant answers are not logged here.
- Back-filled on 2026-11-19 from the session transcript (step 0c of the plan), then kept up to date after each prompt.
- Redaction: the local absolute path in prompt 1's file references was shortened to `~/Downloads/` (it contained the local user name). Nothing else was changed.
- Prompt 1 had two `@` file references to the assessment brief. The brief itself is not copied here.
- Prompt 1 asks to "follow AGENTS.md", but no `AGENTS.md` existed at that time. It was created in step 0b.

---

## Session 1: planning (plan mode) and setup

### Prompt 1 - original request: assessment, AGENTS.md/interview requirements, plan questions, UI spec
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
@"~/Downloads/technical-assessment-multi-participant-human-ai-experiment-platform-v4 (1).md"
@"~/Downloads/technical-assessment-multi-participant-human-ai-experiment-platform-v4 (1).md"
I'm building a take-home assessment for a Full-Stack Developer role at a research institute. The full brief is in the attached assessment file. In short: a web app that simulates a 3-participant group decision-making experiment. Participants chat in real time for 2 rounds of about 1 minute each, then vote on who should be the Decision Maker, and the results are shown at the end. Participants must not know whether the others are humans or AI agents. A config.yml must let me switch between 3 humans, 2 humans + 1 AI, and 1 human + 2 AI without code changes. Stack is fixed: React, FastAPI, PostgreSQL (I already decided on Postgres over MongoDB), all started with one Docker command. The task is capped at 4 hours, so I want a clean working core flow, not extra polish.

Please follow AGENTS.md and the interview requirements: I will present my process in 5 minutes, so every choice must be easy to explain. All my prompts have to go into an AI usage log with the exact model name, so please remind me to keep it updated.

Before writing any code, give me a short plan I can approve. I'd like:
1. A proposed architecture (services, real-time transport, how config.yml drives the session) with one sentence of trade-off per decision.
2. A Postgres data model: tables for sessions, participants, messages and votes, with constraints that enforce the rules at the database level (for example, one vote per participant per round). Say which library you'd use (SQLAlchemy or SQLModel) and how schema creation is handled (Alembic migrations or create-on-startup), keeping it simple for the 4-hour limit.
3. Your recommendation on the open choices the brief leaves to me: tie-breaking, what feedback to show between rounds, how AI agents behave (and how to keep them indistinguishable from humans), what happens when a human disconnects, and whether to use an LLM or scripted replies for the AI. Pick sensible defaults and keep it cheap to run.
4. A build order split into small steps that fit in 4 hours, with a clear cut line for what I drop if I run out of time.
5. A test plan for the core flow and the main edge cases.

For the UI I'd like a dark, minimal developer-tool look: near-black background (about rgb(9,10,11)), off-white text, thin low-contrast borders (white at 10% opacity), rounded cards (about 18px radius), Geist Sans and Geist Mono fonts, big bold headlines with very tight letter-spacing, pill-shaped buttons (off-white with black text), mono uppercase section labels, and small status dots. Use one green accent color only. Screens: waiting room with three slots, chat round with a timer, voting with three cards, and a results page. The UI must never reveal who is human and who is AI. Use the same styling for every participant.
````

### Prompt 2 - plan review 1 (waiting room, Docker check, result rule, pitfalls)
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
1) Waiting room must not leak AI slots: show only a generic "Waiting for participants (n/3)"; AI participants "join" after random human-like delays.
2) First step: prove `docker compose version` and `docker info` work on this machine; stop and tell me if not.
3) Result rule: propose sum of both rounds with round-2 tie-break as the default, and list the trade-off vs "round 2 decides"; I will choose.
4) Add pitfalls to the plan: nginx WebSocket upgrade headers, uvicorn --workers 1, Postgres healthcheck with depends_on.
````

### Prompt 3 - answer to the multiple-choice question "Which final-result rule should the plan use as the default in config.yml?"
- Date: 2026-11-19
- Tool: Claude Code (answered through the question dialog, not typed)
- Model: claude-sonnet-5-5

````text
Sum of both rounds
````

### Prompt 4 - plan review 2 (scope trim, UI waiting screen, Colima)
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
(1) fix the UI spec so the waiting screen shows only the generic count; (2) trim scope: plain CSS first (polish last), simple FKs + UNIQUE, ~10 persona lines, move disconnect takeover to the top of the cut list; (3) keep only three must-have tests plus the rest as stretch; (4) add a 30-minute buffer to the time budget; (5) note the lobby-counter limitation in the README. Do not start coding until I setup colima you can check
````

### Prompt 5 - plan review 3 (reconnect, test timing, DEV_MODE, checkpoint, Docker gate)
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Plan approved with these changes: (1) reconnect-by-token moves to the very end of the cut list, and the server sends a full state snapshot on every WebSocket connect; (2) test configs use 1-2 second rounds, no fake clock needed; (3) guard /api/dev/reset behind DEV_MODE=1; (4) README limitations also mention: no consent or debrief screen in this prototype; (5) add a checkpoint at 2h: the core flow must run end to end (unstyled) or we start cutting. Start with the Docker GATE only; stop and report the command outputs.
````

### Prompt 6 - go-ahead for step 0b
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start 0b
````

### Prompt 7 - plan review 4 (final edits, prompt back-fill step, Docker gate re-run)
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Plan approved with the edits below. Please update the plan text first, then run the Docker GATE only (colima status, docker context ls, docker compose version, docker info). I set up Docker myself, so the gate only verifies it. Stop after that and report the command outputs. Do not write any code or files other than the plan update.

Edits:
1. Add a final reminder step (5 min): after the build, a 5-minute slide deck and a docker compose up demo rehearsal are still required for the interview. Do not build the deck in this session. Just keep it in the plan.
2. Add a step to back-fill ai_logs/prompts.md with all earlier prompts, verbatim, in order: the AGENTS.md request, the design and DB questions, the Docker setup request, and the plan reviews. Each entry gets date, tool and the exact model name. Ask me to confirm the model name instead of guessing.
3. Fix the participants table: create human rows only when the human joins (so token_hash is never missing), and drop the "joined" column. Keep the CHECK (kind='ai' OR token_hash IS NOT NULL). AI rows are created through the same join path with a delay.
4. Add "aborted" to the sessions.status enum (waiting, running, finished, aborted), since a long disconnect aborts the session.
5. Remove "tie_break" from the config.yml fields and keep voting.rule only. Replace the stretch test line "disconnect > grace triggers AI takeover" with "disconnect > grace aborts the session".
6. Move the 2h checkpoint to 2h30, because the unstyled frontend ends at about 155 min in the schedule. Keep the rule: the core flow must run end to end in the browser, unstyled, in at least one config, or we start cutting.

After the GATE, wait for my go-ahead before step 0b.
````

### Prompt 8 - go-ahead and model confirmation
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Go, model confirmed
````

### Prompt 9 - go-ahead for step 1
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 1
````

### Prompt 10 - go-ahead for step 2
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 2
````

### Prompt 11 - go-ahead for step 3
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 3
````

### Prompt 12 - go-ahead for step 4
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 4
````

### Prompt 13 - go-ahead for step 5
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 5
````

### Prompt 14 - go-ahead for step 6
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 6
````

### Prompt 15 - go-ahead for step 7
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 7
````

### Prompt 16 - go-ahead for step 8
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, start step 8
````

### Prompt 17 - go-ahead for git init
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, init git
````

### Prompt 18 - go-ahead for first commit
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Yes, commit
````

### Prompt 19 - create GitHub repo and push
- Date: 2026-11-19
- Tool: Claude Code
- Model: claude-sonnet-5-5

````text
Create the GitHub repo and push
````
