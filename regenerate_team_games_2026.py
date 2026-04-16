"""
Regenerate team_games_2026.csv from actual player data in the database.
This ensures all teams with players get included.
"""
import csv
import psycopg2

# Connect to database
conn = psycopg2.connect("postgresql://localhost:5432/ncaa_basketball")
cur = conn.cursor()

# Get teams and their game counts from the teams table
print("Fetching teams from teams table...")
cur.execute("""
    SELECT team_name, conference, wins, losses, total_games
    FROM teams
    WHERE season = '2025-26'
    ORDER BY team_name
""")
teams_from_table = {row[0]: {
    'team': row[0],
    'conference': row[1],
    'wins': row[2],
    'losses': row[3],
    'total_games': row[4]
} for row in cur.fetchall()}

print(f"Found {len(teams_from_table)} teams in teams table")

# Get ALL teams that have players in the stats
print("\nFinding teams with players in stats...")
cur.execute("""
    SELECT DISTINCT team
    FROM player_stats_pergame
    WHERE season = '2025-26'
    ORDER BY team
""")
teams_with_players = [row[0] for row in cur.fetchall()]

print(f"Found {len(teams_with_players)} teams with players")

# For teams not in the teams table, estimate games from player GP
missing_teams = []
for team in teams_with_players:
    if team not in teams_from_table:
        # Get max GP for this team as an estimate of total games
        cur.execute("""
            SELECT MAX(gp::integer) as max_gp, COUNT(*) as player_count
            FROM player_stats_pergame
            WHERE season = '2025-26' AND team = %s AND gp IS NOT NULL
        """, (team,))
        result = cur.fetchone()
        max_gp = result[0] if result[0] else 32
        player_count = result[1]
        
        missing_teams.append({
            'team': team,
            'conference': 'Unknown',  # We don't have conference data
            'wins': 0,  # Unknown
            'losses': 0,  # Unknown
            'total_games': max_gp  # Use max GP as estimate
        })
        print(f"  Added missing team: {team} ({player_count} players, ~{max_gp} games)")

# Combine all teams
all_teams = list(teams_from_table.values()) + missing_teams

# Save to CSV
output_file = 'data/processed/team_games_2026.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['team', 'conference', 'wins', 'losses', 'total_games'])
    writer.writeheader()
    writer.writerows(all_teams)

print(f"\n{'='*60}")
print(f"✓ Saved {len(all_teams)} teams to {output_file}")
print(f"  - {len(teams_from_table)} from teams table")
print(f"  - {len(missing_teams)} added from player stats")
print(f"{'='*60}")

cur.close()
conn.close()
