import pytest

from cardarena_tournament_core.common.errors import (
    PairingConfigurationError,
    PairingStateError,
)
from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core.pairings.base import BasePairing


class DummyPairing(BasePairing):
    def pair(self) -> Round:
        return Round(
            round_number=len(self.rounds) + 1,
            matchups=[Matchup(player1=self.participants[0], player2=None)],
        )


def test_base_pairing_requires_at_least_one_participant():
    with pytest.raises(PairingConfigurationError, match="At least one participant"):
        DummyPairing([])


def test_base_pairing_rejects_duplicate_participant_ids():
    with pytest.raises(PairingConfigurationError, match="must be unique"):
        DummyPairing([
            Player(id="p1", name="A"),
            Player(id="p1", name="B"),
        ])


def test_submit_results_rejects_out_of_order_round_number():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])
    invalid_round = Round(
        round_number=2,
        matchups=[Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS)],
    )

    with pytest.raises(PairingStateError, match="out of order"):
        pairing.submit_results(invalid_round)


def test_submit_results_rejects_empty_round():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])

    with pytest.raises(PairingStateError, match="at least one matchup"):
        pairing.submit_results(Round(round_number=1, matchups=[]))


def test_submit_results_rejects_incomplete_round():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    pairing = DummyPairing([p0, p1])
    incomplete_round = Round(
        round_number=1,
        matchups=[Matchup(player1=p0, player2=p1)],
    )

    with pytest.raises(PairingStateError, match="Cannot submit incomplete rounds"):
        pairing.submit_results(incomplete_round)


def test_submit_results_rejects_unknown_player1():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    outsider = Player(id="x", name="X")
    pairing = DummyPairing([p0, p1])
    invalid_round = Round(
        round_number=1,
        matchups=[Matchup(player1=outsider, player2=None)],
    )

    with pytest.raises(PairingStateError, match="not registered"):
        pairing.submit_results(invalid_round)


def test_submit_results_rejects_unknown_player2():
    p0, p1 = Player(id="p0", name="P0"), Player(id="p1", name="P1")
    outsider = Player(id="x", name="X")
    pairing = DummyPairing([p0, p1])
    invalid_round = Round(
        round_number=1,
        matchups=[
            Matchup(
                player1=p0,
                player2=outsider,
                outcome=MatchupOutcome.PLAYER1_WINS,
            )
        ],
    )

    with pytest.raises(PairingStateError, match="not registered"):
        pairing.submit_results(invalid_round)
