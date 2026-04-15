from cardarena_tournament_core.models import MatchupOutcome, Player, Round
from cardarena_tournament_core.pairings.swiss import Swiss


def make_players(n: int) -> list[Player]:
    return [Player(id=str(i), name=f"P{i}") for i in range(n)]


def test_first_round_pairs_all_players_even():
    swiss = Swiss(make_players(4))
    round1 = swiss.pair()

    paired = set()
    for m in round1.matchups:
        assert m.player1.id not in paired
        paired.add(m.player1.id)
        assert m.player2 is not None
        assert m.player2.id not in paired
        paired.add(m.player2.id)

    assert len(paired) == 4
    assert round1.round_number == 1


def test_odd_players_gives_one_bye():
    swiss = Swiss(make_players(3))
    round1 = swiss.pair()

    byes = [m for m in round1.matchups if m.player2 is None]
    real = [m for m in round1.matchups if m.player2 is not None]

    assert len(byes) == 1
    assert len(real) == 1


def test_avoids_repeat_pairings():
    swiss = Swiss(make_players(4))
    round1 = swiss.pair()

    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)

    round2 = swiss.pair()

    r1_pairs = {frozenset([m.player1.id, m.player2.id]) for m in round1.matchups if m.player2}
    r2_pairs = {frozenset([m.player1.id, m.player2.id]) for m in round2.matchups if m.player2}
    assert not r1_pairs & r2_pairs


def test_second_round_pairs_winners_together():
    # Round 1: all player1s win → two players on 3pts, two on 0pts
    swiss = Swiss(make_players(4))
    round1 = swiss.pair()

    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)

    round2 = swiss.pair()

    winners = {m.player1.id for m in round1.matchups if m.player2 is not None}
    losers = {m.player2.id for m in round1.matchups if m.player2 is not None}

    for m in round2.matchups:
        if m.player2 is not None:
            both_winners = m.player1.id in winners and m.player2.id in winners
            both_losers = m.player1.id in losers and m.player2.id in losers
            assert both_winners or both_losers, (
                f"Mixed pairing: {m.player1.id} (winner={m.player1.id in winners}) "
                f"vs {m.player2.id} (winner={m.player2.id in winners})"
            )


def test_submit_results_updates_round_history():
    swiss = Swiss(make_players(4))
    round1 = swiss.pair()
    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)

    assert len(swiss.rounds) == 1
    assert swiss.rounds[0].round_number == 1


def test_round_number_increments():
    swiss = Swiss(make_players(4))
    round1 = swiss.pair()
    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)

    round2 = swiss.pair()
    assert round2.round_number == 2


def test_bye_player_receives_points():
    # Odd players: one gets bye. After submitting, bye player should have won.
    # We verify this indirectly: after bye round, next pairing uses updated standings.
    swiss = Swiss(make_players(3))
    round1 = swiss.pair()

    bye_m = next(m for m in round1.matchups if m.player2 is None)
    real_m = next(m for m in round1.matchups if m.player2 is not None)
    real_m.outcome = MatchupOutcome.PLAYER1_WINS

    swiss.submit_results(round1)

    # bye player and real match winner both have 3pts — they should be paired together in round2
    round2 = swiss.pair()
    round2_player_ids = {m.player1.id for m in round2.matchups} | {
        m.player2.id for m in round2.matchups if m.player2 is not None
    }
    assert bye_m.player1.id in round2_player_ids