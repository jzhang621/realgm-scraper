"""
parsers/profile.py — Parse a player Summary page.

Extracts:
  - Profile / bio data
  - All stat tables (per game, totals, advanced, misc) across all career levels
  - Awards, transactions, events
"""

import re
import logging
from typing import Optional
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# Maps the text label on the career tab to a level constant.
# Normalisation: lowercase + strip spaces → e.g. "NCAACareer" → "ncaacareer"
TAB_LABEL_TO_LEVEL = {
    "ncaacareer":           config.LEVEL_NCAA_DI,
    "gleaguecareer":        config.LEVEL_G_LEAGUE,
    "nbacareer":            config.LEVEL_NBA,
    "internationalcareer":  config.LEVEL_INTERNATIONAL,
    "nationalcareer":       config.LEVEL_NATIONAL,
    "aaucareer":            config.LEVEL_AAU,
    "highschoolcareer":     config.LEVEL_HIGH_SCHOOL,
    # Alternate spellings seen in the wild
    "highschoolcareer":     config.LEVEL_HIGH_SCHOOL,
    "highschool career":    config.LEVEL_HIGH_SCHOOL,
    "ncaajucocareer":       config.LEVEL_NCAA_JUCO,
    "jucocareer":           config.LEVEL_NCAA_JUCO,
}

# Maps the stats sub-tab label to a stat_type string
STAT_TAB_TO_TYPE = {
    "summary":   "summary",
    "pergame":   "per_game",
    "totals":    "totals",
    "advanced":  "advanced",
    "misc":      "misc",
}


def parse_player_page(html: str, player_id: str) -> dict:
    """
    Parse a full player Summary page.

    Returns:
      {
        "profile":      dict,
        "per_game":     [rows],
        "totals":       [rows],
        "advanced":     [rows],
        "misc":         [rows],
        "awards":       [rows],
        "transactions": [rows],
        "events":       [rows],
      }
    """
    soup = BeautifulSoup(html, "lxml")

    result = {
        "profile":      _parse_profile(soup, player_id),
        "per_game":     [],
        "totals":       [],
        "advanced":     [],
        "misc":         [],
        "awards":       [],
        "transactions": [],
        "events":       [],
    }

    # Try OLD HTML structure first (section_tabs div)
    section_tabs_div = soup.find("div", class_="section_tabs")
    if section_tabs_div:
        _parse_old_structure(section_tabs_div, soup, player_id, result)
    else:
        # Try NEW HTML structure (h2 tags for career sections)
        _parse_new_structure(soup, player_id, result)

    return result


def _parse_old_structure(section_tabs_div, soup, player_id: str, result: dict):
    """Parse the old HTML structure with section_tabs div."""
    # Get the tab nav items to map panel ID → level.
    # The nav <ul> is a direct child of section_tabs_div with NO class attribute.
    # We find the first <ul> inside section_tabs_div (DFS order puts the nav ul first,
    # before any nested uls inside the content panels).
    tab_nav = section_tabs_div.find("ul")
    if not tab_nav:
        return

    panel_to_level = {}
    for li in tab_nav.find_all("li"):
        a = li.find("a")
        if not a:
            continue
        href = a.get("href", "")           # e.g. "#tabs_profile-2"
        panel_id = href.lstrip("#")         # e.g. "tabs_profile-2"
        label_raw = a.get_text(separator="", strip=True).lower()
        label_clean = re.sub(r"\s+", "", label_raw)  # "gleaguecareer"

        level = TAB_LABEL_TO_LEVEL.get(label_clean)
        if level and panel_id:
            panel_to_level[panel_id] = level

    # Process each career panel
    for panel_id, level in panel_to_level.items():
        panel_div = soup.find("div", id=panel_id)
        if not panel_div:
            continue
        _parse_career_panel(panel_div, level, player_id, result)


