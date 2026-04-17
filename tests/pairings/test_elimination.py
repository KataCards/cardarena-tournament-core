import pytest

from cardarena_tournament_core.common.errors import PairingStateError, TournamentCompleteError
from cardarena_tournament_core.common.models import MatchupOutcome, Player, Round
from cardarena_tournament_core.pairings.elimination import SingleElimination


def make_players(n: int) -> list[Player]:
    return [Player(id=str(i), name=f"P{i}") for i in range(n)]


def test_first_round_4_players_produces_2_matchups():
    elim = SingleElimination(make_players(4))
    r = elim.pair()
    real = [m for m in r.matchups if m.player2 is not None]
    assert len(real) == 2


def test_first_round_seeded_1v4_2v3():
    players = make_players(4)
    elim = SingleElimination(players)
    r = elim.pair()

    pairs = {frozenset([m.player1.id, m.player2.id]) for m in r.matchups if m.player2}
    assert frozenset(["0", "3"]) in pairs  # P0 (seed 1) vs P3 (seed 4)
    assert frozenset(["1", "2"]) in pairs  # P1 (seed 2) vs P2 (seed 3)


def test_winners_advance_to_next_round():
    players = make_players(4)
    elim = SingleElimination(players)
    r1 = elim.pair()

    # P0 and P1 win
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    r2 = elim.pair()
    assert len(r2.matchups) == 1

    r1_winners = {m.player1.id for m in r1.matchups if m.player2 is not None}
    r2_player_ids = {r2.matchups[0].player1.id, r2.matchups[0].player2.id} # type: ignore
    assert r2_player_ids == r1_winners


def test_odd_players_gives_bye():
    elim = SingleElimination(make_players(5))
    r = elim.pair()

    byes = [m for m in r.matchups if m.player2 is None]
    assert len(byes) == 1


def test_bye_player_advances_automatically():
    players = make_players(3)  # P0 vs P2, P1 gets bye
    elim = SingleElimination(players)
    r1 = elim.pair()

    real_m = next(m for m in r1.matchups if m.player2 is not None)
    real_m.outcome = MatchupOutcome.PLAYER1_WINS  # winner of real match advances
    elim.submit_results(r1)

    r2 = elim.pair()
    r2_player_ids = {r2.matchups[0].player1.id}
    if r2.matchups[0].player2 is not None:
        r2_player_ids.add(r2.matchups[0].player2.id)

    # Bye player and real-match winner should both be in round 2
    bye_m = next(m for m in r1.matchups if m.player2 is None)
    assert bye_m.player1.id in r2_player_ids
    assert real_m.player1.id in r2_player_ids


def test_tournament_complete_error_when_champion_found():
    players = make_players(2)
    elim = SingleElimination(players)
    r1 = elim.pair()
    r1.matchups[0].outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    with pytest.raises(TournamentCompleteError):
        elim.pair()


def test_tournament_complete_error_single_player():
    elim = SingleElimination(make_players(1))

    with pytest.raises(TournamentCompleteError):
        elim.pair()


def test_tournament_complete_error_when_all_participants_eliminated():
    elim = SingleElimination(make_players(2))
    elim._active_ids = set()  # clear active roster directly

    with pytest.raises(TournamentCompleteError, match="All participants have been eliminated"):
        elim.pair()


def test_round_numbers_increment():
    elim = SingleElimination(make_players(4))
    r1 = elim.pair()
    assert r1.round_number == 1
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)
    r2 = elim.pair()
    assert r2.round_number == 2


def test_draw_outcome_rejected_in_single_elimination():
    elim = SingleElimination(make_players(2))
    round1 = elim.pair()
    round1.matchups[0].outcome = MatchupOutcome.DRAW

    with pytest.raises(PairingStateError, match="must end with PLAYER1_WINS or PLAYER2_WINS"):
        elim.submit_results(round1)


