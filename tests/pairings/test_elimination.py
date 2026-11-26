import pytest

from cardarena_tournament_core.common.errors import (
    PairingConfigurationError,
    PairingStateError,
    TournamentCompleteError,
)
from cardarena_tournament_core.common.models import (
    Bracket,
    Matchup,
    MatchupOutcome,
    Player,
    Round,
    Team,
)
from cardarena_tournament_core.pairings.elimination import SingleElimination

from tests.pairings.helpers import ids, pair_of, play, players, ranks, set_outcomes


# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------


def test_requires_at_least_one_participant():
    with pytest.raises(PairingConfigurationError):
        SingleElimination([])


def test_rejects_duplicate_ids():
    with pytest.raises(PairingConfigurationError, match="unique"):
        SingleElimination([Player(id="x", name="A"), Player(id="x", name="B")])


# -------------------------------------------------------------------------
# Seeding and round structure
# -------------------------------------------------------------------------


def test_round1_seeding_8():
    r = SingleElimination(players(8)).pair()

    assert ids(r) == [("p1", "p8"), ("p4", "p5"), ("p2", "p7"), ("p3", "p6")]
    assert all(m.bracket is Bracket.WINNERS for m in r.matchups)
    assert r.round_number == 1


def test_round1_byes_go_to_top_seeds_5():
    r = SingleElimination(players(5)).pair()

    assert ids(r) == [("p1", None), ("p4", "p5"), ("p2", None), ("p3", None)]


def test_round1_3_players():
    assert ids(SingleElimination(players(3)).pair()) == [("p1", None), ("p2", "p3")]


def test_round2_pairs_adjacent_winners():
    se = SingleElimination(players(8))
    play(se, se.pair())

    r2 = se.pair()

    assert ids(r2) == [("p1", "p4"), ("p2", "p3")]
    assert r2.round_number == 2


def test_bye_player_advances_to_round2():
    se = SingleElimination(players(5))
    play(se, se.pair(), winners={"p5"})

    assert ids(se.pair()) == [("p1", "p5"), ("p2", "p3")]


def test_full_run_8_champion():
    se = SingleElimination(players(8))
    for expected_rounds_left in (3, 2, 1):
        assert not se.is_complete
        assert se.champion is None
        play(se, se.pair())
        assert len(se.rounds) == 4 - expected_rounds_left

    assert se.is_complete
    assert se.champion is not None and se.champion.id == "p1"
    assert se.active_participant_ids == {"p1"}
    with pytest.raises(TournamentCompleteError, match="P1"):
        se.pair()


def test_player2_win_advances_player2():
    se = SingleElimination(players(2))
    play(se, se.pair(), winners={"p2"})

    assert se.champion is not None and se.champion.id == "p2"


def test_single_participant_is_champion_immediately():
    se = SingleElimination(players(1))

    assert se.is_complete
    assert se.champion is not None and se.champion.id == "p1"
    with pytest.raises(TournamentCompleteError):
        se.pair()


def test_team_participants_work():
    teams = [
        Team(id=f"t{i}", name=f"T{i}", members=(Player(id=f"m{i}", name=f"M{i}"),))
        for i in range(1, 5)
    ]
    se = SingleElimination(teams)
    play(se, se.pair())
    play(se, se.pair())

    assert se.champion is not None and se.champion.id == "t1"


# -------------------------------------------------------------------------
# Results
# -------------------------------------------------------------------------


def test_draw_rejected():
    se = SingleElimination(players(2))
    r = se.pair()
    r.matchups[0].outcome = MatchupOutcome.DRAW

    with pytest.raises(PairingStateError, match="DRAW"):
        se.submit_results(r)
    assert se.rounds == []


def test_incomplete_round_rejected():
    se = SingleElimination(players(2))

    with pytest.raises(PairingStateError, match="incomplete"):
        se.submit_results(se.pair())


def test_round_with_no_matchups_rejected():
    se = SingleElimination(players(2))

    with pytest.raises(PairingStateError, match="at least one matchup"):
        se.submit_results(Round(round_number=1, matchups=[]))


def test_double_loss_eliminates_both_and_gives_walkover():
    se = SingleElimination(players(8))
    play(se, se.pair(), double_loss={pair_of("p1", "p8")})

    assert se.active_participant_ids == {"p4", "p2", "p3"}
    assert ids(se.pair()) == [("p4", None), ("p2", "p3")]


def test_double_loss_semi_ends_tournament_early():
    se = SingleElimination(players(4))
    play(se, se.pair(), double_loss={pair_of("p1", "p4")})

    assert se.is_complete
    assert se.champion is not None and se.champion.id == "p2"


