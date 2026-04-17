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
        1. Match Points
        2. OWP  — Opponents' Win Percentage
        3. OOWP — Opponents' Opponents' Win Percentage

    Unlike Pokémon TCG, Yu-Gi-Oh! does NOT apply a 25% floor to win percentages.
    Standings are sorted by points (descending), then OWP (descending), then OOWP (descending). To get the tiebreaker-number like in KCGN use the util
    yugioh_tiebreak_number function, which encodes the tiebreaker components into a single integer that preserves the sort order.
    """

    WIN_POINTS: ClassVar[int] = 3
    DRAW_POINTS: ClassVar[int] = 1
    LOSS_POINTS: ClassVar[int] = 0
    BYE_POINTS: ClassVar[int] = 3

    # ------------------------------------------------------------------------
    # Calculation interface
    # ------------------------------------------------------------------------

    def calculate(self, rounds: list[Round]) -> list[Standing]:
        """Return standings sorted by points, OWP, then OOWP."""
        return self._build_standings(rounds, min_win_pct=0.0)