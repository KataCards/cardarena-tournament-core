"""Randomized full runs: every bracket terminates and replays identically."""

import random

import pytest

from cardarena_tournament_core.common.errors import PairingStateError
from cardarena_tournament_core.common.models import MatchupOutcome
from cardarena_tournament_core.pairings._bracket import BracketPairing
from cardarena_tournament_core.pairings.double_elimination import DoubleElimination
from cardarena_tournament_core.pairings.elimination import SingleElimination

from tests.pairings.helpers import ids, players, ranks

OUTCOMES = [
    MatchupOutcome.PLAYER1_WINS,
    MatchupOutcome.PLAYER1_WINS,
    MatchupOutcome.PLAYER2_WINS,
    MatchupOutcome.PLAYER2_WINS,
    MatchupOutcome.DOUBLE_LOSS,
]


@pytest.mark.parametrize("cls", [SingleElimination, DoubleElimination])
@pytest.mark.parametrize("n", range(1, 34))
@pytest.mark.parametrize("seed", range(5))
def test_random_run_terminates_and_replays(cls: type[BracketPairing], n: int, seed: int):
    rng = random.Random(seed * 1000 + n)
    tournament = cls(players(n))

    for _ in range(200):
        if tournament.is_complete:
            break
        if rng.random() < 0.1 and len(tournament.active_participant_ids) > 1:
            tournament.remove_active_participant(
                rng.choice(sorted(tournament.active_participant_ids))
            )
            if tournament.is_complete:
                break

        round_ = tournament.pair()
        for matchup in round_.matchups:
            if matchup.player2 is not None:
                matchup.outcome = rng.choice(OUTCOMES)
        try:
            tournament.submit_results(round_)
        except PairingStateError:
            # A double loss in a grand final, or one that would leave nobody.
            for matchup in round_.matchups:
                if matchup.outcome is MatchupOutcome.DOUBLE_LOSS:
                    matchup.outcome = MatchupOutcome.PLAYER1_WINS
            tournament.submit_results(round_)

        clone = cls.from_dict(tournament.to_dict())  # type: ignore[attr-defined]
        assert clone.active_participant_ids == tournament.active_participant_ids
        assert ranks(clone) == ranks(tournament)
        assert clone.is_complete == tournament.is_complete
        if not tournament.is_complete:
            assert ids(clone.pair()) == ids(tournament.pair())

    assert tournament.is_complete
    assert len(tournament.placements()) == n
    seen_real_pairs = [
        (m.player1.id, m.player2.id)
        for r in tournament.rounds
        for m in r.matchups
        if m.player2 is not None
    ]
    assert all(a != b for a, b in seen_real_pairs)
    champion = tournament.champion
    if champion is not None:
        assert ranks(tournament)[0] == (champion.id, 1)
