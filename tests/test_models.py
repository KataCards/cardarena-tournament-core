"""Tests for core data models serialization."""

import pytest

from cardarena_tournament_core.common.models import (
    Matchup,
    MatchupOutcome,
    Player,
    Round,
    Team,
    participant_from_dict,
    participant_to_dict,
)
from cardarena_tournament_core.common.errors import ParticipantValidationError


def test_player_serialization_roundtrip():
    """Verify Player serialization/deserialization preserves all data."""
    player = Player(id="123", name="Alice")
    data = player.to_dict()
    
    assert data == {"type": "player", "id": "123", "name": "Alice"}
    
    restored = Player.from_dict(data)
    assert restored == player
    assert restored.id == "123"
    assert restored.name == "Alice"


def test_team_serialization_roundtrip():
    """Verify Team serialization/deserialization preserves all data."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    p3 = Player(id="p3", name="Charlie")
    team = Team(id="t1", name="Team Alpha", members=(p1, p2, p3))
    data = team.to_dict()
    
    assert data == {
        "type": "team",
        "id": "t1",
        "name": "Team Alpha",
        "members": [
            {"type": "player", "id": "p1", "name": "Alice"},
            {"type": "player", "id": "p2", "name": "Bob"},
            {"type": "player", "id": "p3", "name": "Charlie"}
        ]
    }
    
    restored = Team.from_dict(data)
    assert restored == team
    assert restored.id == "t1"
    assert restored.name == "Team Alpha"
    assert len(restored.members) == 3
    assert restored.members[0].id == "p1"
    assert restored.members[1].id == "p2"
    assert restored.members[2].id == "p3"


def test_participant_to_dict_with_player():
    """Verify participant_to_dict works with Player."""
    player = Player(id="1", name="P1")
    data = participant_to_dict(player)
    assert data["type"] == "player"
    assert data["id"] == "1"


def test_participant_to_dict_with_team():
    """Verify participant_to_dict works with Team."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    team = Team(id="t1", name="Team A", members=(p1, p2))
    data = participant_to_dict(team)
    assert data["type"] == "team"
    assert data["id"] == "t1"
    assert len(data["members"]) == 2


def test_participant_from_dict_with_player():
    """Verify participant_from_dict reconstructs Player correctly."""
    data = {"type": "player", "id": "1", "name": "P1"}
    participant = participant_from_dict(data)
    assert isinstance(participant, Player)
    assert participant.id == "1"
    assert participant.name == "P1"


def test_participant_from_dict_with_team():
    """Verify participant_from_dict reconstructs Team correctly."""
    data = {
        "type": "team",
        "id": "t1",
        "name": "Team A",
        "members": [
            {"type": "player", "id": "p1", "name": "Alice"},
            {"type": "player", "id": "p2", "name": "Bob"}
        ]
    }
    participant = participant_from_dict(data)
    assert isinstance(participant, Team)
    assert participant.id == "t1"
    assert participant.name == "Team A"
    assert len(participant.members) == 2
    assert participant.members[0].id == "p1"
    assert participant.members[1].id == "p2"


def test_participant_from_dict_unknown_type():
    """Verify participant_from_dict raises error for unknown type."""
    data = {"type": "unknown", "id": "1", "name": "Test"}
    with pytest.raises(ParticipantValidationError, match="Unknown participant type"):
        participant_from_dict(data)


def test_matchup_serialization_roundtrip():
    """Verify Matchup serialization/deserialization preserves all data."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    matchup = Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS)
    
    data = matchup.to_dict()
    
    assert data["player1"]["id"] == "1"
    assert data["player2"]["id"] == "2"
    assert data["outcome"] == "player1_wins"
    
    restored = Matchup.from_dict(data)
    assert restored.player1.id == matchup.player1.id
    assert restored.player2 is not None
    assert matchup.player2 is not None
    assert restored.player2.id == matchup.player2.id
    assert restored.outcome == matchup.outcome


def test_matchup_serialization_with_bye():
    """Verify Matchup serialization handles bye (None player2) correctly."""
    p1 = Player(id="1", name="P1")
    matchup = Matchup(player1=p1, player2=None)
    
    data = matchup.to_dict()
    
    assert data["player1"]["id"] == "1"
    assert data["player2"] is None
    assert data["outcome"] == "pending"
    
    restored = Matchup.from_dict(data)
    assert restored.player1.id == "1"
    assert restored.player2 is None
    assert restored.is_bye


def test_matchup_serialization_with_team():
    """Verify Matchup serialization works with Team participants."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    p3 = Player(id="p3", name="Charlie")
    p4 = Player(id="p4", name="Dave")
    
    t1 = Team(id="t1", name="Team A", members=(p1, p2))
    t2 = Team(id="t2", name="Team B", members=(p3, p4))
    matchup = Matchup(player1=t1, player2=t2, outcome=MatchupOutcome.DRAW)
    
    data = matchup.to_dict()
    restored = Matchup.from_dict(data)
    
    assert isinstance(restored.player1, Team)
    assert restored.player2 is not None
    assert isinstance(restored.player2, Team)
    assert restored.player1.id == "t1"
    assert restored.player2.id == "t2"
    assert len(restored.player1.members) == 2
    assert len(restored.player2.members) == 2
    assert restored.outcome == MatchupOutcome.DRAW


