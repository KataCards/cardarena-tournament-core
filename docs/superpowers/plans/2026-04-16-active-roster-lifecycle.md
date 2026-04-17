# Active Roster Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dynamic active-participant removal to Swiss and Elimination, with snapshot-based round validation so already-paired rounds remain submittable after a removal, while Round Robin explicitly rejects removal.

**Architecture:** `BasePairing` gains `_active_ids: set[str]` and a `_round_snapshots` registry. `pair()` implementations register a snapshot of active IDs before returning a round. `_validate_round_submission` checks against the snapshot for that round (when present), falling back to the full registered-participant set. Swiss filters its ranking candidates to active IDs only. Elimination replaces its `_active_participants` list with the inherited `_active_ids` plus a `_seeding_order` list for deterministic bracket ordering. Round Robin overrides `remove_active_participant` to raise immediately with a clear message.

**Tech Stack:** Python 3.11+, pytest, mypy (strict), ruff. Run tests with `uv run pytest -q`, lint with `uv run ruff check .`, type-check with `uv run mypy cardarena_tournament_core tests`. Coverage threshold is 98% — every new branch needs a test.

---

## File Map

| File | Change |
|---|---|
| `cardarena_tournament_core/pairings/base.py` | Add `_active_ids`, `_round_snapshots`, `remove_active_participant`, `reactivate_participant`, `active_participant_ids`, `_register_round_snapshot`; update `_validate_round_submission` |
| `cardarena_tournament_core/pairings/swiss.py` | Filter ranking to active IDs; call `_register_round_snapshot` in `pair()` |
| `cardarena_tournament_core/pairings/elimination.py` | Remove `_active_participants`; add `_seeding_order`/`_participant_map`; compute active list from `_active_ids`; call `_register_round_snapshot` in `pair()` |
| `cardarena_tournament_core/pairings/round_robin.py` | Override `remove_active_participant` to raise `PairingStateError` |
| `cardarena_tournament_core/tournament.py` | Add `remove_active_participant` delegation and `active_participant_ids` property |
| `tests/pairings/test_base.py` | Add lifecycle and snapshot validation tests; update `DummyPairing` to call `_register_round_snapshot` |
| `tests/pairings/test_swiss.py` | Add removal + historical state tests |
| `tests/pairings/test_elimination.py` | Update direct `_active_participants` access; add removal lifecycle tests |
| `tests/pairings/test_round_robin.py` | Add explicit error test |
| `tests/test_tournament.py` | Add removal delegation integration test |
| `tests/scoring/test_validation.py` | Add historical standings preservation test |
| `README.md` | Document full roster vs active roster semantics |

---

## Task 1: BasePairing — active roster state and snapshot validation

**Files:**
- Modify: `cardarena_tournament_core/pairings/base.py`
- Modify: `tests/pairings/test_base.py`

---

- [ ] **Step 1.1: Write the failing tests**

Append these tests to `tests/pairings/test_base.py`. Also update `DummyPairing` to register a round snapshot in `pair()`:

