from dataclasses import dataclass, field
from enum import Enum


class MatchupOutcome(Enum):
    PENDING = "pending"
    PLAYER1_WINS = "player1_wins"
    PLAYER2_WINS = "player2_wins"
    DRAW = "draw"


@dataclass
class Player:
    id: str
    name: str


@dataclass
class Matchup:
    player1: Player
    player2: Player | None  # None = bye
    outcome: MatchupOutcome = MatchupOutcome.PENDING


@dataclass
class Round:
    round_number: int
    matchups: list[Matchup] = field(default_factory=list)


@dataclass
class PlayerStanding:
    player: Player
    points: int
    rank: int
    tiebreakers: dict[str, float] = field(default_factory=dict)
