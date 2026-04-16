"""Backward-compatible re-exports for legacy model imports."""

from cardarena_tournament_core.common.models import (
    Matchup,
    MatchupOutcome,
    Participant,
    Player,
    Round,
    Standing,
    Team,
)

__all__ = [
    "Player",
    "Team",
    "Participant",
    "Matchup",
    "MatchupOutcome",
    "Round",
    "Standing",
]
