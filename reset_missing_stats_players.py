"""
Reset checkpoint status for all players who had 'no section_tabs found'
so they can be re-scraped with the fixed parser.
"""
import sqlite3
import csv

# Read the list of players with missing stats
print("Reading players_missing_stats.csv...")
missing_stats_players = []
with open('data/processed/players_missing_stats.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        missing_stats_players.append(row['player_id'])

print(f"Found {len(missing_stats_players)} players to re-scrape")

# Connect to checkpoint DB
conn = sqlite3.connect('data/checkpoint.db')
cursor = conn.cursor()

# Check current status
cursor.execute("""
    SELECT status, COUNT(*)
    FROM fetch_state
    WHERE player_id IN ({})
    GROUP BY status
""".format(','.join('?' * len(missing_stats_players))), missing_stats_players)

print(f"\nCurrent status of these players:")
for status, count in cursor.fetchall():
    print(f"  {status}: {count}")

# Reset them to pending
cursor.execute("""
    UPDATE fetch_state
    SET status = 'pending',
        fetched_at = NULL,
        error = NULL
    WHERE player_id IN ({})
""".format(','.join('?' * len(missing_stats_players))), missing_stats_players)

updated = cursor.rowcount
conn.commit()

# Show new status
cursor.execute("SELECT status, COUNT(*) FROM fetch_state GROUP BY status")
print(f"\nOverall checkpoint status after reset:")
for status, count in cursor.fetchall():
    print(f"  {status}: {count}")

print(f"\n✓ Reset {updated} players to 'pending' status")
print(f"✓ These players will be re-scraped with the fixed parser")

conn.close()
