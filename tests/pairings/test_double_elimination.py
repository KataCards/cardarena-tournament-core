import pytest

from cardarena_tournament_core.common.errors import PairingStateError, TournamentCompleteError
from cardarena_tournament_core.common.models import Bracket, MatchupOutcome
from cardarena_tournament_core.pairings.double_elimination import DoubleElimination

from tests.pairings.helpers import ids, pair_of, play, players, ranks, set_outcomes

W, L, GF = Bracket.WINNERS, Bracket.LOSERS, Bracket.GRAND_FINAL


def _eight_to_grand_final(grand_final_reset: bool = True) -> DoubleElimination:
    """8 players, higher seed wins everything up to (not including) the grand final."""
    de = DoubleElimination(players(8), grand_final_reset=grand_final_reset)
    play(de, de.pair())
    play(de, de.pair(), winners={"p5", "p6"})
    play(de, de.pair(), winners={"p3", "p4"})
    play(de, de.pair())
    play(de, de.pair(), winners={"p2"})
    return de


# -------------------------------------------------------------------------
# Schedule
# -------------------------------------------------------------------------


def test_8_players_schedule_all_higher_seeds_win():
    de = DoubleElimination(players(8))

    r1 = de.pair()
    assert ids(r1) == [("p1", "p8"), ("p4", "p5"), ("p2", "p7"), ("p3", "p6")]
    assert [m.bracket for m in r1.matchups] == [W] * 4
    play(de, r1)

    r2 = de.pair()
    assert ids(r2) == [("p1", "p4"), ("p2", "p3"), ("p8", "p5"), ("p7", "p6")]
    assert [m.bracket for m in r2.matchups] == [W, W, L, L]
    play(de, r2, winners={"p5", "p6"})

    r3 = de.pair()
    assert ids(r3) == [("p1", "p2"), ("p5", "p3"), ("p6", "p4")]
    assert [m.bracket for m in r3.matchups] == [W, L, L]
    play(de, r3, winners={"p3", "p4"})

    r4 = de.pair()
    assert ids(r4) == [("p3", "p4")]
    assert r4.matchups[0].bracket is L
    play(de, r4)

    r5 = de.pair()
    assert ids(r5) == [("p3", "p2")]
    play(de, r5, winners={"p2"})

    r6 = de.pair()
    assert ids(r6) == [("p1", "p2")]
    assert r6.matchups[0].bracket is GF
    assert r6.round_number == 6
    play(de, r6)

    assert de.is_complete
    assert de.champion is not None and de.champion.id == "p1"
    assert ranks(de) == [
        ("p1", 1), ("p2", 2), ("p3", 3), ("p4", 4),
        ("p5", 5), ("p6", 5), ("p7", 7), ("p8", 7),
    ]
    with pytest.raises(TournamentCompleteError):
        de.pair()


def test_grand_final_reset_played_when_losers_champion_wins():
    de = _eight_to_grand_final()
    play(de, de.pair(), winners={"p2"})

    assert not de.is_complete
    r7 = de.pair()
    assert ids(r7) == [("p1", "p2")]
    assert r7.matchups[0].bracket is GF
    play(de, r7, winners={"p2"})

    assert de.champion is not None and de.champion.id == "p2"
    assert ranks(de)[:3] == [("p2", 1), ("p1", 2), ("p3", 3)]


def test_grand_final_reset_then_winners_champion_wins():
    de = _eight_to_grand_final()
    play(de, de.pair(), winners={"p2"})
    play(de, de.pair())

    assert de.champion is not None and de.champion.id == "p1"
    assert ranks(de)[:2] == [("p1", 1), ("p2", 2)]


def test_no_reset_first_grand_final_decides():
    de = _eight_to_grand_final(grand_final_reset=False)
    play(de, de.pair(), winners={"p2"})

    assert de.is_complete
    assert de.champion is not None and de.champion.id == "p2"
    assert ranks(de)[:2] == [("p2", 1), ("p1", 2)]