def _parse_new_structure(soup, player_id: str, result: dict):
    """
    Parse the new HTML structure where career sections are marked by <h2> tags.
    New format (as of 2026):
      <h2>NCAA Career</h2>
      <p>College: ...</p>
      <h3>NCAA Awards & Honors</h3>
      <table>...</table>
      <h3>NCAA Season Stats</h3>
      <div class="stats_tabs">...</div>
    """
    # Map h2 text to level
    h2_to_level = {
        "ncaa career": config.LEVEL_NCAA_DI,
        "g league career": config.LEVEL_G_LEAGUE,
        "g-league career": config.LEVEL_G_LEAGUE,
        "nba career": config.LEVEL_NBA,
        "international career": config.LEVEL_INTERNATIONAL,
        "national career": config.LEVEL_NATIONAL,
        "aau career": config.LEVEL_AAU,
        "high school career": config.LEVEL_HIGH_SCHOOL,
        "juco career": config.LEVEL_NCAA_JUCO,
    }

    for h2 in soup.find_all("h2"):
        h2_text = h2.get_text(strip=True).lower()
        level = h2_to_level.get(h2_text)
        if not level:
            continue

        # Create a virtual "panel" by finding all content until the next h2
        # We'll collect all siblings after this h2 until we hit another h2
        panel_content = []
        for sibling in h2.find_next_siblings():
            if sibling.name == "h2":
                break
            panel_content.append(sibling)

        # Create a temporary container div with this content
        from bs4 import BeautifulSoup as BS
        temp_soup = BS("<div></div>", "lxml")
        temp_div = temp_soup.find("div")
        for elem in panel_content:
            temp_div.append(elem.extract() if hasattr(elem, 'extract') else elem)

        # Parse this virtual panel
        _parse_career_panel(temp_div, level, player_id, result)


# ─── Profile / Bio ────────────────────────────────────────────────────────────

def _parse_profile(soup, player_id: str) -> dict:
    profile = {"player_id": player_id}

    profile_box = soup.find("div", class_="profile-box")
    if not profile_box:
        return profile

    # Name, position, number from h2.
    # The h2 looks like: "Jabri Abdur-Rahim <span>SF</span> <span>#12</span>"
    # Extract position/number from spans first, then remove spans before reading name.
    h2 = profile_box.find("h2")
    if h2:
        features = h2.find_all("span", class_="feature")
        if len(features) >= 1:
            profile["position"] = features[0].get_text(strip=True)
        if len(features) >= 2:
            profile["jersey_number"] = features[1].get_text(strip=True).lstrip("#")
        # Remove all child tags so only the bare name text node remains
        for tag in h2.find_all(True):
            tag.decompose()
        profile["full_name"] = h2.get_text(strip=True)

    # Key-value pairs from <p> tags
    for p in profile_box.find_all("p"):
        text = p.get_text(separator=" ", strip=True)
        _extract_profile_field(text, p, profile)

    # Current team (may be in right column with a team logo)
    current_team_p = profile_box.find("p", string=re.compile(r"Current Team", re.I))
    if current_team_p:
        a = current_team_p.find("a")
        if a:
            profile["current_team"] = a.get_text(strip=True)
            href = a.get("href", "")
            if "/gleague/" in href:
                profile["current_team_level"] = "G_LEAGUE"
            elif "/nba/" in href:
                profile["current_team_level"] = "NBA"
            elif "/international/" in href:
                profile["current_team_level"] = "INTERNATIONAL"
            else:
                profile["current_team_level"] = "OTHER"

    return profile


def _extract_profile_field(text: str, p_tag, profile: dict):
    """Parse a single <p> tag's text into profile fields."""
    patterns = [
        (r"Height[:\s]+([^\n]+)",           "height_raw"),
        (r"Weight[:\s]+([^\n]+)",           "weight_raw"),
        (r"Born[:\s]+([^\n(]+)",            "dob_raw"),
        (r"Hometown[:\s]+([^\n]+)",         "hometown"),
        (r"Nationality[:\s]+([^\n]+)",      "nationality"),
        (r"Current NBA Status[:\s]+([^\n]+)","nba_status"),
        (r"NBA Draft[:\s]+([^\n]+)",        "draft_raw"),
        (r"Pre-Draft Team[:\s]+([^\n]+)",   "pre_draft_raw"),
        (r"High School[:\s]+([^\n]+)",      "high_school_raw"),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, text, re.I)
        if m and key not in profile:
            raw = m.group(1).strip()
            profile[key] = raw
            _post_process(key, raw, p_tag, profile)