def test_submit_results_with_no_matchups_raises_pairing_state_error():
    elim = SingleElimination(make_players(2))
    empty_round = Round(round_number=1, matchups=[])

    with pytest.raises(PairingStateError, match="no advancing participants"):
        elim.submit_results(empty_round)


def test_player2_win_advances_player2():
    elim = SingleElimination(make_players(2))
    round1 = elim.pair()
    round1.matchups[0].outcome = MatchupOutcome.PLAYER2_WINS
    elim.submit_results(round1)

    with pytest.raises(TournamentCompleteError, match="is the champion"):
        elim.pair()


def test_active_ids_updated_after_submit():
    """After submitting round 1, only winners remain active."""
    players = make_players(4)
    elim = SingleElimination(players)
    r1 = elim.pair()
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    # P0 and P1 are winners (player1 wins in each matchup)
    assert elim.active_participant_ids == frozenset({"0", "1"})


def test_seeding_order_preserved_after_elimination():
    """Active participants used in round 2 must respect original seeding order."""
    players = make_players(4)  # seeds: P0=1, P1=2, P2=3, P3=4
    elim = SingleElimination(players)

    r1 = elim.pair()
    # R1 pairs P0 vs P3 and P1 vs P2; P0 and P1 win
    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)

    r2 = elim.pair()
    assert len(r2.matchups) == 1
    # P0 (seed 1) should be player1, P1 (seed 2) should be player2
    assert r2.matchups[0].player1.id == "0"
    assert r2.matchups[0].player2 is not None
    assert r2.matchups[0].player2.id == "1"


def test_already_paired_round_submittable_after_removal_in_elimination():
    """Removing a player after pairing must not break submission of that round."""
    players = make_players(4)
    elim = SingleElimination(players)

    r1 = elim.pair()           # snapshot taken with all 4 active
    elim.remove_active_participant("3")  # remove after pairing

    for m in r1.matchups:
        m.outcome = MatchupOutcome.PLAYER1_WINS
    elim.submit_results(r1)    # must not raise
    assert len(elim.rounds) == 1


# -------------------------------------------------------------------------
# Reconstruction tests
# -------------------------------------------------------------------------

def test_from_history_matches_sequential_state():
    """CRITICAL: Verify from_history produces identical state to sequential processing."""
    players = make_players(8)
    
    # Path 1: Sequential processing
    elim1 = SingleElimination(players)
    round1 = elim1.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    elim1.submit_results(round1)
    
    # Path 2: Reconstruction from history
    elim2 = SingleElimination.from_history(
        participants=players,
        rounds=[round1],
        active_participant_ids=set(elim1.active_participant_ids)
    )
    
    # Verify IDENTICAL internal state
    assert elim1._active_ids == elim2._active_ids, "Active IDs must match exactly"
    assert elim1._seeding_order == elim2._seeding_order, "Seeding order must match"
    assert len(elim1._rounds) == len(elim2._rounds), "Round count must match"
    
    # Verify next pairing is IDENTICAL
    next1 = elim1.pair()
    next2 = elim2.pair()
    
    pairs1 = {frozenset([m.player1.id, m.player2.id if m.player2 else None]) for m in next1.matchups}
    pairs2 = {frozenset([m.player1.id, m.player2.id if m.player2 else None]) for m in next2.matchups}
    assert pairs1 == pairs2, "Next round pairings must be identical"


def test_from_history_rejects_incomplete_rounds():
    """STRICT VALIDATION: Incomplete rounds must cause immediate failure."""
    players = make_players(8)
    elim = SingleElimination(players)
    round1 = elim.pair()
    # Don't set outcomes - leave incomplete
    
    with pytest.raises(PairingStateError, match="incomplete round"):
        SingleElimination.from_history(
            participants=players,
            rounds=[round1],
            active_participant_ids={p.id for p in players}
        )


