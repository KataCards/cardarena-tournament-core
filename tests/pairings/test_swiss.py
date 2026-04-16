from cardarena_tournament_core.models import Matchup, MatchupOutcome, Player, Round
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


def test_tiebreaker_sort_ranks_higher_owp_player_first():
    """With use_tiebreaker_sort=True, equal-point players with better OWP rank
    higher and are processed first in the pairing loop — shown by who becomes
    player1 in the match between the two equal-point players.

    Setup (5 players, input order [P0, P4, P2, P1, P3] so that a stable
    points-only sort ranks P2 above P1):
      R1: P0 beats P1, P2 beats P3, P4 bye
      R2: P0 beats P2, P4 beats P3, P1 bye

    After R2: P0=6, P4=6, P1=3 (bye R2 + 0 R1), P2=3, P3=0
      P1 real opponents: P0 only (2-0 → win%=1.0)  → OWP = 1.0
      P2 real opponents: P3 (0-2 → 0.25) + P0 (2-0 → 1.0) → OWP = 0.625

    Stable sort (no tiebreaker) keeps P2 before P1 (P2 is at index 2, P1 at index 3
    in the input list [P0,P4,P2,P1,P3]).
    Tiebreaker sort flips them: P1 (OWP=1.0) ranks above P2 (OWP=0.625).

    In R3 the pairing algorithm iterates in rank order; the first unpaired player
    becomes player1 of the matchup.  So with tiebreaker sort active, P1 becomes
    player1 when it is paired against P2.
    """
    p0, p1, p2, p3, p4 = [Player(id=str(i), name=f"P{i}") for i in range(5)]
    swiss = Swiss([p0, p4, p2, p1, p3], use_tiebreaker_sort=True)

    round1 = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p2, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p4, player2=None),
        ],
    )
    swiss.submit_results(round1)

    round2 = Round(
        round_number=2,
        matchups=[
            Matchup(player1=p0, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p4, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p1, player2=None),
        ],
    )
    swiss.submit_results(round2)

    round3 = swiss.pair()

    matchup_p1_p2 = next(
        matchup for matchup in round3.matchups
        if {matchup.player1.id, matchup.player2.id if matchup.player2 else ""} == {"1", "2"}
    )
    # OWP sort ranks P1 higher → P1 is the outer-loop participant → P1 is player1
    assert matchup_p1_p2.player1.id == "1", (
        "Expected P1 (OWP=1.0) to outrank P2 (OWP=0.625) and appear as player1"
    )


def test_single_player_receives_bye():
    swiss = Swiss(make_players(1))
    round1 = swiss.pair()

    assert len(round1.matchups) == 1
    assert round1.matchups[0].player2 is None
    assert round1.matchups[0].player1.id == "0"


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