def test_round_serialization_roundtrip():
    """Verify Round serialization/deserialization preserves all data."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    p3 = Player(id="3", name="P3")
    
    round_obj = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.DRAW),
            Matchup(player1=p3, player2=None)
        ]
    )
    
    data = round_obj.to_dict()
    
    assert data["round_number"] == 1
    assert len(data["matchups"]) == 2
    assert data["matchups"][0]["outcome"] == "draw"
    assert data["matchups"][1]["player2"] is None
    
    restored = Round.from_dict(data)
    assert restored.round_number == round_obj.round_number
    assert len(restored.matchups) == len(round_obj.matchups)
    assert restored.matchups[0].outcome == MatchupOutcome.DRAW
    assert restored.matchups[1].is_bye


def test_round_serialization_empty_matchups():
    """Verify Round serialization handles empty matchups list."""
    round_obj = Round(round_number=5, matchups=[])
    
    data = round_obj.to_dict()
    assert data["round_number"] == 5
    assert data["matchups"] == []
    
    restored = Round.from_dict(data)
    assert restored.round_number == 5
    assert len(restored.matchups) == 0


# -------------------------------------------------------------------------
# Validation tests
# -------------------------------------------------------------------------

def test_player_empty_id_raises_validation_error():
    """Verify Player raises error when id is empty."""
    from cardarena_tournament_core.common.errors import ParticipantValidationError
    
    with pytest.raises(ParticipantValidationError, match="Player id cannot be empty"):
        Player(id="", name="Alice")


def test_player_empty_name_raises_validation_error():
    """Verify Player raises error when name is empty."""
    from cardarena_tournament_core.common.errors import ParticipantValidationError
    
    with pytest.raises(ParticipantValidationError, match="Player name cannot be empty"):
        Player(id="123", name="")


def test_team_empty_id_raises_validation_error():
    """Verify Team raises error when id is empty."""
    from cardarena_tournament_core.common.errors import TeamValidationError
    
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    with pytest.raises(TeamValidationError, match="Team id cannot be empty"):
        Team(id="", name="Team A", members=(p1, p2))


def test_team_empty_name_raises_validation_error():
    """Verify Team raises error when name is empty."""
    from cardarena_tournament_core.common.errors import TeamValidationError
    
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    with pytest.raises(TeamValidationError, match="Team name cannot be empty"):
        Team(id="t1", name="", members=(p1, p2))


def test_team_empty_members_raises_validation_error():
    """Verify Team raises error when members is empty."""
    from cardarena_tournament_core.common.errors import TeamValidationError
    
    with pytest.raises(TeamValidationError, match="Team must have at least one member"):
        Team(id="t1", name="Team A", members=())


def test_team_normalizes_list_to_tuple():
    """Verify Team converts list members to tuple for hashability."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    # Pass a list instead of tuple
    team = Team(id="t1", name="Team A", members=[p1, p2])  # type: ignore[arg-type]
    
    # Should be normalized to tuple
    assert isinstance(team.members, tuple)
    assert len(team.members) == 2
    assert team.members[0] == p1
    assert team.members[1] == p2


def test_team_is_hashable_with_tuple_members():
    """Verify Team is hashable when members is a tuple."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    team = Team(id="t1", name="Team A", members=(p1, p2))
    
    # Should be hashable (frozen dataclass with tuple members)
    team_hash = hash(team)
    assert isinstance(team_hash, int)
    
    # Can be used in sets
    team_set = {team}
    assert team in team_set


def test_team_is_hashable_after_list_normalization():
    """Verify Team is hashable even when initialized with a list."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    # Initialize with list
    team = Team(id="t1", name="Team A", members=[p1, p2])  # type: ignore[arg-type]
    
    # Should still be hashable after normalization
    team_hash = hash(team)
    assert isinstance(team_hash, int)


def test_team_rejects_non_player_members():
    """Verify Team raises error when members contain non-Player objects."""
    from cardarena_tournament_core.common.errors import TeamValidationError
    
    p1 = Player(id="p1", name="Alice")
    
    with pytest.raises(TeamValidationError, match="must be a Player instance"):
        Team(id="t1", name="Team A", members=(p1, "not a player"))  # type: ignore[arg-type]


def test_team_rejects_mixed_valid_invalid_members():
    """Verify Team raises error with specific index when non-Player found."""
    from cardarena_tournament_core.common.errors import TeamValidationError
    
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    with pytest.raises(TeamValidationError, match="at index 2 must be a Player instance"):
        Team(id="t1", name="Team A", members=(p1, p2, {"id": "p3", "name": "Charlie"}))  # type: ignore[arg-type]


