"""Demo: Team tournament using the Team class."""

from cardarena_tournament_core import (
    MatchupOutcome,
    PokemonTCG,
    Swiss,
    Team,
)

# Create teams
team1 = Team(id="t1", name="Dragon Slayers", members=["Alice", "Bob"])
team2 = Team(id="t2", name="Phoenix Rising", members=["Carol", "Dave"])
team3 = Team(id="t3", name="Thunder Wolves", members=["Eve", "Frank"])
team4 = Team(id="t4", name="Shadow Knights", members=["Grace", "Henry"])

# Run Swiss tournament with teams
tournament = Swiss([team1, team2, team3, team4])  # type: ignore

# Round 1
r1 = tournament.pair()
print("Round 1 Matchups:")
for m in r1.matchups:
    p1_name = m.participant1.name if m.participant1 else "BYE"
    p2_name = m.participant2.name if m.participant2 else "BYE"
    print(f"  {p1_name} vs {p2_name}")

# Set results
r1.matchups[0].outcome = MatchupOutcome.PLAYER1_WINS
r1.matchups[1].outcome = MatchupOutcome.PLAYER2_WINS
tournament.submit_results(r1)

# Round 2
r2 = tournament.pair()
print("\nRound 2 Matchups:")
for m in r2.matchups:
    p1_name = m.participant1.name if m.participant1 else "BYE"
    p2_name = m.participant2.name if m.participant2 else "BYE"
    print(f"  {p1_name} vs {p2_name}")

r2.matchups[0].outcome = MatchupOutcome.PLAYER1_WINS
r2.matchups[1].outcome = MatchupOutcome.DRAW
tournament.submit_results(r2)

# Calculate standings
scoring = PokemonTCG()
standings = scoring.calculate(tournament.rounds)

print("\nFinal Team Standings:")
print("=" * 60)
for s in standings:
    team_info = ""
    if isinstance(s.participant, Team):
        team_info = f" (Members: {', '.join(s.participant.members)})"
    print(f"{s.rank}. {s.participant.name}{team_info}")
    print(f"   Points: {s.points}, OWP: {s.tiebreakers.get('owp', 0):.3f}")