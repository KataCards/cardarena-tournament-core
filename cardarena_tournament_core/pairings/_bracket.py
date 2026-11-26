"""Shared engine for fixed-bracket formats (single and double elimination).

A bracket is a static graph of :class:`MatchNode` objects.  Each node has two
slots, and each slot is fed by a :class:`Seed`, the winner of an earlier node
(:class:`WinnerOf`) or the loser of an earlier node (:class:`LoserOf`).  Every
node belongs to a *stage*; all feeders of a node are in earlier stages.

The engine emits one :class:`Round` per stage that has something to play and
resolves submitted rounds against the graph.  Concrete formats only build the
graph and say when a loss eliminates a participant.
"""

import math
from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from cardarena_tournament_core.common.errors import PairingStateError, TournamentCompleteError
from cardarena_tournament_core.common.models import (
    Bracket,
    Matchup,
    MatchupOutcome,
    Participant,
    Round,
    Standing,
    participant_to_dict,
)
from cardarena_tournament_core.pairings.base import BasePairing


# -------------------------------------------------------------------------
# Seeding helpers
# -------------------------------------------------------------------------


def bracket_size(participant_count: int) -> int:
    """Smallest power of two that fits *participant_count* (minimum 2)."""
    size = 2
    while size < participant_count:
        size *= 2
    return size


def seed_positions(size: int) -> list[int]:
    """1-based seeds in bracket order for a bracket of *size* slots.

    Adjacent pairs meet in round 1.  The layout keeps the top seeds apart for
    as long as possible: for 8 slots it is ``[1, 8, 4, 5, 2, 7, 3, 6]``.
    """
    positions = [1, 2]
    while len(positions) < size:
        doubled = len(positions) * 2
        positions = [seed for top in positions for seed in (top, doubled + 1 - top)]
    return positions


# -------------------------------------------------------------------------
# Bracket graph
# -------------------------------------------------------------------------


@dataclass(frozen=True)
class Seed:
    """A slot filled directly by a participant, or empty (first-round bye)."""

    participant: Participant | None


@dataclass(frozen=True)
class WinnerOf:
    """A slot filled by whoever advances from node ``node_id``."""

    node_id: int


@dataclass(frozen=True)
class LoserOf:
    """A slot filled by the surviving loser of node ``node_id``."""

    node_id: int


Source = Seed | WinnerOf | LoserOf


@dataclass(frozen=True)
class MatchNode:
    """One match position in the bracket."""

    id: int
    stage: int
    bracket: Bracket
    source1: Source
    source2: Source


