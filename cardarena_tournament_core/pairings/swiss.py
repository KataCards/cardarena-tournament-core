from cardarena_tournament_core.models import Matchup, MatchupOutcome, Participant, Round
from cardarena_tournament_core.pairings.base import BasePairing

_MIN_WIN_PCT = 0.25


class Swiss(BasePairing):
    """Swiss-system pairing: players are sorted by points and paired against
    opponents of similar standing, avoiding rematches where possible.

    Args:
        participants: All participants entering the tournament.
        use_tiebreaker_sort: When ``True``, players with equal points are
            further ordered by OWP then OOWP before pairing, producing
            strength-of-schedule-aware brackets from round 2 onward.

    Point values used for internal ranking only — independent of the scoring system.
    Both current TCG presets (PokemonTCG, YuGiOh) use the same values.
    """

    WIN_POINTS: int = 3
    DRAW_POINTS: int = 1
    BYE_POINTS: int = 3

    def __init__(
        self,
        participants: list[Participant],
        use_tiebreaker_sort: bool = False,
    ) -> None:
        super().__init__(participants)
        self._points: dict[str, int] = {participant.id: 0 for participant in participants}
        self._played_pairs: set[frozenset[str]] = set()
        self._use_tiebreaker_sort = use_tiebreaker_sort

    # ── public interface ──────────────────────────────────────────────────────

    def pair(self) -> Round:
        """Generate the next round's matchups.

        Players are sorted by points (descending).  When ``use_tiebreaker_sort``
        is enabled and at least one round has been played, equal-point players
        are further sorted by OWP then OOWP.  Each player is then greedily
        paired with the highest-ranked available opponent they haven't yet faced.
        Odd players out receive a bye.
        """
        ranked_participants = self._rank_participants()
        already_paired: set[str] = set()
        matchups: list[Matchup] = []

        for participant in ranked_participants:
            if participant.id in already_paired:
                continue

            opponent = self._find_fresh_opponent(participant, ranked_participants, already_paired)

            if opponent is None:
                # No unplayed opponent available — allow a repeat rather than leaving unpaired
                opponent = self._find_any_opponent(participant, ranked_participants, already_paired)

            if opponent is not None:
                matchups.append(Matchup(player1=participant, player2=opponent))
                already_paired.update([participant.id, opponent.id])
            else:
                matchups.append(Matchup(player1=participant, player2=None))
                already_paired.add(participant.id)

        return Round(round_number=len(self._rounds) + 1, matchups=matchups)

    def submit_results(self, completed_round: Round) -> None:
        """Record outcomes and update points and pairing history."""
        for matchup in completed_round.matchups:
            if matchup.player2 is None:
                self._points[matchup.player1.id] += self.BYE_POINTS
            elif matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                self._points[matchup.player1.id] += self.WIN_POINTS
                self._played_pairs.add(frozenset([matchup.player1.id, matchup.player2.id]))
            elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                self._points[matchup.player2.id] += self.WIN_POINTS
                self._played_pairs.add(frozenset([matchup.player1.id, matchup.player2.id]))
            elif matchup.outcome == MatchupOutcome.DRAW:
                self._points[matchup.player1.id] += self.DRAW_POINTS
                self._points[matchup.player2.id] += self.DRAW_POINTS
                self._played_pairs.add(frozenset([matchup.player1.id, matchup.player2.id]))
        super().submit_results(completed_round)

    # ── private helpers ───────────────────────────────────────────────────────

    def _rank_participants(self) -> list[Participant]:
        if self._use_tiebreaker_sort and self._rounds:
            return sorted(
                self.participants,
                key=lambda participant: (
                    self._points[participant.id],
                    self._owp(participant.id),
                    self._oowp(participant.id),
                ),
                reverse=True,
            )
        return sorted(
            self.participants,
            key=lambda participant: self._points[participant.id],
            reverse=True,
        )

    def _find_fresh_opponent(
        self,
        participant: Participant,
        ranked_participants: list[Participant],
        already_paired: set[str],
    ) -> Participant | None:
        return next(
            (
                candidate
                for candidate in ranked_participants
                if candidate.id not in already_paired
                and candidate.id != participant.id
                and frozenset([participant.id, candidate.id]) not in self._played_pairs
            ),
            None,
        )

    def _find_any_opponent(
        self,
        participant: Participant,
        ranked_participants: list[Participant],
        already_paired: set[str],
    ) -> Participant | None:
        return next(
            (
                candidate
                for candidate in ranked_participants
                if candidate.id not in already_paired
                and candidate.id != participant.id
            ),
            None,
        )

    # ── tiebreaker helpers (used only when use_tiebreaker_sort=True) ──────────

    def _win_percentage(self, player_id: str) -> float:
        """Win% for a player across all submitted rounds (byes excluded, floored at 0.25)."""
        wins = draws = total_games = 0
        for tournament_round in self._rounds:
            for matchup in tournament_round.matchups:
                if matchup.player2 is None:
                    continue  # byes don't count toward win percentage
                if matchup.player1.id == player_id:
                    total_games += 1
                    if matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                        wins += 1
                    elif matchup.outcome == MatchupOutcome.DRAW:
                        draws += 1
                elif matchup.player2.id == player_id:
                    total_games += 1
                    if matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                        wins += 1
                    elif matchup.outcome == MatchupOutcome.DRAW:
                        draws += 1
        if total_games == 0:
            return _MIN_WIN_PCT
        return max((wins + 0.5 * draws) / total_games, _MIN_WIN_PCT)

    def _real_opponent_ids(self, player_id: str) -> list[str]:
        """IDs of all real opponents faced so far (bye matches excluded)."""
        opponent_ids: list[str] = []
        for tournament_round in self._rounds:
            for matchup in tournament_round.matchups:
                if matchup.player2 is None:
                    continue
                if matchup.player1.id == player_id:
                    opponent_ids.append(matchup.player2.id)
                elif matchup.player2.id == player_id:
                    opponent_ids.append(matchup.player1.id)
        return opponent_ids

    def _owp(self, player_id: str) -> float:
        """Opponents' Win Percentage: average win% across all real opponents."""
        opponent_ids = self._real_opponent_ids(player_id)
        if not opponent_ids:
            return 0.0
        return sum(self._win_percentage(opponent_id) for opponent_id in opponent_ids) / len(opponent_ids)

    def _oowp(self, player_id: str) -> float:
        """Opponents' Opponents' Win Percentage: average OWP across all real opponents."""
        opponent_ids = self._real_opponent_ids(player_id)
        if not opponent_ids:
            return 0.0
        return sum(self._owp(opponent_id) for opponent_id in opponent_ids) / len(opponent_ids)
