from cardarena_tournament_core.models import Matchup, MatchupOutcome, Participant, Round
from cardarena_tournament_core.pairings.base import BasePairing


class SingleElimination(BasePairing):
    """Single-elimination bracket. Losers are eliminated; winners advance each round."""

    def __init__(self, participants: list[Participant]) -> None:
        super().__init__(participants)
        self._active: list[Participant] = list(participants)

    def pair(self) -> Round:
        active = self._active
        mid = len(active) // 2
        matchups: list[Matchup] = [
            Matchup(player1=active[i], player2=active[len(active) - 1 - i])
            for i in range(mid)
        ]
        if len(active) % 2 == 1:
            matchups.append(Matchup(player1=active[mid], player2=None))
        return Round(round_number=len(self._rounds) + 1, matchups=matchups)

    def submit_results(self, round: Round) -> None:
        winners: list[Participant] = []
        for m in round.matchups:
            if m.player2 is None:
                winners.append(m.player1)
            elif m.outcome == MatchupOutcome.PLAYER1_WINS:
                winners.append(m.player1)
            elif m.outcome == MatchupOutcome.PLAYER2_WINS:
                winners.append(m.player2)
        self._active = winners
        super().submit_results(round)
