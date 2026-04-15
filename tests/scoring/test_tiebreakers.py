from cardarena_tournament_core.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core.scoring.tiebreakers import (
    calculate_oowp,
    calculate_owp,
    win_percentage,
)


def _rounds() -> list[Round]:
    """4 players, 2 rounds.
    Round 1: P0 beats P1, P2 beats P3
    Round 2: P0 beats P3, P1 beats P2

    Records (excluding byes):
      P0: 2W → win%=1.0
      P1: 1W1L → win%=0.5
      P2: 1W1L → win%=0.5
      P3: 0W2L → win%=0.0 → floored to 0.25
    """
    p0, p1, p2, p3 = [Player(id=str(i), name=f"P{i}") for i in range(4)]
    r1 = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p2, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
        ],
    )
    r2 = Round(
        round_number=2,
        matchups=[
            Matchup(player1=p0, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
        ],
    )
    return [r1, r2]


def test_win_percentage_undefeated():
    rounds = _rounds()
    assert win_percentage("0", rounds) == 1.0


def test_win_percentage_one_win_one_loss():
    rounds = _rounds()
    assert abs(win_percentage("1", rounds) - 0.5) < 0.0001


def test_win_percentage_no_wins_floored():
    rounds = _rounds()
    assert win_percentage("3", rounds) == 0.25


def test_win_percentage_with_draw():
    p0, p1 = Player(id="0", name="P0"), Player(id="1", name="P1")
    rounds = [
        Round(
            round_number=1,
            matchups=[Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.DRAW)],
        )
    ]
    # 0.5 wins / 1 game = 0.5
    assert abs(win_percentage("0", rounds) - 0.5) < 0.0001


def test_win_percentage_excludes_byes():
    p0, p1 = Player(id="0", name="P0"), Player(id="1", name="P1")
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=None),  # bye — excluded
                Matchup(player1=p1, player2=None),
            ],
        )
    ]
    # No real games played → returns floor
    assert win_percentage("0", rounds) == 0.25


def test_owp_calculation():
    rounds = _rounds()
    # P0's opponents: P1 (0.5), P3 (0.25) → OWP = 0.375
    assert abs(calculate_owp("0", rounds) - 0.375) < 0.0001


def test_owp_opponent_excludes_byes():
    p0, p1, p2 = [Player(id=str(i), name=f"P{i}") for i in range(3)]
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
                Matchup(player1=p2, player2=None),  # P2 gets bye — not P0's opponent
            ],
        )
    ]
    # P0's only real opponent is P1; P2 (bye) should not appear in P0's OWP
    owp = calculate_owp("0", rounds)
    # P1: 0W1L → win%=0.25 (floored)
    assert abs(owp - 0.25) < 0.0001


def test_oowp_calculation():
    rounds = _rounds()
    # P0's opponents: P1, P3
    # P1's OWP = avg(P0 win%=1.0, P2 win%=0.5) = 0.75
    # P3's OWP = avg(P2 win%=0.5, P0 win%=1.0) = 0.75
    # P0's OOWP = avg(0.75, 0.75) = 0.75
    assert abs(calculate_oowp("0", rounds) - 0.75) < 0.0001