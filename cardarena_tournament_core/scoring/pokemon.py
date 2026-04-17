from typing import ClassVar

from cardarena_tournament_core.common.models import Round, Standing
from cardarena_tournament_core.scoring.base import TCGBaseScoring


class PokemonTCG(TCGBaseScoring):
    """Pokémon TCG scoring rules.

    Points:
        - Win  → 3 pts
        - Draw → 1 pt
        - Loss → 0 pts
        - Bye  → 3 pts (automatic win, excluded from tiebreaker calculations)

    Tiebreakers (in order):
        1. OWP  — Opponents' Win Percentage
        2. OOWP — Opponents' Opponents' Win Percentage

    Win percentages are floored at 25 % per official rules. Output standings are sorted by points, then OWP, then OOWP in percentage.
    This means that, among players with equal points, a player with more then 25% OWP would rank above a player with a lower OWP; if OWP is also equal, OOWP is used.
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
        return self._build_standings(rounds, min_win_pct=0.25)