"""Tournament orchestrator — wires a pairing format to a scoring system."""

from cardarena_tournament_core.models import Participant, Round, Standing
from cardarena_tournament_core.pairings.base import BasePairing
from cardarena_tournament_core.scoring.base import BaseScoring


class Tournament:
    """High-level orchestrator that couples a pairing format with a scoring system.

    This is a convenience wrapper around :class:`BasePairing` and
    :class:`BaseScoring`.  All pairing logic and round history live in the
    pairing instance; all standings logic lives in the scoring instance.
    ``Tournament`` itself adds no new behaviour — only a unified call site.

    Args:
        pairing:  Any :class:`BasePairing` subclass, already initialised with
                  the participant list (e.g. ``Swiss(players)``).
        scoring:  Any :class:`BaseScoring` subclass instance
                  (e.g. ``PokemonTCG()``).

    Example::

        from cardarena_tournament_core import (
            Player, MatchupOutcome, Swiss, PokemonTCG, Tournament,
        )

        players = [Player(id=str(i), name=f"Player {i}") for i in range(8)]
        tournament = Tournament(pairing=Swiss(players), scoring=PokemonTCG())

        round1 = tournament.pair()
        for matchup in round1.matchups:
            if matchup.player2:
                matchup.outcome = MatchupOutcome.PLAYER1_WINS
        tournament.submit_results(round1)

        for standing in tournament.standings():
            print(f"{standing.rank}. {standing.player.name} — {standing.points} pts")
    """

    def __init__(self, pairing: BasePairing, scoring: BaseScoring) -> None:
        self._pairing = pairing
        self._scoring = scoring

    # ── pairing delegation ────────────────────────────────────────────────────

    def pair(self) -> Round:
        """Generate and return the next round's matchups.

        Delegates to the underlying pairing format.

        Raises:
            TournamentCompleteError: The pairing format has no more rounds to
                generate (round-robin schedule exhausted, or a champion has
                been determined in single elimination).
        """
        return self._pairing.pair()

    def submit_results(self, completed_round: Round) -> None:
        """Record the outcomes of a completed round.

        Delegates to the underlying pairing format, which updates its internal
        standings, rematch history, and active-participant list as appropriate.
        """
        self._pairing.submit_results(completed_round)

    # ── scoring ───────────────────────────────────────────────────────────────

    def standings(self) -> list[Standing]:
        """Compute and return current standings.

        Calls the scoring system with all rounds submitted so far.  Safe to
        call mid-tournament — returns an up-to-date snapshot after each round.
        Returns an empty list before any rounds have been submitted.
        """
        return self._scoring.calculate(self._pairing.rounds)

    # ── read-only views ───────────────────────────────────────────────────────

    @property
    def participants(self) -> list[Participant]:
        """All participants registered for this tournament (read-only copy)."""
        return self._pairing.participants

    @property
    def rounds(self) -> list[Round]:
        """All submitted rounds in chronological order (read-only copy)."""
        return self._pairing.rounds
