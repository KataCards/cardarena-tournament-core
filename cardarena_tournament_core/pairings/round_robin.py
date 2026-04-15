from cardarena_tournament_core.models import Matchup, Participant, Player, Round
from cardarena_tournament_core.pairings.base import BasePairing


class RoundRobin(BasePairing):
    """Circle-method round robin. Produces n−1 rounds (n even) or n rounds (n odd, with byes)."""

    def __init__(self, participants: list[Participant]) -> None:
        super().__init__(participants)
        self._schedule = self._build_schedule()

    def _build_schedule(self) -> list[list[tuple[Participant, Participant | None]]]:
        participants_list: list[Participant] = list(self.participants)
        if len(participants_list) % 2 == 1:
            participants_list.append(Player(id="__bye__", name="BYE"))

        n = len(participants_list)
        # Fix participants_list[0]; rotate participants_list[1:] each round
        fixed = participants_list[0]
        rotating = participants_list[1:]
        schedule: list[list[tuple[Participant, Participant | None]]] = []

        for _ in range(n - 1):
            pairs: list[tuple[Participant, Participant | None]] = []

            # First pair: fixed vs rotating[-1] (last in the rotating ring)
            pairs.append(_as_pair(fixed, rotating[-1]))

            # Remaining pairs: rotating[i] vs rotating[n-2-i-1]
            for i in range(n // 2 - 1):
                pairs.append(_as_pair(rotating[i], rotating[n - 3 - i]))

            schedule.append(pairs)
            # Rotate: move last element to front
            rotating = [rotating[-1]] + rotating[:-1]

        return schedule

    def pair(self) -> Round:
        round_number = len(self._rounds) + 1
        pairs = self._schedule[round_number - 1]
        matchups = [Matchup(player1=p1, player2=p2) for p1, p2 in pairs]
        return Round(round_number=round_number, matchups=matchups)


def _as_pair(a: Participant, b: Participant) -> tuple[Participant, Participant | None]:
    if b.id == "__bye__":
        return (a, None)
    if a.id == "__bye__":
        return (b, None)
    return (a, b)