def test_from_history_rejects_unknown_active_participants():
    """STRICT VALIDATION: Unknown active IDs must cause immediate failure."""
    players = make_players(8)
    
    with pytest.raises(PairingStateError, match="unregistered participants"):
        SingleElimination.from_history(
            participants=players,
            rounds=[],
            active_participant_ids={"999"}  # Unknown ID
        )


def test_to_dict_from_dict_roundtrip():
    """Verify to_dict/from_dict preserves complete state."""
    players = make_players(8)
    elim1 = SingleElimination(players)
    
    round1 = elim1.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    elim1.submit_results(round1)
    
    # Serialize and deserialize
    data = elim1.to_dict()
    elim2 = SingleElimination.from_dict(data)
    
    # Verify identical state
    assert elim1._active_ids == elim2._active_ids
    assert elim1._seeding_order == elim2._seeding_order
    assert len(elim1._rounds) == len(elim2._rounds)


def test_from_history_with_active_override():
    """Verify active_participant_ids override works (manual removal case)."""
    players = make_players(8)
    
    elim1 = SingleElimination(players)
    round1 = elim1.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    elim1.submit_results(round1)
    
    # Manually remove a winner (edge case)
    elim1.remove_active_participant("0")
    
    # Reconstruct with override
    elim2 = SingleElimination.from_history(
        participants=players,
        rounds=[round1],
        active_participant_ids=set(elim1.active_participant_ids)
    )
    
    assert elim2.active_participant_ids == elim1.active_participant_ids
    assert "0" not in elim2.active_participant_ids


def test_from_history_multiple_rounds():
    """Verify reconstruction handles multiple rounds correctly."""
    players = make_players(8)
    
    elim1 = SingleElimination(players)
    
    # Round 1
    round1 = elim1.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    elim1.submit_results(round1)
    
    # Round 2
    round2 = elim1.pair()
    for m in round2.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    elim1.submit_results(round2)
    
    # Reconstruct
    elim2 = SingleElimination.from_history(
        participants=players,
        rounds=[round1, round2],
        active_participant_ids=set(elim1.active_participant_ids)
    )
    
    # Verify state matches
    assert elim1._active_ids == elim2._active_ids
    assert len(elim1._rounds) == len(elim2._rounds)
    
    # Verify next round is identical
    next1 = elim1.pair()
    next2 = elim2.pair()
    
    pairs1 = {frozenset([m.player1.id, m.player2.id if m.player2 else None]) for m in next1.matchups}
    pairs2 = {frozenset([m.player1.id, m.player2.id if m.player2 else None]) for m in next2.matchups}
    assert pairs1 == pairs2


def test_from_history_empty_rounds_list():
    """Verify reconstruction with no rounds creates fresh state."""
    players = make_players(8)
    elim = SingleElimination.from_history(
        participants=players,
        rounds=[],
        active_participant_ids={p.id for p in players}
    )
    
    assert len(elim._rounds) == 0
    assert elim.active_participant_ids == {p.id for p in players}
    assert elim._seeding_order == [str(i) for i in range(8)]


def test_from_history_with_byes():
    """Verify reconstruction handles rounds with byes correctly."""
    players = make_players(7)  # Odd number for bye
    
    elim1 = SingleElimination(players)
    round1 = elim1.pair()
    for m in round1.matchups:
        if m.player2:
            m.outcome = MatchupOutcome.PLAYER1_WINS
    elim1.submit_results(round1)
    
    # Reconstruct
    elim2 = SingleElimination.from_history(
        participants=players,
        rounds=[round1],
        active_participant_ids=set(elim1.active_participant_ids)
    )
    
    # Verify state matches
    assert elim1._active_ids == elim2._active_ids
    
    # Verify next round is identical
    next1 = elim1.pair()
    next2 = elim2.pair()
    
    pairs1 = {frozenset([m.player1.id, m.player2.id if m.player2 else None]) for m in next1.matchups}
    pairs2 = {frozenset([m.player1.id, m.player2.id if m.player2 else None]) for m in next2.matchups}
    assert pairs1 == pairs2