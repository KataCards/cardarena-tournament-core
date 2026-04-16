import pytest

from cardarena_tournament_core.models import MatchupOutcome, Player, TournamentCompleteError
from cardarena_tournament_core.pairings.elimination import SingleElimination


def make_players(n: int) -> list[Player]:
    return [Player(id=str(i), name=f"P{i}") for i in range(n)]


def test_first_round_4_players_produces_2_matchups():
    elim = SingleElimination(make_players(4))
    r = elim.pair()
    real = [m for m in r.matchups if m.player2 is not None]
    assert len(real) == 2


def test_first_round_seeded_1v4_2v3():
    players = make_players(4)
    elim = SingleElimination(players)
    r = elim.pair()

    pairs = {frozenset([m.player1.id, m.player2.id]) for m in r.matchups if m.player2}
    assert frozenset(["0", "3"]) in pairs  # P0 (seed 1) vs P3 (seed 4)
    assert frozenset(["1", "2"]) in pairs  # P1 (seed 2) vs P2 (seed 3)


def test_winners_advance_to_next_round():
    players = make_players(4)
    elim = SingleElimination(players)
    r1 = elim.pair()

    # P0 and P1 win
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    r2 = elim.pair()
    assert len(r2.matchups) == 1

    r1_winners = {m.player1.id for m in r1.matchups if m.player2 is not None}
    r2_player_ids = {r2.matchups[0].player1.id, r2.matchups[0].player2.id} # type: ignore
    assert r2_player_ids == r1_winners


def test_odd_players_gives_bye():
    elim = SingleElimination(make_players(5))
    r = elim.pair()

    byes = [m for m in r.matchups if m.player2 is None]
    assert len(byes) == 1


def test_bye_player_advances_automatically():
    players = make_players(3)  # P0 vs P2, P1 gets bye
    elim = SingleElimination(players)
    r1 = elim.pair()

    real_m = next(m for m in r1.matchups if m.player2 is not None)
    real_m.outcome = MatchupOutcome.PLAYER1_WINS  # winner of real match advances
    elim.submit_results(r1)

    r2 = elim.pair()
    r2_player_ids = {r2.matchups[0].player1.id}
    if r2.matchups[0].player2 is not None:
        r2_player_ids.add(r2.matchups[0].player2.id)

    # Bye player and real-match winner should both be in round 2
    bye_m = next(m for m in r1.matchups if m.player2 is None)
    assert bye_m.player1.id in r2_player_ids
    assert real_m.player1.id in r2_player_ids


def test_tournament_complete_error_when_champion_found():
    players = make_players(2)
    elim = SingleElimination(players)
    r1 = elim.pair()
    r1.matchups[0].outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    with pytest.raises(TournamentCompleteError):
        elim.pair()


def test_tournament_complete_error_single_player():
    elim = SingleElimination(make_players(1))

    with pytest.raises(TournamentCompleteError):
        elim.pair()


def test_round_numbers_increment():
    elim = SingleElimination(make_players(4))
    r1 = elim.pair()
    assert r1.round_number == 1
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)
    r2 = elim.pair()
    assert r2.round_number == 2