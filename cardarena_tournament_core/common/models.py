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


@dataclass(frozen=True)
class Team:
    """A team of players that competes as a single tournament participant."""

    id: str
    name: str
    members: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise TeamValidationError("Team id cannot be empty.")
        if not self.name:
            raise TeamValidationError("Team name cannot be empty.")
        if not self.members:
            raise TeamValidationError("Team must have at least one member.")


# Either an individual player or a team can participate in a tournament.
Participant = Player | Team


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
]