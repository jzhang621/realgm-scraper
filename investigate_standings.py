"""
Investigate RealGM conference standings to get team games played
"""
from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup

browser = BrowserFetcher()

# Fetch WAC standings as example
url = "https://basketball.realgm.com/ncaa/conferences/Western-Athletic-Conference/13/standings"
print(f"Fetching: {url}\n")

html = browser.get(url)
print(f"Fetched {len(html)} bytes\n")

# Save for inspection
with open("wac_standings.html", "w") as f:
    f.write(html)
print("Saved wac_standings.html")

soup = BeautifulSoup(html, 'lxml')

# Look for standings table
print("\n" + "="*60)
print("Looking for standings table...")
print("="*60 + "\n")

# Find all tables
tables = soup.find_all('table')
print(f"Found {len(tables)} tables\n")

for i, table in enumerate(tables):
    print(f"\nTable {i+1}:")
    # Get headers
    headers = table.find_all('th')
    if headers:
        header_texts = [h.get_text(strip=True) for h in headers]
        print(f"  Headers: {header_texts}")
    
    # Get first few rows
    rows = table.find_all('tr')[:5]
    print(f"  Total rows: {len(table.find_all('tr'))}")
    if len(rows) > 1:
        print(f"  Sample row 1:")
        cells = rows[1].find_all(['td', 'th'])
        cell_texts = [c.get_text(strip=True) for c in cells]
        print(f"    {cell_texts}")

browser.close()
