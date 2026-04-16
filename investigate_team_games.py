"""
Investigate how to get team games played from RealGM
"""
from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup

# First, check the teams page
print("Fetching NCAA teams page...")
browser = BrowserFetcher()

url = "https://basketball.realgm.com/ncaa/teams"
html = browser.get(url)

print(f"Fetched {len(html)} bytes\n")

soup = BeautifulSoup(html, 'lxml')

# Look for team links
print("Looking for team links...")
team_links = soup.find_all('a', href=lambda x: x and '/ncaa/team/' in x)

print(f"Found {len(team_links)} potential team links\n")

# Show first 10 examples
print("First 10 team links:")
seen = set()
count = 0
for link in team_links:
    href = link.get('href')
    if href and href not in seen:
        seen.add(href)
        team_name = link.get_text(strip=True)
        print(f"  {team_name}: {href}")
        count += 1
        if count >= 10:
            break

# Now let's check a specific team's page to see schedule/stats
print("\n" + "="*60)
print("Checking a sample team page (Duke)...")
print("="*60 + "\n")

# Try Duke's team page for 2025-26 season
duke_url = "https://basketball.realgm.com/ncaa/team/Duke-Blue-Devils/356/Stats/2026"
print(f"Fetching: {duke_url}\n")

duke_html = browser.get(duke_url)
duke_soup = BeautifulSoup(duke_html, 'lxml')

# Look for games played info
print("Looking for games played information...\n")

# Check for schedule/game logs
schedule_link = duke_soup.find('a', href=lambda x: x and 'Schedule' in str(x))
if schedule_link:
    print(f"Found schedule link: {schedule_link.get('href')}")

# Look for stats tables that might show GP
tables = duke_soup.find_all('table')
print(f"\nFound {len(tables)} tables on the page")

for i, table in enumerate(tables[:3]):  # Check first 3 tables
    headers = table.find_all('th')
    if headers:
        header_text = [h.get_text(strip=True) for h in headers[:10]]
        print(f"\nTable {i+1} headers: {header_text}")

browser.close()
