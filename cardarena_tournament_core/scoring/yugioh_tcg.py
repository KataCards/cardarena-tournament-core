from cardarena_tournament_core.models import MatchupOutcome, Participant, Round, Standing
from cardarena_tournament_core.scoring.base import BaseScoring
from cardarena_tournament_core.scoring.tiebreakers import calculate_oowp, calculate_owp


def _player_map(rounds: list[Round]) -> dict[str, Participant]:
    players: dict[str, Participant] = {}
    for round in rounds:
        for m in round.matchups:
            players[m.player1.id] = m.player1
            if m.player2 is not None:
                players[m.player2.id] = m.player2
    return players


def _encode_tiebreak_number(points: int, owp: float, oowp: float) -> int:
    """Encode points, OWP and OOWP into an 8-digit Yu-Gi-Oh! style tiebreak number.

    Format: XXYYYZZZ where:
    - XX = Total points (e.g., 33 points → 33)
    - YYY = OWP scaled to 0-999 (e.g., 0.726 → 726)
    - ZZZ = OOWP scaled to 0-999 (e.g., 0.677 → 677)

    Example: 33 points, OWP=0.726, OOWP=0.677 → 33726677
    """
    points_part = max(0, min(99, points))
    owp_scaled = max(0, min(999, int(round(owp * 1000))))
    oowp_scaled = max(0, min(999, int(round(oowp * 1000))))
    return points_part * 1000000 + owp_scaled * 1000 + oowp_scaled


class YuGiOh(BaseScoring):
    """Yu-Gi-Oh! TCG scoring: Win=3pts, Draw=1pt, Loss=0pts, Bye=3pts.

    Tiebreakers encoded as 8-digit number: XXYYYZZZ
    - XX = Total points (0-99)
    - YYY = Opponent Win Percentage (OWP) scaled to 0-999
    - ZZZ = Opponent's Opponent Win Percentage (OOWP) scaled to 0-999

    Example: Player with 33 points, OWP=72.6%, OOWP=67.7% gets tiebreak number 33726677
    """

    WIN_POINTS = 3
    DRAW_POINTS = 1
    LOSS_POINTS = 0
    BYE_POINTS = 3

    def calculate(self, rounds: list[Round]) -> list[Standing]:
        player_map = _player_map(rounds)
        points: dict[str, int] = {pid: 0 for pid in player_map}

        for round in rounds:
            for m in round.matchups:
                if m.player2 is None:
                    points[m.player1.id] += self.BYE_POINTS
                elif m.outcome == MatchupOutcome.PLAYER1_WINS:
                    points[m.player1.id] += self.WIN_POINTS
                elif m.outcome == MatchupOutcome.PLAYER2_WINS:
                    points[m.player2.id] += self.WIN_POINTS
                elif m.outcome == MatchupOutcome.DRAW:
                    points[m.player1.id] += self.DRAW_POINTS
                    points[m.player2.id] += self.DRAW_POINTS

        owp_map = {pid: calculate_owp(pid, rounds) for pid in player_map}
        oowp_map = {pid: calculate_oowp(pid, rounds) for pid in player_map}
        tiebreak_map = {
            pid: _encode_tiebreak_number(points[pid], owp_map[pid], oowp_map[pid])
            for pid in player_map
        }

        standings = [
            Standing(
                player=player_map[pid],
                points=points[pid],
                rank=0,
                tiebreakers={
                    "owp": owp_map[pid],
                    "oowp": oowp_map[pid],
                    "tiebreak_number": float(tiebreak_map[pid]),
                },
            )
            for pid in player_map
        ]
        standings.sort(
            key=lambda s: (s.points, s.tiebreakers["tiebreak_number"]),
            reverse=True,
        )
        for rank, s in enumerate(standings, start=1):
            s.rank = rank

        return standings
