"""
Check if we can derive team games played from player stats
"""
import csv
from collections import defaultdict

# Load per game stats for 2025-26
team_max_gp = defaultdict(int)
team_player_count = defaultdict(int)

with open('data/processed/player_stats_pergame.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['season'] == '2025-26' and row['level'] == 'NCAA_DI':
            team = row['team']
            try:
                gp = int(row['gp'])
                team_max_gp[team] = max(team_max_gp[team], gp)
                team_player_count[team] += 1
            except (ValueError, KeyError):
                pass

# Sort teams by max GP
teams_sorted = sorted(team_max_gp.items(), key=lambda x: x[1], reverse=True)

print(f"Total teams with data: {len(teams_sorted)}\n")
print("Team Games Analysis (Top 20 teams by max GP):")
print("="*60)
print(f"{'Team':<20} {'Max GP':>8} {'Players':>8}")
print("-"*60)

for team, max_gp in teams_sorted[:20]:
    print(f"{team:<20} {max_gp:>8} {team_player_count[team]:>8}")

# Overall stats
all_max_gp = [gp for _, gp in teams_sorted]
avg_gp = sum(all_max_gp) / len(all_max_gp)
min_gp = min(all_max_gp)
max_gp = max(all_max_gp)

print(f"\n\nOverall Stats:")
print(f"  Teams with data: {len(teams_sorted)}")
print(f"  Avg team max GP: {avg_gp:.1f}")
print(f"  Min team max GP: {min_gp}")
print(f"  Max team max GP: {max_gp}")

# Check distribution
gp_distribution = defaultdict(int)
for _, gp in teams_sorted:
    gp_distribution[gp] += 1

print(f"\n\nGP Distribution (Top 10):")
for gp in sorted(gp_distribution.keys(), reverse=True)[:10]:
    print(f"  {gp} games: {gp_distribution[gp]} teams")
