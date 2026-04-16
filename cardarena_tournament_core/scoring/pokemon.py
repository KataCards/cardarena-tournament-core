from cardarena_tournament_core.models import Round, Standing
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

    Win percentages are floored at 25 % per official rules.
    """

    WIN_POINTS: int = 3
    DRAW_POINTS: int = 1
    LOSS_POINTS: int = 0
    BYE_POINTS: int = 3

    def calculate(self, rounds: list[Round]) -> list[Standing]:
        """Return standings sorted by points → OWP → OOWP (all descending)."""
        player_map = self._collect_players(rounds)
        points_by_player = self._calculate_points(rounds)
        owp_by_player, oowp_by_player = self._calculate_tiebreakers(
            list(player_map.keys()), rounds, min_win_pct=0.25
        )

        standings: list[Standing] = [
            Standing(
                player=player_map[player_id],
                points=points_by_player[player_id],
                rank=0,
                tiebreakers={
                    "owp": owp_by_player[player_id],
                    "oowp": oowp_by_player[player_id],
                },
            )
            for player_id in player_map
        ]
        standings.sort(
            key=lambda standing: (
                standing.points,
                standing.tiebreakers["owp"],
                standing.tiebreakers["oowp"],
            ),
            reverse=True,
        )
        for rank, standing in enumerate(standings, start=1):
            standing.rank = rank

        return standings