def test_2_players():
    de = DoubleElimination(players(2))

    r1 = de.pair()
    assert ids(r1) == [("p1", "p2")] and r1.matchups[0].bracket is W
    play(de, r1)

    r2 = de.pair()
    assert ids(r2) == [("p1", "p2")] and r2.matchups[0].bracket is GF
    play(de, r2, winners={"p2"})

    r3 = de.pair()
    assert ids(r3) == [("p1", "p2")] and r3.matchups[0].bracket is GF
    play(de, r3)

    assert de.champion is not None and de.champion.id == "p1"


def test_2_players_winner_takes_grand_final_directly():
    de = DoubleElimination(players(2))
    play(de, de.pair(), winners={"p2"})

    r2 = de.pair()
    assert ids(r2) == [("p2", "p1")]
    play(de, r2)

    assert de.champion is not None and de.champion.id == "p2"


def test_1_player_is_champion_immediately():
    de = DoubleElimination(players(1))

    assert de.is_complete and de.champion is not None and de.champion.id == "p1"


def test_4_players_full_run():
    de = DoubleElimination(players(4))

    r1 = de.pair()
    assert ids(r1) == [("p1", "p4"), ("p2", "p3")]
    play(de, r1)

    r2 = de.pair()
    assert ids(r2) == [("p1", "p2"), ("p4", "p3")]
    assert [m.bracket for m in r2.matchups] == [W, L]
    play(de, r2, winners={"p3"})

    r3 = de.pair()
    assert ids(r3) == [("p3", "p2")]
    play(de, r3)

    r4 = de.pair()
    assert ids(r4) == [("p1", "p3")]
    assert r4.matchups[0].bracket is GF
    play(de, r4)

    assert ranks(de) == [("p1", 1), ("p3", 2), ("p2", 3), ("p4", 4)]


def test_5_players_losers_walkovers():
    de = DoubleElimination(players(5))

    r1 = de.pair()
    assert ids(r1) == [("p1", None), ("p4", "p5"), ("p2", None), ("p3", None)]
    play(de, r1)

    r2 = de.pair()
    assert ids(r2) == [("p1", "p4"), ("p2", "p3"), ("p5", None)]
    assert [m.bracket for m in r2.matchups] == [W, W, L]


def test_5_players_runs_to_a_champion():
    de = DoubleElimination(players(5))
    while not de.is_complete:
        play(de, de.pair())

    assert de.champion is not None and de.champion.id == "p1"
    assert len(de.placements()) == 5
    assert ranks(de)[0] == ("p1", 1)


# -------------------------------------------------------------------------
# Results
# -------------------------------------------------------------------------


def test_winners_double_loss_eliminates_both_and_leaves_drop_slot_empty():
    de = DoubleElimination(players(8))
    play(de, de.pair(), double_loss={pair_of("p1", "p8")})

    assert "p1" not in de.active_participant_ids
    assert "p8" not in de.active_participant_ids
    assert ids(de.pair()) == [("p4", None), ("p2", "p3"), ("p5", None), ("p7", "p6")]


def test_losers_double_loss_eliminates_both():
    de = DoubleElimination(players(8))
    play(de, de.pair())
    play(de, de.pair(), double_loss={pair_of("p8", "p5")})

    assert de.active_participant_ids == {"p1", "p2", "p3", "p4", "p7"}
    # p3 dropped from the winners bracket and has nobody to play in L2.
    assert ids(de.pair()) == [("p1", "p2"), ("p3", None), ("p7", "p4")]


def test_grand_final_double_loss_rejected():
    de = _eight_to_grand_final()
    r6 = set_outcomes(de.pair(), double_loss={pair_of("p1", "p2")})

    with pytest.raises(PairingStateError, match="grand final"):
        de.submit_results(r6)
    assert len(de.rounds) == 5


