from cardarena_tournament_core.common.models import Matchup, MatchupOutcome, Player, Round
from cardarena_tournament_core import utils
from cardarena_tournament_core.scoring.union_arena import UnionArena


def test_union_arena_mw_percentage_basic():
    p1, p2 = Player(id="p1", name="P1"), Player(id="p2", name="P2")
    rounds = [
        Round(round_number=1, matchups=[Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS)]),
        Round(round_number=2, matchups=[Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.DRAW)]),
    ]
    # p1: win(3) + draw(1) = 4 points over 2 real rounds => 4 / (2*3) = 0.666...
    assert abs(utils.union_arena_mw_percentage("p1", rounds) - (4 / 6)) < 1e-6
    # p2: loss(0) + draw(1) = 1 / 6, but floored at 1/3 per Union Arena rules
    assert abs(utils.union_arena_mw_percentage("p2", rounds) - (1.0 / 3.0)) < 1e-6


def test_union_arena_basic_points_and_tiebreak_keys():
    standings = UnionArena().calculate([
        Round(round_number=1, matchups=[Matchup(player1=Player(id="p1", name="A"), player2=Player(id="p2", name="B"), outcome=MatchupOutcome.PLAYER1_WINS)])
    ])
    winner = next(s for s in standings if s.player.id == "p1")
    loser = next(s for s in standings if s.player.id == "p2")
    assert winner.points == 3
    assert loser.points == 0
    for s in standings:
        assert "mw_pct" in s.tiebreakers
        assert "omw_pct" in s.tiebreakers


def test_union_arena_circular_h2h_seed_behavior():
    # 3-player round robin circular: p1 beats p2, p2 beats p3, p3 beats p1
    p1, p2, p3 = Player(id="1", name="P1"), Player(id="2", name="P2"), Player(id="3", name="P3")
    rounds = [
        Round(round_number=1, matchups=[Matchup(player1=p1, player2=p2, outcome=MatchupOutcome.PLAYER1_WINS)]),
        Round(round_number=2, matchups=[Matchup(player1=p2, player2=p3, outcome=MatchupOutcome.PLAYER1_WINS)]),
        Round(round_number=3, matchups=[Matchup(player1=p3, player2=p1, outcome=MatchupOutcome.PLAYER1_WINS)]),
    ]

    # seed=None -> stable player.id order
    standings_none = UnionArena().calculate(rounds, seed=None)
    assert [s.player.id for s in standings_none] == sorted(["1", "2", "3"])  # stable id order

    # same seed → identical ordering every time
    order_42a = [s.player.id for s in UnionArena().calculate(rounds, seed=42)]
    order_42b = [s.player.id for s in UnionArena().calculate(rounds, seed=42)]
    assert order_42a == order_42b

    # different seeds → different orderings (with 3 players there are 6 permutations;
    # seeds 42 and 99 are known to produce distinct shuffles for this input)
    order_99 = [s.player.id for s in UnionArena().calculate(rounds, seed=99)]
    assert order_42a != order_99
