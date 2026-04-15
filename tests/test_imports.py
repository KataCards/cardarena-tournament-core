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
        YuGiOh,
    )
    assert Player is not None
    assert Team is not None
    assert Participant is not None
    assert Matchup is not None
    assert MatchupOutcome is not None
    assert Round is not None
    assert Standing is not None
    assert Swiss is not None
    assert RoundRobin is not None
    assert SingleElimination is not None
    assert PokemonTCG is not None
    assert YuGiOh is not None


def test_import_from_submodules():
    from cardarena_tournament_core.pairings import RoundRobin, SingleElimination, Swiss
    from cardarena_tournament_core.scoring import PokemonTCG, YuGiOh

    assert Swiss is not None
    assert RoundRobin is not None
    assert SingleElimination is not None
    assert PokemonTCG is not None
    assert YuGiOh is not None