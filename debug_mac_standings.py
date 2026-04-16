"""Debug MAC conference standings scraping"""
from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup

browser = BrowserFetcher()
url = "https://basketball.realgm.com/ncaa/conferences/Mid-American-Conference/25/standings"

print(f"Fetching MAC standings...")
html = browser.get(url)
soup = BeautifulSoup(html, 'lxml')

# Find all tables
tables = soup.find_all('table')
print(f"\nFound {len(tables)} tables on page\n")

# Inspect each table
for idx, table in enumerate(tables, 1):
    print(f"Table {idx}:")
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    print(f"  Headers: {headers[:10]}")  # Show first 10 headers
    
    rows = table.find_all('tr')[1:]  # Skip header
    print(f"  Data rows: {len(rows)}")
    
    # Show first few team names
    for row in rows[:5]:
        cells = row.find_all('td')
        if len(cells) >= 2:
            team_name = cells[1].get_text(strip=True)
            print(f"    - {team_name}")
    
    print()

browser.close()
