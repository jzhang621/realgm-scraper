import fetcher_browser as fetcher
from parsers.listing import parse_listing

# Test if the number after /desc/ is the page number
urls = {
    "desc_1": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1",
    "desc_2": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/2",
    "desc_3": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/3",
    "1_desc_1": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/1/desc/1",
    "1_desc_2": "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/1/desc/2",
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
            print(f"  First: {players[0]['player_name']}")
    except Exception as e:
        print(f"  Error: {e}")

fetcher.close()