```python
# Updated DummyPairing at top of test_base.py (replaces the existing one)
class DummyPairing(BasePairing):
    def pair(self) -> Round:
        round_number = len(self.rounds) + 1
        self._register_round_snapshot(round_number)
        return Round(
            round_number=round_number,
            matchups=[Matchup(player1=self.participants[0], player2=None)],
        )


# --- NEW TESTS TO APPEND ---

def test_active_participant_ids_initially_equals_all_registered():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])
    assert pairing.active_participant_ids == frozenset({"p0", "p1"})


def test_remove_active_participant_excludes_from_active_ids():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])
    pairing.remove_active_participant("p0")
    assert "p0" not in pairing.active_participant_ids
    assert "p1" in pairing.active_participant_ids


def test_remove_unregistered_participant_raises():
    pairing = DummyPairing([Player(id="p0", name="P0")])
    with pytest.raises(PairingStateError, match="not registered"):
        pairing.remove_active_participant("unknown")


def test_remove_already_inactive_participant_raises():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])
    pairing.remove_active_participant("p0")
    with pytest.raises(PairingStateError, match="already inactive"):
        pairing.remove_active_participant("p0")


def test_reactivate_participant_restores_to_active_ids():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])
    pairing.remove_active_participant("p0")
    pairing.reactivate_participant("p0")
    assert "p0" in pairing.active_participant_ids


def test_reactivate_already_active_participant_raises():
    pairing = DummyPairing([Player(id="p0", name="P0")])
    with pytest.raises(PairingStateError, match="already active"):
        pairing.reactivate_participant("p0")


def test_reactivate_unregistered_participant_raises():
    pairing = DummyPairing([Player(id="p0", name="P0")])
    with pytest.raises(PairingStateError, match="not registered"):
        pairing.reactivate_participant("unknown")


def test_submit_results_succeeds_after_removal_when_round_was_already_paired():
    """Round paired while p0 was active; removing p0 after pairing must not
    break submission of that already-paired round."""
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])

    round1 = pairing.pair()          # snapshot taken: {p0, p1}
    pairing.remove_active_participant("p0")  # remove AFTER pairing
    pairing.submit_results(round1)   # must succeed — p0 was in snapshot
    assert len(pairing.rounds) == 1
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```
uv run pytest tests/pairings/test_base.py -v
```

Expected: failures on `test_active_participant_ids_initially_equals_all_registered`, all `remove_*` / `reactivate_*` tests, and the snapshot test. The existing tests should still pass after updating `DummyPairing` (DummyPairing.pair() now registers a snapshot, which doesn't break existing round submission behaviour).

- [ ] **Step 1.3: Implement active roster state and snapshot validation in base.py**

Replace the body of `cardarena_tournament_core/pairings/base.py` with:

```python
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
        self._active_ids.discard(player_id)

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
```

- [ ] **Step 1.4: Run all base tests and the full suite**

```
uv run pytest tests/pairings/test_base.py -v
```

Expected: all tests pass.

```
uv run pytest -q
```

Expected: no regressions.

- [ ] **Step 1.5: Type-check**

```
uv run mypy cardarena_tournament_core tests
```

Expected: no errors.

- [ ] **Step 1.6: Commit**

```bash
git add cardarena_tournament_core/pairings/base.py tests/pairings/test_base.py
git commit -m "feat(pairings): add active roster lifecycle and round snapshot validation in base pairing"
```

---

## Task 2: Swiss — pair from active IDs, register round snapshot

**Files:**
- Modify: `cardarena_tournament_core/pairings/swiss.py`
- Modify: `tests/pairings/test_swiss.py`

---

- [ ] **Step 2.1: Write the failing tests**

Append to `tests/pairings/test_swiss.py`:

```python
def test_removed_player_excluded_from_future_pairings():
    """After removing a player, they must not appear in any subsequent round."""
    players = make_players(4)
    swiss = Swiss(players)
    round1 = swiss.pair()
    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)

    swiss.remove_active_participant("3")  # remove player with id "3"

    round2 = swiss.pair()
    round2_ids = {m.player1.id for m in round2.matchups}
    round2_ids |= {m.player2.id for m in round2.matchups if m.player2 is not None}
    assert "3" not in round2_ids


def test_already_paired_round_submittable_after_removal():
    """Pairing a round then removing a participant must not block submission."""
    players = make_players(4)
    swiss = Swiss(players)

    round1 = swiss.pair()       # snapshot taken with all 4 active
    swiss.remove_active_participant("0")  # remove after pairing

    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)  # must succeed despite removal
    assert len(swiss.rounds) == 1


def test_removal_preserves_points_and_play_history():
    """Points and played-pair history for a removed player are unaffected."""
    p0, p1, p2, p3 = make_players(4)
    swiss = Swiss([p0, p1, p2, p3])
    round1 = swiss.pair()
    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    swiss.submit_results(round1)

    points_before = swiss._points["0"]
    swiss.remove_active_participant("0")
    assert swiss._points["0"] == points_before
    # played_pairs must still record the pair that included "0"
    assert any("0" in pair for pair in swiss._played_pairs)
