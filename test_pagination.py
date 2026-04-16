import fetcher_browser as fetcher
from parsers.listing import parse_listing

url1 = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
url2 = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/2"

print("Fetching page 1...")
html1 = fetcher.get(url1)
players1 = parse_listing(html1, 2026)
ids1 = set(p["player_id"] for p in players1)
print(f"Page 1: {len(players1)} players")
print(f"First 5 IDs: {list(ids1)[:5]}")

print("\nFetching page 2...")
html2 = fetcher.get(url2)
players2 = parse_listing(html2, 2026)
ids2 = set(p["player_id"] for p in players2)
print(f"Page 2: {len(players2)} players")
print(f"First 5 IDs: {list(ids2)[:5]}")

overlap = len(ids1 & ids2)
print(f"\nOverlap: {overlap} players")
print(f"New on page 2: {len(ids2 - ids1)} players")

fetcher.close()
