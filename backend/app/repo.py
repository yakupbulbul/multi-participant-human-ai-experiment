"""Small data-access functions. They flush but never commit: the caller owns the transaction.

Same-session membership (voter/candidate/author belong to the session) is checked
here, not in the database, to keep the schema simple. See README trade-offs.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as m


async def create_session(db: AsyncSession, condition: str, config_snapshot: dict) -> m.ExperimentSession:
    row = m.ExperimentSession(condition=condition, config_snapshot=config_snapshot)
    db.add(row)
    await db.flush()
    return row


async def add_participant(
    db: AsyncSession,
    session_id: uuid.UUID,
    slot: int,
    label: str,
    kind: str,
    token_hash: str | None = None,
) -> m.Participant:
    row = m.Participant(session_id=session_id, slot=slot, label=label, kind=kind, token_hash=token_hash)
    db.add(row)
    await db.flush()  # constraint violations (duplicate slot/label, human without token) raise here
    return row


async def delete_participant(db: AsyncSession, participant_id: uuid.UUID) -> None:
    """Only used when someone leaves the waiting room (no messages or votes exist yet)."""
    await db.execute(delete(m.Participant).where(m.Participant.id == participant_id))


async def _require_member(db: AsyncSession, session_id: uuid.UUID, participant_id: uuid.UUID) -> None:
    found = await db.scalar(
        select(m.Participant.id).where(
            m.Participant.id == participant_id, m.Participant.session_id == session_id
        )
    )
    if found is None:
        raise ValueError("participant does not belong to this session")


async def add_message(
    db: AsyncSession, session_id: uuid.UUID, round_no: int, participant_id: uuid.UUID, content: str
) -> m.Message:
    await _require_member(db, session_id, participant_id)
    row = m.Message(session_id=session_id, round=round_no, participant_id=participant_id, content=content)
    db.add(row)
    await db.flush()
    return row


async def add_vote(
    db: AsyncSession, session_id: uuid.UUID, round_no: int, voter_id: uuid.UUID, candidate_id: uuid.UUID
) -> m.Vote:
    """A second vote by the same voter in the same round raises IntegrityError (UNIQUE constraint)."""
    await _require_member(db, session_id, voter_id)
    await _require_member(db, session_id, candidate_id)
    row = m.Vote(session_id=session_id, round=round_no, voter_id=voter_id, candidate_id=candidate_id)
    db.add(row)
    await db.flush()
    return row


async def set_status(
    db: AsyncSession, session_id: uuid.UUID, status: str, winner_id: uuid.UUID | None = None
) -> None:
    row = await db.get(m.ExperimentSession, session_id)
    if row is None:
        raise ValueError("unknown session")
    row.status = status
    now = datetime.now(timezone.utc)
    if status == "running":
        row.started_at = now
    elif status in ("finished", "aborted"):
        row.finished_at = now
    if winner_id is not None:
        row.winner_participant_id = winner_id
    await db.flush()


async def get_participants(db: AsyncSession, session_id: uuid.UUID) -> list[m.Participant]:
    result = await db.scalars(
        select(m.Participant).where(m.Participant.session_id == session_id).order_by(m.Participant.created_at)
    )
    return list(result)


async def get_messages(db: AsyncSession, session_id: uuid.UUID, round_no: int | None = None) -> list[m.Message]:
    stmt = select(m.Message).where(m.Message.session_id == session_id).order_by(m.Message.id)
    if round_no is not None:
        stmt = stmt.where(m.Message.round == round_no)
    return list(await db.scalars(stmt))


async def get_votes(db: AsyncSession, session_id: uuid.UUID, round_no: int | None = None) -> list[m.Vote]:
    stmt = select(m.Vote).where(m.Vote.session_id == session_id).order_by(m.Vote.id)
    if round_no is not None:
        stmt = stmt.where(m.Vote.round == round_no)
    return list(await db.scalars(stmt))