def test_double_loss_in_final_rejected_and_state_unchanged():
    se = SingleElimination(players(2))
    r = set_outcomes(se.pair(), double_loss={pair_of("p1", "p2")})

    with pytest.raises(PairingStateError, match="nobody"):
        se.submit_results(r)

    assert se.rounds == []
    assert se.active_participant_ids == {"p1", "p2"}
    assert ids(se.pair()) == [("p1", "p2")]


def test_both_semis_double_loss_rejected():
    se = SingleElimination(players(4))
    r = set_outcomes(se.pair(), double_loss={pair_of("p1", "p4"), pair_of("p2", "p3")})

    with pytest.raises(PairingStateError, match="nobody"):
        se.submit_results(r)
    assert se.active_participant_ids == {"p1", "p2", "p3", "p4"}


def test_double_loss_between_last_two_alive_before_final_rejected():
    se = SingleElimination(players(8))
    # The whole top half goes out in round 1.
    play(se, se.pair(), double_loss={pair_of("p1", "p8"), pair_of("p4", "p5")})
    r2 = se.pair()
    assert ids(r2) == [("p2", "p3")]

    with pytest.raises(PairingStateError, match="nobody"):
        se.submit_results(set_outcomes(r2, double_loss={pair_of("p2", "p3")}))


def test_walkover_only_round_is_emitted():
    se = SingleElimination(players(8))
    play(se, se.pair(), double_loss={pair_of("p1", "p8"), pair_of("p2", "p7")})

    r2 = se.pair()
    assert ids(r2) == [("p4", None), ("p3", None)]
    se.submit_results(r2)

    r3 = se.pair()
    assert ids(r3) == [("p4", "p3")]
    assert r3.round_number == 3


# -------------------------------------------------------------------------
# Submitted rounds are checked against the bracket
# -------------------------------------------------------------------------

P1, P2, P3, P4 = players(4)


def test_submitted_players_swapped_reads_outcome_in_submitted_order():
    se = SingleElimination(players(2))
    se.pair()

    se.submit_results(
        Round(1, [Matchup(player1=P2, player2=P1, outcome=MatchupOutcome.PLAYER1_WINS)])
    )

    assert se.champion is not None and se.champion.id == "p2"


