"""Utility functions for tournament calculations.

This module provides shared utility functions used across different tournament
systems, including win percentage calculations and tiebreaker computations.
"""

from cardarena_tournament_core.common.errors import ScoringValidationError
from cardarena_tournament_core.common.models import MatchupOutcome, Round


# -------------------------------------------------------------------------
# Validation helpers / Private functions
# -------------------------------------------------------------------------

def _validate_player_id(player_id: str) -> None:
    if not player_id:
        raise ScoringValidationError("player_id cannot be empty.")


def _validate_min_win_pct(min_win_pct: float) -> None:
    if not 0.0 <= min_win_pct <= 1.0:
        raise ScoringValidationError("min_win_pct must be within [0.0, 1.0].")

# -------------------------------------------------------------------------
# Calculation helpers / ID Helper
# -------------------------------------------------------------------------


def win_percentage(player_id: str, rounds: list[Round], *, min_win_pct: float = 0.0) -> float:
    """Calculate win percentage for a player across all rounds.

    Win% = (wins + 0.5 × draws) / total_real_games, with optional floor.
    Bye matches are excluded — they don't count as real games.

    Args:
        player_id: The player's unique identifier.
        rounds: All completed rounds to analyze.
        min_win_pct: Minimum win percentage floor (0.0 = no floor, 0.25 = Pokémon TCG).

    Returns:
        Win percentage as a float between min_win_pct and 1.0.
    """
    _validate_player_id(player_id)
    _validate_min_win_pct(min_win_pct)

    wins = draws = total_real_games = 0
    for tournament_round in rounds:
        for matchup in tournament_round.matchups:
            if matchup.player2 is None:
                continue  # bye — not a real game
            if matchup.player1.id == player_id:
                total_real_games += 1
                if matchup.outcome == MatchupOutcome.PLAYER1_WINS:
                    wins += 1
                elif matchup.outcome == MatchupOutcome.DRAW:
                    draws += 1
            elif matchup.player2.id == player_id:
                total_real_games += 1
                if matchup.outcome == MatchupOutcome.PLAYER2_WINS:
                    wins += 1
                elif matchup.outcome == MatchupOutcome.DRAW:
                    draws += 1
    
    if total_real_games == 0:
        return min_win_pct
    
    return max((wins + 0.5 * draws) / total_real_games, min_win_pct)


def real_opponent_ids(player_id: str, rounds: list[Round]) -> list[str]:
    """Get IDs of all real opponents a player has faced.

    Bye matches are excluded.

    Args:
        player_id: The player's unique identifier.
        rounds: All completed rounds to analyze.

    Returns:
        List of opponent IDs in chronological order.
    """
    _validate_player_id(player_id)

    opponent_ids: list[str] = []
    for tournament_round in rounds:
        for matchup in tournament_round.matchups:
            if matchup.player2 is None:
                continue  # bye — no real opponent
            if matchup.player1.id == player_id:
                opponent_ids.append(matchup.player2.id)
            elif matchup.player2.id == player_id:
                opponent_ids.append(matchup.player1.id)
    return opponent_ids


def owp(player_id: str, rounds: list[Round], *, min_win_pct: float = 0.0) -> float:
    """Calculate Opponents' Win Percentage.

    OWP is the average win percentage of all real opponents faced.

    Args:
        player_id: The player's unique identifier.
        rounds: All completed rounds to analyze.
        min_win_pct: Minimum win percentage floor for opponents.

    Returns:
        Average opponent win percentage, or 0.0 if no opponents.
    """
    _validate_player_id(player_id)
    _validate_min_win_pct(min_win_pct)

    opponent_ids = real_opponent_ids(player_id, rounds)
    if not opponent_ids:
        return 0.0

    win_pct_cache: dict[str, float] = {
        opponent_id: win_percentage(opponent_id, rounds, min_win_pct=min_win_pct)
        for opponent_id in set(opponent_ids)
    }
    return sum(
        win_pct_cache[opp_id]
        for opp_id in opponent_ids
    ) / len(opponent_ids)


