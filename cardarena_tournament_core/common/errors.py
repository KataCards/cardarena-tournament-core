"""Exception hierarchy for cardarena_tournament_core."""


# -------------------------------------------------------------------------
# Base categories
# -------------------------------------------------------------------------


class CardArenaError(Exception):
    """Base class for all package-specific exceptions."""


class ConfigurationError(CardArenaError):
    """Raised when object configuration is invalid."""


class ValidationError(CardArenaError):
    """Raised when input data violates model or API constraints."""


class StateError(CardArenaError):
    """Raised when an operation is invalid for the current runtime state."""


# -------------------------------------------------------------------------
# Model validation errors
# -------------------------------------------------------------------------

class ParticipantValidationError(ValidationError):
    """Raised when a player or participant payload is invalid."""


class TeamValidationError(ValidationError):
    """Raised when team data fails validation."""


class MatchupValidationError(ValidationError):
    """Raised when matchup data fails validation."""


class RoundValidationError(ValidationError):
    """Raised when round data fails validation."""


class StandingValidationError(ValidationError):
    """Raised when a standing entry fails validation."""


# -------------------------------------------------------------------------
# Pairing and tournament errors
# -------------------------------------------------------------------------

class TournamentConfigurationError(ConfigurationError):
    """Raised when tournament dependencies are misconfigured."""


class PairingConfigurationError(ConfigurationError):
    """Raised when pairing settings or participant registration are invalid."""


class PairingStateError(StateError):
    """Raised when a pairing action is invalid for current state."""


class TournamentCompleteError(PairingStateError):
    """Raised when ``pair()`` is called after a tournament has concluded."""


# -------------------------------------------------------------------------
# Scoring errors
# -------------------------------------------------------------------------

class ScoringError(CardArenaError):
    """Base class for scoring-specific failures."""


class ScoringValidationError(ValidationError, ScoringError):
    """Raised when standings cannot be calculated from invalid round data."""


class IncompleteRoundError(ScoringValidationError):
    """Raised when scoring is requested for rounds with unresolved matchups."""


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