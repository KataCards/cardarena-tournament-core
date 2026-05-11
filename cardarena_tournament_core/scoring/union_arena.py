"""Union Arena scoring implementation (Bandai official tiebreaker cascade).

Implements the cascade described in the design spec: points, MW%, OMW%,
head-to-head, seeded-random final fallback.
"""
from __future__ import annotations

import random
from typing import List

from cardarena_tournament_core.scoring.base import TCGBaseScoring
from cardarena_tournament_core.common.models import Round, Standing
from cardarena_tournament_core import utils


class UnionArena(TCGBaseScoring):
    WIN_POINTS = 3
    DRAW_POINTS = 1
    LOSS_POINTS = 0
    BYE_POINTS = 3

    def calculate(self, rounds: List[Round], *, seed: int | None = None) -> List[Standing]:
        if not rounds:
            return []

        self._validate_rounds_for_scoring(rounds)

        player_map = self._collect_players(rounds)
        points_by_player = self._calculate_points(rounds)

        # compute MW% and OMW% using Union Arena formulas (floor 1/3)
        player_ids = list(player_map.keys())
        mw_by_player = {
            pid: utils.union_arena_mw_percentage(pid, rounds, min_win_pct=1.0 / 3.0)
            for pid in player_ids
        }
        omw_by_player = {
            pid: utils.union_arena_omw_percentage(pid, rounds, min_win_pct=1.0 / 3.0)
            for pid in player_ids
        }

        standings: List[Standing] = [
            Standing(
                player=player_map[pid],
                points=points_by_player[pid],
                rank=0,
                tiebreakers={"mw_pct": mw_by_player[pid], "omw_pct": omw_by_player[pid]},
            )
            for pid in player_ids
        ]

        # Initial sort: points desc, mw_pct desc, omw_pct desc, player.id asc
        standings.sort(
            key=lambda s: (
                -s.points,
                -s.tiebreakers["mw_pct"],
                -s.tiebreakers["omw_pct"],
                s.player.id,
            )
        )

        # H2H pass: find consecutive groups tied on (points, mw_pct, omw_pct)
        i = 0
        final_order: List[Standing] = []
        rng = random.Random(seed) if seed is not None else None

        while i < len(standings):
            # build group of tied standings
            j = i + 1
            group = [standings[i]]
            while j < len(standings):
                a, b = standings[i], standings[j]
                if (
                    a.points == b.points
                    and a.tiebreakers["mw_pct"] == b.tiebreakers["mw_pct"]
                    and a.tiebreakers["omw_pct"] == b.tiebreakers["omw_pct"]
                ):
                    group.append(standings[j])
                    j += 1
                else:
                    break

            if len(group) == 1:
                final_order.append(group[0])
                i = j
                continue

            # count head-to-head wins within the group
            h2h_wins = {s.player.id: 0 for s in group}
            group_ids = set(h2h_wins.keys())
            for r in rounds:
                for m in r.matchups:
                    if m.player2 is None:
                        continue
                    p1, p2 = m.player1.id, m.player2.id
                    if p1 in group_ids and p2 in group_ids:
                        if m.outcome == m.outcome.PLAYER1_WINS:
                            h2h_wins[p1] += 1
                        elif m.outcome == m.outcome.PLAYER2_WINS:
                            h2h_wins[p2] += 1

            # attach h2h wins to standings for sorting
            for s in group:
                s.tiebreakers["_h2h_wins"] = h2h_wins[s.player.id]

            # sort by h2h wins desc, then keep prior order (player.id) for stability
            group.sort(key=lambda s: (-s.tiebreakers["_h2h_wins"], s.player.id))

            # Seed pass for remaining ties: within any subgroup still tied on h2h
            k = 0
            while k < len(group):
                l = k + 1
                sub = [group[k]]
                while l < len(group):
                    if group[l].tiebreakers["_h2h_wins"] == group[k].tiebreakers["_h2h_wins"]:
                        sub.append(group[l])
                        l += 1
                    else:
                        break

                if len(sub) > 1:
                    if rng is not None:
                        # deterministic shuffle using provided RNG
                        rng.shuffle(sub)
                    # else: keep stable player.id-based order (already sorted by player.id)

                final_order.extend(sub)
                k = l

            # cleanup temporary keys
            for s in group:
                if "_h2h_wins" in s.tiebreakers:
                    del s.tiebreakers["_h2h_wins"]

            i = j

        # assign ranks
        for rank, standing in enumerate(final_order, start=1):
            standing.rank = rank

        return final_order


__all__ = ["UnionArena"]
