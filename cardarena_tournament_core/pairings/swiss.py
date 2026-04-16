from collections.abc import Sequence

from cardarena_tournament_core.common.errors import (
    PairingConfigurationError,
    PairingStateError,
)
from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Participant, Round
from cardarena_tournament_core.pairings.base import BasePairing
from cardarena_tournament_core import utils


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

    DEFAULT_WIN_POINTS: int = 3
    DEFAULT_DRAW_POINTS: int = 1
    DEFAULT_BYE_POINTS: int = 3


    # -------------------------------------------------------------------------
    # Initialization and configuration
    # -------------------------------------------------------------------------

    def __init__(
        self,
        participants: Sequence[Participant],
        use_tiebreaker_sort: bool = False,
        win_points: int = DEFAULT_WIN_POINTS,
        draw_points: int = DEFAULT_DRAW_POINTS,
        bye_points: int = DEFAULT_BYE_POINTS,
        tiebreaker_min_win_pct: float = 0.25,
    ) -> None:
        super().__init__(participants)

        if win_points < 0 or draw_points < 0 or bye_points < 0:
            raise PairingConfigurationError("Swiss point values must be non-negative.")
        if draw_points > win_points:
            raise PairingConfigurationError(
                "draw_points cannot exceed win_points in Swiss pairing."
            )
        if bye_points > win_points:
            raise PairingConfigurationError(
                "bye_points cannot exceed win_points in Swiss pairing."
            )
        if not 0.0 <= tiebreaker_min_win_pct <= 1.0:
            raise PairingConfigurationError(
                "tiebreaker_min_win_pct must be within [0.0, 1.0]."
            )

        self._points: dict[str, int] = {participant.id: 0 for participant in participants}
        self._played_pairs: set[frozenset[str]] = set()
        self._use_tiebreaker_sort = use_tiebreaker_sort
        self._win_points = win_points
        self._draw_points = draw_points
        self._bye_points = bye_points
        self._tiebreaker_min_win_pct = tiebreaker_min_win_pct

    # -------------------------------------------------------------------------
    # Pairing / Submission interface
    # -------------------------------------------------------------------------

    def pair(self) -> Round:
        """Generate the next round's matchups.

        Players are sorted by points (descending).  When ``use_tiebreaker_sort``
        is enabled and at least one round has been played, equal-point players
        are further sorted by OWP then OOWP.  Each player is then greedily
        paired with the highest-ranked available opponent they haven't yet faced.
        Odd players out receive a bye.  Only active participants (not removed via
        ``remove_active_participant``) are considered as pairing candidates.
        """
        round_number = len(self._rounds) + 1
        ranked_participants = self._rank_participants()
        already_paired: set[str] = set()
        matchups: list[Matchup] = []

        for participant in ranked_participants:
            if participant.id in already_paired:
                continue

            opponent = self._find_opponent(participant, ranked_participants, already_paired, allow_repeat=False)

            if opponent is None:
                # No unplayed opponent available — allow a repeat rather than leaving unpaired
                opponent = self._find_opponent(participant, ranked_participants, already_paired, allow_repeat=True)

            if opponent is not None:
                matchups.append(Matchup(player1=participant, player2=opponent))
                already_paired.update([participant.id, opponent.id])
            else:
                matchups.append(Matchup(player1=participant, player2=None))
                already_paired.add(participant.id)

        self._register_round_snapshot(round_number)
        return Round(round_number=round_number, matchups=matchups)

    def submit_results(self, completed_round: Round) -> None:
        """Record outcomes and update points and pairing history."""
        for matchup in completed_round.matchups:
            if matchup.player2 is None:
                self._points[matchup.player1.id] += self._bye_points
            elif matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                self._points[matchup.player1.id] += self._win_points
                self._played_pairs.add(frozenset([matchup.player1.id, matchup.player2.id]))
            elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                self._points[matchup.player2.id] += self._win_points
                self._played_pairs.add(frozenset([matchup.player1.id, matchup.player2.id]))
            elif matchup.outcome == MatchupOutcome.DRAW:
                self._points[matchup.player1.id] += self._draw_points
                self._points[matchup.player2.id] += self._draw_points
                self._played_pairs.add(frozenset([matchup.player1.id, matchup.player2.id]))
            else:
                raise PairingStateError(
                    "Swiss matchups must resolve to PLAYER1_WINS, PLAYER2_WINS, or DRAW."
                )
        super().submit_results(completed_round)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _rank_participants(self) -> list[Participant]:
        active_participants = [p for p in self._participants if p.id in self._active_ids]
        if self._use_tiebreaker_sort and self._rounds:
            return sorted(
                active_participants,
                key=lambda participant: (
                    self._points[participant.id],
                    utils.owp(
                        participant.id,
                        self._rounds,
                        min_win_pct=self._tiebreaker_min_win_pct,
                    ),
                    utils.oowp(
                        participant.id,
                        self._rounds,
                        min_win_pct=self._tiebreaker_min_win_pct,
                    ),
                ),
                reverse=True,
            )
        return sorted(
            active_participants,
            key=lambda participant: self._points[participant.id],
            reverse=True,
        )

    def _find_opponent(
        self,
        participant: Participant,
        ranked_participants: list[Participant],
        already_paired: set[str],
        *,
        allow_repeat: bool,
    ) -> Participant | None:
        """Return the highest-ranked available opponent for *participant*.

        When ``allow_repeat`` is ``False``, only opponents not yet faced are
        considered.  When ``True``, previously played opponents are also eligible
        (used as a last resort to avoid leaving a player without a match).
        """
        return next(
            (
                candidate
                for candidate in ranked_participants
                if candidate.id not in already_paired
                and candidate.id != participant.id
                and (
                    allow_repeat
                    or frozenset([participant.id, candidate.id]) not in self._played_pairs
                )
            ),
            None,
        )