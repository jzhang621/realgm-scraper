from playwright.sync_api import sync_playwright
from parsers.listing import parse_listing
import time

def test_js_pagination():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        all_ids = set()
        
        # Get page 1
        html = page.content()
        players = parse_listing(html, 2026)
        ids = set(p["player_id"] for p in players)
        all_ids.update(ids)
        print(f"Page 1: {len(players)} players, total: {len(all_ids)}")
        
        # Try to click page 2
        try:
            # Look for pagination element with text "2"
            page.click("ul.pagination a:has-text('2')", timeout=5000)
            time.sleep(2)  # Wait for content to load
            
            html2 = page.content()
            players2 = parse_listing(html2, 2026)
            ids2 = set(p["player_id"] for p in players2)
            new = len(ids2 - all_ids)
            all_ids.update(ids2)
            print(f"Page 2 (after click): {len(players2)} players, {new} new, total: {len(all_ids)}")
        except Exception as e:
            print(f"Could not click page 2: {e}")
        
        browser.close()
        
test_js_pagination()
