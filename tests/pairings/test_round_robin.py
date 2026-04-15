from itertools import combinations

from cardarena_tournament_core.models import MatchupOutcome, Player
from cardarena_tournament_core.pairings.round_robin import RoundRobin


def make_players(n: int) -> list[Player]:
    return [Player(id=str(i), name=f"P{i}") for i in range(n)]


def test_round_robin_4_players_produces_3_rounds():
    rr = RoundRobin(make_players(4))
    rounds = []
    for _ in range(3):
        r = rr.pair()
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
        rr.submit_results(r)

    expected = {frozenset([str(i), str(j)]) for i, j in combinations(range(4), 2)}
    assert all_pairs == expected


def test_round_robin_odd_players_gives_byes():
    rr = RoundRobin(make_players(3))  # 3 players → padded to 4 with bye slot

    for _ in range(3):
        r = rr.pair()
        rr.submit_results(r)
        # Each round has exactly one bye
        byes = [m for m in r.matchups if m.player2 is None]
        assert len(byes) == 1


def test_round_robin_round_numbers_increment():
    rr = RoundRobin(make_players(4))
    for expected_num in range(1, 4):
        r = rr.pair()
        assert r.round_number == expected_num
        rr.submit_results(r)


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
        rr.submit_results(r)

    expected = {frozenset([str(i), str(j)]) for i, j in combinations(range(5), 2)}
    assert all_pairs == expected