def _post_process(key: str, raw: str, p_tag, profile: dict):
    """Extract structured values from raw profile strings."""
    if key == "height_raw":
        # e.g. "6-8 (203cm)"
        m = re.search(r"\((\d+)cm\)", raw)
        if m:
            profile["height_cm"] = int(m.group(1))
        profile["height_ft"] = re.sub(r"\s*\(.*?\)", "", raw).strip()

    elif key == "weight_raw":
        # e.g. "215 lbs (98kg)"
        m = re.search(r"(\d+)\s*lbs", raw)
        if m:
            profile["weight_lbs"] = int(m.group(1))
        m2 = re.search(r"\((\d+)kg\)", raw)
        if m2:
            profile["weight_kg"] = int(m2.group(1))

    elif key == "dob_raw":
        # e.g. "Mar 22, 2002" — grab link text for clean date
        a = p_tag.find("a")
        if a:
            profile["dob"] = a.get_text(strip=True).split("(")[0].strip()

    elif key == "draft_raw":
        # e.g. "2025 Undrafted" or "2022 Round 1 Pick 15 by LAL"
        profile["draft_year"] = _first_int(raw)
        if "undrafted" in raw.lower():
            profile["draft_round"] = None
            profile["draft_pick"] = None
            profile["draft_team"] = None
        else:
            m = re.search(r"Round\s*(\d+)", raw, re.I)
            if m:
                profile["draft_round"] = int(m.group(1))
            m2 = re.search(r"Pick\s*(\d+)", raw, re.I)
            if m2:
                profile["draft_pick"] = int(m2.group(1))
            a = p_tag.find("a", href=re.compile(r"/nba/teams/"))
            if a:
                profile["draft_team"] = a.get_text(strip=True)

    elif key == "pre_draft_raw":
        a = p_tag.find("a")
        if a:
            profile["pre_draft_team"] = a.get_text(strip=True)
        m = re.search(r"\((\w+)\)", raw)
        if m:
            profile["pre_draft_class"] = m.group(1)

    elif key == "high_school_raw":
        a = p_tag.find("a")
        if a:
            profile["high_school"] = a.get_text(strip=True)
        # Location in parentheses: "(Blairstown Township, New Jersey)"
        m = re.search(r"\(([^)]+)\)\s*$", raw)
        if m:
            profile["high_school_location"] = m.group(1).strip()


# ─── Career Panel ─────────────────────────────────────────────────────────────

def _parse_career_panel(panel_div, level: str, player_id: str, result: dict):
    """Process one career panel (e.g. NCAA Career, G League Career)."""

    # ── Awards ──
    for awards_table in _find_section_tables(panel_div, r"Awards|Honors"):
        for tr in awards_table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 2:
                award_text = cells[0].get_text(strip=True)
                date_text  = cells[1].get_text(strip=True)
                if award_text:
                    result["awards"].append({
                        "player_id":   player_id,
                        "award_name":  award_text,
                        "level":       level,
                        "award_date":  date_text,
                    })

    # ── Transactions ──
    for txn_table in _find_section_tables(panel_div, r"Transactions"):
        for tr in txn_table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 2:
                date_text = cells[0].get_text(strip=True)
                txn_text  = cells[1].get_text(strip=True)
                if txn_text:
                    result["transactions"].append({
                        "player_id":        player_id,
                        "transaction_date": date_text,
                        "transaction_text": txn_text,
                        "level":            level,
                    })

    # ── Camps / Events ──
    # Only match small listing tables (camp name + year), NOT the "Special Events Stats"
    # table which has many columns (Year, Age, Event, GP, MIN, PTS, ...).
    for events_table in _find_section_tables(panel_div, r"Camp|Academy|National Team"):
        thead = events_table.find("thead")
        if thead:
            col_count = len(thead.find_all("th"))
            if col_count > 4:   # stats table — skip
                continue
        for tr in events_table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 2:
                event_name = cells[0].get_text(strip=True)
                year_text  = cells[1].get_text(strip=True)
                if event_name:
                    result["events"].append({
                        "player_id":  player_id,
                        "event_name": event_name,
                        "year":       year_text,
                        "level":      level,
                    })

    # ── Stats tabs (per game, totals, advanced, misc) ──
    _parse_stats_tabs(panel_div, level, player_id, result)


