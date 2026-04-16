from cardarena_tournament_core.models import Matchup, Participant, Player, Round, TournamentCompleteError
from cardarena_tournament_core.pairings.base import BasePairing

_BYE_PLAYER = Player(id="__bye__", name="BYE")


class RoundRobin(BasePairing):
    """Round-robin pairing using the circle (Berger) method.

    Every participant faces every other participant exactly once.
    - Even number of participants → ``n - 1`` rounds, no byes.
    - Odd number of participants → ``n`` rounds, one bye per round
      (a phantom BYE participant is added internally).
    """

    def __init__(self, participants: list[Participant]) -> None:
        super().__init__(participants)
        self._schedule: list[list[tuple[Participant, Participant | None]]] = (
            self._build_schedule()
        )

    def pair(self) -> Round:
        """Return the pre-computed matchups for the next round.

        Raises:
            TournamentCompleteError: All scheduled rounds have been played.
        """
        next_round_number = len(self._rounds) + 1
        if next_round_number > len(self._schedule):
            raise TournamentCompleteError(
                f"All {len(self._schedule)} rounds of this round-robin have been played."
            )
        scheduled_pairs = self._schedule[next_round_number - 1]
        matchups = [
            Matchup(player1=home, player2=away) for home, away in scheduled_pairs
        ]
        return Round(round_number=next_round_number, matchups=matchups)

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_schedule(self) -> list[list[tuple[Participant, Participant | None]]]:
        """Pre-compute all rounds using the circle method.

        One participant is fixed; the rest rotate one position clockwise each
        round.  Byes are introduced by padding with a phantom participant when
        the field is odd.
        """
        padded_participants: list[Participant] = list(self.participants)
        if len(padded_participants) % 2 == 1:
            padded_participants.append(_BYE_PLAYER)

        player_count = len(padded_participants)
        fixed_participant = padded_participants[0]
        rotating_participants = padded_participants[1:]

        schedule: list[list[tuple[Participant, Participant | None]]] = []

        for _ in range(player_count - 1):
            round_pairs: list[tuple[Participant, Participant | None]] = []

            # Fixed participant always plays the last participant in the rotating list
            round_pairs.append(
                _resolve_bye(fixed_participant, rotating_participants[-1])
            )

            # Pair remaining participants: front half vs mirrored back half
            for seat_index in range(player_count // 2 - 1):
                mirror_index = player_count - 3 - seat_index
                round_pairs.append(
                    _resolve_bye(rotating_participants[seat_index], rotating_participants[mirror_index])
                )

            schedule.append(round_pairs)
            # Rotate: bring the last element to the front
            rotating_participants = [rotating_participants[-1]] + rotating_participants[:-1]

        return schedule


def _resolve_bye(
    participant_a: Participant,
    participant_b: Participant,
) -> tuple[Participant, Participant | None]:
    """Return a ``(player1, player2)`` pair, replacing the phantom BYE with ``None``."""
    if participant_b.id == _BYE_PLAYER.id:
        return (participant_a, None)
    if participant_a.id == _BYE_PLAYER.id:
        return (participant_b, None)
    return (participant_a, participant_b)
