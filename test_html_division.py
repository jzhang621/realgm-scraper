from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup

# Test with a player who has both D1 and non-D1 seasons
# Let's try Tristan Smith who was ranked #1 in 2024-25 but played at Concordia (NEB) - not D1
browser = BrowserFetcher()

# Tristan Smith's player ID from the ratings
player_id = "150304"  # Example
url = f"https://basketball.realgm.com/player/Tristan-Smith/Summary/{player_id}"

print(f"Fetching: {url}\n")
html = browser.get(url)

soup = BeautifulSoup(html, 'lxml')

# Find the stats table
print("Looking for stats tables...")
tables = soup.find_all('table')

for i, table in enumerate(tables):
    print(f"\n{'='*70}")
    print(f"TABLE {i+1}")
    print(f"{'='*70}")
    
    # Get headers
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    print(f"Headers: {headers[:10]}")  # First 10 headers
    
    # Get first few rows
    rows = table.find_all('tr')[1:4]  # Skip header, get first 3 data rows
    for j, row in enumerate(rows):
        print(f"\nRow {j+1}:")
        cells = row.find_all('td')
        if len(cells) > 0:
            # Print all cell text
            cell_texts = [cell.get_text(strip=True) for cell in cells[:15]]
            print(f"  Cell values: {cell_texts}")
            
            # Print the raw HTML of the first few cells to see attributes
            print(f"  Raw HTML of first cell: {cells[0]}")
            if len(cells) > 1:
                print(f"  Raw HTML of second cell: {cells[1]}")

browser.close()