def test_submitted_bracket_label_none_is_accepted():
    se = SingleElimination(players(4))
    se.pair()

    se.submit_results(
        Round(
            1,
            [
                Matchup(player1=P1, player2=P4, outcome=MatchupOutcome.PLAYER1_WINS),
                Matchup(player1=P2, player2=P3, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        )
    )

    assert ids(se.pair()) == [("p1", "p2")]


def test_round_not_fitting_bracket_rejected_and_state_unchanged():
    se = SingleElimination(players(8))
    first = ids(se.pair())
    wrong = Round(
        1,
        [
            Matchup(player1=P1, player2=P2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=P3, player2=P4, outcome=MatchupOutcome.PLAYER1_WINS),
        ],
    )

    with pytest.raises(PairingStateError, match="bracket"):
        se.submit_results(wrong)

    assert se.rounds == []
    assert len(se.active_participant_ids) == 8
    assert ids(se.pair()) == first


def test_same_player_in_two_matchups_rejected():
    se = SingleElimination(players(4))
    se.pair()
    wrong = Round(
        1,
        [
            Matchup(player1=P1, player2=P4, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=P1, player2=None),
        ],
    )

    with pytest.raises(PairingStateError, match="more than one"):
        se.submit_results(wrong)


def test_matchup_from_a_later_round_rejected():
    se = SingleElimination(players(4))
    r1 = set_outcomes(se.pair())
    r1.matchups.append(Matchup(player1=P1, player2=P2, outcome=MatchupOutcome.PLAYER1_WINS))

    with pytest.raises(PairingStateError):
        se.submit_results(r1)


def test_separate_byes_for_two_players_of_one_match_rejected():
    se = SingleElimination(players(4))
    se.pair()
    wrong = Round(
        1,
        [
            Matchup(player1=P1, player2=None),
            Matchup(player1=P4, player2=None),
            Matchup(player1=P2, player2=P3, outcome=MatchupOutcome.PLAYER1_WINS),
        ],
    )

    with pytest.raises(PairingStateError, match="same matchup"):
        se.submit_results(wrong)


def test_matchup_for_eliminated_player_rejected_on_replay():
    se = SingleElimination(players(4))
    play(se, se.pair())
    # Submitted without pair(), as a replay does: p3 lost in round 1.
    wrong = Round(
        2,
        [
            Matchup(player1=P1, player2=P2, outcome=MatchupOutcome.PLAYER1_WINS),
            Matchup(player1=P3, player2=None),
        ],
    )

    with pytest.raises(PairingStateError, match="not a pending match"):
        se.submit_results(wrong)
    assert len(se.rounds) == 1


def test_out_of_order_round_number_rejected():
    se = SingleElimination(players(2))
    r = set_outcomes(se.pair())
    r.round_number = 2

    with pytest.raises(PairingStateError, match="out of order"):
        se.submit_results(r)


# -------------------------------------------------------------------------
# Withdrawals
# -------------------------------------------------------------------------


def test_withdraw_before_round1_gives_opponent_walkover():
    se = SingleElimination(players(4))
    se.remove_active_participant("p4")

    assert ids(se.pair()) == [("p1", None), ("p2", "p3")]


def test_withdraw_between_rounds_gives_walkover():
    se = SingleElimination(players(4))
    play(se, se.pair())
    se.remove_active_participant("p2")

    # Only p1 is left, so the event is over without a final.
    assert se.is_complete
    assert se.champion is not None and se.champion.id == "p1"


def test_withdraw_between_rounds_gives_walkover_8():
    se = SingleElimination(players(8))
    play(se, se.pair())
    se.remove_active_participant("p4")

    assert ids(se.pair()) == [("p1", None), ("p2", "p3")]


def test_already_paired_round_is_submittable_after_withdrawal():
    se = SingleElimination(players(4))
    r1 = se.pair()
    se.remove_active_participant("p4")

    play(se, r1, winners={"p4"})

    # p4 won the match but has withdrawn: p4 is not paired again.
    assert se.active_participant_ids == {"p2"}
    assert se.is_complete


def test_bye_submitted_for_two_player_match_withdraws_the_other():
    se = SingleElimination(players(4))
    se.pair()

    se.submit_results(
        Round(
            1,
            [
                Matchup(player1=P1, player2=None),
                Matchup(player1=P2, player2=P3, outcome=MatchupOutcome.PLAYER1_WINS),
            ],
        )
    )

    assert se.active_participant_ids == {"p1", "p2"}
    with pytest.raises(PairingStateError, match="p4"):
        se.reactivate_participant("p4")


def test_pending_match_missing_from_round_withdraws_both():
    se = SingleElimination(players(4))
    se.pair()

    se.submit_results(
        Round(1, [Matchup(player1=P2, player2=P3, outcome=MatchupOutcome.PLAYER2_WINS)])
    )

    assert se.active_participant_ids == {"p3"}
    assert se.champion is not None and se.champion.id == "p3"


def test_reactivate_before_next_round_restores_match():
    se = SingleElimination(players(4))
    se.remove_active_participant("p4")
    se.reactivate_participant("p4")

    assert ids(se.pair()) == [("p1", "p4"), ("p2", "p3")]


def test_reactivate_eliminated_raises():
    se = SingleElimination(players(4))
    play(se, se.pair())

    with pytest.raises(PairingStateError, match="p4"):
        se.reactivate_participant("p4")


def test_remove_eliminated_raises():
    se = SingleElimination(players(4))
    play(se, se.pair())

    with pytest.raises(PairingStateError, match="already inactive"):
        se.remove_active_participant("p4")


def test_everyone_withdraws_no_champion():
    se = SingleElimination(players(2))
    se.remove_active_participant("p1")
    se.remove_active_participant("p2")

    assert se.is_complete
    assert se.champion is None
    with pytest.raises(TournamentCompleteError, match="No participants"):
        se.pair()


# -------------------------------------------------------------------------
# Persistence
# -------------------------------------------------------------------------


def _mid_event() -> SingleElimination:
    se = SingleElimination(players(8))
    play(se, se.pair(), double_loss={pair_of("p2", "p7")})
    se.remove_active_participant("p4")
    return se


def test_to_dict_keys():
    data = _mid_event().to_dict()

    assert set(data) == {"participants", "rounds", "active_participant_ids"}
    assert data["active_participant_ids"] == ["p1", "p3"]
    assert [p["id"] for p in data["participants"]] == [f"p{i}" for i in range(1, 9)]


def test_to_dict_from_dict_round_trip_next_pairing_identical():
    original = _mid_event()
    restored = SingleElimination.from_dict(original.to_dict())

    assert restored.active_participant_ids == original.active_participant_ids
    assert ids(restored.pair()) == ids(original.pair()) == [("p1", None), ("p3", None)]
    assert len(restored.rounds) == 1


def test_from_history_matches_sequential_state():
    live = SingleElimination(players(8))
    play(live, live.pair())
    play(live, live.pair(), winners={"p4"})

    rebuilt = SingleElimination.from_history(
        participants=players(8),
        rounds=live.rounds,
        active_participant_ids=set(live.active_participant_ids),
    )

    assert ids(rebuilt.pair()) == ids(live.pair()) == [("p4", "p2")]


def test_from_history_empty_rounds():
    rebuilt = SingleElimination.from_history(players(4), [], {"p1", "p2", "p3", "p4"})

    assert ids(rebuilt.pair()) == [("p1", "p4"), ("p2", "p3")]


def test_from_history_rejects_incomplete_round():
    se = SingleElimination(players(4))
    r1 = se.pair()

    with pytest.raises(PairingStateError, match="incomplete round 1"):
        SingleElimination.from_history(players(4), [r1], {"p1", "p2"})


def test_from_history_rejects_unknown_active_id():
    with pytest.raises(PairingStateError, match="ghost"):
        SingleElimination.from_history(players(4), [], {"p1", "ghost"})


def test_from_history_ignores_eliminated_ids_in_active_set():
    live = SingleElimination(players(4))
    play(live, live.pair())

    rebuilt = SingleElimination.from_history(
        players(4), live.rounds, {"p1", "p2", "p3", "p4"}
    )

    assert rebuilt.active_participant_ids == {"p1", "p2"}


def test_from_history_withdrawal_since_last_round_can_be_reactivated():
    live = SingleElimination(players(4))
    play(live, live.pair())

    rebuilt = SingleElimination.from_history(players(4), live.rounds, {"p1"})
    assert rebuilt.is_complete
    rebuilt.reactivate_participant("p2")

    assert ids(rebuilt.pair()) == [("p1", "p2")]


# -------------------------------------------------------------------------
# Placings
# -------------------------------------------------------------------------


def _run_to_end(se: SingleElimination) -> SingleElimination:
    while not se.is_complete:
        play(se, se.pair())
    return se


def test_placements_full_8():
    se = _run_to_end(SingleElimination(players(8)))

    assert ranks(se) == [
        ("p1", 1), ("p2", 2), ("p3", 3), ("p4", 3),
        ("p5", 5), ("p6", 5), ("p7", 5), ("p8", 5),
    ]
    points = {s.player.id: s.points for s in se.placements()}
    assert points == {"p1": 3, "p2": 2, "p3": 1, "p4": 1, "p5": 0, "p6": 0, "p7": 0, "p8": 0}
    assert all(s.tiebreakers == {} for s in se.placements())


def test_placements_before_any_round_all_rank_1():
    assert ranks(SingleElimination(players(3))) == [("p1", 1), ("p2", 1), ("p3", 1)]


def test_placements_mid_event_alive_share_rank_1():
    se = SingleElimination(players(8))
    play(se, se.pair())

    assert ranks(se) == [
        ("p1", 1), ("p2", 1), ("p3", 1), ("p4", 1),
        ("p5", 5), ("p6", 5), ("p7", 5), ("p8", 5),
    ]


def test_placements_walkover_not_counted_as_win():
    se = _run_to_end(SingleElimination(players(5)))

    points = {s.player.id: s.points for s in se.placements()}
    assert se.champion is not None and se.champion.id == "p1"
    assert points["p1"] == 2  # bye in round 1, then two real wins


def test_placements_double_loss_pair_share_rank():
    se = SingleElimination(players(8))
    play(se, se.pair())
    play(se, se.pair(), double_loss={pair_of("p1", "p4")})

    # p2 beat p3 and is the only one left.
    assert ranks(se)[:4] == [("p2", 1), ("p1", 2), ("p3", 2), ("p4", 2)]


def test_placements_withdrawn_before_round1_ranks_with_round1_losers():
    se = SingleElimination(players(4))
    se.remove_active_participant("p4")
    assert ranks(se) == [("p1", 1), ("p2", 1), ("p3", 1), ("p4", 4)]

    play(se, se.pair())

    assert ranks(se) == [("p1", 1), ("p2", 1), ("p3", 3), ("p4", 3)]


def test_placements_withdrawn_between_rounds_ranks_with_next_round_losers():
    se = SingleElimination(players(8))
    play(se, se.pair())
    se.remove_active_participant("p4")
    assert ranks(se)[:4] == [("p1", 1), ("p2", 1), ("p3", 1), ("p4", 4)]

    play(se, se.pair())

    assert ranks(se)[:4] == [("p1", 1), ("p2", 1), ("p3", 3), ("p4", 3)]


def test_placements_identical_after_from_dict():
    se = SingleElimination(players(8))
    play(se, se.pair(), double_loss={pair_of("p2", "p7")})
    se.remove_active_participant("p4")

    restored = SingleElimination.from_dict(se.to_dict())

    assert ranks(restored) == ranks(se)
    assert [s.points for s in restored.placements()] == [s.points for s in se.placements()]


def test_placements_champion_who_withdraws_afterwards_keeps_first_place():
    se = _run_to_end(SingleElimination(players(2)))
    se.remove_active_participant("p1")

    assert ranks(se) == [("p1", 1), ("p2", 2)]
