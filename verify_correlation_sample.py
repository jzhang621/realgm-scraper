"""
Verify we can correlate players to team games
"""
import csv

# Load team games lookup
team_games_lookup = {}
with open('data/processed/team_games_2026.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        team_games_lookup[row['team']] = int(row['total_games'])

# Sample some players and show correlation
print("Sample Player -> Team -> Team Games Correlation:")
print("="*70)

with open('data/processed/player_stats_pergame.csv', 'r') as f:
    reader = csv.DictReader(f)
    count = 0
    matched = 0
    unmatched = 0
    
    for row in reader:
        if row['season'] == '2025-26' and row['level'] == 'NCAA_DI' and count < 15:
            team = row['team']
            player_gp = row['gp']
            
            if team in team_games_lookup:
                team_games = team_games_lookup[team]
                pct_played = (int(player_gp) / team_games * 100) if team_games > 0 else 0
                print(f"✓ {row['player_id']:8} | {team:20} | GP: {player_gp:>2} / {team_games:>2} ({pct_played:5.1f}%)")
                matched += 1
            else:
                print(f"✗ {row['player_id']:8} | {team:20} | GP: {player_gp:>2} / ?? (NO MATCH)")
                unmatched += 1
            
            count += 1

print(f"\n{'='*70}")
print(f"Sample results: {matched} matched, {unmatched} unmatched")
