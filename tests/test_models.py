"""Tests for core data models."""

import pytest

from cardarena_tournament_core.models import Matchup, MatchupOutcome, Player, Standing, Round, Team, TournamentCompleteError


# Player Tests
def test_player_fields():
    p = Player(id="p1", name="Alice")
    assert p.id == "p1"
    assert p.name == "Alice"


def test_player_empty_id_raises_error():
    with pytest.raises(ValueError, match="Player id cannot be empty"):
        Player(id="", name="Alice")


def test_player_empty_name_raises_error():
    with pytest.raises(ValueError, match="Player name cannot be empty"):
        Player(id="p1", name="")


# Team Tests
def test_team_fields():
    team = Team(id="team1", name="Dragon Slayers", members=("Alice", "Bob", "Carol"))
    assert team.id == "team1"
    assert team.name == "Dragon Slayers"
    assert team.members == ("Alice", "Bob", "Carol")


def test_team_empty_id_raises_error():
    with pytest.raises(ValueError, match="Team id cannot be empty"):
        Team(id="", name="Team", members=("Alice",))


def test_team_empty_name_raises_error():
    with pytest.raises(ValueError, match="Team name cannot be empty"):
        Team(id="t1", name="", members=("Alice",))


def test_team_empty_members_raises_error():
    with pytest.raises(ValueError, match="Team must have at least one member"):
        Team(id="t1", name="Team", members=())


# Matchup Tests
def test_matchup_default_outcome_is_pending():
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    m = Matchup(player1=p1, player2=p2)
    assert m.outcome == MatchupOutcome.PENDING


def test_matchup_bye_accepts_none_player2():
    p = Player(id="p1", name="Alice")
    m = Matchup(player1=p, player2=None)
    assert m.player2 is None


def test_matchup_is_bye_property():
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    regular = Matchup(player1=p1, player2=p2)
    bye = Matchup(player1=p1, player2=None)
    assert regular.is_bye is False
    assert bye.is_bye is True


def test_matchup_is_complete_property():
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    pending = Matchup(player1=p1, player2=p2)
    complete = Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS)
    assert pending.is_complete is False
    assert complete.is_complete is True


def test_matchup_cannot_match_player_against_self():
    p = Player(id="p1", name="Alice")
    with pytest.raises(ValueError, match="A participant cannot be matched against themselves"):
        Matchup(player1=p, player2=p)


# Round Tests
def test_round_default_empty_matchups():
    r = Round(round_number=1)
    assert r.matchups == []


def test_round_accepts_matchups():
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    m = Matchup(player1=p1, player2=p2)
    r = Round(round_number=1, matchups=[m])
    assert len(r.matchups) == 1


def test_round_number_must_be_positive():
    with pytest.raises(ValueError, match="round_number must be >= 1"):
        Round(round_number=0)


def test_round_is_complete_property():
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    p3, p4 = Player(id="p3", name="Carol"), Player(id="p4", name="Dave")
    
    incomplete = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p3, player2=p4),
        ],
    )
    complete = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p3, player2=p4, outcome=MatchupOutcome.DRAW),
        ],
    )
    assert incomplete.is_complete is False
    assert complete.is_complete is True


def test_round_get_player_matchup():
    p1, p2 = Player(id="p1", name="Alice"), Player(id="p2", name="Bob")
    p3, p4 = Player(id="p3", name="Carol"), Player(id="p4", name="Dave")
    
    m1 = Matchup(player1=p1, player2=p2)
    m2 = Matchup(player1=p3, player2=p4)
    r = Round(round_number=1, matchups=[m1, m2])
    
    assert r.get_player_matchup("p1") == m1
    assert r.get_player_matchup("p2") == m1
    assert r.get_player_matchup("p3") == m2
    assert r.get_player_matchup("p4") == m2
    assert r.get_player_matchup("p99") is None


# Team as Matchup participant
def test_matchup_accepts_teams_as_participants():
    team1 = Team(id="t1", name="Alpha", members=("Alice", "Bob"))
    team2 = Team(id="t2", name="Beta", members=("Carol", "Dave"))
    m = Matchup(player1=team1, player2=team2)
    assert m.player1 == team1
    assert m.player2 == team2
    assert not m.is_bye


def test_matchup_team_bye():
    team = Team(id="t1", name="Alpha", members=("Alice",))
    m = Matchup(player1=team, player2=None)
    assert m.is_bye


def test_matchup_cannot_match_team_against_itself():
    team = Team(id="t1", name="Alpha", members=("Alice",))
    with pytest.raises(ValueError, match="A participant cannot be matched against themselves"):
        Matchup(player1=team, player2=team)


# TournamentCompleteError
def test_tournament_complete_error_is_exception():
    err = TournamentCompleteError("done")
    assert isinstance(err, Exception)
    assert str(err) == "done"


# Standing Tests
def test_player_standing_fields():
    p = Player(id="p1", name="Alice")
    s = Standing(player=p, points=6, rank=1)
    assert s.player == p
    assert s.points == 6
    assert s.rank == 1


def test_player_standing_default_tiebreakers():
    p = Player(id="p1", name="Alice")
    s = Standing(player=p, points=6, rank=1)
    assert s.tiebreakers == {}


def test_player_standing_with_tiebreakers():
    p = Player(id="p1", name="Alice")
    s = Standing(
        player=p,
        points=6,
        rank=1,
        tiebreakers={"owp": 0.667, "oowp": 0.500},
    )
    assert s.tiebreakers["owp"] == 0.667
    assert s.tiebreakers["oowp"] == 0.500


def test_player_standing_points_cannot_be_negative():
    p = Player(id="p1", name="Alice")
    with pytest.raises(ValueError, match="points cannot be negative"):
        Standing(player=p, points=-1, rank=1)