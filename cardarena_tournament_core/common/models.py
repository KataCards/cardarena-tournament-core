"""Core data models for tournament management."""

from dataclasses import dataclass, field
from enum import Enum

from cardarena_tournament_core.common.errors import (
    MatchupValidationError,
    ParticipantValidationError,
    RoundValidationError,
    StandingValidationError,
    TeamValidationError,
)


# -------------------------------------------------------------------------
# Match outcome model
# -------------------------------------------------------------------------

class MatchupOutcome(str, Enum):
    """Possible outcomes of a tournament matchup."""

    PENDING = "pending"
    PLAYER1_WINS = "player1_wins"
    PLAYER2_WINS = "player2_wins"
    DRAW = "draw"


# -------------------------------------------------------------------------
# Participant models
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class Player:
    """An individual tournament participant identified by a unique id."""

    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ParticipantValidationError("Player id cannot be empty.")
        if not self.name:
            raise ParticipantValidationError("Player name cannot be empty.")

    def to_dict(self) -> dict:
        """Serialize player to dictionary."""
        return {"type": "player", "id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Deserialize player from dictionary."""
        return cls(id=data["id"], name=data["name"])


@dataclass(frozen=True)
class Team:
    """A team of players that competes as a single tournament participant.
    
    Args:
        id: Unique identifier for the team.
        name: Display name for the team.
        members: List of Player objects that make up the team.
    
    Example:
        >>> player1 = Player(id="p1", name="Alice")
        >>> player2 = Player(id="p2", name="Bob")
        >>> team = Team(id="t1", name="Team Alpha", members=[player1, player2])
    """

    id: str
    name: str
    members: tuple["Player", ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise TeamValidationError("Team id cannot be empty.")
        if not self.name:
            raise TeamValidationError("Team name cannot be empty.")
        if not self.members:
            raise TeamValidationError("Team must have at least one member.")

    def to_dict(self) -> dict:
        """Serialize team to dictionary."""
        return {
            "type": "team",
            "id": self.id,
            "name": self.name,
            "members": [member.to_dict() for member in self.members]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Team":
        """Deserialize team from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            members=tuple(Player.from_dict(m) for m in data["members"])
        )


# Either an individual player or a team can participate in a tournament.
Participant = Player | Team


# -------------------------------------------------------------------------
# Participant serialization helpers
# -------------------------------------------------------------------------

def participant_to_dict(participant: Participant) -> dict:
    """Serialize a Participant (Player or Team) to dictionary."""
    return participant.to_dict()


def participant_from_dict(data: dict) -> Participant:
    """Deserialize a Participant from dictionary.

    Raises:
        ParticipantValidationError: Unknown participant type.
    """
    if data["type"] == "player":
        return Player.from_dict(data)
    elif data["type"] == "team":
        return Team.from_dict(data)
    else:
        raise ParticipantValidationError(f"Unknown participant type: {data['type']}")


# -------------------------------------------------------------------------
# Management models
# -------------------------------------------------------------------------

@dataclass
class Matchup:
    """A single scheduled match between two participants.

    When ``player2`` is ``None`` the match is a bye: ``player1`` wins automatically
    without facing a real opponent.
    """

    player1: Participant
    player2: Participant | None
    outcome: MatchupOutcome = MatchupOutcome.PENDING

    def __post_init__(self) -> None:
        if self.player2 is not None and self.player1.id == self.player2.id:
            raise MatchupValidationError(
                "A participant cannot be matched against themselves."
            )

    @property
    def is_bye(self) -> bool:
        """``True`` when ``player2`` is ``None`` (bye match)."""
        return self.player2 is None

    @property
    def is_complete(self) -> bool:
        """``True`` when the matchup no longer requires manual input."""
        return self.is_bye or self.outcome != MatchupOutcome.PENDING

    def to_dict(self) -> dict:
        """Serialize matchup to dictionary."""
        return {
            "player1": participant_to_dict(self.player1),
            "player2": participant_to_dict(self.player2) if self.player2 else None,
            "outcome": self.outcome.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Matchup":
        """Deserialize matchup from dictionary."""
        return cls(
            player1=participant_from_dict(data["player1"]),
            player2=participant_from_dict(data["player2"]) if data["player2"] else None,
            outcome=MatchupOutcome(data["outcome"])
        )


@dataclass
class Round:
    """A single round of play containing one or more matchups."""

    round_number: int
    matchups: list[Matchup] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.round_number < 1:
            raise RoundValidationError("round_number must be >= 1.")

    @property
    def is_complete(self) -> bool:
        """``True`` when every matchup in this round has a recorded outcome."""
        return all(matchup.is_complete for matchup in self.matchups)

    def get_player_matchup(self, player_id: str) -> Matchup | None:
        """Return the matchup that involves *player_id*, or ``None`` if not found."""
        for matchup in self.matchups:
            if matchup.player1.id == player_id:
                return matchup
            if matchup.player2 is not None and matchup.player2.id == player_id:
                return matchup
        return None

    def to_dict(self) -> dict:
        """Serialize round to dictionary."""
        return {
            "round_number": self.round_number,
            "matchups": [m.to_dict() for m in self.matchups]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Round":
        """Deserialize round from dictionary."""
        return cls(
            round_number=data["round_number"],
            matchups=[Matchup.from_dict(m) for m in data["matchups"]]
        )


@dataclass
class Standing:
    """A participant's position in the tournament standings after scoring.

    The ``tiebreakers`` dict holds format-specific secondary sort values, e.g.:
    - Pokémon TCG: ``{"owp": 0.667, "oowp": 0.500}``
    - Yu-Gi-Oh! TCG: ``{"owp": 0.667, "oowp": 0.500}``
    """

    player: Participant
    points: int
    rank: int
    tiebreakers: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.points < 0:
            raise StandingValidationError("points cannot be negative.")
        if self.rank < 0:
            raise StandingValidationError("rank cannot be negative.")


__all__ = [
    "Player",
    "Team",
    "Participant",
    "Matchup",
    "MatchupOutcome",
    "Round",
    "Standing",
    "participant_to_dict",
    "participant_from_dict",
]