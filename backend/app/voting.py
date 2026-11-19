"""Pure voting logic: no I/O, easy to unit test.

Rules (config.yml -> voting.rule):
  sum         votes of both rounds are added; ties -> round-2 votes -> seeded random.
  last_round  only round-2 votes count; ties -> seeded random.
Abstentions simply add no vote. The seed is the session id, so a tie-break is reproducible.
"""
import random
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Decision:
    winner: str
    totals: dict[str, int]  # the scores the rule used
    round_tallies: dict[int, dict[str, int]]
    decided_by_tiebreak: bool


def tally(votes: Iterable[str], labels: Sequence[str]) -> dict[str, int]:
    counts = Counter(votes)
    return {label: counts.get(label, 0) for label in labels}


def _leaders(scores: Mapping[str, int], among: Sequence[str]) -> list[str]:
    best = max(scores[label] for label in among)
    return [label for label in among if scores[label] == best]


def decide(
    round_votes: Mapping[int, Iterable[str]],
    labels: Sequence[str],
    rule: str,
    seed: str,
) -> Decision:
    """round_votes maps round number -> the candidate label of each cast vote."""
    rounds = {r: tally(votes, labels) for r, votes in round_votes.items()}
    round2 = rounds.get(2, tally([], labels))

    if rule == "sum":
        totals = {label: sum(t[label] for t in rounds.values()) for label in labels}
    elif rule == "last_round":
        totals = dict(round2)
    else:
        raise ValueError(f"unknown voting rule: {rule}")

    leaders = _leaders(totals, labels)
    decided_by_tiebreak = len(leaders) > 1
    if decided_by_tiebreak and rule == "sum":
        leaders = _leaders(round2, leaders)  # first tie-break: round-2 votes
    if len(leaders) > 1:
        leaders = [random.Random(seed).choice(sorted(leaders))]  # last tie-break: seeded random

    return Decision(leaders[0], totals, rounds, decided_by_tiebreak)
