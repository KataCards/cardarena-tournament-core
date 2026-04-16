"""Tournament-specific exceptions."""


class TournamentCompleteError(Exception):
    """Raised when ``pair()`` is called but the tournament has already concluded.

    This can happen in two situations:
    - :class:`RoundRobin`: all pre-scheduled rounds have been played.
    - :class:`SingleElimination`: a champion has been determined (only one
      active participant remains) or all participants have been eliminated.
    """


__all__ = ["TournamentCompleteError"]