```

- [ ] **Step 2.2: Run tests to confirm they fail**

```
uv run pytest tests/pairings/test_swiss.py::test_removed_player_excluded_from_future_pairings tests/pairings/test_swiss.py::test_already_paired_round_submittable_after_removal tests/pairings/test_swiss.py::test_removal_preserves_points_and_play_history -v
```

Expected: all three fail.

- [ ] **Step 2.3: Update Swiss to filter active IDs and register snapshots**

In `cardarena_tournament_core/pairings/swiss.py`, make two changes:

**Change 1 — `pair()`: compute round number once and register snapshot before returning.**

Replace the current `pair()` return line:

```python
# OLD
return Round(round_number=len(self._rounds) + 1, matchups=matchups)
```

With a round number local variable and snapshot registration:

```python
def pair(self) -> Round:
    """Generate the next round's matchups.

    Players are sorted by points (descending).  When ``use_tiebreaker_sort``
    is enabled and at least one round has been played, equal-point players
    are further sorted by OWP then OOWP.  Each player is then greedily
    paired with the highest-ranked available opponent they haven't yet faced.
    Odd players out receive a bye.  Only active participants (not removed via
    ``remove_active_participant``) are considered as pairing candidates.
    """
    round_number = len(self._rounds) + 1
    ranked_participants = self._rank_participants()
    already_paired: set[str] = set()
    matchups: list[Matchup] = []

    for participant in ranked_participants:
        if participant.id in already_paired:
            continue

        opponent = self._find_opponent(participant, ranked_participants, already_paired, allow_repeat=False)

        if opponent is None:
            opponent = self._find_opponent(participant, ranked_participants, already_paired, allow_repeat=True)

        if opponent is not None:
            matchups.append(Matchup(player1=participant, player2=opponent))
            already_paired.update([participant.id, opponent.id])
        else:
            matchups.append(Matchup(player1=participant, player2=None))
            already_paired.add(participant.id)

    self._register_round_snapshot(round_number)
    return Round(round_number=round_number, matchups=matchups)
```

**Change 2 — `_rank_participants()`: filter to active IDs only.**

Replace the existing `_rank_participants` with:

```python
def _rank_participants(self) -> list[Participant]:
    active_participants = [p for p in self._participants if p.id in self._active_ids]
    if self._use_tiebreaker_sort and self._rounds:
        return sorted(
            active_participants,
            key=lambda participant: (
                self._points[participant.id],
                utils.owp(
                    participant.id,
                    self._rounds,
                    min_win_pct=self._tiebreaker_min_win_pct,
                ),
                utils.oowp(
                    participant.id,
                    self._rounds,
                    min_win_pct=self._tiebreaker_min_win_pct,
                ),
            ),
            reverse=True,
        )
    return sorted(
        active_participants,
        key=lambda participant: self._points[participant.id],
        reverse=True,
    )
```

- [ ] **Step 2.4: Run Swiss tests**

```
uv run pytest tests/pairings/test_swiss.py -v
```

Expected: all pass.

- [ ] **Step 2.5: Run full suite and type-check**

```
uv run pytest -q && uv run mypy cardarena_tournament_core tests
```

Expected: all pass, no type errors.

- [ ] **Step 2.6: Commit**

```bash
git add cardarena_tournament_core/pairings/swiss.py tests/pairings/test_swiss.py
git commit -m "feat(swiss): pair from active ids and preserve history-based scoring state"
```

---

## Task 3: Tournament — expose active lifecycle through orchestrator

**Files:**
- Modify: `cardarena_tournament_core/tournament.py`
- Modify: `tests/test_tournament.py`

---

- [ ] **Step 3.1: Write the failing test**

Append to `tests/test_tournament.py`:

```python
def test_remove_active_participant_delegates_to_pairing():
    """Tournament.remove_active_participant removes player from future pairings."""
    players = make_players(4)
    t = Tournament(pairing=Swiss(players), scoring=PokemonTCG())

    round1 = t.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)

    t.remove_active_participant("3")  # remove after submitting round 1

    round2 = t.pair()
    round2_ids = {m.player1.id for m in round2.matchups}
    round2_ids |= {m.player2.id for m in round2.matchups if m.player2 is not None}
    assert "3" not in round2_ids


def test_active_participant_ids_property_delegates_to_pairing():
    players = make_players(4)
    t = Tournament(pairing=Swiss(players), scoring=PokemonTCG())
    assert t.active_participant_ids == frozenset({"0", "1", "2", "3"})
    t.remove_active_participant("0")
    assert "0" not in t.active_participant_ids
```

- [ ] **Step 3.2: Run tests to confirm they fail**

```
uv run pytest tests/test_tournament.py::test_remove_active_participant_delegates_to_pairing tests/test_tournament.py::test_active_participant_ids_property_delegates_to_pairing -v
```

Expected: both fail with `AttributeError`.

- [ ] **Step 3.3: Add delegation methods to tournament.py**

In `cardarena_tournament_core/tournament.py`, add the following two items after the existing `# ── read-only views ───` section:

