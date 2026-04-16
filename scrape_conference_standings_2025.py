"""
Scrape all NCAA D1 conference standings to get team games played for 2024-25
"""
from fetcher_browser import BrowserFetcher
from bs4 import BeautifulSoup
import csv
import time

# List of all D1 conferences (manually curated from RealGM)
CONFERENCES = [
    (1, "Atlantic-Coast-Conference", "ACC"),
    (2, "Big-Ten-Conference", "Big Ten"),
    (3, "Big-12-Conference", "Big 12"),
    (4, "American-Conference", "American"),
    (5, "Missouri-Valley-Conference", "Missouri Valley"),
    (6, "Mountain-West-Conference", "Mountain West"),
    (8, "Southeastern-Conference", "SEC"),
    (9, "Conference-USA", "C-USA"),
    (10, "Atlantic-10-Conference", "Atlantic 10"),
    (11, "West-Coast-Conference", "WCC"),
    (12, "Horizon-League", "Horizon"),
    (13, "Western-Athletic-Conference", "WAC"),
    (14, "Ivy-League", "Ivy League"),
    (15, "Coastal-Athletic-Association", "CAA"),
    (16, "Ohio-Valley-Conference", "OVC"),
    (17, "Metro-Atlantic-Athletic-Conference", "MAAC"),
    (18, "America-East-Conference", "America East"),
    (19, "Atlantic-Sun-Conference", "ASUN"),
    (20, "Big-Sky-Conference", "Big Sky"),
    (21, "Big-South-Conference", "Big South"),
    (22, "Big-West-Conference", "Big West"),
    (25, "Mid-American-Conference", "MAC"),
    (26, "Mid-Eastern-Athletic-Conference", "MEAC"),
    (27, "Northeast-Conference", "NEC"),
    (28, "Patriot-League", "Patriot"),
    (29, "Southern-Conference", "SoCon"),
    (30, "Southland-Conference", "Southland"),
    (31, "Southwestern-Athletic-Conference", "SWAC"),
    (32, "The-Summit-League", "Summit"),
    (33, "Sun-Belt-Conference", "Sun Belt"),
    (59, "Big-East-Conference", "Big East"),
]

browser = BrowserFetcher()
all_teams = []

for conf_id, conf_slug, conf_name in CONFERENCES:
    # Try with year parameter first
    url = f"https://basketball.realgm.com/ncaa/conferences/{conf_slug}/{conf_id}/standings/2025"
    print(f"Fetching {conf_name} (2024-25)...")
    
    try:
        html = browser.get(url)
        soup = BeautifulSoup(html, 'lxml')
        
        # Find standings table
        tables = soup.find_all('table')
        
        # Look for table with "Overall Wins" header
        standings_table = None
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if 'Overall Wins' in headers:
                standings_table = table
                break
        
        if not standings_table:
            print(f"  ⚠️  No standings table found")
            continue
        
        # Parse rows
        rows = standings_table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 8:
                # Extract data
                team_cell = cells[1]
                team_name = team_cell.get_text(strip=True)
                overall_wins = cells[6].get_text(strip=True)
                overall_losses = cells[7].get_text(strip=True)
                
                try:
                    wins = int(overall_wins)
                    losses = int(overall_losses)
                    total_games = wins + losses
                    
                    all_teams.append({
                        'team': team_name,
                        'conference': conf_name,
                        'wins': wins,
                        'losses': losses,
                        'total_games': total_games
                    })
                    print(f"  ✓ {team_name}: {total_games} games ({wins}-{losses})")
                except ValueError:
                    print(f"  ⚠️  Could not parse: {team_name}")
        
        time.sleep(0.5)  # Be polite
        
    except Exception as e:
        print(f"  ✗ Error: {e}")

browser.close()

# Save to CSV
output_file = 'data/processed/team_games_2025.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['team', 'conference', 'wins', 'losses', 'total_games'])
    writer.writeheader()
    writer.writerows(all_teams)

print(f"\n{'='*60}")
print(f"✓ Saved {len(all_teams)} teams to {output_file}")
print(f"{'='*60}")

# Show summary stats
if all_teams:
    total_games_list = [t['total_games'] for t in all_teams]
    avg_games = sum(total_games_list) / len(total_games_list)
    min_games = min(total_games_list)
    max_games = max(total_games_list)
    
    print(f"\nSummary:")
    print(f"  Total teams: {len(all_teams)}")
    print(f"  Avg games: {avg_games:.1f}")
    print(f"  Min games: {min_games}")
    print(f"  Max games: {max_games}")
