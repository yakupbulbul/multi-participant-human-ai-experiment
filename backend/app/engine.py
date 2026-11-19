"""Live experiment: join, phase machine, timers, broadcast.

One SessionRunner = one experiment session. State lives in memory (single process,
see --workers 1) and every message, vote and status change is also written to Postgres.

Phases: waiting -> round(1) -> vote(1) -> round(2) -> vote(2) -> results   (or aborted)

Blind rule: nothing built here for a client may contain a participant's kind.
Clients only ever see labels ("Player A".."Player C"), never kinds or ids.
After every change the server pushes each client its full state, so a fresh
connection (reload / reconnect) is the same code path as an update.
"""
import asyncio
import hashlib
import logging
import random
import secrets
import time
import uuid
from dataclasses import dataclass

from fastapi import WebSocket
from sqlalchemy.exc import IntegrityError

from . import ai, db, repo
from .config import ExperimentConfig
from .voting import decide, tally

log = logging.getLogger("uvicorn.error")

LABELS = ["Player A", "Player B", "Player C"]
TOTAL_PLAYERS = 3
START_COUNTDOWN_S = 3
MAX_MESSAGE_LEN = 500


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _condition(cfg: ExperimentConfig) -> str:
    ai = TOTAL_PLAYERS - cfg.human_count
    return f"{cfg.human_count}H" + (f"+{ai}AI" if ai else "")


@dataclass
class Player:
    slot: int
    label: str
    kind: str  # "human" | "ai". Server side only.
    participant_id: uuid.UUID
    token_hash: str | None
    ws: WebSocket | None = None
    grace_task: asyncio.Task | None = None


