from cardarena_tournament_core.models import Matchup, MatchupOutcome, Participant, Round
from cardarena_tournament_core.pairings.base import BasePairing
from cardarena_tournament_core.scoring.tiebreakers import calculate_oowp, calculate_owp


class Swiss(BasePairing):
    def __init__(self, participants: list[Participant], use_tiebreaker_sort: bool = False) -> None:
        super().__init__(participants)
        self._points: dict[str, int] = {p.id: 0 for p in participants}
        self._played_pairs: set[frozenset[str]] = set()
        self._use_tiebreaker_sort = use_tiebreaker_sort

    def pair(self) -> Round:
        if self._use_tiebreaker_sort and self._rounds:
            sorted_participants = sorted(
                self.participants,
                key=lambda p: (
                    self._points[p.id],
                    calculate_owp(p.id, self._rounds),
                    calculate_oowp(p.id, self._rounds),
                ),
                reverse=True,
            )
        else:
            sorted_participants = sorted(
                self.participants, key=lambda p: self._points[p.id], reverse=True
            )

        paired: set[str] = set()
        matchups: list[Matchup] = []

        for participant in sorted_participants:
            if participant.id in paired:
                continue

            # Find best available opponent not yet played
            opponent = next(
                (
                    opp
                    for opp in sorted_participants
                    if opp.id not in paired
                    and opp.id != participant.id
                    and frozenset([participant.id, opp.id]) not in self._played_pairs
                ),
                None,
            )

            # Fallback: allow repeat if no fresh opponent exists
            if opponent is None:
                opponent = next(
                    (
                        opp
                        for opp in sorted_participants
                        if opp.id not in paired and opp.id != participant.id
                    ),
                    None,
                )

            if opponent is not None:
                matchups.append(Matchup(player1=participant, player2=opponent))
                paired.update([participant.id, opponent.id])
            else:
                matchups.append(Matchup(player1=participant, player2=None))
                paired.add(participant.id)

        return Round(round_number=len(self._rounds) + 1, matchups=matchups)

    def submit_results(self, round: Round) -> None:
        for m in round.matchups:
            if m.player2 is None:
                self._points[m.player1.id] += 3
            elif m.outcome == MatchupOutcome.PLAYER1_WINS:
                self._points[m.player1.id] += 3
                self._played_pairs.add(frozenset([m.player1.id, m.player2.id]))
            elif m.outcome == MatchupOutcome.PLAYER2_WINS:
                self._points[m.player2.id] += 3
                self._played_pairs.add(frozenset([m.player1.id, m.player2.id]))
            elif m.outcome == MatchupOutcome.DRAW:
                self._points[m.player1.id] += 1
                self._points[m.player2.id] += 1
                self._played_pairs.add(frozenset([m.player1.id, m.player2.id]))
        super().submit_results(round)