```python
    # -------------------------------------------------------------------------
    # Active roster lifecycle
    # -------------------------------------------------------------------------

    def remove_active_participant(self, player_id: str) -> None:
        """Remove a participant from future pairings while preserving their history.

        Delegates to the underlying pairing format.

        Raises:
            PairingStateError: *player_id* is not registered or is already inactive.
        """
        self._pairing.remove_active_participant(player_id)

    @property
    def active_participant_ids(self) -> frozenset[str]:
        """IDs of participants currently eligible for future pairings (read-only).

        Delegates to the underlying pairing format.
        """
        return self._pairing.active_participant_ids
```

- [ ] **Step 3.4: Run tournament tests and full suite**

```
uv run pytest tests/test_tournament.py -v && uv run pytest -q
```

Expected: all pass.

- [ ] **Step 3.5: Type-check**

```
uv run mypy cardarena_tournament_core tests
```

Expected: no errors.

- [ ] **Step 3.6: Commit**

```bash
git add cardarena_tournament_core/tournament.py tests/test_tournament.py
git commit -m "feat(tournament): expose active participant lifecycle through orchestrator"
```

---

## Task 4: SingleElimination — use active-id source of truth

**Files:**
- Modify: `cardarena_tournament_core/pairings/elimination.py`
- Modify: `tests/pairings/test_elimination.py`

The existing `_active_participants: list[Participant]` is replaced by:
- `_seeding_order: list[str]` — original participant IDs in registration order, used for deterministic bracket seeding.
- `_participant_map: dict[str, Participant]` — O(1) lookup from ID to participant object.
- The inherited `_active_ids: set[str]` (from base) becomes the source of truth.

`pair()` computes `[self._participant_map[pid] for pid in self._seeding_order if pid in self._active_ids]`.  
`submit_results()` extracts winner IDs and sets `self._active_ids = set(winner_ids)` before calling `super()`.

---

- [ ] **Step 4.1: Update the existing test that directly accesses `_active_participants`**

In `tests/pairings/test_elimination.py`, find and update this test:

```python
# OLD
def test_tournament_complete_error_when_all_participants_eliminated():
    elim = SingleElimination(make_players(2))
    elim._active_participants = []

    with pytest.raises(TournamentCompleteError, match="All participants have been eliminated"):
        elim.pair()
```

Replace with:

```python
def test_tournament_complete_error_when_all_participants_eliminated():
    elim = SingleElimination(make_players(2))
    elim._active_ids = set()  # clear active roster directly

    with pytest.raises(TournamentCompleteError, match="All participants have been eliminated"):
        elim.pair()
```

- [ ] **Step 4.2: Add new lifecycle tests for elimination**

Append to `tests/pairings/test_elimination.py`:

```python
def test_active_ids_updated_after_submit():
    """After submitting round 1, only winners remain active."""
    players = make_players(4)
    elim = SingleElimination(players)
    r1 = elim.pair()
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    # P0 and P1 are winners (player1 wins in each matchup)
    assert elim.active_participant_ids == frozenset({"0", "1"})


def test_seeding_order_preserved_after_elimination():
    """Active participants used in round 2 must respect original seeding order."""
    players = make_players(4)  # seeds: P0=1, P1=2, P2=3, P3=4
    elim = SingleElimination(players)

    r1 = elim.pair()
    # R1 pairs P0 vs P3 and P1 vs P2; P0 and P1 win
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    r2 = elim.pair()
    assert len(r2.matchups) == 1
    # P0 (seed 1) should be player1, P1 (seed 2) should be player2
    assert r2.matchups[0].player1.id == "0"
    assert r2.matchups[0].player2 is not None
    assert r2.matchups[0].player2.id == "1"


def test_already_paired_round_submittable_after_removal_in_elimination():
    """Removing a player after pairing must not break submission of that round."""
    players = make_players(4)
    elim = SingleElimination(players)

    r1 = elim.pair()           # snapshot taken with all 4 active
    elim.remove_active_participant("3")  # remove after pairing

    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)    # must not raise
    assert len(elim.rounds) == 1
```

- [ ] **Step 4.3: Run tests to confirm only the new tests fail**

```
uv run pytest tests/pairings/test_elimination.py -v
```

Expected: the updated `_active_participants` test now refers to `_active_ids`, which doesn't exist yet in elimination (it's inherited from base, but the test was previously setting `_active_participants`). All tests pass except the three new lifecycle ones.

