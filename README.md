# cardarena-tournament-core

[![PyPI version](https://img.shields.io/pypi/v/cardarena-tournament-core)](https://pypi.org/project/cardarena-tournament-core/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

A framework-agnostic Python library for running card game tournaments. Swiss pairing, Round Robin, and Single Elimination — with Pokémon TCG and Yu-Gi-Oh! scoring out of the box and a clean extension API for custom formats.

No Django. No ORM. No dependencies. Pure Python 3.11+.

---

## Features

- **Swiss pairing** — points-based greedy matching, rematch avoidance, optional OWP/OOWP-weighted tiebreaker sort
- **Round Robin** — full schedule via the Berger circle method; even and odd player counts
- **Single Elimination** — mirrored seeding (1 vs N, 2 vs N-1, …), automatic bye advancement
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

```python
from cardarena_tournament_core import Player, MatchupOutcome, SingleElimination, TournamentCompleteError

players = [Player(id=str(i), name=f"Seed {i+1}") for i in range(8)]
elim = SingleElimination(players)

try:
    while True:
        round_ = elim.pair()
        for matchup in round_.matchups:
            if matchup.player2 is not None:
                matchup.outcome = MatchupOutcome.PLAYER1_WINS
        elim.submit_results(round_)
except TournamentCompleteError as e:
    print(e)  # "Seed 1 is the champion — the tournament is complete."
```

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

**Swiss** and **Single Elimination** formats support stateless reconstruction from round history. This enables you to:

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

### Single Elimination Reconstruction

```python
from cardarena_tournament_core import Player, SingleElimination, MatchupOutcome

# Original tournament
players = [Player(id=str(i), name=f"Seed {i+1}") for i in range(8)]
elim = SingleElimination(players)

# Play quarterfinals
round1 = elim.pair()
for matchup in round1.matchups:
    if matchup.player2:
        matchup.outcome = MatchupOutcome.PLAYER1_WINS
elim.submit_results(round1)

# Serialize and save
state = elim.to_dict()

# Reconstruct
reconstructed = SingleElimination.from_dict(state)

# Continue with semifinals
round2 = reconstructed.pair()
```

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
    "win_points": 3,
    "draw_points": 1,
    "bye_points": 3,
    "use_tiebreaker_sort": false,
    "tiebreaker_min_win_pct": 0.25
}
```

**Single Elimination:**
```python
{
    "participants": [
        {"type": "player", "id": "0", "name": "Seed 1"},
        {"type": "player", "id": "1", "name": "Seed 2"},
        # ... all participants
    ],
    "rounds": [
        {
            "round_number": 1,
            "matchups": [
                {
                    "player1": {"type": "player", "id": "0", "name": "Seed 1"},
                    "player2": {"type": "player", "id": "7", "name": "Seed 8"},
                    "outcome": "player1_wins"
                },
                # ... all matchups
            ]
        }
    ],
    "active_participant_ids": ["0", "2", "4", "6"]  # Winners advance
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

# Reconstruct Swiss state
swiss = Swiss.from_history(
    participants=participants,
    rounds=rounds,
    active_participant_ids=set(tournament_data["active_participant_ids"]),
    win_points=tournament_data.get("win_points", 3),
    draw_points=tournament_data.get("draw_points", 1),
    bye_points=tournament_data.get("bye_points", 3),
    use_tiebreaker_sort=tournament_data.get("use_tiebreaker_sort", False),
    tiebreaker_min_win_pct=tournament_data.get("tiebreaker_min_win_pct", 0.25)
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
│   └── elimination.py
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
    Matchup, MatchupOutcome,
    Round, Standing,
    # Serialization helpers
    participant_to_dict, participant_from_dict,
    # Errors
    TournamentCompleteError,
    # Pairings
    BasePairing, Swiss, RoundRobin, SingleElimination,
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