class SessionRunner:
    def __init__(self, cfg: ExperimentConfig, session_id: uuid.UUID, labels: list[str]):
        self.cfg = cfg
        self.session_id = session_id
        self.labels = labels  # labels[slot]; shuffled so the slot order never leaks
        self.players: dict[int, Player] = {}
        self.phase = "waiting"
        self.round_no: int | None = None
        self.ends_at: float | None = None  # epoch seconds; clients only render a countdown
        self.messages: list[dict] = []
        self.votes: dict[int, dict[str, str]] = {1: {}, 2: {}}  # round -> voter label -> candidate label
        self._committed = {1: 0, 2: 0}  # votes already written to the database, per round
        self.feedback: dict | None = None  # round-1 tally, shown during round 2
        self.result: dict | None = None
        self._lock = asyncio.Lock()
        self._run_task: asyncio.Task | None = None
        self._ai_tasks: list[asyncio.Task] = []
        self._all_voted = asyncio.Event()

    @classmethod
    async def create(cls, cfg: ExperimentConfig) -> "SessionRunner":
        labels = LABELS[:]
        random.shuffle(labels)
        async with db.SessionLocal.begin() as s:
            row = await repo.create_session(s, _condition(cfg), cfg.model_dump(mode="json"))
        runner = cls(cfg, row.id, labels)
        runner._schedule_ai_joins()
        return runner

    # ---- joining -------------------------------------------------------

    async def _add_player(self, slot: int, kind: str, token_hash: str | None) -> Player:
        async with db.SessionLocal.begin() as s:
            row = await repo.add_participant(s, self.session_id, slot, self.labels[slot], kind, token_hash)
        player = Player(slot, self.labels[slot], kind, row.id, token_hash)
        self.players[slot] = player
        return player

    def _maybe_start(self) -> None:
        if len(self.players) == TOTAL_PLAYERS and self._run_task is None:
            self.ends_at = time.time() + START_COUNTDOWN_S
            self._run_task = asyncio.create_task(self._run())

    async def join_human(self, ws: WebSocket) -> tuple[Player, str] | None:
        """New human takes the next free human slot. Returns (player, token) or None if not possible."""
        async with self._lock:
            if self.phase != "waiting":
                return None
            free = [
                slot
                for slot, kind in enumerate(self.cfg.participants)
                if kind == "human" and slot not in self.players
            ]
            if not free:
                return None
            token = secrets.token_urlsafe(24)
            player = await self._add_player(free[0], "human", _hash(token))
            player.ws = ws
            self._maybe_start()
            return player, token

    async def reattach_by_token(self, token: str, ws: WebSocket) -> Player | None:
        """Give a returning player the new socket. Under the same lock as detach(), so a reload
        (old socket closing while the new one connects) can never delete a player that just came back."""
        h = _hash(token)
        async with self._lock:
            player = next((p for p in self.players.values() if p.token_hash == h), None)
            if player is None:
                return None
            old, player.ws = player.ws, ws
            if player.grace_task:
                player.grace_task.cancel()
                player.grace_task = None
        if old is not None:
            try:
                await old.close()
            except Exception:
                pass
        return player

    def _schedule_ai_joins(self) -> None:
        """AI 'joins' go through the same add-player path after a random delay, like a human arriving."""
        lo, hi = self.cfg.ai.join_delay_s
        for slot, kind in enumerate(self.cfg.participants):
            if kind == "ai":
                self._ai_tasks.append(asyncio.create_task(self._join_ai_later(slot, random.uniform(lo, hi))))

    async def _join_ai_later(self, slot: int, delay: float) -> None:
        await asyncio.sleep(delay)
        async with self._lock:
            if self.phase != "waiting" or slot in self.players:
                return
            await self._add_player(slot, "ai", None)
            self._maybe_start()
        await self.broadcast()

    # ---- leaving -------------------------------------------------------

    async def detach(self, player: Player, ws: WebSocket) -> None:
        async with self._lock:
            if player.ws is not ws:
                return  # replaced by a newer connection of the same player (checked under the lock)
            player.ws = None
            if self.phase == "waiting":
                # Leaving the waiting room frees the slot; a started countdown is cancelled.
                # Identity check: never remove a different player who now holds the same slot.
                if self.players.get(player.slot) is player:
                    async with db.SessionLocal.begin() as s:
                        await repo.delete_participant(s, player.participant_id)
                    del self.players[player.slot]
                if len(self.players) < TOTAL_PLAYERS and self._run_task is not None:
                    self._run_task.cancel()
                    self._run_task = None
                    self.ends_at = None
            elif self.phase in ("round", "vote"):
                player.grace_task = asyncio.create_task(self._abort_after_grace(player))
        await self.broadcast()

    async def _abort_after_grace(self, player: Player) -> None:
        await asyncio.sleep(self.cfg.disconnect_grace_s)
        if player.ws is None:
            await self.abort()

    async def abort(self) -> None:
        if self.phase in ("results", "aborted"):
            return
        self.phase = "aborted"
        self.ends_at = None
        self._cancel_tasks()
        try:
            async with db.SessionLocal.begin() as s:
                await repo.set_status(s, self.session_id, "aborted")
        except Exception:
            log.exception("could not persist aborted status")
        await self.broadcast()

    def _cancel_tasks(self) -> None:
        current = asyncio.current_task()
        for task in [self._run_task, *self._ai_tasks, *(p.grace_task for p in self.players.values())]:
            if task is not None and task is not current:
                task.cancel()

    async def shutdown(self) -> None:
        """Stop everything and close sockets (used by the dev reset and on app shutdown)."""
        if self.phase in ("waiting", "round", "vote"):
            await self.abort()
        self._cancel_tasks()
        for p in self.players.values():
            if p.ws is not None:
                try:
                    await p.ws.close()
                except Exception:
                    pass

    # ---- player actions (humans and AI use the same two functions) -------

    async def submit_message(self, player: Player, content: str) -> None:
        content = content.strip()[:MAX_MESSAGE_LEN]
        if not content or self.phase != "round":
            return
        round_no = self.round_no
        async with db.SessionLocal.begin() as s:
            row = await repo.add_message(s, self.session_id, round_no, player.participant_id, content)
        self.messages.append(
            {"id": row.id, "round": round_no, "sender": player.label, "content": content, "ts": time.time()}
        )
        await self.broadcast()

    async def submit_vote(self, player: Player, candidate_label: str) -> None:
        if self.phase != "vote" or candidate_label not in self.labels:
            return
        round_no = self.round_no
        if player.label in self.votes[round_no]:
            return  # one vote per round (the database UNIQUE constraint is the last guard)
        candidate = next(p for p in self.players.values() if p.label == candidate_label)
        self.votes[round_no][player.label] = candidate_label  # reserve first: blocks a double submit
        try:
            async with db.SessionLocal.begin() as s:
                await repo.add_vote(s, self.session_id, round_no, player.participant_id, candidate.participant_id)
        except IntegrityError:
            pass  # already stored
        except Exception:
            self.votes[round_no].pop(player.label, None)
            raise
        self._committed[round_no] += 1
        # End the vote early only when all 3 votes are stored, not merely reserved in memory.
        if self._committed[round_no] == TOTAL_PLAYERS:
            self._all_voted.set()
        await self.broadcast()

    async def _wait_votes_committed(self, round_no: int) -> None:
        """Before closing a vote, let any vote that is still being written finish (bounded to 2 s)."""
        for _ in range(200):
            if self._committed[round_no] >= len(self.votes[round_no]):
                return
            await asyncio.sleep(0.01)

    # ---- phase machine -------------------------------------------------

    async def _enter(self, phase: str, round_no: int | None, seconds: float | None) -> None:
        self.phase = phase
        self.round_no = round_no
        self.ends_at = time.time() + seconds if seconds else None
        await self.broadcast()
        if phase in ("round", "vote"):  # each AI plays this phase on its own timer
            for player in self.players.values():
                if player.kind == "ai":
                    self._ai_tasks.append(asyncio.create_task(ai.play_phase(self, player)))

    async def _run(self) -> None:
        try:
            await asyncio.sleep(START_COUNTDOWN_S)
            async with db.SessionLocal.begin() as s:
                await repo.set_status(s, self.session_id, "running")
            for round_no in (1, 2):
                await self._enter("round", round_no, self.cfg.round_seconds)
                await asyncio.sleep(self.cfg.round_seconds)
                self._all_voted.clear()
                await self._enter("vote", round_no, self.cfg.vote_seconds)
                try:  # ends early when all 3 voted, otherwise after vote_seconds (non-voters abstain)
                    await asyncio.wait_for(self._all_voted.wait(), self.cfg.vote_seconds)
                except asyncio.TimeoutError:
                    pass
                await self._wait_votes_committed(round_no)
                if round_no == 1:
                    self.feedback = {"round": 1, "tally": tally(self.votes[1].values(), self.labels)}
            await self._finish()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("session run failed")
            await self.abort()

    async def _finish(self) -> None:
        d = decide(
            {r: list(v.values()) for r, v in self.votes.items()},
            self.labels,
            self.cfg.voting.rule,
            seed=str(self.session_id),
        )
        winner = next(p for p in self.players.values() if p.label == d.winner)
        self.result = {
            "winner": d.winner,
            "totals": d.totals,
            "round_tallies": {str(r): t for r, t in d.round_tallies.items()},
            "decided_by_tiebreak": d.decided_by_tiebreak,
        }
        async with db.SessionLocal.begin() as s:
            await repo.set_status(s, self.session_id, "finished", winner_id=winner.participant_id)
        await self._enter("results", None, None)

    # ---- state pushed to clients ------------------------------------------

    def state_for(self, me: Player) -> dict:
        state: dict = {
            "type": "state",
            "phase": self.phase,
            "round": self.round_no,
            "ends_at": self.ends_at,
            "now": time.time(),  # lets the client correct for clock skew when rendering countdowns
            "waiting": {"count": len(self.players), "total": TOTAL_PLAYERS},
        }
        if self.phase != "waiting":  # labels and chat are revealed only once the experiment starts
            state["you"] = {"label": me.label}
            state["players"] = sorted(self.labels)
            state["messages"] = [{**m, "mine": m["sender"] == me.label} for m in self.messages]
            state["feedback"] = self.feedback
            state["result"] = self.result
            if self.phase == "vote":
                state["voted"] = me.label in self.votes[self.round_no]
        return state

    async def broadcast(self) -> None:
        for player in list(self.players.values()):
            if player.ws is None:
                continue
            try:
                await player.ws.send_json(self.state_for(player))
            except Exception:
                pass  # dead socket: its receive loop handles the disconnect


class Lobby:
    """Holds the one live session. A finished or aborted session is replaced by the next arrival."""

    def __init__(self, cfg: ExperimentConfig):
        self.cfg = cfg
        self.runner: SessionRunner | None = None
        self._lock = asyncio.Lock()

    async def attach(
        self, ws: WebSocket, token: str | None
    ) -> tuple[SessionRunner, Player, str | None] | None:
        """Returns (runner, player, new_token). new_token is None on reconnect. None = session full/in progress."""
        async with self._lock:
            runner = self.runner
            if token and runner is not None:
                player = await runner.reattach_by_token(token, ws)
                if player is not None:
                    return runner, player, None
            if runner is None or runner.phase in ("results", "aborted"):
                runner = self.runner = await SessionRunner.create(self.cfg)
            joined = await runner.join_human(ws)
            if joined is None:
                return None
            return runner, joined[0], joined[1]

    async def reset(self) -> None:
        async with self._lock:
            if self.runner is not None:
                await self.runner.shutdown()
            self.runner = None
