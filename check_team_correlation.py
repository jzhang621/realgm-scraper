"""
Check if team names in player stats match team names in standings
"""
import csv

# Load teams from standings
standings_teams = set()
with open('data/processed/team_games_2026.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        standings_teams.add(row['team'])

print(f"Teams in standings: {len(standings_teams)}")
print(f"Sample: {sorted(list(standings_teams))[:10]}\n")

# Load teams from player stats (2025-26 only)
player_teams = set()
with open('data/processed/player_stats_pergame.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['season'] == '2025-26' and row['level'] == 'NCAA_DI':
            if row['team']:
                player_teams.add(row['team'])

print(f"Teams in player stats: {len(player_teams)}")
print(f"Sample: {sorted(list(player_teams))[:10]}\n")

# Find matches and mismatches
matched = standings_teams & player_teams
standings_only = standings_teams - player_teams
players_only = player_teams - standings_teams

print(f"{'='*60}")
print(f"CORRELATION ANALYSIS")
print(f"{'='*60}")
print(f"✓ Matched teams: {len(matched)}")
print(f"⚠️  In standings but not player stats: {len(standings_only)}")
print(f"⚠️  In player stats but not standings: {len(players_only)}")

if standings_only:
    print(f"\nTeams in standings but missing from player stats:")
    for team in sorted(standings_only)[:20]:
        print(f"  - {team}")

if players_only:
    print(f"\nTeams in player stats but missing from standings (first 20):")
    for team in sorted(players_only)[:20]:
        print(f"  - {team}")

# Check a sample player to see team name format
print(f"\n{'='*60}")
print(f"SAMPLE PLAYER DATA")
print(f"{'='*60}")
with open('data/processed/player_stats_pergame.csv', 'r') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        if row['season'] == '2025-26' and row['level'] == 'NCAA_DI' and count < 5:
            print(f"Player {row['player_id']}: team='{row['team']}'")
            count += 1
