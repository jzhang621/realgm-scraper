from fetcher_browser import BrowserFetcher

browser = BrowserFetcher()

# Save teams list page
print("Fetching teams page...")
html = browser.get("https://basketball.realgm.com/ncaa/teams")
with open("ncaa_teams.html", "w") as f:
    f.write(html)
print(f"Saved ncaa_teams.html ({len(html)} bytes)")

# Save a sample team page
print("\nFetching Duke 2026 team page...")
html = browser.get("https://basketball.realgm.com/ncaa/team/Duke-Blue-Devils/356/Stats/2026")
with open("duke_2026.html", "w") as f:
    f.write(html)
print(f"Saved duke_2026.html ({len(html)} bytes)")

browser.close()
