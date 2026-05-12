"""
NIL PRO MCP Server

Exposes NIL PRO basketball analytics as MCP tools for Claude.
Install: pipx install nil-pro-mcp
Configure: set NIL_PRO_API_URL env var to your deployed backend URL.
"""

from mcp.server.fastmcp import FastMCP
import httpx
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "NIL PRO",
    instructions=(
        "You help a basketball talent agent evaluate NCAA D1 players for NIL deals. "
        "When the user mentions a player by name, always call search_players first to get their player_id. "
        "Use rank_players to find/filter players by position, class, conference, or stats. "
        "Use get_player_profile for a full breakdown of a specific player. "
        "Use find_comps to identify comparable players for market positioning. "
        "Use compare_players to put 2-5 players side by side. "
        "Default season is '2025-26' unless the user specifies otherwise."
    ),
)

API_URL = os.environ.get("NIL_PRO_API_URL", "http://localhost:8000").rstrip("/")
DEFAULT_SEASON = "2025-26"
TIMEOUT = 20.0


def _get(path: str, params: dict | None = None) -> dict:
    """GET with one retry to handle Render cold starts."""
    url = f"{API_URL}{path}"
    for attempt in range(2):
        try:
            resp = httpx.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            if attempt == 1:
                raise


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _pct(v) -> str:
    if v is None:
        return "N/A"
    return f"{float(v) * 100:.1f}%"


def _f(v, d=1) -> str:
    if v is None:
        return "N/A"
    return f"{float(v):.{d}f}"


def _rating_line(p: dict) -> str:
    rating = _f(p.get("final_rating"), 1)
    return (
        f"★{rating}  "
        f"{_f(p.get('pts'))}pts  "
        f"{_f(p.get('reb'))}reb  "
        f"{_f(p.get('ast'))}ast  "
        f"{_f(p.get('min'))}min  "
        f"FG {_pct(p.get('fg_pct'))}  "
        f"3P {_pct(p.get('fg3_pct'))}"
    )


