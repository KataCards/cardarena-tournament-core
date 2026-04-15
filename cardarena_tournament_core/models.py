"""Core data models for tournament management."""

from dataclasses import dataclass, field
from enum import Enum


class MatchupOutcome(Enum):
    """Possible outcomes of a tournament matchup."""

    PENDING = "pending"
    PLAYER1_WINS = "player1_wins"
    PLAYER2_WINS = "player2_wins"
    DRAW = "draw"


@dataclass(frozen=True)
class Player:
    """Individual tournament participant."""

    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Player id cannot be empty")
        if not self.name:
            raise ValueError("Player name cannot be empty")


@dataclass(frozen=True)
class Team:
    """Team tournament participant."""

    id: str
    name: str
    members: list[str]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Team id cannot be empty")
        if not self.name:
            raise ValueError("Team name cannot be empty")
        if not self.members:
            raise ValueError("Team must have at least one member")


# Type alias for any tournament participant
Participant = Player | Team


@dataclass
class Matchup:
    """Single match between two participants (players or teams).

    If player2 is None, player1 receives a bye (automatic win).
    """

    player1: Participant
    player2: Participant | None
    outcome: MatchupOutcome = MatchupOutcome.PENDING

    def __post_init__(self) -> None:
        if self.player1 is None:
            raise ValueError("player1 cannot be None")
        if self.player2 is not None and self.player1.id == self.player2.id:
            raise ValueError("A participant cannot be matched against themselves")

    @property
    def is_bye(self) -> bool:
        """True if this is a bye (player2 is None)."""
        return self.player2 is None

    @property
    def is_complete(self) -> bool:
        """True if outcome is not PENDING."""
        return self.outcome != MatchupOutcome.PENDING


@dataclass
class Round:
    """Single round of tournament play containing multiple matchups."""

    round_number: int
    matchups: list[Matchup] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.round_number < 1:
            raise ValueError("round_number must be >= 1")

    @property
    def is_complete(self) -> bool:
        """True if all matchups are complete."""
        return all(m.is_complete for m in self.matchups)

    def get_player_matchup(self, player_id: str) -> Matchup | None:
        """Find matchup containing the specified player."""
        for matchup in self.matchups:
            if matchup.player1.id == player_id:
                return matchup
            if matchup.player2 is not None and matchup.player2.id == player_id:
                return matchup
        return None


@dataclass
class Standing:
    """Participant's standing in tournament rankings.

    Works for both individual players and teams.
    Tiebreakers dict is flexible to accommodate different scoring systems:
    - Pokémon: {"owp": 0.667, "oowp": 0.500}
    - Yu-Gi-Oh!: {"owp": 0.667, "oowp": 0.500, "tiebreak_number": 9667500.0}
    """

    player: Participant
    points: int
    rank: int
    tiebreakers: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.points < 0:
            raise ValueError("points cannot be negative")
