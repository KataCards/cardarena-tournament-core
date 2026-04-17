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


# -------------------------------------------------------------------------
# yugioh_tiebreak_number
# -------------------------------------------------------------------------

def test_yugioh_tiebreak_number_known_example():
    # 33 pts, OWP 72.6%, OOWP 67.7% → 33726677
    assert utils.yugioh_tiebreak_number(33, 0.726, 0.677) == 33_726_677


def test_yugioh_tiebreak_number_with_loss_rounds():
    # 18 pts, OWP 72.6%, OOWP 67.7%, lost round 7 → sum=49 → 18726677049
    assert utils.yugioh_tiebreak_number(18, 0.726, 0.677, loss_rounds=[7]) == 18_726_677_049


def test_yugioh_tiebreak_number_higher_beats_lower():
    a = utils.yugioh_tiebreak_number(33, 0.726, 0.677)
    b = utils.yugioh_tiebreak_number(33, 0.726, 0.640)
    assert a > b


def test_yugioh_tiebreak_number_loss_in_later_round_is_better():
    early = utils.yugioh_tiebreak_number(6, 0.5, 0.5, loss_rounds=[1])
    late = utils.yugioh_tiebreak_number(6, 0.5, 0.5, loss_rounds=[5])
    assert late > early


def test_yugioh_tiebreak_number_no_loss_rounds_is_8_digits():
    result = utils.yugioh_tiebreak_number(33, 0.726, 0.677)
    assert len(str(result)) == 8


def test_yugioh_tiebreak_number_with_loss_rounds_is_11_digits():
    result = utils.yugioh_tiebreak_number(33, 0.726, 0.677, loss_rounds=[3])
    assert len(str(result)) == 11


def test_yugioh_tiebreak_number_multiple_loss_rounds():
    # Lost rounds 3 and 5: sum of squares = 9 + 25 = 34
    result = utils.yugioh_tiebreak_number(6, 0.5, 0.5, loss_rounds=[3, 5])
    loss_block = result % 1000
    assert loss_block == 34


def test_yugioh_tiebreak_number_empty_loss_rounds():
    # Empty list means zero loss block → last 3 digits are 000
    result = utils.yugioh_tiebreak_number(6, 0.5, 0.5, loss_rounds=[])
    assert result % 1000 == 0


def test_yugioh_tiebreak_number_rejects_negative_points():
    with pytest.raises(ValueError, match="points must be non-negative"):
        utils.yugioh_tiebreak_number(-1, 0.5, 0.5)


def test_yugioh_tiebreak_number_rejects_owp_out_of_range():
    with pytest.raises(ValueError, match="owp_val must be within"):
        utils.yugioh_tiebreak_number(3, 1.1, 0.5)


def test_yugioh_tiebreak_number_rejects_oowp_out_of_range():
    with pytest.raises(ValueError, match="oowp_val must be within"):
        utils.yugioh_tiebreak_number(3, 0.5, -0.1)


def test_yugioh_tiebreak_number_rejects_non_positive_loss_round():
    with pytest.raises(ValueError, match="loss round numbers must be positive"):
        utils.yugioh_tiebreak_number(3, 0.5, 0.5, loss_rounds=[0])
