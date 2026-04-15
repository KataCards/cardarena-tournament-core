from cardarena_tournament_core import Swiss, YuGiOh, Player, MatchupOutcome

# Create 4 players
players = [Player(id=str(i), name=f'P{i}') for i in range(4)]

# Run 2 rounds
tournament = Swiss(players)

# Round 1
r1 = tournament.pair()
for m in r1.matchups:
    m.outcome = MatchupOutcome.PLAYER1_WINS
tournament.submit_results(r1)

# Round 2
r2 = tournament.pair()
for m in r2.matchups:
    m.outcome = MatchupOutcome.PLAYER1_WINS
tournament.submit_results(r2)

# Calculate standings with Yu-Gi-Oh! scoring
scoring = YuGiOh()
standings = scoring.calculate(tournament.rounds)

print('Yu-Gi-Oh! Standings (XXYYYZZZ format):')
print('=' * 70)
for s in standings:
    tiebreak = int(s.tiebreakers['tiebreak_number'])
    points_part = tiebreak // 1000000
    owp_part = (tiebreak % 1000000) // 1000
    oowp_part = tiebreak % 1000
    print(f'{s.rank}. {s.player.name}: {s.points} pts')
    print(f'   Tiebreak: {tiebreak:08d} = {points_part:02d}|{owp_part:03d}|{oowp_part:03d}')
    print(f'   (Points: {s.points}, OWP: {s.tiebreakers["owp"]:.3f}, OOWP: {s.tiebreakers["oowp"]:.3f})')
    print()