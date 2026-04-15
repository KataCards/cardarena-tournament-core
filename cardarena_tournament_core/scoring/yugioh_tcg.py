from cardarena_tournament_core.models import MatchupOutcome, Round, Standing
from cardarena_tournament_core.scoring.tcg_base import TCGBaseScoring


class YuGiOh(TCGBaseScoring):
    """Yu-Gi-Oh! TCG scoring rules.

    Points:
        - Win  → 3 pts
        - Draw → 1 pt
        - Loss → 0 pts
        - Bye  → 3 pts (automatic win, excluded from tiebreaker calculations)

    Tiebreakers:
        All three tiebreakers are encoded into a single 8-digit integer
        ``XXYYYZZZ`` so that a single numeric comparison produces the correct
        ranking:

        - ``XX``  = total points (clamped to 0–99)
        - ``YYY`` = OWP  scaled to 0–999  (e.g. 72.6 % → 726)
        - ``ZZZ`` = OOWP scaled to 0–999  (e.g. 67.7 % → 677)

        Example: 33 pts, OWP = 72.6 %, OOWP = 67.7 % → tiebreak number 33726677

    Win percentages are floored at 25 % per official rules.
    """

    WIN_POINTS: int = 3
    DRAW_POINTS: int = 1
    LOSS_POINTS: int = 0
    BYE_POINTS: int = 3

    def calculate(self, rounds: list[Round]) -> list[Standing]:
        """Return standings sorted by tiebreak number (descending).

        The tiebreak number naturally encodes points → OWP → OOWP priority,
        so a single sort on that integer produces the correct final ranking.
        """
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
                    "tiebreak_number": float(
                        self._encode_tiebreak_number(
                            points_by_player[player_id],
                            owp_by_player[player_id],
                            oowp_by_player[player_id],
                        )
                    ),
                },
            )
            for player_id in player_map
        ]
        standings.sort(
            key=lambda standing: (standing.points, standing.tiebreakers["tiebreak_number"]),
            reverse=True,
        )
        for rank, standing in enumerate(standings, start=1):
            standing.rank = rank

        return standings

    def _encode_tiebreak_number(self, points: int, owp: float, oowp: float) -> int:
        """Encode points + OWP + OOWP into the XXYYYZZZ integer format."""
        points_component = max(0, min(99, points))
        owp_component = max(0, min(999, int(round(owp * 1000))))
        oowp_component = max(0, min(999, int(round(oowp * 1000))))
        return points_component * 1_000_000 + owp_component * 1_000 + oowp_component
