from typing import ClassVar

from cardarena_tournament_core.common.models import Round, Standing
from cardarena_tournament_core.scoring.base import TCGBaseScoring


class YuGiOh(TCGBaseScoring):
    """Yu-Gi-Oh! TCG scoring rules.

    Points:
        - Win  → 3 pts
        - Draw → 1 pt
        - Loss → 0 pts
        - Bye  → 3 pts (automatic win, excluded from tiebreaker calculations)

    Tiebreakers (in order):
        1. OWP  — Opponents' Win Percentage
        2. OOWP — Opponents' Opponents' Win Percentage

    Unlike Pokémon TCG, Yu-Gi-Oh! does NOT apply a 25% floor to win percentages.
    """

    WIN_POINTS: ClassVar[int] = 3
    DRAW_POINTS: ClassVar[int] = 1
    LOSS_POINTS: ClassVar[int] = 0
    BYE_POINTS: ClassVar[int] = 3

    def calculate(self, rounds: list[Round]) -> list[Standing]:
        """Return standings sorted by points, OWP, then OOWP."""
        return self._build_standings(rounds, min_win_pct=0.0)