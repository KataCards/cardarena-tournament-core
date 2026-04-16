from itertools import combinations

import pytest

from cardarena_tournament_core.common.errors import TournamentCompleteError
from cardarena_tournament_core.common.models import MatchupOutcome, Player, Round
from cardarena_tournament_core.pairings.round_robin import RoundRobin


def make_players(n: int) -> list[Player]:
    return [Player(id=str(i), name=f"P{i}") for i in range(n)]


def complete_round(round_: Round) -> None:
    for matchup in round_.matchups:
        if matchup.player2 is not None:
            matchup.outcome = MatchupOutcome.PLAYER1_WINS


def test_round_robin_4_players_produces_3_rounds():
    rr = RoundRobin(make_players(4))
    rounds = []
    for _ in range(3):
        r = rr.pair()
        complete_round(r)
        rr.submit_results(r)
        rounds.append(r)
    assert len(rounds) == 3


def test_round_robin_each_pair_plays_exactly_once():
    players = make_players(4)
    rr = RoundRobin(players)

    all_pairs: set[frozenset[str]] = set()
    for _ in range(3):
        r = rr.pair()
        for m in r.matchups:
            if m.player2 is not None:
                pair = frozenset([m.player1.id, m.player2.id])
                assert pair not in all_pairs, f"Duplicate pairing: {pair}"
                all_pairs.add(pair)
        complete_round(r)
        rr.submit_results(r)

    expected = {frozenset([str(i), str(j)]) for i, j in combinations(range(4), 2)}
    assert all_pairs == expected


def test_round_robin_odd_players_gives_byes():
    rr = RoundRobin(make_players(3))  # 3 players → padded to 4 with bye slot

    for _ in range(3):
        r = rr.pair()
        complete_round(r)
        rr.submit_results(r)
        # Each round has exactly one bye
        byes = [m for m in r.matchups if m.player2 is None]
        assert len(byes) == 1


def test_round_robin_round_numbers_increment():
    rr = RoundRobin(make_players(4))
    for expected_num in range(1, 4):
        r = rr.pair()
        assert r.round_number == expected_num
        complete_round(r)
        rr.submit_results(r)


def test_tournament_complete_error_after_schedule_exhausted():
    rr = RoundRobin(make_players(4))
    for _ in range(3):
        r = rr.pair()
        complete_round(r)
        rr.submit_results(r)

    with pytest.raises(TournamentCompleteError):
        rr.pair()


def test_round_robin_5_players_each_pair_once():
    players = make_players(5)
    rr = RoundRobin(players)

    all_pairs: set[frozenset[str]] = set()
    for _ in range(5):  # 5 players → 5 rounds (padded to 6 → 5 rounds)
        r = rr.pair()
        for m in r.matchups:
            if m.player2 is not None:
                pair = frozenset([m.player1.id, m.player2.id])
                assert pair not in all_pairs, f"Duplicate: {pair}"
                all_pairs.add(pair)
        complete_round(r)
        rr.submit_results(r)

    expected = {frozenset([str(i), str(j)]) for i, j in combinations(range(5), 2)}
    assert all_pairs == expected


def test_remove_active_participant_raises_with_clear_message():
    """Round Robin must reject removal because the schedule is pre-computed."""
    from cardarena_tournament_core.common.errors import PairingStateError
    rr = RoundRobin(make_players(4))
    with pytest.raises(PairingStateError, match="not supported for Round Robin"):
        rr.remove_active_participant("0")