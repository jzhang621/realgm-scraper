"""
Test fetching and parsing A.B. Coulibaly's page
"""
from fetcher_browser import BrowserFetcher
from parsers.profile import parse_player_page

url = "https://basketball.realgm.com/player/AB-Coulibaly/Summary/250731"
print(f"Fetching: {url}\n")

browser = BrowserFetcher()
html = browser.get(url)
browser.close()

print(f"Fetched {len(html)} bytes")

# Parse the page
print(f"\nParsing player 250731 (A.B. Coulibaly)...")
print("=" * 60)

result = parse_player_page(html, "250731")

print(f"\nProfile data:")
print(f"  Name: {result['profile'].get('full_name')}")
print(f"  Position: {result['profile'].get('position')}")
print(f"  Height: {result['profile'].get('height_ft')}")
print(f"  Weight: {result['profile'].get('weight_lbs')} lbs")

print(f"\nStats counts:")
print(f"  Per Game rows: {len(result['per_game'])}")
print(f"  Totals rows: {len(result['totals'])}")
print(f"  Advanced rows: {len(result['advanced'])}")
print(f"  Misc rows: {len(result['misc'])}")
print(f"  Awards: {len(result['awards'])}")
print(f"  Transactions: {len(result['transactions'])}")

if result['per_game']:
    print(f"\n✓ Per Game stats (all rows):")
    for row in result['per_game']:
        print(f"  {row.get('season')}: {row.get('team')} ({row.get('level')}) - " +
              f"{row.get('gp')}GP, {row.get('pts')}PPG, " +
              f"{row.get('trb')}RPG, {row.get('ast')}APG")
else:
    print("\n✗ NO PER GAME STATS FOUND!")

if result['totals']:
    print(f"\n✓ Totals stats (all rows):")
    for row in result['totals']:
        print(f"  {row.get('season')}: {row.get('team')} ({row.get('level')}) - " +
              f"{row.get('gp')}GP, {row.get('pts')}PTS total")
else:
    print("\n✗ NO TOTALS STATS FOUND!")

if result['awards']:
    print(f"\nAwards:")
    for award in result['awards']:
        print(f"  {award.get('award_name')} ({award.get('award_date')})")
