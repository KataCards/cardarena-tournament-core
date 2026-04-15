from cardarena_tournament_core.models import MatchupOutcome, Participant, Round, Standing
from cardarena_tournament_core.scoring.base import BaseScoring

_MIN_WIN_PCT = 0.25


class YuGiOh(BaseScoring):
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
        player_map: dict[str, Participant] = self._collect_players(rounds)
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

    # ── tiebreaker helpers ────────────────────────────────────────────────────

    def _collect_players(self, rounds: list[Round]) -> dict[str, Participant]:
        """Build an id → participant map from all matchups in *rounds*."""
        player_map: dict[str, Participant] = {}
        for tournament_round in rounds:
            for matchup in tournament_round.matchups:
                player_map[matchup.player1.id] = matchup.player1
                if matchup.player2 is not None:
                    player_map[matchup.player2.id] = matchup.player2
        return player_map

    def _win_percentage(self, player_id: str, rounds: list[Round]) -> float:
        """Win% = (wins + 0.5 × draws) / real games played, floored at 25 %.

        Bye matches are excluded — they don't count as real games.
        """
        wins = draws = total_real_games = 0
        for tournament_round in rounds:
            for matchup in tournament_round.matchups:
                if matchup.player2 is None:
                    continue  # bye — not a real game
                if matchup.player1.id == player_id:
                    total_real_games += 1
                    if matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                        wins += 1
                    elif matchup.outcome == MatchupOutcome.DRAW:
                        draws += 1
                elif matchup.player2.id == player_id:
                    total_real_games += 1
                    if matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                        wins += 1
                    elif matchup.outcome == MatchupOutcome.DRAW:
                        draws += 1
        if total_real_games == 0:
            return _MIN_WIN_PCT
        return max((wins + 0.5 * draws) / total_real_games, _MIN_WIN_PCT)

    def _real_opponent_ids(self, player_id: str, rounds: list[Round]) -> list[str]:
        """IDs of every real opponent *player_id* has faced (byes excluded)."""
        opponent_ids: list[str] = []
        for tournament_round in rounds:
            for matchup in tournament_round.matchups:
                if matchup.player2 is None:
                    continue
                if matchup.player1.id == player_id:
                    opponent_ids.append(matchup.player2.id)
                elif matchup.player2.id == player_id:
                    opponent_ids.append(matchup.player1.id)
        return opponent_ids

    def _owp(self, player_id: str, rounds: list[Round]) -> float:
        """Opponents' Win Percentage: average win% of all real opponents."""
        opponent_ids = self._real_opponent_ids(player_id, rounds)
        if not opponent_ids:
            return 0.0
        return (
            sum(self._win_percentage(opponent_id, rounds) for opponent_id in opponent_ids)
            / len(opponent_ids)
        )

    def _oowp(self, player_id: str, rounds: list[Round]) -> float:
        """Opponents' Opponents' Win Percentage: average OWP of all real opponents."""
        opponent_ids = self._real_opponent_ids(player_id, rounds)
        if not opponent_ids:
            return 0.0
        return (
            sum(self._owp(opponent_id, rounds) for opponent_id in opponent_ids)
            / len(opponent_ids)
        )

    def _encode_tiebreak_number(self, points: int, owp: float, oowp: float) -> int:
        """Encode points + OWP + OOWP into the XXYYYZZZ integer format."""
        points_component = max(0, min(99, points))
        owp_component = max(0, min(999, int(round(owp * 1000))))
        oowp_component = max(0, min(999, int(round(oowp * 1000))))
        return points_component * 1_000_000 + owp_component * 1_000 + oowp_component
