import fetcher_browser as fetcher
from parsers.listing import parse_listing

# Test if maybe page 1 should explicitly be "/1/desc/1"
urls = {
    "current_p1": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1",
    "explicit_p1": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/1/desc/1",
    "page_2": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/2/desc/1",
    "page_3": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/3/desc/1",
    "page_4": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/4/desc/1",
}

all_ids = set()
for name, url in urls.items():
    print(f"\n{name}: {url}")
    try:
        html = fetcher.get(url)
        players = parse_listing(html, 2026)
        ids = set(p["player_id"] for p in players)
        new = len(ids - all_ids)
        all_ids.update(ids)
        print(f"  {len(players)} players, {new} new, total unique: {len(all_ids)}")
        if players:
            print(f"  First player: {players[0]['player_name']} (ID: {players[0]['player_id']})")
    except Exception as e:
        print(f"  Error: {e}")

fetcher.close()
