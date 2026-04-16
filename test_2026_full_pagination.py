import sys
import logging
from fetcher_browser import BrowserFetcher
from parsers.listing import parse_listing

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

url = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
print(f"Testing pagination for 2026...")
print(f"URL: {url}\n")

# Create browser fetcher
browser = BrowserFetcher()

# Get all pages
html_pages = browser.get_paginated_listing(url, max_pages=60)

print(f"\nFetched {len(html_pages)} HTML pages")

# Parse all pages
all_players = []
all_ids = set()

for page_idx, html in enumerate(html_pages, 1):
    players = parse_listing(html, 2026)
    new_count = 0
    for p in players:
        if p["player_id"] not in all_ids:
            all_ids.add(p["player_id"])
            all_players.append(p)
            new_count += 1
    print(f"Page {page_idx}: {len(players)} parsed, {new_count} new, total unique: {len(all_ids)}")

print(f"\n✓ Total unique players for 2026: {len(all_ids)}")
print(f"Expected: ~5200")

# Check for Darryn Peterson
darryn = [p for p in all_players if "peterson" in p["player_name"].lower() and "darryn" in p["player_name"].lower()]
if darryn:
    print(f"\n✓ Found Darryn Peterson: {darryn[0]}")
else:
    print(f"\n✗ Darryn Peterson NOT found")

browser.close()