- [ ] **Step 4.4: Refactor elimination.py**

Replace `cardarena_tournament_core/pairings/elimination.py` with:

```python
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
```

- [ ] **Step 4.5: Run elimination tests and full suite**

```
uv run pytest tests/pairings/test_elimination.py -v && uv run pytest -q
```

Expected: all pass.

- [ ] **Step 4.6: Type-check**

```
uv run mypy cardarena_tournament_core tests
```

Expected: no errors.

- [ ] **Step 4.7: Commit**

```bash
git add cardarena_tournament_core/pairings/elimination.py tests/pairings/test_elimination.py
git commit -m "refactor(elimination): align elimination with active-id source of truth"
```

---

## Task 5: RoundRobin — explicitly block dynamic removal

**Files:**
- Modify: `cardarena_tournament_core/pairings/round_robin.py`
- Modify: `tests/pairings/test_round_robin.py`

---

- [ ] **Step 5.1: Write the failing test**

Append to `tests/pairings/test_round_robin.py`:

```python
def test_remove_active_participant_raises_with_clear_message():
    """Round Robin must reject removal because the schedule is pre-computed."""
    from cardarena_tournament_core.common.errors import PairingStateError
    rr = RoundRobin(make_players(4))
    with pytest.raises(PairingStateError, match="not supported for Round Robin"):
        rr.remove_active_participant("0")
```

- [ ] **Step 5.2: Run test to confirm it fails**

```
uv run pytest tests/pairings/test_round_robin.py::test_remove_active_participant_raises_with_clear_message -v
```

Expected: `FAILED` — no override exists yet so the base method would succeed (or no error raised).

- [ ] **Step 5.3: Add the override to round_robin.py**

In `cardarena_tournament_core/pairings/round_robin.py`, add the import and override after the `__init__` block:

First, add `PairingStateError` to the existing import line at the top of the file:

```python
# Change this line:
from cardarena_tournament_core.common.errors import TournamentCompleteError

# To this:
from cardarena_tournament_core.common.errors import PairingStateError, TournamentCompleteError
```

Then add this method to the `RoundRobin` class, after `__init__` and before `pair()`:

```python
    # -------------------------------------------------------------------------
    # Unsupported lifecycle operations
    # -------------------------------------------------------------------------

    def remove_active_participant(self, player_id: str) -> None:
        """Not supported for Round Robin tournaments.

        The full schedule is pre-computed at initialization and cannot be
        modified.  Use Swiss pairing for tournaments that require dynamic
        roster changes.

        Raises:
            PairingStateError: Always.
        """
        raise PairingStateError(
            "Dynamic participant removal is not supported for Round Robin tournaments. "
            "The schedule is pre-computed at initialization and cannot be modified. "
            "Use Swiss pairing for tournaments that require dynamic roster changes."
        )
```

- [ ] **Step 5.4: Run Round Robin tests and full suite**

```
uv run pytest tests/pairings/test_round_robin.py -v && uv run pytest -q
```

Expected: all pass.

- [ ] **Step 5.5: Type-check**

```
uv run mypy cardarena_tournament_core tests
```

Expected: no errors.

- [ ] **Step 5.6: Commit**

```bash
git add cardarena_tournament_core/pairings/round_robin.py tests/pairings/test_round_robin.py
git commit -m "feat(round-robin): explicitly block dynamic removal with clear error"
```

---

## Task 6: Scoring — verify removed players appear in historical standings

**Files:**
- Modify: `tests/scoring/test_validation.py`

---

- [ ] **Step 6.1: Write the failing test**

Append to `tests/scoring/test_validation.py`:

```python
def test_removed_player_still_in_historical_standings():
    """Removing a player from the active roster after round 1 must not erase
    their standing entry — scoring reads from round history, not active IDs."""
    from cardarena_tournament_core.pairings.swiss import Swiss
    from cardarena_tournament_core.scoring.pokemon import PokemonTCG

    p0, p1, p2, p3 = [Player(id=str(i), name=f"P{i}") for i in range(4)]
    pairing = Swiss([p0, p1, p2, p3])
    scoring = PokemonTCG()

    round1 = pairing.pair()
    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    pairing.submit_results(round1)

    # Identify a winner (player1 of a real matchup) and remove them
    winner_id = next(m.player1.id for m in round1.matchups if m.player2 is not None)
    pairing.remove_active_participant(winner_id)

    standings = scoring.calculate(pairing.rounds)
    standing_ids = {s.player.id for s in standings}

    # Removed player still appears in standings
    assert winner_id in standing_ids

    # Their points are correct (3 for a win)
    winner_standing = next(s for s in standings if s.player.id == winner_id)
    assert winner_standing.points == 3
```

