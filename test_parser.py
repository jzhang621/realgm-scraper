#!/usr/bin/env python3
"""Test parser on a specific HTML file."""

import sys
sys.path.insert(0, '/Users/jimmyzhang/Development/realgm-scraper')

from parsers.profile import parse_player_page

# Read the HTML file
html_path = "/Users/jimmyzhang/Development/realgm-scraper/data/raw/players/befc4c3c3e3cc90ca2456cd5e08e950e.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Parse it
result = parse_player_page(html, "103951")

# Print results
print(f"Profile: {result['profile'].get('full_name', 'N/A')}")
print(f"Per game stats: {len(result['per_game'])} rows")
print(f"Totals stats: {len(result['totals'])} rows")
print(f"Advanced stats: {len(result['advanced'])} rows")
print(f"Misc stats: {len(result['misc'])} rows")
print(f"Awards: {len(result['awards'])} rows")
print(f"Transactions: {len(result['transactions'])} rows")
print(f"Events: {len(result['events'])} rows")

if result['per_game']:
    print("\nFirst per_game row:")
    print(result['per_game'][0])
else:
    print("\nNo per_game stats found - debugging...")

    # Let's check if section_tabs is found
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    section_tabs_div = soup.find("div", class_="section_tabs")
    print(f"Found section_tabs div: {section_tabs_div is not None}")

    if section_tabs_div:
        tab_nav = section_tabs_div.find("ul")
        print(f"Found tab nav: {tab_nav is not None}")

        if tab_nav:
            import re
            panel_to_level = {}
            for li in tab_nav.find_all("li"):
                a = li.find("a")
                if a:
                    href = a.get("href", "")
                    panel_id = href.lstrip("#")
                    label_raw = a.get_text(separator="", strip=True).lower()
                    label_clean = re.sub(r"\s+", "", label_raw)
                    print(f"  Tab: {label_raw} -> cleaned: {label_clean} -> {panel_id}")

                    # Try to map
                    TAB_LABEL_TO_LEVEL = {
                        "ncaacareer": "NCAA_DI",
                        "gleaguecareer": "G_LEAGUE",
                        "nbacareer": "NBA",
                        "internationalcareer": "INTERNATIONAL",
                        "nationalcareer": "NATIONAL",
                        "aaucareer": "AAU",
                        "highschoolcareer": "HIGH_SCHOOL",
                    }
                    level = TAB_LABEL_TO_LEVEL.get(label_clean)
                    print(f"    -> maps to level: {level}")
                    if level and panel_id:
                        panel_to_level[panel_id] = level

            print(f"\nPanel to level mapping: {panel_to_level}")

            # Now check if the panels exist
            for panel_id, level in panel_to_level.items():
                panel_div = soup.find("div", id=panel_id)
                print(f"\nPanel {panel_id} ({level}): found={panel_div is not None}")

                if panel_div:
                    # Find stats_tabs divs
                    stats_tabs_divs = panel_div.find_all("div", class_="stats_tabs", recursive=True)
                    print(f"  Found {len(stats_tabs_divs)} stats_tabs divs")

                    for idx, stats_tabs_div in enumerate(stats_tabs_divs):
                        tab_nav2 = stats_tabs_div.find("ul")
                        if tab_nav2:
                            print(f"  Stats tabs #{idx} nav found:")
                            for li2 in tab_nav2.find_all("li"):
                                a2 = li2.find("a")
                                if a2:
                                    href2 = a2.get("href", "").lstrip("#")
                                    label2 = a2.get_text(strip=True)
                                    print(f"    {label2} -> {href2}")

                                    # Check if this sub-panel exists and has a table
                                    if label2.lower() == "per game":
                                        sub_panel = stats_tabs_div.find("div", id=href2)
                                        if sub_panel:
                                            table = sub_panel.find("table")
                                            if table:
                                                tbody = table.find("tbody")
                                                if tbody:
                                                    rows = tbody.find_all("tr")
                                                    print(f"      -> Found table with {len(rows)} rows in tbody")
                                                else:
                                                    print(f"      -> Table found but NO tbody")
                                            else:
                                                print(f"      -> Sub-panel found but NO table")
                                        else:
                                            print(f"      -> Sub-panel {href2} NOT found")
