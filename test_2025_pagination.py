import fetcher_browser as fetcher
from parsers.listing import parse_listing

# Test 2025 pagination to see if it works differently
year = 2025
base = f"https://basketball.realgm.com/ncaa/stats/{year}/Averages/All/All/Season/All/desc/1"

print(f"Testing {year} pagination...")
all_ids = set()

# Pattern 1: Original (desc/1, desc/2, desc/3...)
for page in [1, 2, 3]:
    url = base.replace('/desc/1', f'/desc/{page}')
    html = fetcher.get(url)
    players = parse_listing(html, year)
    ids = set(p["player_id"] for p in players)
    new = len(ids - all_ids)
    all_ids.update(ids)
    print(f"  desc/{page}: {len(players)} players, {new} new, total: {len(all_ids)}")

print(f"\n{year} allows {len(all_ids)} unique players with desc/ pattern")

# Pattern 2: Number before desc (2/desc/1, 3/desc/1...)
for page in [2, 3, 4]:
    url = base.replace('/desc/', f'/{page}/desc/')
    html = fetcher.get(url)
    players = parse_listing(html, year)
    ids = set(p["player_id"] for p in players)
    new = len(ids - all_ids)
    all_ids.update(ids)
    print(f"  {page}/desc/1: {len(players)} players, {new} new, total: {len(all_ids)}")

fetcher.close()
print(f"\nTotal unique for {year}: {len(all_ids)}")
