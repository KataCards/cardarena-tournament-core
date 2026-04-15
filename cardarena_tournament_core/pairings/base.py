from abc import ABC, abstractmethod

from cardarena_tournament_core.models import Participant, Round


class BasePairing(ABC):
    def __init__(self, participants: list[Participant]) -> None:
        self.participants = participants
        self._rounds: list[Round] = []

    @abstractmethod
    def pair(self) -> Round:
        """Generate and return the next round's pairings."""

    def submit_results(self, round: Round) -> None:
        """Record a completed round. Subclasses call super() after updating their own state."""
        self._rounds.append(round)

    @property
    def rounds(self) -> list[Round]:
        """All submitted rounds (read-only copy)."""
        return list(self._rounds)
