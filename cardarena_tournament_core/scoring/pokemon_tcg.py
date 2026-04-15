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


class PokemonTCG(BaseScoring):
    """Pokémon TCG scoring: Win=3pts, Draw=1pt, Loss=0pts, Bye=3pts.
    Tiebreakers: OWP then OOWP. Byes excluded from tiebreaker calculations."""

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

        standings = [
            Standing(
                player=player_map[pid],
                points=points[pid],
                rank=0,
                tiebreakers={"owp": owp_map[pid], "oowp": oowp_map[pid]},
            )
            for pid in player_map
        ]
        standings.sort(
            key=lambda s: (s.points, s.tiebreakers["owp"], s.tiebreakers["oowp"]),
            reverse=True,
        )
        for rank, s in enumerate(standings, start=1):
            s.rank = rank

        return standings
