from cardarena_tournament_core.models import MatchupOutcome, Round, Standing
from cardarena_tournament_core.scoring.tcg_base import TCGBaseScoring


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
        points_by_player: dict[str, int] = {player_id: 0 for player_id in player_map}

        for tournament_round in rounds:
            for matchup in tournament_round.matchups:
                if matchup.player2 is None:
                    points_by_player[matchup.player1.id] += self.BYE_POINTS
                elif matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                    points_by_player[matchup.player1.id] += self.WIN_POINTS
                elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                    points_by_player[matchup.player2.id] += self.WIN_POINTS
                elif matchup.outcome == MatchupOutcome.DRAW:
                    points_by_player[matchup.player1.id] += self.DRAW_POINTS
                    points_by_player[matchup.player2.id] += self.DRAW_POINTS

        # Compute tiebreakers once per player to avoid redundant passes
        owp_by_player: dict[str, float] = {
            player_id: self._owp(player_id, rounds) for player_id in player_map
        }
        oowp_by_player: dict[str, float] = {
            player_id: self._oowp(player_id, rounds) for player_id in player_map
        }

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
