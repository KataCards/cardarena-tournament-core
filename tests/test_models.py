from cardarena_tournament_core.models import MatchupOutcome, Matchup, Player, PlayerStanding, Round


def test_player_fields():
    p = Player(id="p1", name="Alice")
    assert p.id == "p1"
    assert p.name == "Alice"


def test_matchup_default_outcome_is_pending():
    p1, p2 = Player(id="p1", name="A"), Player(id="p2", name="B")
    m = Matchup(player1=p1, player2=p2)
    assert m.outcome == MatchupOutcome.PENDING


def test_matchup_bye_accepts_none_player2():
    p = Player(id="p1", name="A")
    m = Matchup(player1=p, player2=None)
    assert m.player2 is None


def test_round_default_empty_matchups():
    r = Round(round_number=1)
    assert r.matchups == []


def test_round_accepts_matchups():
    p1, p2 = Player(id="p1", name="A"), Player(id="p2", name="B")
    r = Round(round_number=1, matchups=[Matchup(player1=p1, player2=p2)])
    assert len(r.matchups) == 1


def test_player_standing_fields():
    p = Player(id="p1", name="A")
    s = PlayerStanding(player=p, points=6, rank=1, tiebreakers={"owp": 0.65})
    assert s.points == 6
    assert s.tiebreakers["owp"] == 0.65


def test_player_standing_default_tiebreakers():
    p = Player(id="p1", name="A")
    s = PlayerStanding(player=p, points=0, rank=1)
    assert s.tiebreakers == {}
