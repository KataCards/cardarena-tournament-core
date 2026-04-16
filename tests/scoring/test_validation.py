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


def test_removed_player_still_in_historical_standings():
    """Removing a player from the active roster after round 1 must not erase
    their standing entry — scoring reads from round history, not active IDs."""
    from cardarena_tournament_core.pairings.swiss import Swiss
    from cardarena_tournament_core.scoring.pokemon import PokemonTCG

    p0, p1, p2, p3 = [Player(id=str(i), name=f"P{i}") for i in range(4)]
    pairing = Swiss([p0, p1, p2, p3])
    scoring = PokemonTCG()

    round1 = pairing.pair()
    for m in round1.matchups:
        if m.player2 is not None:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    pairing.submit_results(round1)

    # Identify a winner (player1 of a real matchup) and remove them
    winner_id = next(m.player1.id for m in round1.matchups if m.player2 is not None)
    pairing.remove_active_participant(winner_id)

    standings = scoring.calculate(pairing.rounds)
    standing_ids = {s.player.id for s in standings}

    # Removed player still appears in standings
    assert winner_id in standing_ids

    # Their points are correct (3 for a win)
    winner_standing = next(s for s in standings if s.player.id == winner_id)
    assert winner_standing.points == 3
