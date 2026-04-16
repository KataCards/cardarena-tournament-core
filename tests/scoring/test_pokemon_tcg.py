from cardarena_tournament_core.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core.scoring.pokemon import PokemonTCG


def _two_player_round(outcome: MatchupOutcome) -> list[Round]:
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    return [Round(round_number=1, matchups=[Matchup(player1=p1, player2=p2, outcome=outcome)])]


def test_win_gives_3_points():
    standings = PokemonTCG().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))
    winner = next(s for s in standings if s.player.id == "p1")
    loser = next(s for s in standings if s.player.id == "p2")
    assert winner.points == 3
    assert loser.points == 0


def test_draw_gives_1_point_each():
    standings = PokemonTCG().calculate(_two_player_round(MatchupOutcome.DRAW))
    assert all(s.points == 1 for s in standings)


def test_loss_gives_0_points():
    standings = PokemonTCG().calculate(_two_player_round(MatchupOutcome.PLAYER2_WINS))
    winner = next(s for s in standings if s.player.id == "p2")
    loser = next(s for s in standings if s.player.id == "p1")
    assert winner.points == 3
    assert loser.points == 0


def test_bye_gives_3_points():
    p = Player(id="p1", name="Alice")
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p, player2=None)])]
    standings = PokemonTCG().calculate(rounds)
    assert standings[0].points == 3


def test_standings_sorted_by_points_descending():
    standings = PokemonTCG().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))
    assert standings[0].points >= standings[1].points


def test_standings_include_owp_and_oowp():
    standings = PokemonTCG().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))
    for s in standings:
        assert "owp" in s.tiebreakers
        assert "oowp" in s.tiebreakers


def test_standings_ranked_1_indexed():
    standings = PokemonTCG().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))
    assert standings[0].rank == 1
    assert standings[1].rank == 2


def test_owp_tiebreak_used_when_points_tied():
    """Two players with equal points: higher OWP wins the tiebreak."""
    # P0 beats P1 and P3; P2 beats P1 and P3 → P0 and P2 both on 6pts
    # P0's opponents: P1 (1W1L → 0.5), P3 (0W2L → 0.25) → OWP=0.375
    # P2's opponents: P1 (1W1L → 0.5), P3 (0W2L → 0.25) → OWP=0.375  (same — need asymmetric setup)
    # Use asymmetric setup instead:
    # Round 1: P0 beats P1, P2 beats P3
    # Round 2: P0 beats P2, P1 beats P3
    # P0: 2W=6pts. P1: 1W1L=3pts. P2: 1W1L=3pts. P3: 0W2L=0pts.
    # P1 opponents: P0(1.0), P3(0.25) → OWP=0.625
    # P2 opponents: P3(0.25), P0(1.0) → OWP=0.625  (same again)
    # Use: Round 1: P0 beats P1, P2 beats P3 / Round 2: P1 beats P2, P0 beats P3
    p0, p1, p2, p3 = [Player(id=str(i), name=f"P{i}") for i in range(4)]
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
                Matchup(player1=p2, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
        Round(
            round_number=2,
            matchups=[
                Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
                Matchup(player1=p0, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
    ]
    # P0: 6pts. P1: 3pts (beat P2, lost to P0). P2: 3pts (beat P3, lost to P1). P3: 0pts.
    # P1 OWP: avg(P0 win%=1.0, P2 win%=0.5) = 0.75
    # P2 OWP: avg(P3 win%=0.25, P1 win%=0.5) = 0.375
    standings = PokemonTCG().calculate(rounds)
    p1_standing = next(s for s in standings if s.player.id == "1")
    p2_standing = next(s for s in standings if s.player.id == "2")
    # Both 3pts, but P1 has higher OWP (0.75 > 0.375) → P1 ranked above P2
    assert p1_standing.rank < p2_standing.rank


def test_bye_excluded_from_tiebreakers():
    """A bye should not appear as an opponent in OWP/OOWP."""
    p0, p1 = Player(id="0", name="P0"), Player(id="1", name="P1")
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=None),  # P0 gets bye
                Matchup(player1=p1, player2=None),  # P1 gets bye
            ],
        )
    ]
    standings = PokemonTCG().calculate(rounds)
    for s in standings:
        # No real opponents → OWP should be 0.0 (no opponents to average)
        assert s.tiebreakers["owp"] == 0.0
        assert s.tiebreakers["oowp"] == 0.0


def test_calculate_empty_rounds_returns_empty():
    assert PokemonTCG().calculate([]) == []