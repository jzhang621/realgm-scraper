import fetcher_browser as fetcher
from parsers.listing import check_pagination
from bs4 import BeautifulSoup

url = "https://basketball.realgm.com/ncaa/stats/2026/Averages/All/All/Season/All/desc/1"
print(f"Fetching {url}")
html = fetcher.get(url)

# Check for pagination div
soup = BeautifulSoup(html, "lxml")
pagination_elems = soup.find_all("ul", class_=lambda x: x and "pagination" in x.lower())
print(f"\nFound {len(pagination_elems)} pagination elements")

for i, pag in enumerate(pagination_elems):
    print(f"\nPagination {i+1}:")
    links = pag.find_all("a", href=True)[:10]  # First 10 links
    for link in links:
        print(f"  {link.get_text(strip=True)}: {link['href']}")

# Try the check_pagination function
extra = check_pagination(html)
print(f"\ncheck_pagination found: {extra[:5]}")

fetcher.close()
