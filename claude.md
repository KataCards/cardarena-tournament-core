# CLAUDE.md — cardarena-tournament-core

## What This Project Is

A standalone, framework-agnostic Python package extracted from the CardArena backend.
It provides tournament pairing algorithms, pluggable scoring systems, and tiebreaker logic
that can be used by any tournament management application — not just CardArena.

This is part of the CardArena `-core` ecosystem, meaning it is open source but directly
tied to the CardArena project and maintained by KataCards.

---

## Why It Exists

The CardArena backend (Django REST API) contains pairing and scoring logic that is tightly
coupled to its ORM. This package is a clean rewrite of that logic as pure Python — no Django,
no ORM, no framework dependency. The CardArena backend will consume this package via a thin
Django adapter layer once complete.

---

## Current State (as of project creation)

- Folder structure scaffolded
- `pyproject.toml` in place (hatchling build system, Python >=3.11)
- Package module stubs created (`pairings/`, `scoring/`)
- `reference/` folder contains raw extracts from the CardArena backend — **do not publish these**

### Reference files (in `/reference`)
| File | Origin | Purpose |
|------|--------|---------|
| `swiss.py` | `game_logic/swiss.py` | Working Swiss pairing — Django-coupled, to be rewritten |
| `tiebreakers_extract.py` | `tournaments/views.py` | OWP/OOWP logic extracted — to be generalized |
| `POKEMON_TCG_SCORING.md` | backend docs | Pokémon TCG scoring rules reference |
| `IMPLEMENTATION_SUMMARY.md` | backend docs | Summary of original implementation |
| `QUICK_REFERENCE.md` | backend docs | Quick reference for scoring/tiebreaker logic |

---

## Target Package Structure

```
cardarena_tournament_core/
├── models.py               # Pure Python dataclasses: Player, Matchup, Round, Tournament
├── engine.py               # Main orchestrator
├── pairings/
│   ├── base.py             # Abstract PairingAlgorithm class
│   ├── swiss.py            # Swiss pairing (rewrite of reference/swiss.py)
│   ├── round_robin.py      # Round Robin (new)
│   └── elimination.py      # Single & Double Elimination (new)
└── scoring/
    ├── systems.py          # Pluggable ScoringSystem class (win/draw/loss points)
    └── tiebreakers.py      # OWP, OOWP, SOS, etc. (rewrite of reference/tiebreakers_extract.py)
```

---

## Key Design Principles

- **No Django, no ORM** — all inputs and outputs are plain Python objects/dataclasses
- **Pluggable scoring** — win/draw/loss points are configurable, not hardcoded
- **Pluggable tiebreakers** — OWP/OOWP (Pokémon), SOS (chess), etc. selectable per tournament
- **Pluggable pairing formats** — Swiss, Round Robin, Single/Double Elimination
- The CardArena Django backend will connect via a thin adapter — that adapter is **not** part of this package

---

## What Still Needs to Be Built

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` — dataclasses | ❌ Not started | Inform design from `reference/swiss.py` and backend models |
| Swiss pairing rewrite | ❌ Not started | Port from `reference/swiss.py`, remove all ORM calls |
| Round Robin | ❌ Not started | New implementation |
| Single Elimination | ❌ Not started | New implementation |
| Double Elimination | ❌ Not started | Most complex — winners/losers bracket |
| Scoring system | ❌ Not started | Replace hardcoded dicts with proper class |
| Tiebreakers | ❌ Not started | Extract from `reference/tiebreakers_extract.py` |
| Tests | ❌ Not started | Full suite per algorithm |
| README | ❌ Not started | Public-facing docs |

---

## Important Notes

- The `reference/` folder must **never be published** — it contains Django-coupled code extracted from the private CardArena backend
- The package name is `cardarena-tournament-core` — renaming to something more generic is under consideration if broader OSS adoption becomes the goal
- Start with `models.py` and API design before implementing any algorithms — the data contract must be stable first