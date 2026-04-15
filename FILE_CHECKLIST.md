# Tournament Core Package - File Checklist

## Core Package Files

### Root Directory
- [X] `LICENSE`
- [-] `README.md`
- [X] `pyproject.toml`
- [-] `uv.lock`
- [X] `claude.md`
- [X] `test_yugioh_example.py` (demo script)


I want points to be part of the class i.e. set the points once for win draw lose, you can pcik premade ones like pokemon or yugioh
Add even heaver weightes swissparing based on owp and oowp (optional)

The Tiebreakers are tcg specific, i.e. the yare part of the tcg even if basically the same, here a repetition is actually allowed to be
rename yugioh into yugioh_tcg or tcp as prefix.
check models.py

Morgen fertig werden.


### cardarena_tournament_core/
- [X] `__init__.py` (main package exports)
- [ ] `models.py` (Player, Matchup, Round, PlayerStanding, MatchupOutcome)

### cardarena_tournament_core/pairings/
- [ ] `__init__.py` (pairings exports)

# Change into True / False or Introduce Error Rasining then none is also ok.
- [ ] `base.py` (BasePairing abstract class)

- [ ] `swiss.py` (Swiss pairing algorithm)

- [ ] `round_robin.py` (Round Robin pairing algorithm)

- [ ] `elimination.py` (Single Elimination pairing algorithm)

### cardarena_tournament_core/scoring/
- [ ] `__init__.py` (scoring exports)
- [ ] `base.py` (BaseScoring abstract class)
- [ ] `tiebreakers.py` (win_percentage, calculate_owp, calculate_oowp)
- [ ] `pokemon_tcg.py` (Pokémon TCG scoring system)
- [ ] `yugioh.py` (Yu-Gi-Oh! TCG scoring system)

## Test Files

### tests/
- [ ] `__init__.py`
- [ ] `test_models.py` (7 tests)
- [ ] `test_imports.py` (2 tests)

### tests/pairings/
- [ ] `__init__.py`
- [ ] `test_swiss.py` (7 tests)
- [ ] `test_round_robin.py` (5 tests)
- [ ] `test_elimination.py` (6 tests)

### tests/scoring/
- [ ] `__init__.py`
- [ ] `test_tiebreakers.py` (8 tests)
- [ ] `test_pokemon_tcg.py` (9 tests)
- [ ] `test_yugioh.py` (9 tests)

