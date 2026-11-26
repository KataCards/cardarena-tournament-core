from collections.abc import Sequence
from typing import Any

from cardarena_tournament_core.common.models import (
    Bracket,
    Participant,
    Round,
    participant_from_dict,
)
from cardarena_tournament_core.pairings._bracket import (
    BracketPairing,
    LoserOf,
    MatchNode,
    NodeBuilder,
    Source,
    WinnerOf,
)


class DoubleElimination(BracketPairing):
    """Double-elimination bracket: a participant is out after two losses.

    Everyone starts in the winners bracket, seeded like
    :class:`SingleElimination`.  Losing there drops a participant into the
    losers bracket; losing in the losers bracket eliminates them.  The winners
    of the two brackets meet in the grand final.

    Args:
        participants: All participants in seed order (first = seed 1).
        grand_final_reset: When ``True`` (default) and the losers-bracket
            champion wins the grand final, both finalists have one loss and a
            second, deciding grand final is played.  When ``False`` the first
            grand final decides.

    Round schedule.  Each match is played in the earliest round after both of
    its feeder matches.  With winners rounds ``W1..Wn`` and losers rounds
    ``L1..L(2n-2)``, ``Wk`` is played in round ``k`` and ``Lj`` in round
    ``j + 1``; the grand final follows the last losers round.  For eight
    participants: ``W1`` | ``W2 + L1`` | ``W3 + L2`` | ``L3`` | ``L4`` |
    grand final | second grand final (if needed).

    Losers bracket layout.  ``L1`` pairs the losers of adjacent ``W1`` matches.
    Every even round ``L(2k)`` plays the previous losers-round winners against
    the losers dropping from ``W(k+1)``; the drops enter in reversed bracket
    order so that rematches come as late as possible.  Every odd round after
    ``L1`` pairs the previous losers-round winners with each other.

    Matchups carry a :class:`Bracket` label.  They must end ``PLAYER1_WINS``,
    ``PLAYER2_WINS`` or ``DOUBLE_LOSS``.  A double loss eliminates both
    players outright, in either bracket, and is rejected in a grand final.
    """

    # -------------------------------------------------------------------------
    # Initialization and configuration
    # -------------------------------------------------------------------------

    def __init__(
        self, participants: Sequence[Participant], grand_final_reset: bool = True
    ) -> None:
        # Set before super().__init__(), which builds the bracket.
        self._grand_final_reset = grand_final_reset
        self._first_grand_final_id = -1
        super().__init__(participants)

    def _config(self) -> dict[str, Any]:
        return {"grand_final_reset": self._grand_final_reset}

    # -------------------------------------------------------------------------
    # Bracket definition
    # -------------------------------------------------------------------------

    def _build_nodes(self) -> list[MatchNode]:
        builder = NodeBuilder()
        winners = builder.add_winners_rounds(self._participants)
        winners_round_count = len(winners)

        losers_champion: Source
        if winners_round_count == 1:
            # Two participants: no losers bracket, the loser of W1 gets a second chance.
            losers_champion = LoserOf(winners[0][0].id)
            grand_final_stage = 2
        else:
            first = winners[0]
            previous = [
                builder.add(
                    2, Bracket.LOSERS, LoserOf(first[2 * i].id), LoserOf(first[2 * i + 1].id)
                )
                for i in range(len(first) // 2)
            ]
            for k in range(1, winners_round_count):
                drops = winners[k]
                previous = [
                    builder.add(
                        2 * k + 1,
                        Bracket.LOSERS,
                        WinnerOf(previous[i].id),
                        LoserOf(drops[len(drops) - 1 - i].id),
                    )
                    for i in range(len(drops))
                ]
                if k < winners_round_count - 1:
                    previous = [
                        builder.add(
                            2 * k + 2,
                            Bracket.LOSERS,
                            WinnerOf(previous[2 * i].id),
                            WinnerOf(previous[2 * i + 1].id),
                        )
                        for i in range(len(previous) // 2)
                    ]
            losers_champion = WinnerOf(previous[0].id)
            grand_final_stage = 2 * winners_round_count

        grand_final = builder.add(
            grand_final_stage,
            Bracket.GRAND_FINAL,
            WinnerOf(winners[-1][0].id),
            losers_champion,
        )
        self._first_grand_final_id = grand_final.id
        if self._grand_final_reset:
            # Slot 1 stays the winners-bracket champion, who lost the first final.
            builder.add(
                grand_final_stage + 1,
                Bracket.GRAND_FINAL,
                LoserOf(grand_final.id),
                WinnerOf(grand_final.id),
            )
        return builder.nodes

    def _loser_is_eliminated(self, node: MatchNode, loser_slot: int) -> bool:
        if node.bracket is Bracket.WINNERS:
            return False
        if node.id == self._first_grand_final_id and loser_slot == 1:
            # The winners-bracket champion's first loss.
            return not self._grand_final_reset
        return True

    # -------------------------------------------------------------------------
    # Serialization and reconstruction
    # -------------------------------------------------------------------------

    @classmethod
    def from_history(
        cls,
        participants: Sequence[Participant],
        rounds: Sequence[Round],
        active_participant_ids: set[str],
        grand_final_reset: bool = True,
    ) -> "DoubleElimination":
        """Reconstruct a double-elimination tournament from its round history.

        Results and withdrawals are read from the rounds themselves.  After
        the replay a participant is active only if they are still in the
        bracket *and* their id is in *active_participant_ids*.

        Raises:
            PairingConfigurationError: Invalid participant list.
            PairingStateError: A round is incomplete or does not fit the
                bracket, or *active_participant_ids* contains unknown ids.
        """
        instance = cls(participants=participants, grand_final_reset=grand_final_reset)
        instance._replay(rounds, active_participant_ids)
        return instance

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DoubleElimination":
        """Reconstruct a tournament from the output of :meth:`to_dict`."""
        return cls.from_history(
            participants=[participant_from_dict(p) for p in data["participants"]],
            rounds=[Round.from_dict(r) for r in data["rounds"]],
            active_participant_ids=set(data["active_participant_ids"]),
            **data.get("config", {}),
        )