def test_team_serialization_roundtrip_preserves_tuple():
    """Verify Team serialization/deserialization maintains tuple type."""
    p1 = Player(id="p1", name="Alice")
    p2 = Player(id="p2", name="Bob")
    
    # Create with list
    team = Team(id="t1", name="Team A", members=[p1, p2])  # type: ignore[arg-type]
    
    # Serialize
    data = team.to_dict()
    
    # Deserialize
    restored = Team.from_dict(data)
    
    # Should be tuple
    assert isinstance(restored.members, tuple)
    assert len(restored.members) == 2
    assert restored.members[0].id == "p1"
    assert restored.members[1].id == "p2"


def test_matchup_same_participant_raises_validation_error():
    """Verify Matchup raises error when participant plays themselves."""
    from cardarena_tournament_core.common.errors import MatchupValidationError
    
    player = Player(id="1", name="P1")
    
    with pytest.raises(MatchupValidationError, match="cannot be matched against themselves"):
        Matchup(player1=player, player2=player)


def test_round_invalid_round_number_raises_validation_error():
    """Verify Round raises error when round_number is less than 1."""
    from cardarena_tournament_core.common.errors import RoundValidationError
    
    with pytest.raises(RoundValidationError, match="round_number must be >= 1"):
        Round(round_number=0, matchups=[])


def test_round_get_player_matchup_returns_none_when_not_found():
    """Verify get_player_matchup returns None when player not in round."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    
    round_obj = Round(
        round_number=1,
        matchups=[Matchup(player1=p1, player2=p2)]
    )
    
    result = round_obj.get_player_matchup("999")
    assert result is None


def test_round_get_player_matchup_finds_player1():
    """Verify get_player_matchup finds matchup when player is player1."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    
    matchup = Matchup(player1=p1, player2=p2)
    round_obj = Round(round_number=1, matchups=[matchup])
    
    result = round_obj.get_player_matchup("1")
    assert result == matchup


def test_round_get_player_matchup_finds_player2():
    """Verify get_player_matchup finds matchup when player is player2."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    
    matchup = Matchup(player1=p1, player2=p2)
    round_obj = Round(round_number=1, matchups=[matchup])
    
    result = round_obj.get_player_matchup("2")
    assert result == matchup


def test_standing_negative_points_raises_validation_error():
    """Verify Standing raises error when points is negative."""
    from cardarena_tournament_core.common.errors import StandingValidationError
    from cardarena_tournament_core.common.models import Standing
    
    player = Player(id="1", name="P1")
    
    with pytest.raises(StandingValidationError, match="points cannot be negative"):
        Standing(player=player, points=-1, rank=1)


def test_standing_negative_rank_raises_validation_error():
    """Verify Standing raises error when rank is negative."""
    from cardarena_tournament_core.common.errors import StandingValidationError
    from cardarena_tournament_core.common.models import Standing
    
    player = Player(id="1", name="P1")
    
    with pytest.raises(StandingValidationError, match="rank cannot be negative"):
        Standing(player=player, points=10, rank=-1)


def test_matchup_is_bye_property():
    """Verify is_bye property returns True when player2 is None."""
    p1 = Player(id="1", name="P1")
    
    matchup = Matchup(player1=p1, player2=None)
    assert matchup.is_bye is True
    
    p2 = Player(id="2", name="P2")
    matchup2 = Matchup(player1=p1, player2=p2)
    assert matchup2.is_bye is False


def test_matchup_is_complete_property_with_bye():
    """Verify is_complete returns True for bye matches."""
    p1 = Player(id="1", name="P1")
    matchup = Matchup(player1=p1, player2=None)
    
    assert matchup.is_complete is True


def test_matchup_is_complete_property_with_pending():
    """Verify is_complete returns False for pending matches."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    matchup = Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PENDING)
    
    assert matchup.is_complete is False


def test_matchup_is_complete_property_with_outcome():
    """Verify is_complete returns True when outcome is set."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    matchup = Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS)
    
    assert matchup.is_complete is True


def test_round_is_complete_property_all_complete():
    """Verify is_complete returns True when all matchups are complete."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    p3 = Player(id="3", name="P3")
    
    round_obj = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p3, player2=None)  # Bye is complete
        ]
    )
    
    assert round_obj.is_complete is True


def test_round_is_complete_property_some_incomplete():
    """Verify is_complete returns False when any matchup is incomplete."""
    p1 = Player(id="1", name="P1")
    p2 = Player(id="2", name="P2")
    p3 = Player(id="3", name="P3")
    p4 = Player(id="4", name="P4")
    
    round_obj = Round(
        round_number=1,
        matchups=[
            Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=p3, player2=p4)  # Pending
        ]
    )
    
    assert round_obj.is_complete is False