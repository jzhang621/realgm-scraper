"""
Verify the 2023-24 season data scraping worked correctly
"""
import os
import sys
from bs4 import BeautifulSoup
from parsers.player import parse_player_html

# Get the 50 player IDs we scraped from the log
player_ids_scraped = [
    104913,  # Chandler-Lawson
    105343,  # Blake-Hinson
    106474,  # Branden-Carlson
    106678,  # DeJuan-Clayton
    106824,  # Aanen-Moody
]

print("="*60)
print("  VERIFYING 2023-24 SEASON DATA")
print("="*60)

for player_id in player_ids_scraped:
    # Find the HTML file for this player
    player_hash = None
    for filename in os.listdir('data/raw/players'):
        if filename.endswith('.html'):
            filepath = os.path.join('data/raw/players', filename)
            with open(filepath, 'r') as f:
                content = f.read()
                if f'/player/{player_id}/' in content:
                    player_hash = filename
                    break

    if not player_hash:
        print(f"\n❌ Player {player_id}: HTML file not found")
        continue

    # Parse the HTML file
    filepath = os.path.join('data/raw/players', player_hash)
    with open(filepath, 'r') as f:
        html = f.read()

    data = parse_player_html(html, player_id)

    print(f"\n{'='*60}")
    print(f"Player {player_id}: {data['player_name']}")
    print(f"{'='*60}")

    # Check for 2023-24 season data
    seasons_found = set()
    if data.get('stats_pergame'):
        for stat in data['stats_pergame']:
            seasons_found.add(stat.get('season'))

    if data.get('stats_totals'):
        for stat in data['stats_totals']:
            seasons_found.add(stat.get('season'))

    print(f"Seasons found: {sorted(seasons_found)}")

    if '2023-24' in seasons_found:
        print(f"✅ 2023-24 data: FOUND")

        # Show 2023-24 per-game stats
        for stat in data.get('stats_pergame', []):
            if stat.get('season') == '2023-24':
                print(f"   Team: {stat.get('team')}")
                print(f"   GP: {stat.get('gp')}, PPG: {stat.get('ppg')}, RPG: {stat.get('rpg')}, APG: {stat.get('apg')}")
                break

        # If player also has 2024-25 data, show it for comparison
        if '2024-25' in seasons_found:
            print(f"\n✅ 2024-25 data: FOUND (for comparison)")
            for stat in data.get('stats_pergame', []):
                if stat.get('season') == '2024-25':
                    print(f"   Team: {stat.get('team')}")
                    print(f"   GP: {stat.get('gp')}, PPG: {stat.get('ppg')}, RPG: {stat.get('rpg')}, APG: {stat.get('apg')}")
                    break
    else:
        print(f"❌ 2023-24 data: NOT FOUND")

print(f"\n{'='*60}")
print("VERIFICATION COMPLETE")
print(f"{'='*60}")