- [ ] **Step 6.2: Run test to confirm it passes (scoring is already ID-agnostic)**

```
uv run pytest tests/scoring/test_validation.py::test_removed_player_still_in_historical_standings -v
```

Expected: PASS — scoring reads from rounds, not active IDs. This test is a regression guard.

- [ ] **Step 6.3: Run full suite**

```
uv run pytest -q
```

Expected: all pass.

- [ ] **Step 6.4: Commit**

```bash
git add tests/scoring/test_validation.py
git commit -m "test(scoring): verify removed players still represented in historical standings"
```

---

## Task 7: README — document active-player lifecycle semantics

**Files:**
- Modify: `README.md`

---

- [ ] **Step 7.1: Add a "Participant Lifecycle" section to README.md**

Locate the appropriate section in `README.md` and add (or append) the following content under a `## Participant Lifecycle` heading:

```markdown
## Participant Lifecycle

### Full Roster vs. Active Roster

Every tournament format tracks two distinct participant sets:

- **Full roster** (`pairing.participants`) — all participants registered at initialization. Immutable. Used for historical scoring and tiebreaker calculations.
- **Active roster** (`pairing.active_participant_ids`) — participants eligible for future pairings. Starts equal to the full roster; updated as participants are removed or (optionally) reactivated.

### Removing a Participant

```python
tournament.remove_active_participant(player_id)
```

- The participant is excluded from all future rounds generated by `pair()`.
- All historical rounds, points, and tiebreaker data are preserved.
- Standings computed after removal still include the removed participant's historical entries.
- Rounds that were already paired (before the removal) can still be submitted normally.

### Reactivating a Participant

```python
pairing.reactivate_participant(player_id)
```

Returns an inactive participant to the active roster. Not exposed through `Tournament` by default; use the underlying pairing object directly when needed.

### Round Robin Limitation (Phase 1)

`RoundRobin` does **not** support dynamic removal. The full schedule is pre-computed at initialization; calling `remove_active_participant` raises `PairingStateError` immediately.

Use `Swiss` pairing if your tournament requires dropping participants mid-event.

### Example: Mid-Tournament Drop (Swiss)

```python
from cardarena_tournament_core import Player, MatchupOutcome, Swiss, PokemonTCG, Tournament

players = [Player(id=str(i), name=f"Player {i}") for i in range(8)]
tournament = Tournament(pairing=Swiss(players), scoring=PokemonTCG())

# Play round 1
round1 = tournament.pair()
for matchup in round1.matchups:
    if matchup.player2:
        matchup.outcome = MatchupOutcome.PLAYER1_WINS
tournament.submit_results(round1)

# Player 7 drops after round 1
tournament.remove_active_participant("7")

# Round 2 pairs the remaining 7 active players (one receives a bye)
round2 = tournament.pair()

# Standings still include Player 7's round 1 result
standings = tournament.standings()
```
```

- [ ] **Step 7.2: Verify README renders correctly (visual check)**

Open `README.md` in your editor and confirm:
- No broken markdown (unmatched backticks, unclosed code fences)
- All code examples are syntactically valid Python

- [ ] **Step 7.3: Run full quality gate**

```
uv sync --extra dev
uv run ruff check .
uv run mypy cardarena_tournament_core tests
uv run pytest -q
```

Expected: all pass, coverage ≥ 98%.

- [ ] **Step 7.4: Commit**

```bash
git add README.md
git commit -m "docs(readme): document active-player lifecycle semantics"
```

---

## Final Acceptance Checklist

- [ ] `uv run pytest -q` — all tests pass, coverage ≥ 98%
- [ ] `uv run ruff check .` — no lint errors
- [ ] `uv run mypy cardarena_tournament_core tests` — no type errors
- [ ] Swiss pairs only active players but keeps full historical state
- [ ] Submitting an already-paired round works even after one participant was removed post-pairing
- [ ] Elimination uses the same active-id lifecycle model (no separate `_active_participants` list)
- [ ] Round Robin raises `PairingStateError` with a descriptive message on removal attempt
- [ ] No breaking API changes — all existing tests pass unchanged
