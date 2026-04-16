"""Shared OWP/OOWP tiebreaker helpers for TCG scoring systems.

This module is an internal implementation detail — it is not part of the public
API.  ``TCGBaseScoring`` exists solely to deduplicate the OWP/OOWP calculation
shared by every TCG scoring class; it carries no TCG-specific rules itself.
"""

from cardarena_tournament_core.models import MatchupOutcome, Participant, Round
from cardarena_tournament_core.scoring.base.base import BaseScoring

_MIN_WIN_PCT = 0.25


class TCGBaseScoring(BaseScoring):
    """Intermediate base for TCG scoring systems.

    Provides OWP and OOWP helpers used by all TCG formats.  Concrete
    subclasses must still implement :meth:`calculate` with their own point
    values and sort key.
    """

    def _collect_players(self, rounds: list[Round]) -> dict[str, Participant]:
        """Build an ``{id: participant}`` map from every matchup across all rounds."""
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
        """IDs of every real opponent *player_id* has faced (bye matches excluded)."""
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
