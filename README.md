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
- **Yu-Gi-Oh! TCG scoring** — same points + XXYYYZZZ encoded tiebreak number for single-value sorting
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
        f"tiebreak={standing.tiebreakers['tiebreak_number']}"
    )
```

The tiebreak number encodes `XXYYYZZZ`: XX = points, YYY = OWP × 1000, ZZZ = OOWP × 1000 — so a single integer comparison gives the correct final ordering.

### Teams

`Team` is a first-class participant alongside `Player`. Pass teams anywhere a player is expected:

```python
from cardarena_tournament_core import Team, Swiss

teams = [
    Team(id="t1", name="Mystic Dragons", members=("Alice", "Bob")),
    Team(id="t2", name="Storm Hawks",    members=("Carol", "Dave")),
]
swiss = Swiss(teams)
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
├── models.py               # Player, Team, Matchup, Round, Standing, TournamentCompleteError
├── tournament.py           # Tournament orchestrator
├── py.typed                # PEP 561 typed package marker
├── pairings/
│   ├── base/
│   │   └── __init__.py     # BasePairing ABC
│   ├── swiss.py
│   ├── round_robin.py
│   └── elimination.py
└── scoring/
    ├── base/
    │   └── __init__.py     # BaseScoring ABC
    └── tcg/
        ├── __init__.py     # re-exports TCGBaseScoring, PokemonTCG, YuGiOh
        ├── base_tcg.py     # TCGBaseScoring — shared OWP/OOWP helpers (internal)
        ├── pokemon_tcg.py
        └── yugioh_tcg.py
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
    TournamentCompleteError,
    # Pairings
    BasePairing, Swiss, RoundRobin, SingleElimination,
    # Scoring
    BaseScoring, PokemonTCG, YuGiOh,
)
```

---

## Development

```bash
git clone https://github.com/KataCards/cardarena-tournament-core
cd cardarena-tournament-core
pip install -e ".[dev]"
pytest
```

Dev dependencies: `pytest`, `pytest-cov`, `ruff`.

---

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).

Part of the [CardArena](https://github.com/KataCards) open-source ecosystem, maintained by KataCards.
