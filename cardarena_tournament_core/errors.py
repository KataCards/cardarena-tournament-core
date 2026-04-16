"""Backward-compatible re-exports for legacy error imports."""

from cardarena_tournament_core.common.errors import (
	CardArenaError,
	ConfigurationError,
	IncompleteRoundError,
	MatchupValidationError,
	PairingConfigurationError,
	PairingStateError,
	ParticipantValidationError,
	RoundValidationError,
	ScoringError,
	ScoringValidationError,
	StandingValidationError,
	StateError,
	TeamValidationError,
	TournamentCompleteError,
	TournamentConfigurationError,
	ValidationError,
)

__all__ = [
	"CardArenaError",
	"ConfigurationError",
	"ValidationError",
	"StateError",
	"ParticipantValidationError",
	"TeamValidationError",
	"MatchupValidationError",
	"RoundValidationError",
	"StandingValidationError",
	"TournamentConfigurationError",
	"PairingConfigurationError",
	"PairingStateError",
	"TournamentCompleteError",
	"ScoringError",
	"ScoringValidationError",
	"IncompleteRoundError",
]