def test_second_grand_final_double_loss_rejected():
    de = _eight_to_grand_final()
    play(de, de.pair(), winners={"p2"})
    r7 = set_outcomes(de.pair(), double_loss={pair_of("p1", "p2")})

    with pytest.raises(PairingStateError, match="grand final"):
        de.submit_results(r7)


def test_draw_rejected():
    de = DoubleElimination(players(2))
    r1 = de.pair()
    r1.matchups[0].outcome = MatchupOutcome.DRAW

    with pytest.raises(PairingStateError, match="DRAW"):
        de.submit_results(r1)


def test_double_loss_leaving_nobody_rejected():
    de = DoubleElimination(players(2))
    r1 = set_outcomes(de.pair(), double_loss={pair_of("p1", "p2")})

    with pytest.raises(PairingStateError, match="nobody"):
        de.submit_results(r1)


# -------------------------------------------------------------------------
# Withdrawals
# -------------------------------------------------------------------------


def test_withdrawn_player_does_not_drop_to_losers():
    de = DoubleElimination(players(8))
    se_like_round = de.pair()
    de.remove_active_participant("p8")
    # p8 had already been paired; they lose, but have withdrawn.
    play(de, se_like_round)

    assert ids(de.pair()) == [("p1", "p4"), ("p2", "p3"), ("p5", None), ("p7", "p6")]


def test_winners_champion_withdraws_before_grand_final_places_second():
    de = DoubleElimination(players(8))
    play(de, de.pair())
    play(de, de.pair(), winners={"p5", "p6"})
    play(de, de.pair(), winners={"p3", "p4"})
    de.remove_active_participant("p1")
    snapshot = DoubleElimination.from_dict(de.to_dict())
    assert ranks(snapshot) == ranks(de)

    play(de, de.pair())
    play(de, de.pair(), winners={"p2"})

    assert de.is_complete
    assert de.champion is not None and de.champion.id == "p2"
    assert ranks(de)[:4] == [("p2", 1), ("p1", 2), ("p3", 3), ("p4", 4)]


def test_only_one_alive_completes_without_grand_final():
    de = DoubleElimination(players(4))
    play(de, de.pair())
    for pid in ("p2", "p3", "p4"):
        de.remove_active_participant(pid)

    assert de.is_complete
    assert de.champion is not None and de.champion.id == "p1"


# -------------------------------------------------------------------------
# Persistence
# -------------------------------------------------------------------------


def test_to_dict_config_and_round_trip_mid_event():
    de = DoubleElimination(players(8))
    play(de, de.pair())
    play(de, de.pair(), winners={"p5", "p6"})
    play(de, de.pair(), winners={"p3", "p4"})

    data = de.to_dict()
    restored = DoubleElimination.from_dict(data)

    assert data["config"] == {"grand_final_reset": True}
    assert set(data) == {"participants", "rounds", "active_participant_ids", "config"}
    assert data["rounds"][1]["matchups"][2]["bracket"] == "losers"
    assert ids(restored.pair()) == ids(de.pair()) == [("p3", "p4")]
    assert restored.active_participant_ids == de.active_participant_ids


def test_from_dict_keeps_grand_final_reset_false():
    de = _eight_to_grand_final(grand_final_reset=False)
    restored = DoubleElimination.from_dict(de.to_dict())
    play(restored, restored.pair(), winners={"p2"})

    assert restored.to_dict()["config"] == {"grand_final_reset": False}
    assert restored.is_complete


def test_from_history_respects_grand_final_reset_false():
    de = _eight_to_grand_final(grand_final_reset=False)
    play(de, de.pair(), winners={"p2"})

    rebuilt = DoubleElimination.from_history(
        players(8), de.rounds, set(de.active_participant_ids), grand_final_reset=False
    )

    assert rebuilt.is_complete
    assert rebuilt.champion is not None and rebuilt.champion.id == "p2"


def test_from_history_rejects_incomplete_round():
    de = DoubleElimination(players(4))

    with pytest.raises(PairingStateError, match="incomplete round 1"):
        DoubleElimination.from_history(players(4), [de.pair()], {"p1"})
