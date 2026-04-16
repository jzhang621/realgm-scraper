import psycopg2
import csv

# Connect to database
conn = psycopg2.connect("postgresql://localhost:5432/ncaa_basketball")
cur = conn.cursor()

# Get all teams with players in 2025-26
cur.execute("""
    SELECT DISTINCT team
    FROM player_stats_pergame
    WHERE season = '2025-26'
    ORDER BY team
""")
teams_with_players = {row[0] for row in cur.fetchall()}

# Load team_games_2026.csv
teams_in_csv = set()
try:
    with open('data/processed/team_games_2026.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            teams_in_csv.add(row['team'])
except FileNotFoundError:
    print("team_games_2026.csv not found in data/processed/")
    teams_in_csv = set()

# Find missing teams
missing_teams = teams_with_players - teams_in_csv

print(f"Total teams with players: {len(teams_with_players)}")
print(f"Teams in CSV: {len(teams_in_csv)}")
print(f"Missing teams: {len(missing_teams)}\n")

if missing_teams:
    print("Teams with players but NOT in team_games_2026.csv:")
    print("=" * 60)
    
    # Get player count for each missing team
    missing_with_counts = []
    for team in sorted(missing_teams):
        cur.execute("""
            SELECT COUNT(DISTINCT player_id)
            FROM player_stats_pergame
            WHERE season = '2025-26' AND team = %s
        """, (team,))
        player_count = cur.fetchone()[0]
        missing_with_counts.append((team, player_count))
    
    # Sort by player count
    missing_with_counts.sort(key=lambda x: x[1], reverse=True)
    
    # Show NCAA teams first (likely just have more players)
    print("\nMissing teams (sorted by player count):")
    for team, count in missing_with_counts[:50]:
        print(f"  {team:<40} ({count} players)")
    
    if len(missing_with_counts) > 50:
        print(f"\n  ... and {len(missing_with_counts) - 50} more teams")

cur.close()
conn.close()
