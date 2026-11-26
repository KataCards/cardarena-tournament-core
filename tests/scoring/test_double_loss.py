"""Double loss: both players lose a played match."""

import pytest

from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core.scoring.base import BaseScoring
from cardarena_tournament_core.scoring.pokemon import PokemonTCG
from cardarena_tournament_core.scoring.union_arena import UnionArena
from cardarena_tournament_core.scoring.yugioh import YuGiOh

A, B, C, D = (Player(id=i, name=i.upper()) for i in "abcd")


def _round1() -> Round:
    return Round(
        round_number=1,
        matchups=[
            Matchup(player1=A, player2=B, outcome=MatchupOutcome.DOUBLE_LOSS),
            Matchup(player1=C, player2=D, outcome=MatchupOutcome.PLAYER1_WINS),
        ],
    )


@pytest.mark.parametrize("scoring", [YuGiOh(), PokemonTCG(), UnionArena()])
def test_double_loss_gives_both_players_loss_points(scoring: BaseScoring):
    by_id = {s.player.id: s for s in scoring.calculate([_round1()])}

    assert by_id["a"].points == 0
    assert by_id["b"].points == 0
    assert by_id["c"].points == 3
    assert by_id["d"].points == 0


@pytest.mark.parametrize("scoring", [YuGiOh(), PokemonTCG(), UnionArena()])
def test_double_loss_players_rank_below_the_winner(scoring: BaseScoring):
    standings = scoring.calculate([_round1()])

    assert standings[0].player.id == "c"
    assert len(standings) == 4


def test_yugioh_owp_treats_double_loss_opponent_as_winless():
    by_id = {s.player.id: s for s in YuGiOh().calculate([_round1()])}

    # A's only opponent is B, who played one match and did not win it.
    assert by_id["a"].tiebreakers["owp"] == 0.0
    # D's only opponent is C, who won their only match.
    assert by_id["d"].tiebreakers["owp"] == 1.0


def test_union_arena_head_to_head_ignores_double_loss():
    # A and B tie on everything; the double loss between them gives neither a
    # head-to-head win, so the stable id order decides.
    standings = UnionArena().calculate([_round1()])
    tail = [s.player.id for s in standings if s.player.id in {"a", "b"}]

    assert tail == ["a", "b"]
