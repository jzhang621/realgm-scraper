import fetcher_browser as fetcher
from parsers.listing import parse_listing

url = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
season_player_ids = set()

# Page 1
print("Page 1...")
html1 = fetcher.get(url)
players1 = parse_listing(html1, 2026)
ids1 = set(p["player_id"] for p in players1)
season_player_ids.update(ids1)
print(f"  {len(players1)} players, total: {len(season_player_ids)}")

# Page 2 (using new pattern)
page_url = url.replace('/desc/', f'/2/desc/')
print(f"\nPage 2: {page_url}")
html2 = fetcher.get(page_url)
players2 = parse_listing(html2, 2026)
ids2 = set(p["player_id"] for p in players2)
new = len(ids2 - season_player_ids)
season_player_ids.update(ids2)
print(f"  {len(players2)} players, {new} new, total: {len(season_player_ids)}")

# Page 3
page_url = url.replace('/desc/', f'/3/desc/')
print(f"\nPage 3: {page_url}")
html3 = fetcher.get(page_url)
players3 = parse_listing(html3, 2026)
ids3 = set(p["player_id"] for p in players3)
new = len(ids3 - season_player_ids)
season_player_ids.update(ids3)
print(f"  {len(players3)} players, {new} new, total: {len(season_player_ids)}")

fetcher.close()
print(f"\n✓ Pagination working! Got {len(season_player_ids)} unique players across 3 pages")
