"""Smoke tests: verify the public API is importable from the package root."""


def test_import_from_package_root():
    from cardarena_tournament_core import (
        Matchup,
        MatchupOutcome,
        Participant,
        Player,
        Standing,
        PokemonTCG,
        Round,
        RoundRobin,
        SingleElimination,
        Swiss,
        Team,
        Tournament,
        TournamentCompleteError,
        YuGiOh,
    )
    assert Player is not None
    assert Team is not None
    assert Participant is not None
    assert Matchup is not None
    assert MatchupOutcome is not None
    assert Round is not None
    assert Standing is not None
    assert TournamentCompleteError is not None
    assert Swiss is not None
    assert RoundRobin is not None
    assert SingleElimination is not None
    assert PokemonTCG is not None
    assert YuGiOh is not None
    assert Tournament is not None


def test_import_from_submodules():
    from cardarena_tournament_core.pairings import RoundRobin, SingleElimination, Swiss
    from cardarena_tournament_core.scoring import PokemonTCG, YuGiOh

    assert Swiss is not None
    assert RoundRobin is not None
    assert SingleElimination is not None
    assert PokemonTCG is not None
    assert YuGiOh is not None


def test_abstract_base_classes_importable_for_extension():
    """Users who want to implement custom formats must be able to import the ABCs."""
    from cardarena_tournament_core import BasePairing, BaseScoring

    assert BasePairing is not None
    assert BaseScoring is not None


def test_legacy_error_module_is_importable():
    from cardarena_tournament_core.errors import (
        PairingStateError,
        ScoringValidationError,
        TournamentCompleteError,
    )

    assert PairingStateError is not None
    assert ScoringValidationError is not None
    assert TournamentCompleteError is not None