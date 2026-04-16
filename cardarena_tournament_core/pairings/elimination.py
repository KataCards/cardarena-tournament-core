from cardarena_tournament_core.models import Matchup, MatchupOutcome, Participant, Round, TournamentCompleteError
from cardarena_tournament_core.pairings.base import BasePairing


class SingleElimination(BasePairing):
    """Single-elimination bracket: lose once and you're out.

    Participants are seeded in the order they are provided.  Round 1 pairs
    seed 1 vs. seed N, seed 2 vs. seed N-1, etc.  Winners advance; losers
    are eliminated.  An odd number of active participants gives the middle
    seed a bye (automatic advancement).
    """

    def __init__(self, participants: list[Participant]) -> None:
        super().__init__(participants)
        self._active_participants: list[Participant] = list(participants)

    def pair(self) -> Round:
        """Generate matchups for the current elimination round.

        Seeds are mirrored: the highest seed plays the lowest, the second
        highest plays the second lowest, and so on.

        Raises:
            TournamentCompleteError: A champion has been determined (one active
                participant remains) or all participants have been eliminated.
        """
        active = self._active_participants
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
            # Middle seed has no opponent this round — advances automatically
            matchups.append(Matchup(player1=active[half], player2=None))

        return Round(round_number=len(self._rounds) + 1, matchups=matchups)

    def submit_results(self, completed_round: Round) -> None:
        """Eliminate losers and update the active participant list."""
        winners: list[Participant] = []
        for matchup in completed_round.matchups:
            if matchup.player2 is None:
                winners.append(matchup.player1)
            elif matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                winners.append(matchup.player1)
            elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                winners.append(matchup.player2)
        self._active_participants = winners
        super().submit_results(completed_round)
