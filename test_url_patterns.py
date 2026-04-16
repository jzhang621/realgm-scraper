import fetcher_browser as fetcher
from parsers.listing import parse_listing

# Try different URL patterns for page 2
patterns = [
    "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1/2",
    "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/2/1",
    "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/2/desc/1",
    "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc?page=2",
]

base_url = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
print("Fetching base page...")
html_base = fetcher.get(base_url)
players_base = parse_listing(html_base, 2026)
ids_base = set(p["player_id"] for p in players_base)
print(f"Base URL: {len(players_base)} players, first ID: {list(ids_base)[0] if ids_base else 'none'}")

for pattern in patterns:
    try:
        print(f"\nTrying: {pattern}")
        html = fetcher.get(pattern)
        players = parse_listing(html, 2026)
        ids = set(p["player_id"] for p in players)
        overlap = len(ids & ids_base)
        new = len(ids - ids_base)
        print(f"  {len(players)} players, overlap: {overlap}, new: {new}")
        if new > 0:
            print(f"  ✓ FOUND WORKING PATTERN! First new ID: {list(ids - ids_base)[0]}")
            break
    except Exception as e:
        print(f"  ✗ Error: {e}")

fetcher.close()