class NodeBuilder:
    """Collects nodes and hands out consecutive ids."""

    def __init__(self) -> None:
        self.nodes: list[MatchNode] = []

    def add(self, stage: int, bracket: Bracket, source1: Source, source2: Source) -> MatchNode:
        node = MatchNode(
            id=len(self.nodes), stage=stage, bracket=bracket, source1=source1, source2=source2
        )
        self.nodes.append(node)
        return node

    def add_winners_rounds(self, participants: Sequence[Participant]) -> list[list[MatchNode]]:
        """Add a seeded single-elimination tree; round ``k`` is at stage ``k``.

        Returns the nodes grouped by round, each in bracket order.
        """
        size = bracket_size(len(participants))
        slots: list[Participant | None] = [
            participants[seed - 1] if seed <= len(participants) else None
            for seed in seed_positions(size)
        ]
        rounds = [
            [
                self.add(1, Bracket.WINNERS, Seed(slots[2 * i]), Seed(slots[2 * i + 1]))
                for i in range(size // 2)
            ]
        ]
        while len(rounds[-1]) > 1:
            previous = rounds[-1]
            rounds.append(
                [
                    self.add(
                        len(rounds) + 1,
                        Bracket.WINNERS,
                        WinnerOf(previous[2 * i].id),
                        WinnerOf(previous[2 * i + 1].id),
                    )
                    for i in range(len(previous) // 2)
                ]
            )
        return rounds


# -------------------------------------------------------------------------
# Mutable tournament state
# -------------------------------------------------------------------------


@dataclass(frozen=True)
class _Result:
    """Who leaves a resolved node through its winner and loser exits."""

    winner_id: str | None = None
    loser_id: str | None = None


@dataclass
class _State:
    """Everything that changes while a bracket is played.

    ``exits`` maps a participant who is out for good (eliminated, or withdrawn
    and passed over by a submitted round) to the stage of the match they lost
    or forfeited.
    """

    resolved: dict[int, _Result] = field(default_factory=dict)
    exits: dict[str, int] = field(default_factory=dict)
    wins: dict[str, int] = field(default_factory=dict)
    active: set[str] = field(default_factory=set)

    def copy(self) -> "_State":
        return _State(
            resolved=dict(self.resolved),
            exits=dict(self.exits),
            wins=dict(self.wins),
            active=set(self.active),
        )


# -------------------------------------------------------------------------
# Engine
# -------------------------------------------------------------------------


class BracketPairing(BasePairing):
    """Base class for formats played on a fixed, seeded bracket.

    The participant list is the seed order (first = seed 1).

    Subclasses implement :meth:`_build_nodes` and may override
    :meth:`_loser_is_eliminated` and :meth:`_config`.
    """

    # -------------------------------------------------------------------------
    # Initialization and configuration
    # -------------------------------------------------------------------------

    def __init__(self, participants: Sequence[Participant]) -> None:
        super().__init__(participants)
        self._by_id: dict[str, Participant] = {p.id: p for p in self._participants}
        self._nodes: list[MatchNode] = sorted(
            self._build_nodes(), key=lambda node: (node.stage, node.id)
        )
        self._resolved: dict[int, _Result] = {}
        self._exits: dict[str, int] = {}
        self._wins: dict[str, int] = {p.id: 0 for p in self._participants}

    # -------------------------------------------------------------------------
    # Hooks for concrete formats
    # -------------------------------------------------------------------------

    @abstractmethod
    def _build_nodes(self) -> list[MatchNode]:
        """Return every node of the bracket for ``self._participants``."""

    def _loser_is_eliminated(self, node: MatchNode, loser_slot: int) -> bool:
        """Whether losing *node* from slot ``1`` or ``2`` ends the loser's event."""
        return True

    def _config(self) -> dict[str, Any]:
        """Constructor options to persist in :meth:`to_dict`."""
        return {}

    # -------------------------------------------------------------------------
    # Pairing / Submission interface
    # -------------------------------------------------------------------------

    def pair(self) -> Round:
        """Generate the next round of the bracket.

        A participant whose opponent slot is empty gets a walkover, emitted as
        a bye matchup.  Stages with nothing to play are skipped.

        Raises:
            TournamentCompleteError: At most one participant is still active.
        """
        if self.is_complete:
            champion = self.champion
            if champion is not None:
                raise TournamentCompleteError(
                    f"{champion.name} is the champion — the tournament is complete."
                )
            raise TournamentCompleteError("No participants remain in the tournament.")

        state = self._state()
        for stage in self._stages():
            matchups: list[Matchup] = []
            for node in self._nodes_at(stage):
                if node.id in state.resolved:
                    continue
                present = [
                    self._by_id[pid]
                    for pid in self._occupants(node, state)
                    if pid is not None and pid in state.active
                ]
                if len(present) == 2:
                    matchups.append(
                        Matchup(player1=present[0], player2=present[1], bracket=node.bracket)
                    )
                elif len(present) == 1:
                    matchups.append(
                        Matchup(player1=present[0], player2=None, bracket=node.bracket)
                    )
            if matchups:
                round_number = len(self._rounds) + 1
                self._register_round_snapshot(round_number)
                return Round(round_number=round_number, matchups=matchups)

        raise TournamentCompleteError(  # pragma: no cover - two active participants always meet
            "The bracket has no further matches."
        )

    def submit_results(self, completed_round: Round) -> None:
        """Record a completed round and advance the bracket.

        Every submitted matchup must be a pending match of the bracket (its two
        participants in either order) or a bye for one of that match's
        participants.  A participant of a pending match who does not appear is
        treated as withdrawn.  Bracket labels on submitted matchups are not
        checked.  If the round is rejected, nothing changes.

        Raises:
            PairingStateError: The round does not fit the bracket, contains a
                draw, has a double loss in a grand final, or its double losses
                would leave nobody in the tournament.
        """
        self._validate_round_submission(completed_round)
        state = self._apply_round(completed_round, self._state())
        super().submit_results(completed_round)
        self._resolved = state.resolved
        self._exits = state.exits
        self._wins = state.wins
        self._active_ids = state.active

    # -------------------------------------------------------------------------
    # Active roster lifecycle
    # -------------------------------------------------------------------------

    def reactivate_participant(self, player_id: str) -> None:
        """Re-admit a withdrawn participant.

        Only possible until a submitted round has passed them over.

        Raises:
            PairingStateError: *player_id* is not registered, is already
                active, or is out of the tournament for good.
        """
        if player_id in self._exits:
            raise PairingStateError(
                f"Cannot reactivate participant '{player_id}': "
                "they are out of the bracket for good."
            )
        super().reactivate_participant(player_id)

    # -------------------------------------------------------------------------
    # Read-only views
    # -------------------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """``True`` once at most one participant is still active."""
        return len(self._active_ids) <= 1

    @property
    def champion(self) -> Participant | None:
        """The winner, or ``None`` while running or if everyone withdrew."""
        if len(self._active_ids) == 1:
            return self._by_id[next(iter(self._active_ids))]
        return None

    def placements(self) -> list[Standing]:
        """Placings of every registered participant, best first.

        - ``rank`` is 1 + the number of participants who lasted longer.
          Participants who went out in the same round share a rank (two
          semi-final losers are both 3rd, the next rank is 5th).  Participants
          still active share rank 1.
        - A withdrawn participant counts as having forfeited their next
          scheduled match and ranks with whoever goes out in that round.
        - ``points`` is the number of real match wins (walkovers excluded).
        - ``tiebreakers`` is empty.

        Entries are ordered by rank, then seed.
        """
        exit_stage = {p.id: self._exit_stage(p.id) for p in self._participants}
        seed = {p.id: index for index, p in enumerate(self._participants)}

        standings = [
            Standing(
                player=p,
                points=self._wins[p.id],
                rank=1 + sum(1 for other in exit_stage.values() if other > exit_stage[p.id]),
            )
            for p in self._participants
        ]
        standings.sort(key=lambda standing: (standing.rank, seed[standing.player.id]))
        return standings

    # -------------------------------------------------------------------------
    # Serialization and reconstruction
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Export tournament state for persistence.

        Keys: ``participants`` (seed order), ``rounds``,
        ``active_participant_ids`` (sorted) and, for formats with constructor
        options, ``config``.
        """
        data: dict[str, Any] = {
            "participants": [participant_to_dict(p) for p in self._participants],
            "rounds": [r.to_dict() for r in self._rounds],
            "active_participant_ids": sorted(self._active_ids),
        }
        config = self._config()
        if config:
            data["config"] = config
        return data

    def _replay(self, rounds: Sequence[Round], active_participant_ids: set[str]) -> None:
        """Rebuild state on a fresh instance from *rounds*.

        Afterwards a participant is active only if the bracket says so *and*
        their id is in *active_participant_ids*.
        """
        unknown_ids = active_participant_ids - self._participant_ids
        if unknown_ids:
            raise PairingStateError(
                "active_participant_ids contains unregistered participants: "
                f"{', '.join(sorted(unknown_ids))}"
            )

        for round_obj in rounds:
            if not round_obj.is_complete:
                raise PairingStateError(
                    f"Cannot reconstruct from incomplete round {round_obj.round_number}. "
                    "All rounds must have recorded outcomes."
                )
            self.submit_results(round_obj)

        self._active_ids &= active_participant_ids

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _state(self) -> _State:
        return _State(
            resolved=self._resolved, exits=self._exits, wins=self._wins, active=self._active_ids
        )

    def _exit_stage(self, participant_id: str) -> float:
        """Stage at which a participant left; ``inf`` while they are active."""
        if participant_id in self._active_ids:
            return math.inf
        if participant_id in self._exits:
            return self._exits[participant_id]
        # Withdrawn but not yet passed over: they forfeit the match they wait in.
        state = self._state()
        for node in self._nodes:
            if node.id not in state.resolved and participant_id in self._occupants(node, state):
                return node.stage
        # Withdrew after winning the last match: nobody outlasted them.
        return math.inf

    def _stages(self) -> list[int]:
        return sorted({node.stage for node in self._nodes})

    def _nodes_at(self, stage: int) -> list[MatchNode]:
        return [node for node in self._nodes if node.stage == stage]

    def _occupants(self, node: MatchNode, state: _State) -> tuple[str | None, str | None]:
        """Ids sitting in the node's two slots, ignoring anyone out for good."""
        return (
            self._resolve_source(node.source1, state),
            self._resolve_source(node.source2, state),
        )

    def _resolve_source(self, source: Source, state: _State) -> str | None:
        participant_id: str | None
        if isinstance(source, Seed):
            participant_id = source.participant.id if source.participant is not None else None
        else:
            result = state.resolved.get(source.node_id)
            if result is None:
                return None
            participant_id = result.winner_id if isinstance(source, WinnerOf) else result.loser_id
        if participant_id is None or participant_id in state.exits:
            return None
        return participant_id

    def _apply_round(self, completed_round: Round, current: _State) -> _State:
        """Return the state after *completed_round*, leaving *current* untouched."""
        state = current.copy()

        by_participant: dict[str, Matchup] = {}
        for matchup in completed_round.matchups:
            for participant in (matchup.player1, matchup.player2):
                if participant is None:
                    continue
                if participant.id in by_participant:
                    raise PairingStateError(
                        f"Participant '{participant.id}' appears in more than one matchup "
                        "of the submitted round."
                    )
                by_participant[participant.id] = matchup

        remaining = {id(matchup) for matchup in completed_round.matchups}
        had_double_loss = False

        for stage in self._stages():
            used_this_stage = False
            for node in self._nodes_at(stage):
                if node.id in state.resolved:
                    continue
                occupants = self._occupants(node, state)
                if occupants == (None, None):
                    continue

                submitted = self._matchup_for(node, occupants, by_participant)
                if submitted is None:
                    # Nobody from this match was submitted: both have withdrawn.
                    self._withdraw(occupants, node, state)
                    state.resolved[node.id] = _Result()
                    continue

                remaining.discard(id(submitted))
                used_this_stage = True
                had_double_loss |= self._resolve_node(node, occupants, submitted, state)

            if used_this_stage:
                break

        if remaining:
            raise PairingStateError(
                "Submitted round does not fit the bracket: it contains a matchup that "
                "is not a pending match of the current round."
            )
        if had_double_loss and not state.active:
            raise PairingStateError(
                "A double loss cannot be recorded here: it would leave nobody in the "
                "tournament. Someone has to win."
            )
        return state

    def _matchup_for(
        self,
        node: MatchNode,
        occupants: tuple[str | None, str | None],
        by_participant: dict[str, Matchup],
    ) -> Matchup | None:
        """Find the submitted matchup for *node* and check that it fits."""
        present = {pid for pid in occupants if pid is not None}
        found = [by_participant[pid] for pid in occupants if pid in by_participant]
        if not found:
            return None

        matchup = found[0]
        if any(other is not matchup for other in found):
            raise PairingStateError(
                "Submitted round does not fit the bracket: "
                f"{' and '.join(sorted(present))} must be in the same matchup."
            )
        submitted = {matchup.player1.id}
        if matchup.player2 is not None:
            submitted.add(matchup.player2.id)
        if not submitted <= present:
            raise PairingStateError(
                "Submitted round does not fit the bracket: unexpected pairing "
                f"{' vs '.join(sorted(submitted))}."
            )
        return matchup

    def _resolve_node(
        self,
        node: MatchNode,
        occupants: tuple[str | None, str | None],
        matchup: Matchup,
        state: _State,
    ) -> bool:
        """Apply one submitted matchup to *node*.  Returns ``True`` on a double loss."""
        if matchup.player2 is None:
            # Walkover.  An occupant who was not submitted has withdrawn.
            absent = tuple(pid for pid in occupants if pid != matchup.player1.id)
            self._withdraw(absent, node, state)
            state.resolved[node.id] = _Result(winner_id=matchup.player1.id)
            return False

        if matchup.outcome == MatchupOutcome.DOUBLE_LOSS:
            if node.bracket is Bracket.GRAND_FINAL:
                raise PairingStateError(
                    "A grand final cannot end in DOUBLE_LOSS: someone has to win."
                )
            for participant_id in (matchup.player1.id, matchup.player2.id):
                self._eliminate(participant_id, node, state)
            state.resolved[node.id] = _Result()
            return True

        if matchup.outcome == MatchupOutcome.PLAYER1_WINS:
            winner_id, loser_id = matchup.player1.id, matchup.player2.id
        elif matchup.outcome == MatchupOutcome.PLAYER2_WINS:
            winner_id, loser_id = matchup.player2.id, matchup.player1.id
        else:
            raise PairingStateError(
                "Elimination matchups must end with PLAYER1_WINS, PLAYER2_WINS or "
                f"DOUBLE_LOSS, not {matchup.outcome.name}."
            )

        state.wins[winner_id] += 1
        loser_slot = 1 if occupants[0] == loser_id else 2
        if self._loser_is_eliminated(node, loser_slot):
            self._eliminate(loser_id, node, state)
            state.resolved[node.id] = _Result(winner_id=winner_id)
        else:
            state.resolved[node.id] = _Result(winner_id=winner_id, loser_id=loser_id)
        return False

    @staticmethod
    def _eliminate(participant_id: str, node: MatchNode, state: _State) -> None:
        state.exits[participant_id] = node.stage
        state.active.discard(participant_id)

    def _withdraw(
        self, participant_ids: Sequence[str | None], node: MatchNode, state: _State
    ) -> None:
        for participant_id in participant_ids:
            if participant_id is not None:
                self._eliminate(participant_id, node, state)


__all__ = [
    "BracketPairing",
    "MatchNode",
    "NodeBuilder",
    "Seed",
    "WinnerOf",
    "LoserOf",
    "Source",
    "bracket_size",
    "seed_positions",
]
