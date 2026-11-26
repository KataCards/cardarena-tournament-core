"""Shared helpers for bracket-format tests."""

from collections.abc import Collection

from cardarena_tournament_core.common.models import MatchupOutcome, Player, Round
from cardarena_tournament_core.pairings._bracket import BracketPairing
from cardarena_tournament_core.pairings.base import BasePairing


def players(n: int) -> list[Player]:
    """``n`` players in seed order: ``p1`` is seed 1."""
    return [Player(id=f"p{i}", name=f"P{i}") for i in range(1, n + 1)]


def ids(round_: Round) -> list[tuple[str, str | None]]:
    """The round's pairings as ``(player1 id, player2 id or None)``."""
    return [(m.player1.id, m.player2.id if m.player2 else None) for m in round_.matchups]


def set_outcomes(
    round_: Round,
    winners: Collection[str] = (),
    double_loss: Collection[frozenset[str]] = (),
) -> Round:
    """Record outcomes on *round_* in place.

    A matchup is won by player 2 when their id is in *winners*, otherwise by
    player 1.  Pairs listed in *double_loss* get ``DOUBLE_LOSS``.
    """
    for matchup in round_.matchups:
        if matchup.player2 is None:
            continue
        if frozenset({matchup.player1.id, matchup.player2.id}) in double_loss:
            matchup.outcome = MatchupOutcome.DOUBLE_LOSS
        elif matchup.player2.id in winners:
            matchup.outcome = MatchupOutcome.PLAYER2_WINS
        else:
            matchup.outcome = MatchupOutcome.PLAYER1_WINS
    return round_


def play(
    pairing: BasePairing,
    round_: Round,
    winners: Collection[str] = (),
    double_loss: Collection[frozenset[str]] = (),
) -> None:
    """Record outcomes (see :func:`set_outcomes`) and submit the round."""
    pairing.submit_results(set_outcomes(round_, winners, double_loss))


def pair_of(a: str, b: str) -> frozenset[str]:
    return frozenset({a, b})


def ranks(pairing: BracketPairing) -> list[tuple[str, int]]:
    """Placings as ``(participant id, rank)`` in reported order."""
    return [(s.player.id, s.rank) for s in pairing.placements()]
