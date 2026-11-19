"""Must-have test 1: decide() rules and tie-break (pure logic, no database)."""
import pytest

from app.voting import decide

LABELS = ["Player A", "Player B", "Player C"]
A, B, C = LABELS


def test_sum_rule_clear_winner_and_rules_can_disagree():
    votes = {1: [A, A, A], 2: [B, B, C]}
    by_sum = decide(votes, LABELS, "sum", seed="s")
    by_last = decide(votes, LABELS, "last_round", seed="s")
    assert by_sum.winner == A and by_sum.totals[A] == 3 and not by_sum.decided_by_tiebreak
    assert by_last.winner == B  # round 2 alone decides under last_round


def test_sum_rule_tie_is_broken_by_round_two_votes():
    d = decide({1: [A, A], 2: [B, B]}, LABELS, "sum", seed="s")  # A=2, B=2 overall
    assert d.winner == B and d.decided_by_tiebreak


@pytest.mark.parametrize("rule", ["sum", "last_round"])
def test_seeded_random_tiebreak_is_reproducible(rule):
    votes = {1: [A, B], 2: [A, B]}  # A and B tied in every way
    first = decide(votes, LABELS, rule, seed="session-1")
    assert first.decided_by_tiebreak and first.winner in (A, B)
    assert all(decide(votes, LABELS, rule, seed="session-1").winner == first.winner for _ in range(10))


@pytest.mark.parametrize("rule", ["sum", "last_round"])
def test_all_abstain_still_picks_a_winner(rule):
    d = decide({1: [], 2: []}, LABELS, rule, seed="s")
    assert d.winner in LABELS and d.decided_by_tiebreak
