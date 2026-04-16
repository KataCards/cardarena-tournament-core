import pytest

from cardarena_tournament_core.common.errors import ScoringValidationError
from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core import utils


def make_players() -> tuple[Player, Player, Player]:
    return (
        Player(id="p0", name="P0"),
        Player(id="p1", name="P1"),
        Player(id="p2", name="P2"),
    )


def test_win_percentage_no_games_returns_floor():
    p0, _, _ = make_players()
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p0, player2=None)])]

    assert utils.win_percentage(p0.id, rounds, min_win_pct=0.25) == 0.25


def test_win_percentage_counts_wins_and_draws():
    p0, p1, p2 = make_players()
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
        Round(
            round_number=2,
            matchups=[
                Matchup(player1=p0, player2=p2, outcome=MatchupOutcome.DRAW),
            ],
        ),
    ]

    # (1 win + 0.5 draw) / 2 games = 0.75
    assert utils.win_percentage(p0.id, rounds) == 0.75


def test_real_opponent_ids_excludes_byes_and_preserves_order():
    p0, p1, p2 = make_players()
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
                Matchup(player1=p2, player2=None),
            ],
        ),
        Round(
            round_number=2,
            matchups=[
                Matchup(player1=p2, player2=p0, outcome=MatchupOutcome.PLAYER2_WINS),
            ],
        ),
    ]

    assert utils.real_opponent_ids(p0.id, rounds) == [p1.id, p2.id]


def test_owp_returns_zero_when_player_has_no_opponents():
    p0, _, _ = make_players()
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p0, player2=None)])]

    assert utils.owp(p0.id, rounds) == 0.0


def test_oowp_returns_zero_when_player_has_no_opponents():
    p0, _, _ = make_players()
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p0, player2=None)])]

    assert utils.oowp(p0.id, rounds) == 0.0


def test_owp_and_oowp_with_three_players():
    p0, p1, p2 = make_players()
    rounds = [
        Round(
            round_number=1,
            matchups=[
                Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
        Round(
            round_number=2,
            matchups=[
                Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
        Round(
            round_number=3,
            matchups=[
                Matchup(player1=p2, player2=p0, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        ),
    ]

    assert 0.0 <= utils.owp(p0.id, rounds) <= 1.0
    assert 0.0 <= utils.oowp(p0.id, rounds) <= 1.0


def test_utils_reject_empty_player_id():
    p0, _, _ = make_players()
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p0, player2=None)])]

    with pytest.raises(ScoringValidationError, match="player_id cannot be empty"):
        utils.real_opponent_ids("", rounds)


def test_utils_reject_invalid_min_win_pct():
    p0, _, _ = make_players()
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p0, player2=None)])]

    with pytest.raises(ScoringValidationError, match="min_win_pct must be within"):
        utils.win_percentage(p0.id, rounds, min_win_pct=1.5)

    with pytest.raises(ScoringValidationError, match="min_win_pct must be within"):
        utils.owp(p0.id, rounds, min_win_pct=-0.1)

    with pytest.raises(ScoringValidationError, match="min_win_pct must be within"):
        utils.oowp(p0.id, rounds, min_win_pct=-0.1)
