"""Tests for the Tournament orchestrator."""

import pytest

from cardarena_tournament_core.common.errors import (
    TournamentCompleteError,
    TournamentConfigurationError,
)
from cardarena_tournament_core.common.models import MatchupOutcome, Player
from cardarena_tournament_core.pairings.elimination import SingleElimination
from cardarena_tournament_core.pairings.round_robin import RoundRobin
from cardarena_tournament_core.pairings.swiss import Swiss
from cardarena_tournament_core.scoring.pokemon import PokemonTCG
from cardarena_tournament_core.scoring.yugioh import YuGiOh
from cardarena_tournament_core.tournament import Tournament


def make_players(n: int) -> list[Player]:
    return [Player(id=str(i), name=f"P{i}") for i in range(n)]


def make_tournament(n: int = 4) -> Tournament:
    return Tournament(pairing=Swiss(make_players(n)), scoring=PokemonTCG())


# ----
# Delegation
# ----

def test_pair_returns_round():
    t = make_tournament()
    round1 = t.pair()
    assert round1.round_number == 1
    assert len(round1.matchups) == 2


def test_submit_results_updates_round_history():
    t = make_tournament()
    round1 = t.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)
    assert len(t.rounds) == 1


def test_rounds_property_reflects_submitted_rounds():
    t = make_tournament()
    assert t.rounds == []
    round1 = t.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)
    assert len(t.rounds) == 1
    assert t.rounds[0].round_number == 1


def test_participants_property():
    players = make_players(4)
    t = Tournament(pairing=Swiss(players), scoring=PokemonTCG())
    assert len(t.participants) == 4
    assert {p.id for p in t.participants} == {"0", "1", "2", "3"}


# ----
# Standings
# ----

def test_standings_empty_before_any_rounds():
    t = make_tournament()
    assert t.standings() == []


def test_standings_after_one_round():
    t = make_tournament()
    round1 = t.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)

    standings = t.standings()
    assert len(standings) == 4
    assert standings[0].points == 3
    assert standings[0].rank == 1


def test_standings_sorted_by_points_descending():
    t = make_tournament()
    round1 = t.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)

    standings = t.standings()
    points = [s.points for s in standings]
    assert points == sorted(points, reverse=True)


def test_standings_callable_mid_tournament():
    t = make_tournament()
    for _ in range(2):
        round_ = t.pair()
        for m in round_.matchups:
            if m.player2:
                m.outcome = MatchupOutcome.PLAYER1_WINS
        t.submit_results(round_)
        standings = t.standings()
        assert len(standings) == 4


# ----
# Pairing/scoring combinations
# ----

def test_round_robin_with_yugioh_scoring():
    players = make_players(4)
    t = Tournament(pairing=RoundRobin(players), scoring=YuGiOh())

    for _ in range(3):
        round_ = t.pair()
        for m in round_.matchups:
            if m.player2:
                m.outcome = MatchupOutcome.PLAYER1_WINS
        t.submit_results(round_)

    standings = t.standings()
    assert len(standings) == 4
    # YuGiOh now uses OWP/OOWP tiebreakers (tiebreak_number was removed)
    assert all("owp" in s.tiebreakers for s in standings)
    assert all("oowp" in s.tiebreakers for s in standings)


def test_single_elimination_with_pokemon_scoring():
    players = make_players(4)
    t = Tournament(pairing=SingleElimination(players), scoring=PokemonTCG())

    round1 = t.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)

    round2 = t.pair()
    for m in round2.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round2)

    standings = t.standings()
    assert len(standings) == 4


# ----
# Error propagation
# ----

def test_tournament_complete_error_propagates():
    players = make_players(2)
    t = Tournament(pairing=SingleElimination(players), scoring=PokemonTCG())

    round1 = t.pair()
    round1.matchups[0].outcome = MatchupOutcome.PLAYER1_WINS
    t.submit_results(round1)

    with pytest.raises(TournamentCompleteError):
        t.pair()


def test_constructor_rejects_invalid_pairing_dependency():
    with pytest.raises(TournamentConfigurationError, match="pairing must be an instance"):
        Tournament(pairing=object(), scoring=PokemonTCG())  # type: ignore[arg-type]


def test_constructor_rejects_invalid_scoring_dependency():
    with pytest.raises(TournamentConfigurationError, match="scoring must be an instance"):
        Tournament(pairing=Swiss(make_players(2)), scoring=object())  # type: ignore[arg-type]


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