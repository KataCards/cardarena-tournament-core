from abc import ABC, abstractmethod

from cardarena_tournament_core.models import Round, Standing


class BaseScoring(ABC):
    @abstractmethod
    def calculate(self, rounds: list[Round]) -> list[Standing]:
        """Compute standings from a list of completed rounds."""