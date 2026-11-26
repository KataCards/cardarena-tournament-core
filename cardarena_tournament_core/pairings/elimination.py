from collections.abc import Sequence
from typing import Any

from cardarena_tournament_core.common.models import (
    Participant,
    Round,
    participant_from_dict,
)
from cardarena_tournament_core.pairings._bracket import BracketPairing, MatchNode, NodeBuilder


class SingleElimination(BracketPairing):
    """Single-elimination bracket: lose once and you're out.

    The participant list is the seed order (first = seed 1).  Seeds are placed
    in standard bracket positions — for eight participants round 1 is 1v8,
    4v5, 2v7, 3v6 — so the top seeds can only meet late.  When the field is not
    a power of two the top seeds receive first-round byes.

    Each later round pairs the winners of adjacent matches of the round
    before.  A participant whose opponent slot is empty (after a double loss
    or a withdrawal) advances by walkover, emitted as a bye matchup.

    Matchups must end ``PLAYER1_WINS``, ``PLAYER2_WINS`` or ``DOUBLE_LOSS``.
    A double loss eliminates both players.

    The tournament is complete as soon as at most one participant is still
    active; see :attr:`is_complete` and :attr:`champion`.
    """

    # -------------------------------------------------------------------------
    # Bracket definition
    # -------------------------------------------------------------------------

    def _build_nodes(self) -> list[MatchNode]:
        builder = NodeBuilder()
        builder.add_winners_rounds(self._participants)
        return builder.nodes

    # -------------------------------------------------------------------------
    # Serialization and reconstruction
    # -------------------------------------------------------------------------

    @classmethod
    def from_history(
        cls,
        participants: Sequence[Participant],
        rounds: Sequence[Round],
        active_participant_ids: set[str],
    ) -> "SingleElimination":
        """Reconstruct a single-elimination tournament from its round history.

        Results and withdrawals are read from the rounds themselves.  After
        the replay a participant is active only if they are still in the
        bracket *and* their id is in *active_participant_ids*; that covers
        withdrawals made since the last submitted round.

        Args:
            participants: All tournament participants in seeding order.
            rounds: Complete round history in chronological order.
            active_participant_ids: Ids currently eligible for pairing.

        Raises:
            PairingConfigurationError: Invalid participant list.
            PairingStateError: A round is incomplete or does not fit the
                bracket, or *active_participant_ids* contains unknown ids.
        """
        instance = cls(participants=participants)
        instance._replay(rounds, active_participant_ids)
        return instance

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SingleElimination":
        """Reconstruct a tournament from the output of :meth:`to_dict`."""
        return cls.from_history(
            participants=[participant_from_dict(p) for p in data["participants"]],
            rounds=[Round.from_dict(r) for r in data["rounds"]],
            active_participant_ids=set(data["active_participant_ids"]),
        )
