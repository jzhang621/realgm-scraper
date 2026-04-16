"""
parsers/listing.py — Parse season player listing pages.

Two URL patterns:
  Stats listing  (used for seeding — all players in a season):
    https://basketball.realgm.com/ncaa/stats/{year}/Averages/All/All/Season/All/desc/1

  Bio listing  (international/profile players — smaller set, richer metadata):
    https://basketball.realgm.com/ncaa/players/{year}

Both return the same player dict shape:
  player_id, player_name, url_slug, team, conference, position, class_year, season
"""

import re
import logging
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Extracts url_slug and player_id from href like:
# /player/Jabri-Abdur-Rahim/Summary/117329
PLAYER_HREF_RE = re.compile(r"/player/([^/]+)/Summary/(\d+)")

# URL pattern for the stats listing (all players, one page)
STATS_LISTING_URL = (
    "https://basketball.realgm.com/ncaa/stats/{year}"
    "/Averages/All/All/Season/All/desc/1"
)


def stats_listing_url(season: int) -> str:
    """Return the stats listing URL for a given season year."""
    return STATS_LISTING_URL.format(year=season)


# ---------------------------------------------------------------------------
# Core parser — works for both stats and bio listing pages
# ---------------------------------------------------------------------------

def parse_listing(html: str, season: int) -> list:
    """
    Parse a season listing page HTML (stats or bio format).
    Returns list of player dicts for that season.
    """
    soup = BeautifulSoup(html, "lxml")
    players = []

    table = _find_player_table(soup)
    if table is None:
        logger.error(f"Could not find player table for season {season}")
        return players

    thead = table.find("thead")
    if not thead:
        logger.error(f"No thead in player table for season {season}")
        return players

    headers = [th.get_text(strip=True) for th in thead.find_all("th")]
    logger.info(f"Season {season} columns: {headers}")

    tbody = table.find("tbody")
    if not tbody:
        return players

    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        player = _parse_row(cells, headers, season)
        if player:
            players.append(player)

    logger.info(f"Season {season}: parsed {len(players)} players")
    return players


def _find_player_table(soup):
    """Find the first table that contains player links."""
    for table in soup.find_all("table"):
        if table.find("a", href=PLAYER_HREF_RE):
            return table
    return None


def _parse_row(cells, headers, season: int) -> Optional[dict]:
    """Parse one table row into a player dict."""
    player_id = None
    url_slug = None
    player_name = None

    for cell in cells:
        link = cell.find("a", href=PLAYER_HREF_RE)
        if link:
            match = PLAYER_HREF_RE.search(link["href"])
            if match:
                url_slug = match.group(1)
                player_id = match.group(2)
                player_name = link.get_text(strip=True)
            break

    if not player_id:
        return None

    col_map = {}
    for i, cell in enumerate(cells):
        if i < len(headers):
            col_map[headers[i]] = cell.get_text(strip=True)

    return {
        "player_id":    player_id,
        "player_name":  player_name,
        "url_slug":     url_slug,
        "season":       season,
        # Stats page uses "Team" (abbrev); bio page uses "School" (full name)
        "team":         _get(col_map, ["Team", "School"]),
        "conference":   _get(col_map, ["Conference", "Conf"]),
        "position":     _get(col_map, ["Position", "Pos", "P"]),
        "class_year":   _get(col_map, ["Class", "Yr"]),
    }


def _get(col_map: dict, keys: list) -> Optional[str]:
    """Try multiple possible column name variants."""
    for k in keys:
        if k in col_map and col_map[k]:
            return col_map[k]
    return None


# ---------------------------------------------------------------------------
# Pagination (rarely needed — stats listing fits on one page)
# ---------------------------------------------------------------------------

def check_pagination(html: str) -> list:
    """
    Check if the listing page has multiple pages.
    Returns list of additional page URLs if any (empty if single page).

    Note: RealGM stats pages use JavaScript-based pagination with 100 players per page.
    This function is currently not effective for stats pages - we only get page 1.
    TODO: Implement page count detection and URL generation for stats pages.
    """
    soup = BeautifulSoup(html, "lxml")
    extra_urls = []

    pagination = soup.find("ul", class_=re.compile(r"pagination", re.I))
    if not pagination:
        return extra_urls

    for link in pagination.find_all("a", href=True):
        href = link["href"]
        # Skip javascript links and anchors
        if href and href not in extra_urls and href != "#" and not href.startswith("javascript:"):
            extra_urls.append(href)

    return extra_urls
