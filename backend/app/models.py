"""Database schema. Rules are enforced here (UNIQUE / CHECK / FK), not only in code.

Deliberately simple: single-column FKs, no relationships, no composite FKs.
"Voter/candidate/author belongs to the same session" is checked in repo.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExperimentSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('waiting', 'running', 'finished', 'aborted')",
            name="ck_sessions_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(16), default="waiting", server_default="waiting")
    condition: Mapped[str] = mapped_column(String(16))  # e.g. "1H+2AI"; server-side only
    config_snapshot: Mapped[dict] = mapped_column(JSONB)  # config.yml as run, for reproducibility
    # use_alter: sessions <-> participants reference each other, so this FK is added after both tables exist.
    winner_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("participants.id", use_alter=True, name="fk_sessions_winner"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Participant(Base):
    """A row exists only after the participant joined (humans and AI alike)."""

    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("session_id", "slot", name="uq_participants_session_slot"),
        UniqueConstraint("session_id", "label", name="uq_participants_session_label"),
        CheckConstraint("slot BETWEEN 0 AND 2", name="ck_participants_slot"),
        CheckConstraint("kind IN ('human', 'ai')", name="ck_participants_kind"),
        # A human always has a token; only AI rows may lack one.
        CheckConstraint("kind = 'ai' OR token_hash IS NOT NULL", name="ck_participants_human_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    slot: Mapped[int] = mapped_column(SmallInteger)  # position in config.yml participants list
    label: Mapped[str] = mapped_column(String(16))  # "Player A".."Player C" (shuffled per session)
    kind: Mapped[str] = mapped_column(String(8))  # "human" | "ai". Stored for analysis, NEVER sent to clients.
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # sha256 hex of the join token
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("round BETWEEN 1 AND 2", name="ck_messages_round"),
        CheckConstraint("char_length(content) BETWEEN 1 AND 500", name="ck_messages_content_len"),
        Index("ix_messages_session_round_created", "session_id", "round", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    round: Mapped[int] = mapped_column(SmallInteger)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        # The core rule: one vote per participant per round.
        UniqueConstraint("session_id", "round", "voter_id", name="uq_votes_one_per_voter_round"),
        CheckConstraint("round BETWEEN 1 AND 2", name="ck_votes_round"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    round: Mapped[int] = mapped_column(SmallInteger)
    voter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"))  # self-vote allowed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
