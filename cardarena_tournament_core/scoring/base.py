"""Base classes for tournament scoring systems."""

from abc import ABC, abstractmethod

from cardarena_tournament_core.models import MatchupOutcome, Participant, Round, Standing
from cardarena_tournament_core import utils


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


class TCGBaseScoring(BaseScoring):
    """Intermediate base for TCG scoring systems.

    Provides shared point calculation and tiebreaker helpers used by all TCG
    formats.  Concrete subclasses must still implement :meth:`calculate` with
    their own final sorting and standing construction.

    Class attributes (must be defined by subclasses):
        WIN_POINTS: Points awarded for a win.
        DRAW_POINTS: Points awarded for a draw.
        LOSS_POINTS: Points awarded for a loss (typically 0).
        BYE_POINTS: Points awarded for a bye.
    """

    WIN_POINTS: int
    DRAW_POINTS: int
    LOSS_POINTS: int
    BYE_POINTS: int

    def _collect_players(self, rounds: list[Round]) -> dict[str, Participant]:
        """Build an ``{id: participant}`` map from every matchup across all rounds."""
        player_map: dict[str, Participant] = {}
        for tournament_round in rounds:
            for matchup in tournament_round.matchups:
                player_map[matchup.player1.id] = matchup.player1
                if matchup.player2 is not None:
                    player_map[matchup.player2.id] = matchup.player2
        return player_map

    def _calculate_points(self, rounds: list[Round]) -> dict[str, int]:
        """Calculate total points for each player across all rounds.

        Uses the class's WIN_POINTS, DRAW_POINTS, LOSS_POINTS, and BYE_POINTS
        constants to award points based on match outcomes.

        Args:
            rounds: All completed rounds to analyze.

        Returns:
            Dictionary mapping player IDs to their total points.
        """
        player_map = self._collect_players(rounds)
        points_by_player: dict[str, int] = {player_id: 0 for player_id in player_map}

        for tournament_round in rounds:
            for matchup in tournament_round.matchups:
                if matchup.player2 is None:
                    points_by_player[matchup.player1.id] += self.BYE_POINTS
                elif matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                    points_by_player[matchup.player1.id] += self.WIN_POINTS
                    points_by_player[matchup.player2.id] += self.LOSS_POINTS
                elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                    points_by_player[matchup.player2.id] += self.WIN_POINTS
                    points_by_player[matchup.player1.id] += self.LOSS_POINTS
                elif matchup.outcome == MatchupOutcome.DRAW:
                    points_by_player[matchup.player1.id] += self.DRAW_POINTS
                    points_by_player[matchup.player2.id] += self.DRAW_POINTS

        return points_by_player

    def _calculate_tiebreakers(
        self, player_ids: list[str], rounds: list[Round], *, min_win_pct: float = 0.0
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Calculate OWP and OOWP for all players.

        Args:
            player_ids: List of all player IDs to calculate tiebreakers for.
            rounds: All completed rounds to analyze.
            min_win_pct: Minimum win percentage floor (0.0 = no floor, 0.25 = Pokémon).

        Returns:
            Tuple of (owp_by_player, oowp_by_player) dictionaries.
        """
        owp_by_player: dict[str, float] = {
            player_id: utils.owp(player_id, rounds, min_win_pct=min_win_pct)
            for player_id in player_ids
        }
        oowp_by_player: dict[str, float] = {
            player_id: utils.oowp(player_id, rounds, min_win_pct=min_win_pct)
            for player_id in player_ids
        }
        return owp_by_player, oowp_by_player