"""
Test fetching A.C. Bryant's page to see the actual HTML structure
"""
import sys
from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup

url = "https://basketball.realgm.com/player/AC-Bryant/Summary/212898"
print(f"Fetching: {url}\n")

browser = BrowserFetcher()
html = browser.get(url)
browser.close()

print(f"Fetched {len(html)} bytes")

# Parse and check for section_tabs
soup = BeautifulSoup(html, "lxml")

# Check for section_tabs div
section_tabs_div = soup.find("div", class_="section_tabs")
print(f"\nFound section_tabs div: {section_tabs_div is not None}")

if section_tabs_div:
    print("✓ section_tabs div EXISTS")
    # Show first 500 chars
    print(f"\nFirst 500 chars of section_tabs:\n{str(section_tabs_div)[:500]}")
else:
    print("✗ section_tabs div NOT FOUND")

    # Search for any div with "tab" in the class name
    print("\nSearching for divs with 'tab' in class name:")
    tab_divs = soup.find_all("div", class_=lambda x: x and "tab" in x.lower())
    for div in tab_divs[:10]:
        print(f"  Found: <div class=\"{div.get('class')}\">")

    # Check if stats tables exist
    print("\nSearching for stats tables:")
    tables = soup.find_all("table", limit=5)
    print(f"  Found {len(tables)} tables on page")

    # Save HTML to file for manual inspection
    with open("ac_bryant_debug.html", "w") as f:
        f.write(html)
    print(f"\n✓ Saved full HTML to: ac_bryant_debug.html")
