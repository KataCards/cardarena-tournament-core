from abc import ABC, abstractmethod
from collections.abc import Sequence

from cardarena_tournament_core.models import Participant, Round


class BasePairing(ABC):
    """Abstract base class for all tournament pairing formats.

    Subclasses implement :meth:`pair` to generate the next round's matchups and
    may override :meth:`submit_results` to update internal state (e.g. points,
    active-player lists).  Always call ``super().submit_results(completed_round)``
    at the end of any override so the round history stays consistent.
    """

    def __init__(self, participants: Sequence[Participant]) -> None:
        self._participants: list[Participant] = list(participants)
        self._rounds: list[Round] = []

    @abstractmethod
    def pair(self) -> Round:
        """Generate and return the next round's pairings."""

    def submit_results(self, completed_round: Round) -> None:
        """Record a completed round.

        Subclasses should update their own state first, then call
        ``super().submit_results(completed_round)`` to append to the history.
        """
        self._rounds.append(completed_round)

    @property
    def participants(self) -> list[Participant]:
        """All participants in this tournament (read-only copy)."""
        return list(self._participants)

    @property
    def rounds(self) -> list[Round]:
        """All submitted rounds in chronological order (read-only copy)."""
        return list(self._rounds)


__all__ = ["BasePairing"]