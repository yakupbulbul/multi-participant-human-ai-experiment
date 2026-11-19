"""Must-have test 3: full flow for all three conditions, and nothing sent to clients reveals human vs AI.

Uses tests/config.test.yml (1 s rounds, real timers, no fake clock). Clients are in-process
fake sockets that record every JSON payload the server pushes.
"""
import asyncio
import json
import time
from pathlib import Path

import pytest

from app import db, engine, repo
from app.config import load_config
from app.engine import Lobby
from app.models import ExperimentSession

TEST_CONFIG = Path(__file__).parent / "config.test.yml"
CONDITIONS = [
    ["human", "human", "human"],
    ["human", "human", "ai"],
    ["human", "ai", "ai"],
]
FORBIDDEN = ['"kind"', '"human"', '"ai"', "token_hash", "participant_id"]


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_json(self, data: dict) -> None:
        self.sent.append(json.dumps(data))  # must be JSON serialisable, like the real socket

    async def close(self) -> None:
        pass


async def wait_for(predicate, timeout: float = 20.0) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("timed out waiting for the experiment")


@pytest.mark.parametrize("participants", CONDITIONS, ids=["3H", "2H+1AI", "1H+2AI"])
def test_full_flow_and_blind_payloads(participants, run, schema, monkeypatch):
    monkeypatch.setattr(engine, "START_COUNTDOWN_S", 0.1)
    humans = participants.count("human")

    async def go() -> None:
        cfg = load_config(str(TEST_CONFIG)).model_copy(update={"participants": participants})
        lobby = Lobby(cfg)
        sockets = [FakeWS() for _ in range(humans)]
        attached = [await lobby.attach(ws, None) for ws in sockets]
        runner = attached[0][0]
        players = [a[1] for a in attached]

        for round_no in (1, 2):
            await wait_for(lambda: runner.phase == "round" and runner.round_no == round_no)
            for p in players:
                await runner.submit_message(p, f"hello from round {round_no}")
            await wait_for(lambda: runner.phase == "vote" and runner.round_no == round_no)
            for p in players:
                await runner.submit_vote(p, runner.labels[0])
        await wait_for(lambda: runner.phase == "results")

        # The session finished with a winner and everything was persisted.
        assert runner.result["winner"] in runner.labels
        async with db.SessionLocal() as s:
            row = await s.get(ExperimentSession, runner.session_id)
            assert row.status == "finished" and row.winner_participant_id is not None
            stored = await repo.get_participants(s, runner.session_id)
            assert len(stored) == 3
            assert sorted(p.kind for p in stored) == sorted(participants)  # kinds kept server-side only
            stored_votes = await repo.get_votes(s, runner.session_id)
            # Every vote the session counted is in the database. An AI may rarely vote too late (abstain),
            # but the humans always vote, so at least humans x 2 votes exist.
            assert len(stored_votes) == sum(len(v) for v in runner.votes.values())
            assert len(stored_votes) >= humans * 2

        # Blind: no payload sent to any client contains a kind or an internal id.
        blob = "".join("".join(ws.sent) for ws in sockets)
        assert blob, "clients received no state"
        for needle in FORBIDDEN:
            assert needle not in blob, f"{needle} leaked to a client"

        # Same message shape for every sender, human or AI.
        last_state = json.loads(sockets[0].sent[-1])
        shapes = {tuple(sorted(m)) for m in last_state["messages"]}
        assert len(shapes) == 1, shapes

        await runner.shutdown()

    run(go())
