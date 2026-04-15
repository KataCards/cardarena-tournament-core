from cardarena_tournament_core.models import MatchupOutcome, Round

_DEFAULT_MIN_WIN_PCT = 0.25


def win_percentage(player_id: str, rounds: list[Round], min_pct: float = _DEFAULT_MIN_WIN_PCT) -> float:
    """Win% for tiebreaker purposes: (wins + 0.5*draws) / real_games, floored at min_pct.
    Byes (player2=None) are excluded from the calculation."""
    wins = draws = total = 0
    for round in rounds:
        for m in round.matchups:
            if m.player2 is None:
                continue  # exclude byes

            if m.player1.id == player_id:
                total += 1
                if m.outcome == MatchupOutcome.PLAYER1_WINS:
                    wins += 1
                elif m.outcome == MatchupOutcome.DRAW:
                    draws += 1
            elif m.player2.id == player_id:
                total += 1
                if m.outcome == MatchupOutcome.PLAYER2_WINS:
                    wins += 1
                elif m.outcome == MatchupOutcome.DRAW:
                    draws += 1

    if total == 0:
        return min_pct
    return max((wins + 0.5 * draws) / total, min_pct)


def _opponent_ids(player_id: str, rounds: list[Round]) -> list[str]:
    """All real opponents a player has faced (byes excluded)."""
    opponents: list[str] = []
    for round in rounds:
        for m in round.matchups:
            if m.player2 is None:
                continue
            if m.player1.id == player_id:
                opponents.append(m.player2.id)
            elif m.player2.id == player_id:
                opponents.append(m.player1.id)
    return opponents


def calculate_owp(player_id: str, rounds: list[Round], min_pct: float = _DEFAULT_MIN_WIN_PCT) -> float:
    """OWP: average win% of all real opponents."""
    opp_ids = _opponent_ids(player_id, rounds)
    if not opp_ids:
        return 0.0
    return sum(win_percentage(opp_id, rounds, min_pct) for opp_id in opp_ids) / len(opp_ids)


def calculate_oowp(player_id: str, rounds: list[Round], min_pct: float = _DEFAULT_MIN_WIN_PCT) -> float:
    """OOWP: average OWP of all real opponents."""
    opp_ids = _opponent_ids(player_id, rounds)
    if not opp_ids:
        return 0.0
    return sum(calculate_owp(opp_id, rounds, min_pct) for opp_id in opp_ids) / len(opp_ids)