def _player_header(p: dict) -> str:
    conf = p.get("conference") or ""
    team_str = f"{p.get('team', '')} ({conf})" if conf else p.get("team", "")
    return (
        f"{p.get('full_name', 'Unknown')} | "
        f"{team_str} | "
        f"{p.get('pos_group') or p.get('position', '')} | "
        f"{p.get('class_year', '')}"
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_players(
    name: str,
    season: str = DEFAULT_SEASON,
) -> str:
    """
    Search for players by name. Always call this first when the user mentions
    a player by name — it returns the player_id needed by other tools.

    Args:
        name: Player name or partial name (e.g. "Cooper Flagg", "flagg")
        season: Season in "YYYY-YY" format (default: 2025-26)
    """
    try:
        data = _get("/api/search", {"q": name, "season": season, "limit": 10})
    except Exception as e:
        return f"Error searching for '{name}': {e}"

    results = data.get("results", [])
    if not results:
        return f"No players found matching '{name}' in {season}."

    lines = [f"Search results for '{name}' ({season}):\n"]
    for p in results:
        rating = f"  ★{_f(p.get('final_rating'))}" if p.get("final_rating") else ""
        lines.append(
            f"  {p['full_name']} | {p.get('team', '')} | {p.get('position', '')} | "
            f"ID: {p['player_id']}{rating}"
        )
    return "\n".join(lines)


@mcp.tool()
def rank_players(
    season: str = DEFAULT_SEASON,
    position_group: Optional[str] = None,
    class_year: Optional[str] = None,
    conference: Optional[str] = None,
    team: Optional[str] = None,
    sort_by: str = "final_rating",
    sort_dir: str = "desc",
    min_pts: Optional[float] = None,
    max_pts: Optional[float] = None,
    min_reb: Optional[float] = None,
    min_ast: Optional[float] = None,
    min_gp: Optional[int] = None,
    max_gp: Optional[int] = None,
    min_min: Optional[float] = None,
    min_fg3_pct: Optional[float] = None,
    min_rating: Optional[float] = None,
    limit: int = 25,
) -> str:
    """
    Find and rank players using filters. Use this for queries like:
    "top guards in the ACC", "freshman bigs averaging 15+ points",
    "senior guards with good 3-point shooting".

    Args:
        season: Season in "YYYY-YY" format (default: 2025-26)
        position_group: "Guard", "Wing", or "Big"
        class_year: "Freshman", "Sophomore", "Junior", "Senior", or "Graduate"
        conference: Conference name, e.g. "ACC", "Big Ten", "SEC", "Big 12",
                    "Big East", "Pac-12", "American", "Mountain West"
        team: Exact team name, e.g. "Duke", "Kentucky"
        sort_by: Column to sort by. Common options: final_rating, pts, reb, ast,
                 stl, blk, min, fg_pct, fg3_pct, ft_pct, per, usg_pct, ws
        sort_dir: "desc" (default) or "asc"
        min_pts: Minimum points per game
        max_pts: Maximum points per game
        min_reb: Minimum rebounds per game
        min_ast: Minimum assists per game
        min_gp: Minimum games played
        max_gp: Maximum games played
        min_min: Minimum minutes per game
        min_fg3_pct: Minimum 3-point % (as decimal, e.g. 0.35 for 35%)
        min_rating: Minimum NIL PRO rating
        limit: Number of results to return (default 25, max 200)
    """
    params: dict = {
        "sort_col": sort_by,
        "sort_dir": sort_dir,
        "limit": min(limit, 200),
        "offset": 0,
    }

    if position_group:
        params["pos_group"] = position_group
    if class_year:
        params["class_year"] = class_year
    if conference:
        params["conference"] = conference
    if team:
        params["team"] = team
    if min_pts is not None:
        params["pts_min"] = min_pts
    if max_pts is not None:
        params["pts_max"] = max_pts
    if min_reb is not None:
        params["reb_min"] = min_reb
    if min_ast is not None:
        params["ast_min"] = min_ast
    if min_gp is not None:
        params["gp_min"] = min_gp
    if max_gp is not None:
        params["gp_max"] = max_gp
    if min_min is not None:
        params["min_min"] = min_min
    if min_fg3_pct is not None:
        params["fg3_pct_min"] = min_fg3_pct
    if min_rating is not None:
        params["final_rating_min"] = min_rating

    try:
        data = _get(f"/api/players/{season}", params)
    except Exception as e:
        return f"Error fetching players: {e}"

    players = data.get("data", [])
    total = data.get("count", len(players))

    if not players:
        return "No players found matching those filters."

    # Build filter description
    filters = []
    if position_group:
        filters.append(position_group)
    if class_year:
        filters.append(class_year)
    if conference:
        filters.append(conference)
    if team:
        filters.append(team)
    filter_str = " | ".join(filters) if filters else "All players"

    lines = [f"{filter_str} — {season} ({total} results, showing {len(players)})\n"]
    lines.append(f"{'#':<4} {'Name':<22} {'Team':<20} {'Conf':<12} {'Pos':<6} {'Yr':<5} {'Rtg':>5}  Stats")
    lines.append("-" * 110)

    for i, p in enumerate(players, 1):
        conf = (p.get("conference") or "")[:11]
        team_name = (p.get("team") or "")[:19]
        name = (p.get("full_name") or "")[:21]
        pos = (p.get("pos_group") or "")[:5]
        yr = (p.get("class_year") or "")[:4]
        rating = _f(p.get("final_rating"))
        stats = (
            f"{_f(p.get('pts'))}pts  "
            f"{_f(p.get('reb'))}reb  "
            f"{_f(p.get('ast'))}ast  "
            f"{_f(p.get('min'))}min  "
            f"FG {_pct(p.get('fg_pct'))}  "
            f"3P {_pct(p.get('fg3_pct'))}"
        )
        lines.append(
            f"{i:<4} {name:<22} {team_name:<20} {conf:<12} {pos:<6} {yr:<5} {rating:>5}  {stats}"
        )
        lines.append(f"     ID: {p['player_id']}  |  GP: {p.get('gp', 'N/A')}  |  STL {_f(p.get('stl'))}  BLK {_f(p.get('blk'))}  TOV {_f(p.get('tov'))}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def get_player_profile(
    player_id: str,
    season: Optional[str] = None,
) -> str:
    """
    Get a full profile for a player: bio, all seasons of stats, NIL PRO rating
    with complete boost breakdown, and similar players.

    Use this for deep dives: "Tell me everything about Player X",
    "What does Player X need to improve?", "How has Player X developed?"

    Args:
        player_id: Player ID from search_players
        season: If provided, show only this season's stats. Otherwise shows all seasons.
    """
    try:
        data = _get(f"/api/profile/{player_id}")
    except Exception as e:
        return f"Error fetching profile for {player_id}: {e}"

    bio = data.get("bio", {})
    seasons = data.get("seasons", [])
    similarity = data.get("similarity", {})

    if season:
        seasons = [s for s in seasons if s.get("season") == season]

    lines = []

    # Bio
    lines.append(f"=== {bio.get('full_name', player_id)} ===")
    lines.append(
        f"Position: {bio.get('position', 'N/A')}  |  "
        f"Height: {bio.get('height_ft', 'N/A')}  |  "
        f"Weight: {bio.get('weight_lbs', 'N/A')} lbs  |  "
        f"Hometown: {bio.get('hometown', 'N/A')}"
    )
    lines.append("")

    # Season stats
    for s in seasons:
        s_label = s.get("season", "")
        rating = s.get("rating") or {}
        pg = s.get("pergame") or {}
        adv = s.get("advanced") or {}
        misc = s.get("misc") or {}

        lines.append(f"--- {s_label} | {rating.get('team', pg.get('team', 'N/A'))} | {rating.get('position', 'N/A')} | {pg.get('class_year', 'N/A')} ---")

        if rating:
            lines.append(
                f"NIL PRO Rating: {_f(rating.get('final_rating'))}  "
                f"(Base: {_f(rating.get('base_rating'))}  "
                f"Game Adj: {_f(rating.get('game_adj'))})"
            )
            lines.append(
                f"  Boosts — Min: +{_f(rating.get('min_boost'))}  "
                f"3P: +{_f(rating.get('three_boost'))}  "
                f"FG: +{_f(rating.get('fg_boost'))}  "
                f"AST: +{_f(rating.get('ast_boost'))}  "
                f"BLK: +{_f(rating.get('blk_boost'))}  "
                f"FT: +{_f(rating.get('free_throw_boost'))}  "
                f"DD: +{_f(rating.get('double_double_boost'))}  "
                f"TD: +{_f(rating.get('triple_double_boost'))}"
            )
            lines.append(
                f"  Percentiles — Min: {rating.get('min_per', 'N/A')}th  "
                f"Pts: {rating.get('pts_per', 'N/A')}th  "
                f"Reb: {rating.get('reb_per', 'N/A')}th  "
                f"Ast: {rating.get('ast_per', 'N/A')}th  "
                f"Blk: {rating.get('blk_per', 'N/A')}th  "
                f"Stl: {rating.get('stl_per', 'N/A')}th  "
                f"FG%: {rating.get('fgpct_per', 'N/A')}th  "
                f"3P%: {rating.get('p3pct_per', 'N/A')}th  "
                f"FT%: {rating.get('ftpct_per', 'N/A')}th"
            )

        if pg:
            lines.append(
                f"  Per Game — GP: {pg.get('gp', 'N/A')}  "
                f"Min: {_f(pg.get('min'))}  "
                f"Pts: {_f(pg.get('pts'))}  "
                f"Reb: {_f(pg.get('trb') or pg.get('reb'))}  "
                f"Ast: {_f(pg.get('ast'))}  "
                f"Stl: {_f(pg.get('stl'))}  "
                f"Blk: {_f(pg.get('blk'))}  "
                f"Tov: {_f(pg.get('tov'))}"
            )
            lines.append(
                f"  Shooting — FG: {_pct(pg.get('fg_pct'))} ({_f(pg.get('fgm'))}/{_f(pg.get('fga'))})  "
                f"3P: {_pct(pg.get('fg3_pct'))} ({_f(pg.get('fg3m'))}/{_f(pg.get('fg3a'))})  "
                f"FT: {_pct(pg.get('ft_pct'))} ({_f(pg.get('ftm'))}/{_f(pg.get('fta'))})"
            )

        if adv:
            lines.append(
                f"  Advanced — PER: {_f(adv.get('per'))}  "
                f"TS%: {_pct(adv.get('ts_pct'))}  "
                f"eFG%: {_pct(adv.get('efg_pct'))}  "
                f"USG%: {_f(adv.get('usg_pct'))}%  "
                f"ORtg: {_f(adv.get('ortg'))}  "
                f"DRtg: {_f(adv.get('drtg'))}"
            )

        if misc:
            lines.append(
                f"  Misc — DD: {misc.get('dbl_dbl', 0)}  "
                f"TD: {misc.get('tpl_dbl', 0)}  "
                f"AST/TO: {_f(misc.get('ast_to_ratio'))}  "
                f"Win%: {_pct(misc.get('win_pct'))}  "
                f"WS: {_f(misc.get('ws'))}"
            )

        lines.append("")

    # Similarity (top 3 per segment, most recent season only)
    if similarity:
        lines.append("--- Similar Players (2025-26) ---")
        for segment, comps in similarity.items():
            lines.append(f"  {segment.upper()}:")
            for c in comps[:3]:
                lines.append(
                    f"    {c['sim_name']} | {c['sim_team']} | {c['sim_pos']} | "
                    f"★{_f(c.get('sim_rating'))} | "
                    f"Similarity: {_f(float(c.get('score', 0)) * 100, 1)}%  "
                    f"(ID: {c['sim_player_id']})"
                )
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def find_comps(
    player_id: str,
    season: str = DEFAULT_SEASON,
    segment: Optional[str] = None,
) -> str:
    """
    Find players most similar to a given player. Critical for NIL market
    positioning — use to answer "who is Player X comparable to?" or
    "what deals have similar players gotten?"

    Args:
        player_id: Player ID from search_players
        season: Season to compare (default: 2025-26)
        segment: Filter to one similarity segment. Options: overall, scoring,
                 defense, playmaking, playing_time. Omit to see all segments.
    """
    try:
        data = _get(f"/api/similarity/{player_id}/{season}")
    except Exception as e:
        return f"Error fetching comps for {player_id}: {e}"

    segments = data.get("segments", {})
    if not segments:
        return f"No similarity data found for player {player_id} in {season}."

    if segment:
        matched = {k: v for k, v in segments.items() if segment.lower() in k.lower()}
        if not matched:
            return f"Segment '{segment}' not found. Available: {', '.join(segments.keys())}"
        segments = matched

    lines = [f"Comps for player {player_id} ({season}):\n"]

    for seg_name, comps in segments.items():
        lines.append(f"{seg_name.upper().replace('_', ' ')} COMPS")
        lines.append("-" * 60)
        for c in comps[:8]:
            score_pct = _f(float(c.get("score", 0)) * 100, 1)
            lines.append(
                f"  #{c['rank']}  {c['sim_name']:<22} | "
                f"{c['sim_team']:<18} | "
                f"{c['sim_pos']:<5} | "
                f"★{_f(c.get('sim_rating'))} | "
                f"Sim: {score_pct}%  "
                f"(ID: {c['sim_player_id']})"
            )
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def compare_players(
    player_ids: str,
    season: str = DEFAULT_SEASON,
) -> str:
    """
    Compare 2-5 players side by side for a given season.

    Args:
        player_ids: Comma-separated player IDs (2-5 players), e.g. "abc123,def456,ghi789"
        season: Season in "YYYY-YY" format (default: 2025-26)
    """
    try:
        data = _get("/api/compare-many", {"player_ids": player_ids, "season": season})
    except Exception as e:
        return f"Error comparing players: {e}"

    players = data.get("players", [])
    if not players:
        return "No data found for those player IDs in this season."

    lines = [f"Player Comparison — {season}\n"]

    # Header row
    stat_labels = [
        ("Rating",    "final_rating",  lambda v: _f(v)),
        ("GP",        "gp",            lambda v: str(v) if v is not None else "N/A"),
        ("Min",       "min",           lambda v: _f(v)),
        ("Pts",       "pts",           lambda v: _f(v)),
        ("Reb",       "reb",           lambda v: _f(v)),
        ("Ast",       "ast",           lambda v: _f(v)),
        ("Stl",       "stl",           lambda v: _f(v)),
        ("Blk",       "blk",           lambda v: _f(v)),
        ("Tov",       "tov",           lambda v: _f(v)),
        ("FG%",       "fg_pct",        lambda v: _pct(v)),
        ("3P%",       "fg3_pct",       lambda v: _pct(v)),
        ("FT%",       "ft_pct",        lambda v: _pct(v)),
        ("TS%",       "ts_pct",        lambda v: _pct(v)),
        ("PER",       "per",           lambda v: _f(v)),
        ("USG%",      "usg_pct",       lambda v: _f(v) + "%"),
        ("ORtg",      "ortg",          lambda v: _f(v)),
        ("DRtg",      "drtg",          lambda v: _f(v)),
        ("WS",        "ws",            lambda v: _f(v)),
        ("AST/TO",    "ast_to_ratio",  lambda v: _f(v)),
    ]

    # Player headers
    for p in players:
        conf = p.get("conference") or ""
        team_str = f"{p.get('team', '')} ({conf})" if conf else p.get("team", "")
        lines.append(
            f"  {p.get('full_name', p['player_id'])} | "
            f"{team_str} | "
            f"{p.get('pos_group') or p.get('position', '')} | "
            f"{p.get('class_year', '')} | "
            f"ID: {p['player_id']}"
        )
    lines.append("")

    # Stat rows
    col_w = 12
    label_w = 8
    header = f"{'Stat':<{label_w}}" + "".join(
        f"{(p.get('full_name') or p['player_id'])[:col_w]:<{col_w}}" for p in players
    )
    lines.append(header)
    lines.append("-" * (label_w + col_w * len(players)))

    for label, key, fmt in stat_labels:
        row = f"{label:<{label_w}}"
        values = [p.get(key) for p in players]
        formatted = [fmt(v) for v in values]

        # Highlight best value (highest for most stats, lowest for tov/drtg)
        try:
            numeric = [float(v) if v is not None else None for v in values]
            valid = [v for v in numeric if v is not None]
            if valid:
                best = min(valid) if key in ("tov", "drtg") else max(valid)
                formatted = [
                    f"[{f}]" if (numeric[i] is not None and numeric[i] == best) else f
                    for i, f in enumerate(formatted)
                ]
        except (TypeError, ValueError):
            pass

        row += "".join(f"{v:<{col_w}}" for v in formatted)
        lines.append(row)

    lines.append("\n[ ] = best value in category")
    return "\n".join(lines)


@mcp.tool()
def get_leaderboard(
    stat: str = "pts",
    season: str = DEFAULT_SEASON,
    limit: int = 10,
) -> str:
    """
    Get the national leaders for a specific stat. Use for market context:
    "who leads the country in scoring?", "top shot-blockers this season".

    Args:
        stat: One of: pts, reb, ast, stl, blk, fg_pct, fg3_pct, ft_pct, min
        season: Season in "YYYY-YY" format (default: 2025-26)
        limit: Number of players to return (default 10)
    """
    try:
        data = _get(f"/api/stats/leaderboard/{season}", {"stat": stat, "limit": limit})
    except Exception as e:
        return f"Error fetching leaderboard: {e}"

    leaders = data.get("leaders", [])
    if not leaders:
        return f"No leaderboard data for {stat} in {season}."

    stat_labels = {
        "pts": "Points", "reb": "Rebounds", "ast": "Assists",
        "stl": "Steals", "blk": "Blocks", "min": "Minutes",
        "fg_pct": "FG%", "fg3_pct": "3P%", "ft_pct": "FT%",
    }
    label = stat_labels.get(stat, stat.upper())

    lines = [f"National Leaders — {label} ({season})\n"]
    for i, p in enumerate(leaders, 1):
        val = p.get(stat)
        if stat.endswith("_pct"):
            val_str = _pct(val)
        else:
            val_str = _f(val)

        rating = f"  ★{_f(p.get('final_rating'))}" if p.get("final_rating") else ""
        lines.append(
            f"  #{i:<3} {p.get('full_name', ''):<22} | "
            f"{p.get('team', ''):<20} | "
            f"GP: {p.get('gp', 'N/A'):<4} | "
            f"{label}: {val_str}{rating}  "
            f"(ID: {p.get('player_id', '')})"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
