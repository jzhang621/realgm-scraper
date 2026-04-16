"""
Get list of all NCAA D1 conferences from RealGM
"""
from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup
import re

browser = BrowserFetcher()

# Start from a known conference page to find navigation
url = "https://basketball.realgm.com/ncaa/conferences"
print(f"Fetching: {url}\n")

html = browser.get(url)
soup = BeautifulSoup(html, 'lxml')

# Look for conference links
print("Searching for conference links...")

# Find links with /ncaa/conferences/ pattern
conference_links = []
for link in soup.find_all('a', href=True):
    href = link['href']
    # Match pattern: /ncaa/conferences/{name}/{id}/
    if '/ncaa/conferences/' in href and href.count('/') >= 4:
        # Extract conference name and ID
        match = re.search(r'/ncaa/conferences/([^/]+)/(\d+)', href)
        if match:
            conf_name = match.group(1)
            conf_id = match.group(2)
            conf_text = link.get_text(strip=True)
            
            # Avoid duplicates
            key = (conf_name, conf_id)
            if key not in [c[:2] for c in conference_links]:
                conference_links.append((conf_name, conf_id, conf_text))

print(f"\nFound {len(conference_links)} conferences:\n")
for name, id, text in sorted(conference_links):
    print(f"  {text:40} (ID: {id:3}, slug: {name})")

browser.close()

# Save to file
with open('conferences.txt', 'w') as f:
    for name, id, text in sorted(conference_links):
        f.write(f"{id},{name},{text}\n")
print(f"\n✓ Saved to conferences.txt")
