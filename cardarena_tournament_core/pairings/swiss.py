from collections.abc import Sequence
from typing import Any

from cardarena_tournament_core.common.errors import (
    PairingConfigurationError,
    PairingStateError,
    TournamentCompleteError,
)
from cardarena_tournament_core.common.models import (
    Matchup,
    MatchupOutcome,
    Participant,
    Round,
    participant_from_dict,
    participant_to_dict,
)
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

        self._points: dict[str, int] = {
            participant.id: 0 for participant in self._participants
        }
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

        if not ranked_participants:
            raise TournamentCompleteError(
                "No active participants remain — the tournament cannot be paired."
            )

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

    # -------------------------------------------------------------------------
    # Serialization and reconstruction
    # -------------------------------------------------------------------------

    @classmethod
    def from_history(
        cls,
        participants: Sequence[Participant],
        rounds: Sequence[Round],
        active_participant_ids: set[str],
        use_tiebreaker_sort: bool = False,
        win_points: int = DEFAULT_WIN_POINTS,
        draw_points: int = DEFAULT_DRAW_POINTS,
        bye_points: int = DEFAULT_BYE_POINTS,
        tiebreaker_min_win_pct: float = 0.25,
    ) -> "Swiss":
        """Reconstruct a Swiss tournament from its round history.

        Enables stateless operation by rebuilding all internal state (_points,
        _played_pairs, etc.) from the complete round history. The reconstructed
        instance will have identical state to one that processed the same rounds
        sequentially.

        Args:
            participants: All tournament participants (must include all players
                         that appear in any round).
            rounds: Complete round history in chronological order. Each round
                   must have all outcomes recorded (is_complete == True).
            active_participant_ids: Set of participant IDs currently eligible
                                   for pairing. Always provided by design.
            use_tiebreaker_sort: Enable OWP/OOWP tiebreaker sorting.
            win_points: Points awarded for a win.
            draw_points: Points awarded for a draw.
            bye_points: Points awarded for a bye.
            tiebreaker_min_win_pct: Minimum win percentage floor for tiebreakers.

        Returns:
            Swiss instance with state matching the provided history.

        Raises:
            PairingConfigurationError: Invalid configuration parameters.
            PairingStateError: Round history is invalid (incomplete rounds,
                              unknown participants, out-of-order rounds, or
                              active_participant_ids contains unknown IDs).

        Example:
            >>> # Reconstruct from external storage
            >>> swiss = Swiss.from_history(
            ...     participants=[participant_from_dict(p) for p in data["participants"]],
            ...     rounds=[Round.from_dict(r) for r in data["rounds"]],
            ...     active_participant_ids=set(data["active_participant_ids"]),
            ...     **data["config"]
            ... )
            >>> next_round = swiss.pair()
        """
        # Create fresh instance with initial state
        instance = cls(
            participants=participants,
            use_tiebreaker_sort=use_tiebreaker_sort,
            win_points=win_points,
            draw_points=draw_points,
            bye_points=bye_points,
            tiebreaker_min_win_pct=tiebreaker_min_win_pct,
        )

        # STRICT VALIDATION: Verify all active IDs are registered participants
        unknown_ids = active_participant_ids - instance._participant_ids
        if unknown_ids:
            raise PairingStateError(
                f"active_participant_ids contains unregistered participants: "
                f"{', '.join(sorted(unknown_ids))}"
            )

        # Set active participants (always provided by design)
        instance._active_ids = set(active_participant_ids)

        # Replay all rounds to rebuild derived state (_points, _played_pairs)
        for round_obj in rounds:
            # STRICT VALIDATION: Fail fast on incomplete rounds
            if not round_obj.is_complete:
                raise PairingStateError(
                    f"Cannot reconstruct from incomplete round {round_obj.round_number}. "
                    f"All rounds must have recorded outcomes."
                )

            # submit_results will:
            # 1. Validate round integrity (sequential numbering, valid participants)
            # 2. Update _points based on outcomes
            # 3. Update _played_pairs with new matchups
            # 4. Append to _rounds history
            instance.submit_results(round_obj)

        return instance

    def to_dict(self) -> dict[str, Any]:
        """Export tournament state for persistence.

        Returns a dictionary containing all data needed to reconstruct this
        tournament via from_history() or to serialize to a database.

        Returns:
            Dictionary with keys:
            - participants: List of participant dicts
            - rounds: List of round dicts
            - active_participant_ids: List of active participant IDs
            - config: Configuration parameters

        Example:
            >>> swiss = Swiss(players, use_tiebreaker_sort=True)
            >>> # ... run tournament ...
            >>> state = swiss.to_dict()
            >>> # Save to external storage
        """
        return {
            "participants": [participant_to_dict(p) for p in self._participants],
            "rounds": [r.to_dict() for r in self._rounds],
            "active_participant_ids": sorted(self._active_ids),
            "config": {
                "use_tiebreaker_sort": self._use_tiebreaker_sort,
                "win_points": self._win_points,
                "draw_points": self._draw_points,
                "bye_points": self._bye_points,
                "tiebreaker_min_win_pct": self._tiebreaker_min_win_pct,
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Swiss":
        """Reconstruct tournament from serialized state.

        Convenience wrapper around from_history() that accepts the dictionary
        format produced by to_dict().

        Args:
            data: Dictionary from to_dict() or database.

        Returns:
            Reconstructed Swiss instance.

        Example:
            >>> state = load_from_storage(tournament_id)
            >>> swiss = Swiss.from_dict(state)
            >>> next_round = swiss.pair()
        """
        participants = [participant_from_dict(p) for p in data["participants"]]
        rounds = [Round.from_dict(r) for r in data["rounds"]]
        active_ids = set(data["active_participant_ids"])
        config = data["config"]

        return cls.from_history(
            participants=participants,
            rounds=rounds,
            active_participant_ids=active_ids,
            **config
        )