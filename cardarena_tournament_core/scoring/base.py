from abc import ABC, abstractmethod

from cardarena_tournament_core.models import Round, Standing


class BaseScoring(ABC):
    """Abstract base class for all tournament scoring systems.

    Implement :meth:`calculate` to turn a list of completed rounds into an
    ordered list of :class:`~cardarena_tournament_core.models.Standing` objects.
    """

    @abstractmethod
    def calculate(self, rounds: list[Round]) -> list[Standing]:
        """Compute and return standings from the given completed rounds.

        The returned list must be sorted from first place to last place.
        Each :class:`~cardarena_tournament_core.models.Standing` must have
        its ``rank`` field set (1-indexed).
        """
