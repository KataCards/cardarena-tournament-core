# cardarena-tournament-core

[![PyPI version](https://img.shields.io/pypi/v/cardarena-tournament-core)](https://pypi.org/project/cardarena-tournament-core/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

A framework-agnostic Python library for running card game tournaments. Swiss pairing, Round Robin, Single and Double Elimination — with Pokémon TCG and Yu-Gi-Oh! scoring out of the box and a clean extension API for custom formats.

No Django. No ORM. No dependencies. Pure Python 3.11+.

---

## Features

- **Swiss pairing** — points-based greedy matching, rematch avoidance, optional OWP/OOWP-weighted tiebreaker sort
- **Round Robin** — full schedule via the Berger circle method; even and odd player counts
- **Single Elimination** — fixed bracket with standard seeding (1v8, 4v5, 2v7, 3v6), byes for the top seeds, walkovers, final placings
- **Double Elimination** — winners and losers bracket, grand final with optional reset
- **Double loss** — a `DOUBLE_LOSS` match outcome (both players lose), supported by every format and scoring system
- **Pokémon TCG scoring** — Win/Draw/Loss/Bye points + OWP and OOWP tiebreakers (floor 25 %)
- **Yu-Gi-Oh! TCG scoring** — same points + OWP and OOWP tiebreakers (no floor)
- **Extensible** — subclass `BasePairing` or `BaseScoring` to add your own format
- **Fully typed** — ships a `py.typed` marker; works with mypy and pyright out of the box

---

## Installation

```bash
pip install cardarena-tournament-core
```

Requires Python 3.11 or later.

---

## Quick Start

### Tournament (recommended entry point)

`Tournament` wires a pairing format and a scoring system together so you never need to manage them separately:

```python
from cardarena_tournament_core import (
    Player, MatchupOutcome, Swiss, PokemonTCG, Tournament, TournamentCompleteError,
)

players = [Player(id=str(i), name=f"Player {i}") for i in range(8)]
tournament = Tournament(pairing=Swiss(players), scoring=PokemonTCG())

try:
    while True:
        round_ = tournament.pair()

        for matchup in round_.matchups:
            if matchup.player2 is not None:
                matchup.outcome = MatchupOutcome.PLAYER1_WINS

        tournament.submit_results(round_)

        for standing in tournament.standings():
            print(f"{standing.rank}. {standing.player.name} — {standing.points} pts")

except TournamentCompleteError:
    print("Tournament complete!")
```

Swap in any combination — `RoundRobin` + `YuGiOh()`, `SingleElimination` + `PokemonTCG()`, or your own custom subclasses.

### Swiss Pairing (standalone)

```python
from cardarena_tournament_core import Player, MatchupOutcome, Swiss

players = [Player(id=str(i), name=f"Player {i}") for i in range(8)]
swiss = Swiss(players)

round1 = swiss.pair()

for matchup in round1.matchups:
    if matchup.player2 is not None:
        matchup.outcome = MatchupOutcome.PLAYER1_WINS

swiss.submit_results(round1)

# Generate round 2 — winners are paired together
round2 = swiss.pair()
```

**Optional: OWP/OOWP-weighted pairing** — from round 2 onward, equal-point players are further ordered by opponent win percentage before the greedy matching pass:

```python
swiss = Swiss(players, use_tiebreaker_sort=True)
```

### Round Robin

```python
from cardarena_tournament_core import Player, RoundRobin, TournamentCompleteError

players = [Player(id=str(i), name=f"Player {i}") for i in range(4)]
rr = RoundRobin(players)  # pre-computes all 3 rounds at construction

try:
    while True:
        round_ = rr.pair()
        # ... play and record results ...
        rr.submit_results(round_)
except TournamentCompleteError:
    print("All rounds played!")
```

### Single Elimination

The participant list is the seed order: the first participant is seed 1.

```python
from cardarena_tournament_core import Player, MatchupOutcome, SingleElimination

players = [Player(id=str(i), name=f"Seed {i}") for i in range(1, 9)]
elim = SingleElimination(players)

while not elim.is_complete:
    round_ = elim.pair()
    for matchup in round_.matchups:
        if matchup.player2 is not None:
            matchup.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(round_)

print(elim.champion.name)  # "Seed 1"
for standing in elim.placements():
    print(standing.rank, standing.player.name)  # 1 Seed 1, 2 Seed 2, 3 Seed 3, 3 Seed 4, 5 ...
```

How the bracket works:

- **Seeding.** Seeds go into standard bracket positions. Round 1 for eight participants is 1v8, 4v5, 2v7, 3v6, so seeds 1 and 2 can only meet in the final. Each later round pairs the winners of adjacent matches.
- **Byes.** If the field is not a power of two, the top seeds get the first-round byes (five participants: seeds 1, 2 and 3 have a bye, 4 plays 5).
- **Walkovers.** If a participant's opponent slot is empty — after a double loss or a withdrawal — they advance with a bye matchup (`player2=None`) in that round.
- **Results.** A matchup must end `PLAYER1_WINS`, `PLAYER2_WINS` or `DOUBLE_LOSS`. A draw raises `PairingStateError`.
- **Withdrawals.** `remove_active_participant()` takes a participant out of future rounds; their next opponent gets a walkover.
- **Completion.** The tournament is complete as soon as at most one participant is still active — `is_complete` is `True`, `champion` returns the winner, and `pair()` raises `TournamentCompleteError`. A champion decided on the bracket stays the champion even if they are marked inactive afterwards. If a round was paired before the last withdrawal it can still be submitted and may change the result, so treat completion as final only when no paired round is outstanding.
- **Placings.** `placements()` returns a `Standing` for every participant. Participants who went out in the same round share a rank; `points` is the number of real match wins.
- **Labels.** Every matchup carries `bracket=Bracket.WINNERS`.

`submit_results()` checks the round against the bracket. Each matchup must be a pending match (its two participants, in either order) or a bye for one of them; anything else raises `PairingStateError` and changes nothing. A participant of a pending match who is missing from the submitted round is treated as withdrawn.

> **Always submit the whole round.** Leaving a pending match out of a submitted round withdraws both of its participants without an error.

### Double Elimination

A participant is out after two losses. Everyone starts in the winners bracket; a loss there drops them into the losers bracket, and a loss in the losers bracket eliminates them. The two bracket champions meet in the grand final.

```python
from cardarena_tournament_core import Bracket, DoubleElimination, MatchupOutcome, Player

players = [Player(id=str(i), name=f"Seed {i}") for i in range(1, 9)]
bracket = DoubleElimination(players)  # grand_final_reset=True by default

while not bracket.is_complete:
    round_ = bracket.pair()
    for matchup in round_.matchups:
        # matchup.bracket is Bracket.WINNERS, Bracket.LOSERS or Bracket.GRAND_FINAL
        if matchup.player2 is not None:
            matchup.outcome = MatchupOutcome.PLAYER1_WINS
    bracket.submit_results(round_)

print(bracket.champion.name)  # "Seed 1"
```

Each match is played in the earliest round after both of its feeder matches. For eight participants:

| Round | Matches |
|-------|---------|
| 1 | Winners round 1 |
| 2 | Winners round 2 + losers round 1 |
| 3 | Winners final + losers round 2 |
| 4 | Losers round 3 |
| 5 | Losers final |
| 6 | Grand final |
| 7 | Second grand final (only if needed) |

- **Grand final reset.** With `grand_final_reset=True`, if the losers-bracket champion wins the grand final, both finalists have one loss and a second, deciding grand final is played. With `grand_final_reset=False` the first grand final decides.
- **Losers bracket.** Players dropping from the winners bracket cross over to a different part of the losers bracket each round, so two players who already met cannot meet again before the bracket forces it (32 participants: not before round 6).
- **Withdrawals** remove a participant from the whole event; they do not drop into the losers bracket.
- Seeding, byes, walkovers, completion, placings and the `submit_results()` checks work as in single elimination.

### Double Loss

`MatchupOutcome.DOUBLE_LOSS` records a match that both players lose (a Yu-Gi-Oh! tournament result).

| Where | Effect |
|-------|--------|
| Scoring (Pokémon, Yu-Gi-Oh!, Union Arena) | Both players get loss points (0). |
| Tiebreakers | A played match that neither player won: it counts in both players' win percentages. |
| Swiss | No points; the two are recorded as having played and are not paired again. |
| Round Robin | Accepted as a completed result. |
| Single elimination | Both players are eliminated; the opponent waiting for the winner gets a walkover. |
| Double elimination | Both players are eliminated outright, in either bracket. |

In elimination formats a double loss is rejected (`PairingStateError`) when it would leave nobody in the tournament — for example in the final — and always in a grand final. Someone has to win.

### Scoring — Pokémon TCG

```python
from cardarena_tournament_core import PokemonTCG

# Pass all completed rounds (scoring is stateless — no submit_results needed)
standings = PokemonTCG().calculate(rounds)

for standing in standings:
    print(
        f"{standing.rank}. {standing.player.name} — "
        f"{standing.points} pts  "
        f"OWP={standing.tiebreakers['owp']:.3f}  "
        f"OOWP={standing.tiebreakers['oowp']:.3f}"
    )
```

### Scoring — Yu-Gi-Oh! TCG

```python
from cardarena_tournament_core import YuGiOh

standings = YuGiOh().calculate(rounds)

for standing in standings:
    print(
        f"{standing.rank}. {standing.player.name} — "
        f"{standing.points} pts  "
        f"OWP={standing.tiebreakers['owp']:.3f}  "
        f"OOWP={standing.tiebreakers['oowp']:.3f}"
    )
```

### Teams

`Team` is a first-class participant alongside `Player`. Teams are composed of `Player` objects and can be used anywhere a player is expected:

```python
from cardarena_tournament_core import Player, Team, Swiss

# Create individual players
alice = Player(id="p1", name="Alice")
bob = Player(id="p2", name="Bob")
carol = Player(id="p3", name="Carol")
dave = Player(id="p4", name="Dave")

# Create teams with Player objects as members
teams = [
    Team(id="t1", name="Mystic Dragons", members=(alice, bob)),
    Team(id="t2", name="Storm Hawks", members=(carol, dave)),
]

# Use teams in any pairing format
swiss = Swiss(teams)

# Access team member information
for team in teams:
    print(f"{team.name}: {', '.join(m.name for m in team.members)}")
    # Output: Mystic Dragons: Alice, Bob
    #         Storm Hawks: Carol, Dave
```

**Serialization:** Teams serialize to JSON-friendly dictionaries with nested player data:

```python
team_dict = teams[0].to_dict()
# {
#     "type": "team",
#     "id": "t1",
#     "name": "Mystic Dragons",
#     "members": [
#         {"type": "player", "id": "p1", "name": "Alice"},
#         {"type": "player", "id": "p2", "name": "Bob"}
#     ]
# }

# Reconstruct from dictionary
restored_team = Team.from_dict(team_dict)
```

---

## Stateless Tournament Reconstruction

**Swiss**, **Single Elimination** and **Double Elimination** formats support stateless reconstruction from round history. This enables you to:

- **Persist tournaments** to any database (SQL, NoSQL, file storage)
- **Reconstruct state** deterministically from historical data
- **Resume tournaments** across server restarts or different processes
- **Migrate tournaments** between systems

### Core Concepts

Tournament state is **derived** from:
1. **Participant list** — all registered players/teams
2. **Round history** — completed rounds with outcomes
3. **Active participant IDs** — participants still eligible for pairing
4. **Configuration** — format-specific settings (points, tiebreakers, etc.)

### Swiss Reconstruction

```python
from cardarena_tournament_core import Player, Swiss, MatchupOutcome

# Original tournament
players = [Player(id=str(i), name=f"Player {i}") for i in range(8)]
swiss = Swiss(players)

# Play round 1
round1 = swiss.pair()
round1.matchups[0].outcome = MatchupOutcome.PLAYER1_WINS
round1.matchups[1].outcome = MatchupOutcome.DRAW
round1.matchups[2].outcome = MatchupOutcome.PLAYER2_WINS
round1.matchups[3].outcome = MatchupOutcome.PLAYER1_WINS
swiss.submit_results(round1)

# Play round 2
round2 = swiss.pair()
for matchup in round2.matchups:
    if matchup.player2:
        matchup.outcome = MatchupOutcome.PLAYER1_WINS
swiss.submit_results(round2)

# Serialize complete state
tournament_state = swiss.to_dict()
# Save to database: db.tournaments.insert_one(tournament_state)

# Later: Reconstruct from database
# tournament_data = db.tournaments.find_one({"_id": tournament_id})
reconstructed = Swiss.from_dict(tournament_state)

# State is identical — continue tournament
round3 = reconstructed.pair()
```

### Elimination Reconstruction

`SingleElimination` and `DoubleElimination` rebuild their bracket by replaying the rounds. Results and withdrawals are read from the rounds themselves, so the history is all you need to store.

```python
from cardarena_tournament_core import DoubleElimination, MatchupOutcome, Player

players = [Player(id=str(i), name=f"Seed {i}") for i in range(1, 9)]
bracket = DoubleElimination(players, grand_final_reset=False)

round1 = bracket.pair()
for matchup in round1.matchups:
    if matchup.player2:
        matchup.outcome = MatchupOutcome.PLAYER1_WINS
bracket.submit_results(round1)

state = bracket.to_dict()                          # includes config.grand_final_reset
reconstructed = DoubleElimination.from_dict(state)

round2 = reconstructed.pair()                      # winners round 2 + losers round 1
```

`from_history(participants, rounds, active_participant_ids)` does the same from separate pieces. After the replay a participant is active only if they are still in the bracket **and** their id is in `active_participant_ids`; pass the ids of everyone who has not dropped.

### Serialization Format

**Swiss:**
```python
{
    "participants": [
        {"type": "player", "id": "0", "name": "Player 0"},
        {"type": "player", "id": "1", "name": "Player 1"},
        # ... all participants
    ],
    "rounds": [
        {
            "round_number": 1,
            "matchups": [
                {
                    "player1": {"type": "player", "id": "0", "name": "Player 0"},
                    "player2": {"type": "player", "id": "1", "name": "Player 1"},
                    "outcome": "player1_wins"
                },
                # ... all matchups
            ]
        },
        # ... all rounds
    ],
    "active_participant_ids": ["0", "1", "2", "3", "4", "5", "6", "7"],
    "config": {
        "win_points": 3,
        "draw_points": 1,
        "bye_points": 3,
        "use_tiebreaker_sort": false,
        "tiebreaker_min_win_pct": 0.25
    }
}
```

**Single Elimination** (Double Elimination adds `"config": {"grand_final_reset": true}`):
```python
{
    "participants": [
        {"type": "player", "id": "1", "name": "Seed 1"},
        {"type": "player", "id": "2", "name": "Seed 2"},
        # ... all participants, in seed order
    ],
    "rounds": [
        {
            "round_number": 1,
            "matchups": [
                {
                    "player1": {"type": "player", "id": "1", "name": "Seed 1"},
                    "player2": {"type": "player", "id": "8", "name": "Seed 8"},
                    "outcome": "player1_wins",
                    "bracket": "winners"   # "winners", "losers", "grand_final", or null outside brackets
                },
                # ... all matchups
            ]
        }
    ],
    "active_participant_ids": ["1", "2", "3", "4"]  # still in the tournament
}
```

### Advanced: Reconstruction from History

For maximum flexibility, reconstruct directly from round history:

```python
from cardarena_tournament_core import Swiss, Player, Round, participant_from_dict

# Load from your database
tournament_data = db.tournaments.find_one({"_id": tournament_id})

# Reconstruct participants
participants = [
    participant_from_dict(p) for p in tournament_data["participants"]
]

# Reconstruct rounds
rounds = [Round.from_dict(r) for r in tournament_data["rounds"]]

# Reconstruct Swiss config
config = tournament_data.get("config", {})

# Reconstruct Swiss state
swiss = Swiss.from_history(
    participants=participants,
    rounds=rounds,
    active_participant_ids=set(tournament_data["active_participant_ids"]),
    win_points=config.get("win_points", 3),
    draw_points=config.get("draw_points", 1),
    bye_points=config.get("bye_points", 3),
    use_tiebreaker_sort=config.get("use_tiebreaker_sort", False),
    tiebreaker_min_win_pct=config.get("tiebreaker_min_win_pct", 0.25)
)

# Continue tournament
next_round = swiss.pair()
```

### Validation & Error Handling

Reconstruction validates all input data:

```python
from cardarena_tournament_core import PairingStateError

try:
    swiss = Swiss.from_history(
        participants=participants,
        rounds=rounds,
        active_participant_ids=active_ids
    )
except PairingStateError as e:
    # Handles:
    # - Incomplete rounds (pending matchups)
    # - Unknown participant IDs in active set
    # - Invalid round data
    print(f"Reconstruction failed: {e}")
```

### Best Practices

1. **Always validate before saving:**
   ```python
   # Ensure round is complete before serializing
   if not round_.is_complete:
       raise ValueError("Cannot save incomplete round")
   
   state = swiss.to_dict()
   db.save(state)
   ```

2. **Store configuration explicitly:**
   ```python
   # Don't rely on defaults — store all config
   state = swiss.to_dict()
   assert "win_points" in state
   assert "use_tiebreaker_sort" in state
   ```

3. **Version your schema:**
   ```python
   state = swiss.to_dict()
   state["schema_version"] = "1.0"
   db.save(state)
   ```

4. **Handle participant drops:**
   ```python
   # Active IDs track who's still playing
   swiss.remove_active_participant("player_7")
   state = swiss.to_dict()
   # state["active_participant_ids"] excludes "player_7"
   ```

5. **Test reconstruction in CI:**
   ```python
   # Verify state preservation
   original = Swiss(players)
   # ... play rounds ...
   
   state = original.to_dict()
   reconstructed = Swiss.from_dict(state)
   
   assert original.rounds == reconstructed.rounds
   assert original.active_participant_ids == reconstructed.active_participant_ids
   ```

---

## Migrating to 2.0

2.0 replaces the old single-elimination pairing with a real bracket. Swiss, Round Robin and the scoring systems behave as before for the outcomes that already existed.

- **Pairing order changed.** `SingleElimination` no longer re-pairs the survivors top-against-bottom each round. It uses fixed bracket positions, and byes go to the top seeds instead of the middle seed.
- **`submit_results()` is stricter.** Rounds are checked against the bracket; a matchup that is not a pending match raises `PairingStateError`.
- **1.x elimination histories do not replay.** Round histories produced by 1.x `SingleElimination` generally do not fit the new bracket and cannot be loaded with `from_history()` / `from_dict()`.
- **`from_history()` no longer revives eliminated participants.** `active_participant_ids` can only narrow the set of participants still in the bracket.
- **New outcome.** `MatchupOutcome.DOUBLE_LOSS` exists; code that switches over every outcome needs a branch for it.
- **New serialized key.** `Matchup.to_dict()` includes `"bracket"`. Dictionaries without the key still load.

---

## Extending

### Custom Pairing Format

```python
from cardarena_tournament_core import BasePairing, Round

class SnakePairing(BasePairing):
    def pair(self) -> Round:
        # implement your logic here
        ...
```

`BasePairing` provides:
- `self.participants` — read-only list of all participants
- `self.rounds` — read-only list of submitted rounds
- `submit_results(round)` — appends to history; call `super().submit_results(round)` in overrides

### Custom Scoring System

```python
from cardarena_tournament_core import BaseScoring, Round, Standing

class ChessScoring(BaseScoring):
    def calculate(self, rounds: list[Round]) -> list[Standing]:
        # compute and return sorted standings with rank set
        ...
```

---

## Project Structure

```
cardarena_tournament_core/
├── __init__.py             # Public API
├── common/
│   ├── __init__.py
│   ├── errors.py           # Semantic exception hierarchy
│   └── models.py           # Core data models
├── tournament.py           # Tournament orchestrator
├── utils.py                # Win%, OWP, OOWP helpers
├── py.typed                # PEP 561 typed package marker
├── pairings/
│   ├── __init__.py
│   ├── base.py             # BasePairing ABC
│   ├── swiss.py
│   ├── round_robin.py
│   ├── _bracket.py         # Shared bracket engine (seeding, match graph)
│   ├── elimination.py      # SingleElimination
│   └── double_elimination.py
└── scoring/
    ├── __init__.py
    ├── base.py             # BaseScoring and shared TCG scoring helpers
    ├── pokemon.py
    └── yugioh.py
```

---

## Public API

All public names are importable directly from the package root:

```python
from cardarena_tournament_core import (
    # Orchestrator
    Tournament,
    # Models
    Player, Team, Participant,
    Matchup, MatchupOutcome, Bracket,
    Round, Standing,
    # Serialization helpers
    participant_to_dict, participant_from_dict,
    # Errors
    TournamentCompleteError,
    # Pairings
    BasePairing, Swiss, RoundRobin, SingleElimination, DoubleElimination,
    # Scoring
    BaseScoring, PokemonTCG, YuGiOh,
)
```

---

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

In elimination formats this only works for a withdrawn participant until a submitted round has passed them over. A participant who was eliminated, or whose match was submitted without them, is out for good and `reactivate_participant` raises `PairingStateError`.

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

---

## Development

```bash
git clone https://github.com/KataCards/cardarena-tournament-core
cd cardarena-tournament-core
uv sync --extra dev
uv run ruff check .
uv run mypy cardarena_tournament_core tests
uv run pytest
```

Dev dependencies include `pytest`, `pytest-cov`, `ruff`, and `mypy`.

---

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).

Part of the [CardArena](https://github.com/KataCards) ecosystem, maintained by KataCards.