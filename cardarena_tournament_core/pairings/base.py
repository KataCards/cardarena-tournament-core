from abc import ABC, abstractmethod
from collections.abc import Sequence

from cardarena_tournament_core.common.errors import (
    PairingConfigurationError,
    PairingStateError,
)
from cardarena_tournament_core.common.models import Participant, Round


class BasePairing(ABC):
    """Abstract base class for all tournament pairing formats.

    Subclasses implement :meth:`pair` to generate the next round's matchups and
    may override :meth:`submit_results` to update internal state (e.g. points,
    active-player lists).  Always call ``super().submit_results(completed_round)``
    at the end of any override so the round history stays consistent.
    """

    # -------------------------------------------------------------------------
    # Initialization and validation
    # -------------------------------------------------------------------------

    def __init__(self, participants: Sequence[Participant]) -> None:
        participant_list = list(participants)
        if not participant_list:
            raise PairingConfigurationError(
                "At least one participant is required to initialize a pairing format."
            )

        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        for participant in participant_list:
            if participant.id in seen_ids:
                duplicate_ids.add(participant.id)
            seen_ids.add(participant.id)

        if duplicate_ids:
            duplicates = ", ".join(sorted(duplicate_ids))
            raise PairingConfigurationError(
                f"Participant ids must be unique. Duplicates found: {duplicates}."
            )

        self._participants: list[Participant] = participant_list
        self._participant_ids: set[str] = seen_ids
        self._active_ids: set[str] = set(seen_ids)
        self._rounds: list[Round] = []
        self._round_snapshots: dict[int, frozenset[str]] = {}

    # -------------------------------------------------------------------------
    # Active roster lifecycle
    # -------------------------------------------------------------------------

    def remove_active_participant(self, player_id: str) -> None:
        """Mark a participant as inactive for future pairings.

        Historical rounds, points, and tiebreaker data are preserved.
        The participant will not appear as a candidate in future ``pair()`` calls.

        Raises:
            PairingStateError: *player_id* is not registered, or is already inactive.
        """
        if player_id not in self._participant_ids:
            raise PairingStateError(
                f"Cannot remove participant '{player_id}': not registered in this tournament."
            )
        if player_id not in self._active_ids:
            raise PairingStateError(
                f"Cannot remove participant '{player_id}': already inactive."
            )
        self._active_ids.remove(player_id)

    def reactivate_participant(self, player_id: str) -> None:
        """Re-admit an inactive participant for future pairings.

        Raises:
            PairingStateError: *player_id* is not registered, or is already active.
        """
        if player_id not in self._participant_ids:
            raise PairingStateError(
                f"Cannot reactivate participant '{player_id}': not registered in this tournament."
            )
        if player_id in self._active_ids:
            raise PairingStateError(
                f"Cannot reactivate participant '{player_id}': already active."
            )
        self._active_ids.add(player_id)

    # -------------------------------------------------------------------------
    # Internal snapshot registry
    # -------------------------------------------------------------------------

    def _register_round_snapshot(self, round_number: int) -> None:
        """Save the current active-id set as the authoritative participant list
        for *round_number*.  Called by ``pair()`` implementations just before
        returning a new round.

        The snapshot is used by ``_validate_round_submission`` so that a removal
        made *after* pairing does not prevent submission of that already-paired round.
        """
        self._round_snapshots[round_number] = frozenset(self._active_ids)

    # -------------------------------------------------------------------------
    # Internal validation
    # -------------------------------------------------------------------------

    def _validate_round_submission(self, completed_round: Round) -> None:
        expected_round_number = len(self._rounds) + 1
        if completed_round.round_number != expected_round_number:
            raise PairingStateError(
                "Round submission out of order. "
                f"Expected round {expected_round_number}, got {completed_round.round_number}."
            )

        if not completed_round.matchups:
            raise PairingStateError("Submitted round must contain at least one matchup.")

        if not completed_round.is_complete:
            raise PairingStateError(
                "Cannot submit incomplete rounds. Record all matchup outcomes first."
            )

        # Use the snapshot taken at pair() time when available; fall back to all
        # registered participant IDs for backward compatibility with formats that
        # do not register snapshots.
        valid_ids: frozenset[str] | set[str] = self._round_snapshots.get(
            completed_round.round_number, self._participant_ids
        )

        for matchup in completed_round.matchups:
            if matchup.player1.id not in valid_ids:
                raise PairingStateError(
                    "Round contains a participant that is not registered in this tournament: "
                    f"{matchup.player1.id}."
                )
            if matchup.player2 is not None and matchup.player2.id not in valid_ids:
                raise PairingStateError(
                    "Round contains a participant that is not registered in this tournament: "
                    f"{matchup.player2.id}."
                )

    # -------------------------------------------------------------------------
    # Pairing / Submission interface
    # -------------------------------------------------------------------------

    @abstractmethod
    def pair(self) -> Round:
        """Generate and return the next round's pairings."""
        ...

    def submit_results(self, completed_round: Round) -> None:
        """Record a completed round.

        Subclasses should update their own state first, then call
        ``super().submit_results(completed_round)`` to append to the history.
        """
        self._validate_round_submission(completed_round)
        self._rounds.append(completed_round)

    # -------------------------------------------------------------------------
    # Read-only views
    # -------------------------------------------------------------------------

    @property
    def participants(self) -> list[Participant]:
        """All participants in this tournament (read-only copy)."""
        return list(self._participants)

    @property
    def active_participant_ids(self) -> frozenset[str]:
        """IDs of participants currently eligible for future pairings (read-only)."""
        return frozenset(self._active_ids)

    @property
    def rounds(self) -> list[Round]:
        """All submitted rounds in chronological order (read-only copy)."""
        return list(self._rounds)


__all__ = ["BasePairing"]
