"""Must-have test 2: the one-vote-per-participant-per-round rule lives in the database."""
import pytest
from sqlalchemy.exc import IntegrityError

from app import db, repo


def test_duplicate_vote_in_same_round_raises_integrity_error(run, schema):
    async def go() -> None:
        async with db.SessionLocal() as s:
            session = await repo.create_session(s, "1H+2AI", {})
            a = await repo.add_participant(s, session.id, 0, "Player A", "human", token_hash="t" * 64)
            b = await repo.add_participant(s, session.id, 1, "Player B", "ai")
            c = await repo.add_participant(s, session.id, 2, "Player C", "ai")

            await repo.add_vote(s, session.id, 1, a.id, b.id)
            with pytest.raises(IntegrityError):  # same voter, same round
                await repo.add_vote(s, session.id, 1, a.id, c.id)
            await s.rollback()  # nothing from this test is kept

    run(go())


def test_same_voter_may_vote_again_in_the_other_round(run, schema):
    async def go() -> None:
        async with db.SessionLocal() as s:
            session = await repo.create_session(s, "1H+2AI", {})
            a = await repo.add_participant(s, session.id, 0, "Player A", "human", token_hash="t" * 64)
            b = await repo.add_participant(s, session.id, 1, "Player B", "ai")
            await repo.add_vote(s, session.id, 1, a.id, b.id)
            await repo.add_vote(s, session.id, 2, a.id, b.id)  # different round: allowed
            assert len(await repo.get_votes(s, session.id)) == 2
            await s.rollback()

    run(go())
