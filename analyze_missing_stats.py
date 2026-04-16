"""
Analyze players in 2025/2026 rosters who have no stats data.
"""
import csv

# Read all players with "no section_tabs" warning from logs
print("Reading log files for 'no section_tabs' warnings...")
no_stats_players = set()

import re
log_files = ['scraper.log', 'scraper_2025_2026.log']
pattern = re.compile(r'Player (\d+):.*no section_tabs found')

for log_file in log_files:
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    no_stats_players.add(match.group(1))
    except FileNotFoundError:
        print(f"  {log_file} not found, skipping")

print(f"Found {len(no_stats_players)} players with 'no section_tabs' warning")

# Read season rosters for 2025/2026
print("\nReading 2025/2026 season rosters...")
roster_players = {}
with open('data/processed/season_rosters.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['season'] in ['2025', '2026']:
            player_id = row['player_id']
            if player_id not in roster_players:
                roster_players[player_id] = {
                    'player_name': row['player_name'],
                    'seasons': []
                }
            if row['season'] not in roster_players[player_id]['seasons']:
                roster_players[player_id]['seasons'].append(row['season'])

print(f"Found {len(roster_players)} unique players in 2025/2026 rosters")

# Find intersection - players in rosters who have no stats
missing_stats_players = []
for player_id in roster_players:
    if player_id in no_stats_players:
        missing_stats_players.append({
            'player_id': player_id,
            'player_name': roster_players[player_id]['player_name'],
            'seasons': ','.join(sorted(roster_players[player_id]['seasons']))
        })

print(f"\n{len(missing_stats_players)} players in 2025/2026 rosters have NO STATS")
print(f"That's {100 * len(missing_stats_players) / len(roster_players):.1f}% of all 2025/2026 roster players")

# Save to CSV
output_file = 'data/processed/players_missing_stats.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['player_id', 'player_name', 'seasons'])
    writer.writeheader()
    writer.writerows(sorted(missing_stats_players, key=lambda x: x['player_name']))

print(f"\nSaved report to: {output_file}")

# Show sample
print("\nSample of players with no stats:")
for player in sorted(missing_stats_players, key=lambda x: x['player_name'])[:20]:
    print(f"  {player['player_name']} (ID: {player['player_id']}, Seasons: {player['seasons']})")
