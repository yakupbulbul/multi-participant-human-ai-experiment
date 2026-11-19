"""Scripted AI participants: a short list of lines plus random timing. No LLM, no API key.

An AI acts only through SessionRunner.submit_message / submit_vote, the same two
functions a human's WebSocket messages go through, so the output is identical in
shape, limits and persistence. Nothing here is visible to clients.
"""
import asyncio
import logging
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import Player, SessionRunner

log = logging.getLogger("uvicorn.error")

OPENING = "hey everyone"
LINES = [
    "so how do we decide who should be the decision maker?",
    "i'm fine with anyone honestly, as long as we agree",
    "what do you two think?",
    "{peer} has been pretty clear so far, i'd go with them",
    "i think {peer} would be a good pick",
    "makes sense to me",
    "yeah i agree, let's not overthink it",
    "does anyone have a strong preference?",
    "{peer} seems reasonable, any objections?",
]  # plus OPENING = 10 lines in total

# Real timing (60 s rounds, 20 s votes). Scaled down for short test rounds.
MESSAGE_GAP_S = (2.0, 9.0)
MESSAGES_PER_ROUND = (2, 4)
VOTE_DELAY_S = (1.0, 6.0)


def _compose(runner: "SessionRunner", me: "Player") -> str:
    mine = {m["content"] for m in runner.messages if m["sender"] == me.label}
    first_ever = not mine
    options = [line for line in LINES if line not in mine]
    greeted = any(m["content"] == OPENING for m in runner.messages)  # never two identical greetings
    if first_ever and runner.round_no == 1 and not greeted and random.random() < 0.5:
        return OPENING
    peer = random.choice([label for label in runner.labels if label != me.label])
    return random.choice(options or LINES).format(peer=peer)


def _choose(runner: "SessionRunner", me: "Player") -> str:
    """Weighted random vote: more active participants are slightly more likely, self is less likely."""
    round_no = runner.round_no
    weights = []
    for label in runner.labels:
        w = 1.0 + sum(1 for m in runner.messages if m["round"] == round_no and m["sender"] == label)
        if runner.feedback:
            w += runner.feedback["tally"].get(label, 0)
        if label == me.label:
            w *= 0.5
        weights.append(w)
    return random.choices(runner.labels, weights=weights)[0]


async def play_phase(runner: "SessionRunner", me: "Player") -> None:
    phase, round_no = runner.phase, runner.round_no
    try:
        if phase == "round":
            scale = min(1.0, runner.cfg.round_seconds / 60)
            for _ in range(random.randint(*MESSAGES_PER_ROUND)):
                await asyncio.sleep(random.uniform(*MESSAGE_GAP_S) * scale)
                if runner.phase != "round" or runner.round_no != round_no:
                    return
                await runner.submit_message(me, _compose(runner, me))
        elif phase == "vote":
            scale = min(1.0, runner.cfg.vote_seconds / 20)
            await asyncio.sleep(random.uniform(*VOTE_DELAY_S) * scale)
            if runner.phase != "vote" or runner.round_no != round_no:
                return
            await runner.submit_vote(me, _choose(runner, me))
    except asyncio.CancelledError:
        raise
    except Exception:
        log.exception("ai participant failed")
