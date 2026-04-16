import pytest

from cardarena_tournament_core.common.errors import IncompleteRoundError, ScoringValidationError
from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core.scoring.pokemon import PokemonTCG


def make_players() -> tuple[Player, Player]:
    return Player(id="p0", name="P0"), Player(id="p1", name="P1")


def test_scoring_rejects_incomplete_rounds():
    p0, p1 = make_players()
    rounds = [Round(round_number=1, matchups=[Matchup(player1=p0, player2=p1)])]

    with pytest.raises(IncompleteRoundError, match="incomplete rounds"):
        PokemonTCG().calculate(rounds)


def test_scoring_rejects_duplicate_round_numbers():
    p0, p1 = make_players()
    rounds = [
        Round(
            round_number=1,
            matchups=[Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS)],
        ),
        Round(
            round_number=1,
            matchups=[Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER2_WINS)],
        ),
    ]

    with pytest.raises(ScoringValidationError, match="Round numbers must be unique"):
        PokemonTCG().calculate(rounds)


def test_scoring_rejects_round_with_no_matchups():
    with pytest.raises(ScoringValidationError, match="at least one matchup"):
        PokemonTCG().calculate([Round(round_number=1, matchups=[])])


def test_scoring_rejects_unknown_non_pending_outcome_value():
    p0, p1 = make_players()
    matchup = Matchup(player1=p0, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS)
    matchup.outcome = "invalid"  # type: ignore[assignment]

    with pytest.raises(ScoringValidationError, match="Cannot score matchup"):
        PokemonTCG().calculate([Round(round_number=1, matchups=[matchup])])
