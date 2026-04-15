from cardarena_tournament_core.models import MatchupOutcome, Participant, Round, Standing
from cardarena_tournament_core.scoring.base import BaseScoring

_MIN_WIN_PCT = 0.25


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
        player_map = self._build_player_map(rounds)
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

        standings = [
            Standing(
                player=player_map[pid],
                points=points[pid],
                rank=0,
                tiebreakers={
                    "owp": self._owp(pid, rounds),
                    "oowp": self._oowp(pid, rounds),
                    "tiebreak_number": float(
                        self._encode_tiebreak_number(
                            points[pid],
                            self._owp(pid, rounds),
                            self._oowp(pid, rounds),
                        )
                    ),
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

    # ── tiebreaker helpers ────────────────────────────────────────────────────

    def _build_player_map(self, rounds: list[Round]) -> dict[str, Participant]:
        players: dict[str, Participant] = {}
        for round in rounds:
            for m in round.matchups:
                players[m.player1.id] = m.player1
                if m.player2 is not None:
                    players[m.player2.id] = m.player2
        return players

    def _win_pct(self, player_id: str, rounds: list[Round]) -> float:
        wins = draws = total = 0
        for round in rounds:
            for m in round.matchups:
                if m.player2 is None:
                    continue
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
            return _MIN_WIN_PCT
        return max((wins + 0.5 * draws) / total, _MIN_WIN_PCT)

    def _opponent_ids(self, player_id: str, rounds: list[Round]) -> list[str]:
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

    def _owp(self, player_id: str, rounds: list[Round]) -> float:
        opp_ids = self._opponent_ids(player_id, rounds)
        if not opp_ids:
            return 0.0
        return sum(self._win_pct(opp, rounds) for opp in opp_ids) / len(opp_ids)

    def _oowp(self, player_id: str, rounds: list[Round]) -> float:
        opp_ids = self._opponent_ids(player_id, rounds)
        if not opp_ids:
            return 0.0
        return sum(self._owp(opp, rounds) for opp in opp_ids) / len(opp_ids)

    def _encode_tiebreak_number(self, points: int, owp: float, oowp: float) -> int:
        """Encode as XXYYYZZZ: XX=points, YYY=OWP*1000, ZZZ=OOWP*1000."""
        points_part = max(0, min(99, points))
        owp_scaled = max(0, min(999, int(round(owp * 1000))))
        oowp_scaled = max(0, min(999, int(round(oowp * 1000))))
        return points_part * 1000000 + owp_scaled * 1000 + oowp_scaled