def _parse_stats_tabs(panel_div, level: str, player_id: str, result: dict):
    """
    Find all stats_tabs within this career panel and extract rows from each sub-tab.
    Each stats_tabs div covers one block (e.g. Regular Season, Summer League, Special Events).
    """
    for stats_tabs_div in panel_div.find_all("div", class_="stats_tabs", recursive=True):
        # Map each sub-tab panel_id → stat_type.
        # The nav <ul> is the first direct child of stats_tabs_div (no class attribute).
        tab_nav = stats_tabs_div.find("ul")
        if not tab_nav:
            continue

        sub_panel_to_type = {}
        for li in tab_nav.find_all("li"):
            a = li.find("a")
            if not a:
                continue
            href = a.get("href", "").lstrip("#")
            label = a.get_text(strip=True).lower().replace(" ", "")
            stat_type = STAT_TAB_TO_TYPE.get(label)
            if stat_type and href:
                sub_panel_to_type[href] = stat_type

        for sub_panel_id, stat_type in sub_panel_to_type.items():
            # Skip "summary" tab — per_game has the same data + more columns
            if stat_type == "summary":
                continue

            sub_panel = stats_tabs_div.find("div", id=sub_panel_id)
            if not sub_panel:
                continue

            # Bootstrap Table creates multiple <table> elements:
            # - First table is empty (for fixed header)
            # - Second table contains the actual data
            # Find the first table that has a tbody with rows
            table = None
            for t in sub_panel.find_all("table"):
                tbody = t.find("tbody")
                if tbody and tbody.find("tr"):
                    table = t
                    break

            if not table:
                continue

            rows = _parse_stat_table(table, level, player_id, stat_type)
            if stat_type == "per_game":
                result["per_game"].extend(rows)
            elif stat_type == "totals":
                result["totals"].extend(rows)
            elif stat_type == "advanced":
                result["advanced"].extend(rows)
            elif stat_type == "misc":
                result["misc"].extend(rows)


def _parse_stat_table(table, level: str, player_id: str, stat_type: str) -> list:
    """Parse a single stat table into a list of row dicts."""
    rows = []

    thead = table.find("thead")
    if not thead:
        return rows

    # Get column names from the last header row (some tables have two header rows)
    header_rows = thead.find_all("tr")
    headers = [th.get_text(strip=True) for th in header_rows[-1].find_all("th")]

    tbody = table.find("tbody")
    if not tbody:
        return rows

    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if not cells or len(cells) < 3:
            continue

        # Build col_map
        col_map = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                col_map[headers[i]] = cell.get_text(strip=True)

        # Skip redshirt / missing-data rows (all stat cells are "-")
        stat_vals = [v for k, v in col_map.items() if k not in ("Season", "Age", "School", "Team", "League", "Class", "Year", "Event")]
        if all(v == "-" or v == "" for v in stat_vals):
            continue

        row = _build_stat_row(col_map, level, player_id, stat_type)
        if row:
            rows.append(row)

    return rows


