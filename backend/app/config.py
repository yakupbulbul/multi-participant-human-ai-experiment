"""Load and validate config.yml. Fails fast at startup on any invalid value."""
import os
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ParticipantKind = Literal["human", "ai"]


class VotingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule: Literal["sum", "last_round"] = "sum"


class AiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["scripted"] = "scripted"  # an LLM mode is out of scope for the 4-hour limit
    join_delay_s: tuple[float, float] = (2.0, 12.0)

    @field_validator("join_delay_s")
    @classmethod
    def _delay_range(cls, v: tuple[float, float]) -> tuple[float, float]:
        if v[0] < 0 or v[0] > v[1]:
            raise ValueError("join_delay_s must be [min, max] with 0 <= min <= max")
        return v


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participants: list[ParticipantKind]
    rounds: Literal[2] = 2
    round_seconds: int = Field(60, ge=1)
    vote_seconds: int = Field(20, ge=1)
    disconnect_grace_s: int = Field(30, ge=1)  # a human gone longer than this aborts the session
    voting: VotingConfig = VotingConfig()
    ai: AiConfig = AiConfig()

    @model_validator(mode="after")
    def _check_participants(self) -> "ExperimentConfig":
        if len(self.participants) != 3:
            raise ValueError("participants must have exactly 3 entries")
        if "human" not in self.participants:
            raise ValueError("participants must include at least one human")
        return self

    @property
    def human_count(self) -> int:
        return self.participants.count("human")


def load_config(path: str | None = None) -> ExperimentConfig:
    path = path or os.environ.get("CONFIG_PATH", "config.yml")
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ExperimentConfig.model_validate(raw)
