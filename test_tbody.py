#!/usr/bin/env python3
"""Test BeautifulSoup tbody parsing."""

from bs4 import BeautifulSoup

# Read the HTML file
html_path = "/Users/jimmyzhang/Development/realgm-scraper/data/raw/players/befc4c3c3e3cc90ca2456cd5e08e950e.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

print("Testing with lxml parser:")
soup = BeautifulSoup(html, "lxml")

# Find the NBA panel
panel = soup.find("div", id="tabs_profile-1")
print(f"Found NBA panel: {panel is not None}")

if panel:
    # Find first stats_tabs div
    stats_tabs_div = panel.find("div", class_="stats_tabs")
    print(f"Found stats_tabs div: {stats_tabs_div is not None}")

    if stats_tabs_div:
        # Find the Per Game sub-panel
        per_game_panel = stats_tabs_div.find("div", id="tabs_nba_reg-2")
        print(f"Found per_game panel (tabs_nba_reg-2): {per_game_panel is not None}")

        if per_game_panel:
            # Find the table
            table = per_game_panel.find("table")
            print(f"Found table: {table is not None}")

            if table:
                # Find tbody
                tbody = table.find("tbody")
                print(f"Found tbody: {tbody is not None}")

                if tbody:
                    rows = tbody.find_all("tr")
                    print(f"Found {len(rows)} rows in tbody")
                    if rows:
                        print(f"First row text: {rows[0].get_text(strip=True)[:100]}")
                else:
                    print("\nDEBUG: tbody not found. Let's check table structure...")
                    print(f"Table name: {table.name}")
                    print(f"Table children (first 5):")
                    for i, child in enumerate(table.children):
                        if i >= 5:
                            break
                        if hasattr(child, 'name'):
                            print(f"  {i}: {child.name}")
                        else:
                            print(f"  {i}: NavigableString")

                    # Try finding rows directly in table
                    direct_rows = table.find_all("tr")
                    print(f"\nDirect tr search found: {len(direct_rows)} rows")

print("\n" + "="*60)
print("Testing with html.parser:")
print("="*60 + "\n")

soup2 = BeautifulSoup(html, "html.parser")
panel2 = soup2.find("div", id="tabs_profile-1")
print(f"Found NBA panel: {panel2 is not None}")

if panel2:
    stats_tabs_div2 = panel2.find("div", class_="stats_tabs")
    print(f"Found stats_tabs div: {stats_tabs_div2 is not None}")

    if stats_tabs_div2:
        per_game_panel2 = stats_tabs_div2.find("div", id="tabs_nba_reg-2")
        print(f"Found per_game panel (tabs_nba_reg-2): {per_game_panel2 is not None}")

        if per_game_panel2:
            table2 = per_game_panel2.find("table")
            print(f"Found table: {table2 is not None}")

            if table2:
                tbody2 = table2.find("tbody")
                print(f"Found tbody: {tbody2 is not None}")

                if tbody2:
                    rows2 = tbody2.find_all("tr")
                    print(f"Found {len(rows2)} rows in tbody")
                    if rows2:
                        print(f"First row: {rows2[0].get_text()[:100]}")