def oowp(player_id: str, rounds: list[Round], *, min_win_pct: float = 0.0) -> float:
    """Calculate Opponents' Opponents' Win Percentage.

    OOWP is the average OWP of all real opponents faced.

    Args:
        player_id: The player's unique identifier.
        rounds: All completed rounds to analyze.
        min_win_pct: Minimum win percentage floor for opponents.

    Returns:
        Average opponent OWP, or 0.0 if no opponents.
    """
    _validate_player_id(player_id)
    _validate_min_win_pct(min_win_pct)

    opponent_ids = real_opponent_ids(player_id, rounds)
    if not opponent_ids:
        return 0.0

    owp_cache: dict[str, float] = {
        opponent_id: owp(opponent_id, rounds, min_win_pct=min_win_pct)
        for opponent_id in set(opponent_ids)
    }
    return sum(
        owp_cache[opp_id]
        for opp_id in opponent_ids
    ) / len(opponent_ids)


def yugioh_tiebreak_number(
    points: int,
    owp_val: float,
    oowp_val: float,
    loss_rounds: list[int] | None = None,
) -> int:
    """Encode a Yu-Gi-Oh! tiebreak number from its components.

    The tiebreak number is a single integer that preserves multi-level sort order:
    a higher number always beats a lower number, block by block.

    Format without loss rounds — 8 digits: ``XXYYYZZZ``
    Format with loss rounds    — 11 digits: ``XXYYYZZZTTT``

    Blocks:
        XX  — match points, clamped to [0, 99]
        YYY — OWP * 1000, rounded and clamped to [0, 999]
        ZZZ — OOWP * 1000, rounded and clamped to [0, 999]
        TTT — sum of (round_number² for each round lost), clamped to [0, 999]
              Later losses (higher round numbers) contribute more, rewarding players
              who fell later in the event.

    Examples:
        33 pts, OWP 72.6%, OOWP 67.7%                → 33726677
        18 pts, OWP 72.6%, OOWP 67.7%, lost round 7  → 18726677049

    Args:
        points:      Total match points for the player.
        owp_val:     Opponents' win percentage as a float in [0.0, 1.0].
        oowp_val:    Opponents' opponents' win percentage as a float in [0.0, 1.0].
        loss_rounds: Round numbers in which the player lost (any order).
                     When provided, a third 3-digit block is appended.
                     The sum of squares is clamped to 999; for accuracy across
                     very long events (> ~12 rounds with multiple losses) verify
                     the sum does not exceed 999 before calling.

    Returns:
        An integer suitable for direct comparison: higher is better.

    Raises:
        ValueError: ``points`` is negative, or either win-percentage argument is
                    outside [0.0, 1.0], or any loss round number is not positive.
    """
    if points < 0:
        raise ValueError(f"points must be non-negative, got {points}.")
    if not 0.0 <= owp_val <= 1.0:
        raise ValueError(f"owp_val must be within [0.0, 1.0], got {owp_val}.")
    if not 0.0 <= oowp_val <= 1.0:
        raise ValueError(f"oowp_val must be within [0.0, 1.0], got {oowp_val}.")

    points_block = min(points, 99)
    owp_block = min(round(owp_val * 1000), 999)
    oowp_block = min(round(oowp_val * 1000), 999)

    if loss_rounds is None:
        return points_block * 1_000_000 + owp_block * 1_000 + oowp_block

    if any(r < 1 for r in loss_rounds):
        raise ValueError("All loss round numbers must be positive integers.")

    loss_block = min(sum(r * r for r in loss_rounds), 999)
    return points_block * 1_000_000_000 + owp_block * 1_000_000 + oowp_block * 1_000 + loss_block


__all__ = ["win_percentage", "real_opponent_ids", "owp", "oowp", "yugioh_tiebreak_number"]