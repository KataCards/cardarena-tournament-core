from cardarena_tournament_core.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core.scoring.yugioh import YuGiOh


def _two_player_round(outcome: MatchupOutcome) -> list[Round]:
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    return [Round(round_number=1, matchups=[Matchup(player1=p1, player2=p2, outcome=outcome)])]


def test_win_gives_3_points():
    standings = YuGiOh().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))
    winner = next(s for s in standings if s.player.id == "p1")
    loser = next(s for s in standings if s.player.id == "p2")
    assert winner.points == 3
    assert loser.points == 0


def test_draw_gives_1_point_each():
    standings = YuGiOh().calculate(_two_player_round(MatchupOutcome.DRAW))
    assert all(s.points == 1 for s in standings)


def test_bye_gives_3_points():
    p = Player(id="p1", name="Alice")
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p, player2=None)])]
    standings = YuGiOh().calculate(rounds)
    assert standings[0].points == 3


def test_standings_include_tiebreakers():
    """Yu-Gi-Oh! standings should include owp and oowp tiebreakers."""
    standings = YuGiOh().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))
    for s in standings:
        assert "owp" in s.tiebreakers
        assert "oowp" in s.tiebreakers
        # tiebreak_number was removed - now using Pythonic tuple sorting
        assert "tiebreak_number" not in s.tiebreakers


def test_owp_calculation():
    """Test OWP (Opponents' Win Percentage) calculation.
    
    OWP is the average win percentage of all opponents faced.
    """
    # Simple 4-player scenario
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
                Matchup(player1=p0, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
                Matchup(player1=p1, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
    ]
    
    # P0: 2-0 (beat P1, P2) = 6 points
    # P1: 1-1 (lost to P0, beat P3) = 3 points
    # P2: 1-1 (beat P3, lost to P0) = 3 points
    # P3: 0-2 (lost to P2, P1) = 0 points
    
    standings = YuGiOh().calculate(rounds)
    p0_standing = next(s for s in standings if s.player.id == "0")
    
    # P0 has 6 points
    assert p0_standing.points == 6
    
    # P0's opponents: P1 (1-1 = 0.5), P2 (1-1 = 0.5)
    # OWP = (0.5 + 0.5) / 2 = 0.5
    assert abs(p0_standing.tiebreakers["owp"] - 0.5) < 0.01


def test_owp_breaks_ties():
    """Two players with same points: higher OWP wins."""
    # Create scenario where two players have same points but different opponent strength
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
    
    # P0: 6pts (beat P1, P3). P1: 3pts (beat P2). P2: 3pts (beat P3). P3: 0pts.
    # P1 opponents: P0 (2-0=1.0), P2 (1-1=0.5) → OWP = 0.75
    # P2 opponents: P3 (0-2=0.25), P1 (1-1=0.5) → OWP = 0.375
    
    standings = YuGiOh().calculate(rounds)
    p1_standing = next(s for s in standings if s.player.id == "1")
    p2_standing = next(s for s in standings if s.player.id == "2")
    
    # Both have 3 points
    assert p1_standing.points == 3
    assert p2_standing.points == 3
    
    # P1 should rank higher due to better OWP
    assert p1_standing.rank < p2_standing.rank
    assert p1_standing.tiebreakers["owp"] > p2_standing.tiebreakers["owp"]


def test_tiebreaker_values_are_floats():
    """OWP and OOWP should be float values between 0.0 and 1.0."""
    p0, p1 = Player(id="0", name="P0"), Player(id="1", name="P1")
    rounds = [
        Round(
            round_number=1,
            matchups=[Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS)],
        )
    ]
    
    standings = YuGiOh().calculate(rounds)
    for s in standings:
        owp = s.tiebreakers["owp"]
        oowp = s.tiebreakers["oowp"]
        # Should be floats between 0.0 and 1.0
        assert isinstance(owp, float)
        assert isinstance(oowp, float)
        assert 0.0 <= owp <= 1.0
        assert 0.0 <= oowp <= 1.0


def test_bye_excluded_from_tiebreakers():
    """Byes should not affect tiebreak calculations."""
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
    
    standings = YuGiOh().calculate(rounds)
    for s in standings:
        # Each player has 3 points from bye
        assert s.points == 3
        # No real opponents → OWP and OOWP should be 0.0
        assert s.tiebreakers["owp"] == 0.0
        assert s.tiebreakers["oowp"] == 0.0


def test_standings_sorted_by_points_then_owp_then_oowp():
    """Standings should be sorted by points (desc), then OWP (desc), then OOWP (desc)."""
    standings = YuGiOh().calculate(_two_player_round(MatchupOutcome.PLAYER1_WINS))

    # Winner should be ranked 1st
    assert standings[0].points >= standings[1].points

    # If points are equal, higher OWP should rank higher
    if standings[0].points == standings[1].points:
        assert standings[0].tiebreakers["owp"] >= standings[1].tiebreakers["owp"]
        # If OWP is also equal, higher OOWP should rank higher
        if standings[0].tiebreakers["owp"] == standings[1].tiebreakers["owp"]:
            assert standings[0].tiebreakers["oowp"] >= standings[1].tiebreakers["oowp"]


def test_calculate_empty_rounds_returns_empty():
    assert YuGiOh().calculate([]) == []