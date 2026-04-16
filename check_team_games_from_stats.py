"""
Check if we can derive team games played from player stats
"""
import pandas as pd

# Load per game stats for 2025-26
stats = pd.read_csv('data/processed/player_stats_pergame.csv')

# Filter for 2025-26 NCAA D1 only
stats_2026 = stats[(stats['season'] == '2025-26') & (stats['level'] == 'NCAA_DI')]

print(f"Total player-season records for 2025-26 NCAA D1: {len(stats_2026)}\n")

# Group by team and find max GP
team_games = stats_2026.groupby('team')['gp'].agg(['max', 'mean', 'count']).reset_index()
team_games.columns = ['team', 'max_gp', 'avg_gp', 'player_count']
team_games = team_games.sort_values('max_gp', ascending=False)

print("Team Games Analysis (Top 15 teams by max GP):")
print("="*70)
print(team_games.head(15).to_string(index=False))

print(f"\n\nOverall Stats:")
print(f"  Teams with data: {len(team_games)}")
print(f"  Avg team max GP: {team_games['max_gp'].mean():.1f}")
print(f"  Min team max GP: {team_games['max_gp'].min()}")
print(f"  Max team max GP: {team_games['max_gp'].max()}")

# Check distribution
print(f"\n\nGP Distribution:")
gp_dist = team_games['max_gp'].value_counts().sort_index(ascending=False)
for gp, count in gp_dist.head(10).items():
    print(f"  {int(gp)} games: {count} teams")

# Sample: Show a specific team's players
print(f"\n\nSample: Players from a team (first team with data)")
sample_team = team_games.iloc[0]['team']
team_players = stats_2026[stats_2026['team'] == sample_team][['player_id', 'team', 'gp', 'pts']]
print(f"\nTeam: {sample_team}")
print(team_players.head(10).to_string(index=False))
