import fetcher_browser as fetcher
from bs4 import BeautifulSoup

url = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
html = fetcher.get(url)
soup = BeautifulSoup(html, "lxml")

# Check pagination info
pag = soup.find("ul", class_=lambda x: x and "pagination" in x.lower())
if pag:
    # Look for page count indicators
    items = pag.find_all("a")
    page_nums = []
    for item in items:
        text = item.get_text(strip=True)
        if text.isdigit():
            page_nums.append(int(text))
    print(f"Pagination pages found in HTML: {sorted(page_nums)}")
    print(f"Max page number: {max(page_nums) if page_nums else 'none'}")

# Check if there's a total count
table = soup.find("table")
if table:
    # Look for row count or total players indicator
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
        print(f"Table has {len(rows)} rows visible")

# Check for any JavaScript that might show total count
scripts = soup.find_all("script")
for script in scripts:
    if script.string and "player" in script.string.lower() and ("total" in script.string.lower() or "count" in script.string.lower()):
        # Extract relevant snippet
        lines = [l.strip() for l in script.string.split('\n') if 'total' in l.lower() or 'count' in l.lower()]
        if lines:
            print(f"\nRelevant script content:")
            for line in lines[:5]:
                print(f"  {line[:100]}")

fetcher.close()
