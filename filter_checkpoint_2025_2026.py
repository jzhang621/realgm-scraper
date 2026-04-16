"""
Filter checkpoint to only include players from 2025/2026 seasons.
Removes all other players from the pending queue.
"""
import sqlite3
import csv

# Read all player IDs from 2025/2026 season rosters
print("Reading 2025/2026 season rosters...")
players_2025_2026 = set()
with open('data/processed/season_rosters.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['season'] in ['2025', '2026']:
            players_2025_2026.add(row['player_id'])

print(f"Found {len(players_2025_2026)} unique players in 2025/2026 seasons")

# Connect to checkpoint DB
conn = sqlite3.connect('data/checkpoint.db')
cursor = conn.cursor()

# Get current counts
cursor.execute("SELECT status, COUNT(*) FROM fetch_state GROUP BY status")
before_counts = dict(cursor.fetchall())
print(f"\nBefore filtering:")
for status, count in before_counts.items():
    print(f"  {status}: {count}")

# Delete players NOT in 2025/2026
cursor.execute("""
    DELETE FROM fetch_state 
    WHERE player_id NOT IN ({})
""".format(','.join('?' * len(players_2025_2026))), list(players_2025_2026))

deleted = cursor.rowcount
conn.commit()

# Get new counts
cursor.execute("SELECT status, COUNT(*) FROM fetch_state GROUP BY status")
after_counts = dict(cursor.fetchall())
print(f"\nAfter filtering:")
for status, count in after_counts.items():
    print(f"  {status}: {count}")

print(f"\n✓ Removed {deleted} players not in 2025/2026")
print(f"✓ Checkpoint now contains ONLY 2025/2026 players")

conn.close()