def _build_stat_row(col_map: dict, level: str, player_id: str, stat_type: str) -> dict:
    """Map column values into a normalized stat row dict."""

    # Detect if this is JUCO (school cell has text but no link — handled upstream)
    # We mark as JUCO if level is NCAA_DI but school is unlinked (parser can't easily tell here,
    # so we store as NCAA_DI and let post-processing differentiate if needed)

    base = {
        "player_id":    player_id,
        "season":       _get(col_map, ["Season", "Year"]),
        "age":          _safe_int(_get(col_map, ["Age"])),
        "level":        level,
        "league_name":  _get(col_map, ["League"]),
        "team":         _get(col_map, ["Team", "School"]),
        "class_year":   _get(col_map, ["Class"]),
        "stat_type":    stat_type,
    }

    if stat_type in ("per_game", "totals"):
        base.update({
            "gp":       _safe_int(_get(col_map, ["GP"])),
            "gs":       _safe_int(_get(col_map, ["GS"])),
            "min":      _safe_float(_get(col_map, ["MIN"])),
            "pts":      _safe_float(_get(col_map, ["PTS"])),
            "fgm":      _safe_float(_get(col_map, ["FGM"])),
            "fga":      _safe_float(_get(col_map, ["FGA"])),
            "fg_pct":   _safe_float(_get(col_map, ["FG%"])),
            "fg3m":     _safe_float(_get(col_map, ["3PM"])),
            "fg3a":     _safe_float(_get(col_map, ["3PA"])),
            "fg3_pct":  _safe_float(_get(col_map, ["3P%"])),
            "ftm":      _safe_float(_get(col_map, ["FTM"])),
            "fta":      _safe_float(_get(col_map, ["FTA"])),
            "ft_pct":   _safe_float(_get(col_map, ["FT%"])),
            "off_reb":  _safe_float(_get(col_map, ["OFF"])),
            "def_reb":  _safe_float(_get(col_map, ["DEF"])),
            "trb":      _safe_float(_get(col_map, ["TRB", "REB"])),
            "ast":      _safe_float(_get(col_map, ["AST"])),
            "stl":      _safe_float(_get(col_map, ["STL"])),
            "blk":      _safe_float(_get(col_map, ["BLK"])),
            "tov":      _safe_float(_get(col_map, ["TOV"])),
            "pf":       _safe_float(_get(col_map, ["PF"])),
        })

    elif stat_type == "advanced":
        base.update({
            "gp":           _safe_int(_get(col_map, ["GP"])),
            "gs":           _safe_int(_get(col_map, ["GS"])),
            "ts_pct":       _safe_float(_get(col_map, ["TS%"])),
            "efg_pct":      _safe_float(_get(col_map, ["eFG%"])),
            "orb_pct":      _safe_float(_get(col_map, ["ORB%"])),
            "drb_pct":      _safe_float(_get(col_map, ["DRB%"])),
            "trb_pct":      _safe_float(_get(col_map, ["TRB%"])),
            "ast_pct":      _safe_float(_get(col_map, ["AST%"])),
            "tov_pct":      _safe_float(_get(col_map, ["TOV%"])),
            "stl_pct":      _safe_float(_get(col_map, ["STL%"])),
            "blk_pct":      _safe_float(_get(col_map, ["BLK%"])),
            "usg_pct":      _safe_float(_get(col_map, ["USG%"])),
            "total_s_pct":  _safe_float(_get(col_map, ["Total S %"])),
            "ppr":          _safe_float(_get(col_map, ["PPR"])),
            "pps":          _safe_float(_get(col_map, ["PPS"])),
            "ortg":         _safe_float(_get(col_map, ["ORtg"])),
            "drtg":         _safe_float(_get(col_map, ["DRtg"])),
            "per":          _safe_float(_get(col_map, ["PER"])),
        })

    elif stat_type == "misc":
        base.update({
            "gp":           _safe_int(_get(col_map, ["GP"])),
            "gs":           _safe_int(_get(col_map, ["GS"])),
            "dbl_dbl":      _safe_int(_get(col_map, ["Dbl Dbl"])),
            "tpl_dbl":      _safe_int(_get(col_map, ["Tpl Dbl"])),
            "pts_40":       _safe_int(_get(col_map, ["40 Pts"])),
            "reb_20":       _safe_int(_get(col_map, ["20 Reb"])),
            "ast_20":       _safe_int(_get(col_map, ["20 Ast"])),
            "techs":        _safe_int(_get(col_map, ["Techs"])),
            "hob":          _safe_float(_get(col_map, ["HOB"])),
            "ast_to_ratio": _safe_float(_get(col_map, ["Ast/TO"])),
            "stl_to_ratio": _safe_float(_get(col_map, ["Stl/TO"])),
            "ft_per_fga":   _safe_float(_get(col_map, ["FT/FGA"])),
            "wins":         _safe_int(_get(col_map, ["W's"])),
            "losses":       _safe_int(_get(col_map, ["L's"])),
            "win_pct":      _safe_float(_get(col_map, ["Win %"])),
            "ows":          _safe_float(_get(col_map, ["OWS"])),
            "dws":          _safe_float(_get(col_map, ["DWS"])),
            "ws":           _safe_float(_get(col_map, ["WS"])),
        })

    return base


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_section_tables(panel_div, heading_pattern: str):
    """
    Find tables that appear under a heading matching the pattern.
    Yields each matching table.
    """
    pattern = re.compile(heading_pattern, re.I)
    for h3 in panel_div.find_all("h3"):
        if pattern.search(h3.get_text()):
            # The table follows the h3 (look in next siblings or nearby div)
            table = _next_table(h3)
            if table:
                yield table


def _next_table(tag):
    """Find the next <table> after a given tag in the DOM."""
    for sibling in tag.find_next_siblings():
        if sibling.name == "table":
            return sibling
        table = sibling.find("table") if hasattr(sibling, "find") else None
        if table:
            return table
    return None


def _get(col_map: dict, keys: list):
    for k in keys:
        if k in col_map:
            v = col_map[k].strip()
            if v and v != "-":
                return v
    return None


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val.replace(",", "").replace("%", ""))
    except (ValueError, AttributeError):
        return None


def _safe_int(val) -> Optional[int]:
    f = _safe_float(val)
    return int(f) if f is not None else None


def _first_int(s: str) -> Optional[int]:
    m = re.search(r"\d{4}", s)
    return int(m.group()) if m else None
