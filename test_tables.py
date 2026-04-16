#!/usr/bin/env python3
"""Test which table BeautifulSoup finds."""

from bs4 import BeautifulSoup

html_path = "/Users/jimmyzhang/Development/realgm-scraper/data/raw/players/befc4c3c3e3cc90ca2456cd5e08e950e.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

# Find the per game sub-panel
per_game_panel = soup.find("div", id="tabs_nba_reg-2")
if per_game_panel:
    all_tables = per_game_panel.find_all("table")
    print(f"Total tables found: {len(all_tables)}")

    for i, table in enumerate(all_tables):
        tbody = table.find("tbody")
        thead = table.find("thead")
        direct_rows = table.find_all("tr", recursive=False)
        all_rows = table.find_all("tr")

        print(f"\nTable {i}:")
        print(f"  Has thead: {thead is not None}")
        print(f"  Has tbody: {tbody is not None}")
        print(f"  Direct tr children: {len(direct_rows)}")
        print(f"  All tr descendants: {len(all_rows)}")

        if tbody:
            tbody_rows = tbody.find_all("tr")
            print(f"  tbody has {len(tbody_rows)} rows")
            if tbody_rows:
                first_cell = tbody_rows[0].find("td")
                if first_cell:
                    print(f"  First cell text: {first_cell.get_text(strip=True)}")
