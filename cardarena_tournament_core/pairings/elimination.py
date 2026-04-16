from collections.abc import Sequence

from cardarena_tournament_core.common.errors import PairingStateError, TournamentCompleteError
from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Participant, Round
from cardarena_tournament_core.pairings.base import BasePairing


class SingleElimination(BasePairing):
    """Single-elimination bracket: lose once and you're out.

    Participants are seeded in the order they are provided.  Round 1 pairs
    seed 1 vs. seed N, seed 2 vs. seed N-1, etc.  Winners advance; losers
    are eliminated.  An odd number of active participants gives the middle
    seed a bye (automatic advancement).
    """

    # -------------------------------------------------------------------------
    # Initialization and configuration
    # -------------------------------------------------------------------------

    def __init__(self, participants: Sequence[Participant]) -> None:
        super().__init__(participants)
        # Original registration order drives deterministic seeding across all rounds.
        self._seeding_order: list[str] = [p.id for p in self._participants]
        self._participant_map: dict[str, Participant] = {p.id: p for p in self._participants}

    # -------------------------------------------------------------------------
    # Pairing / Submission interface
    # -------------------------------------------------------------------------

    def pair(self) -> Round:
        """Generate matchups for the current elimination round.

        Seeds are mirrored: the highest seed plays the lowest, the second
        highest plays the second lowest, and so on.

        Raises:
            TournamentCompleteError: A champion has been determined (one active
                participant remains) or all participants have been eliminated.
        """
        active = [
            self._participant_map[pid]
            for pid in self._seeding_order
            if pid in self._active_ids
        ]

        if len(active) <= 1:
            if len(active) == 1:
                raise TournamentCompleteError(
                    f"{active[0].name} is the champion — the tournament is complete."
                )
            raise TournamentCompleteError("All participants have been eliminated.")

        half = len(active) // 2
        matchups: list[Matchup] = [
            Matchup(player1=active[seed_index], player2=active[len(active) - 1 - seed_index])
            for seed_index in range(half)
        ]

        if len(active) % 2 == 1:
            matchups.append(Matchup(player1=active[half], player2=None))

        round_number = len(self._rounds) + 1
        self._register_round_snapshot(round_number)
        return Round(round_number=round_number, matchups=matchups)

    def submit_results(self, completed_round: Round) -> None:
        """Eliminate losers and update the active participant set."""
        winner_ids: list[str] = []
        for matchup in completed_round.matchups:
            if matchup.player2 is None:
                winner_ids.append(matchup.player1.id)
            elif matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                winner_ids.append(matchup.player1.id)
            elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                winner_ids.append(matchup.player2.id)
            else:
                raise PairingStateError(
                    "Single elimination matchups must end with PLAYER1_WINS or "
                    "PLAYER2_WINS."
                )

        if not winner_ids:
            raise PairingStateError(
                "Submitting this round produced no advancing participants."
            )

        self._active_ids = set(winner_ids)
        super().submit_results(completed_round)
