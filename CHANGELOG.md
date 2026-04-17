# CHANGELOG

<!-- version list -->

## v1.1.0 (2026-04-17)

### Bug Fixes

- Accept Sequence[Participant] instead of list[Participant] in pairing constructors
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Address all code review must-fix items
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Lint fixes
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Make Player frozen/hashable; fix pyproject.toml wheel package path
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Removed ruff dependency
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Swiss oneshort var
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **elimination**: Update _active_ids after super call to prevent state corruption
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **pairings**: Use set.remove instead of discard in remove_active_participant
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **swiss**: Raise TournamentCompleteError when no active participants remain
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

### Chores

- Cleaned up file structure
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Fixed docs
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Fixed docs in pokemon.py
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Fixed indentation
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Set up project scaffolding for cardarena-tournament-core
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Update pyproject.toml
  ([`1f9dada`](https://github.com/KataCards/cardarena-tournament-core/commit/1f9dada287c12e55ff657991b7af7b9d8139ee7f))

### Continuous Integration

- Add GitHub Actions workflows and commitlint config
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

### Documentation

- **elimination**: Document submit_results advancement semantics
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **readme**: Document active-player lifecycle semantics
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **readme**: Fix code fence style in lifecycle example
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

### Features

- Add core data models (Player, Matchup, Round, PlayerStanding)
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Add more comprehensive comment and fix two broken tests
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Add Tournament orchestrator
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Implement approved nice-to-haves A–E
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Implement full tournament core — pairings, scoring, and models
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Introduced github workflow
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Remove legacy test
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **pairings**: Add active roster lifecycle and round snapshot validation in base pairing
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **round-robin**: Explicitly block dynamic removal with clear error
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **swiss**: Pair from active ids and preserve history-based scoring state
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **tournament**: Expose active participant lifecycle through orchestrator
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **utils**: Add yugioh_tiebreak_number encoding utility
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

### Refactoring

- Add type checks, test coverage, and DRY principles
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Adjust structure
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Descriptive names, full type hints, remove standalone tiebreakers
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Flatten base sub-packages and clean up root
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Move TCG scoring classes into scoring/tcg/ sub-package
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Remove backwards compatibility
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Restructure base modules into base/ sub-packages
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- Tiebreakers inline in TCG classes, rename yugioh → yugioh_tcg
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

- **elimination**: Align elimination with active-id source of truth
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))

### Testing

- **scoring**: Verify removed players still represented in historical standings
  ([`0bf9f60`](https://github.com/KataCards/cardarena-tournament-core/commit/0bf9f6016dd48416d61395a1548d7aadd6c0ae3c))


## v1.0.1 (2026-04-17)

### Bug Fixes

- Delete docs
  ([`5b1a600`](https://github.com/KataCards/cardarena-tournament-core/commit/5b1a6004f96e365286c0d6b84da117b502461b36))


## v1.0.0 (2026-04-17)

- Initial Release
