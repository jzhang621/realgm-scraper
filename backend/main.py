"""
FastAPI Backend for NCAA Basketball Stats
"""
from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os
import time
import hmac
import hashlib
import psycopg2
import psycopg2.extras
from decimal import Decimal
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

# ── Auth config ────────────────────────────────────────────────────────────
AUTH_USERNAME = os.getenv('AUTH_USERNAME', '')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', '')
AUTH_SECRET   = os.getenv('AUTH_SECRET', '')
COOKIE_NAME   = 'nilpro_session'

def _make_token():
    """Deterministic token: HMAC of username+password using AUTH_SECRET."""
    msg = f'{AUTH_USERNAME}:{AUTH_PASSWORD}'.encode()
    return hmac.new(AUTH_SECRET.encode(), msg, hashlib.sha256).hexdigest()

def _is_authenticated(request: Request) -> bool:
    if not AUTH_SECRET:
        return True  # auth disabled if secret not configured
    token = request.cookies.get(COOKIE_NAME, '')
    return hmac.compare_digest(token, _make_token())

# ── Auth middleware (registered after app is created, below) ───────────────
_PUBLIC_PATHS = {'/auth/login', '/auth/logout', '/login.html'}

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/ncaa_basketball')
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)

app = FastAPI(
    title="NCAA Basketball Stats API",
    description="API for NCAA D1 Basketball player statistics and ratings",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip compression — compresses large JSON responses ~70%
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Login page HTML ────────────────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NIL PRO — Login</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height:100vh; display:flex; align-items:center; justify-content:center; }
.card { background:white; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.25); padding:40px 36px; width:340px; }
.brand { text-align:center; font-size:28px; font-weight:800; letter-spacing:-0.5px; color:#222; margin-bottom:28px; }
.brand span { color:#667eea; }
label { display:block; font-size:12px; font-weight:600; color:#666; margin-bottom:5px; text-transform:uppercase; letter-spacing:0.4px; }
input[type=text], input[type=password] { width:100%; padding:10px 12px; border:1.5px solid #e0e0e0; border-radius:8px; font-size:14px; outline:none; transition:border-color 0.15s; margin-bottom:16px; }
input:focus { border-color:#667eea; }
button { width:100%; padding:11px; background:linear-gradient(135deg,#667eea,#764ba2); color:white; border:none; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; transition:opacity 0.15s; }
button:hover { opacity:0.9; }
.error { color:#e53e3e; font-size:13px; text-align:center; margin-bottom:14px; }
</style>
</head>
<body>
<div class="card">
  <div class="brand">NIL <span>PRO</span></div>
  <!-- ERROR -->
  <form method="POST" action="/auth/login">
    <label>Username</label>
    <input type="text" name="username" autofocus autocomplete="username">
    <label>Password</label>
    <input type="password" name="password" autocomplete="current-password">
    <button type="submit">Sign In</button>
  </form>
</div>
</body>
</html>"""

@app.get("/login.html", response_class=HTMLResponse)
async def login_page():
    return LOGIN_HTML

# ── Auth middleware + routes ───────────────────────────────────────────────
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Allow public paths through
    if path in _PUBLIC_PATHS or path.startswith('/auth/'):
        return await call_next(request)
    # Allow if authenticated
    if _is_authenticated(request):
        return await call_next(request)
    # API calls get 401, browser navigation gets redirect
    if path.startswith('/api/'):
        return JSONResponse({'detail': 'Not authenticated'}, status_code=401)
    return RedirectResponse('/login.html', status_code=302)

@app.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if not AUTH_SECRET:
        return RedirectResponse('/', status_code=302)
    if username == AUTH_USERNAME and password == AUTH_PASSWORD:
        token = _make_token()
        resp = RedirectResponse('/', status_code=302)
        resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite='lax', max_age=60*60*24*30)
        return resp
    return HTMLResponse(LOGIN_HTML.replace('<!-- ERROR -->', '<p class="error">Invalid username or password.</p>'), status_code=401)

@app.get("/auth/logout")
async def logout():
    resp = RedirectResponse('/login.html', status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp

# Helper function to convert rows to dict, normalizing Decimal/date types inline
def rows_to_dict(rows, result):
    """Convert database rows to list of dicts with JSON-safe types"""
    columns = list(result.keys())
    out = []
    for row in rows:
        d = {}
        for k, v in zip(columns, row):
            if isinstance(v, Decimal):
                d[k] = float(v)
            elif isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
            else:
                d[k] = v
        out.append(d)
    return out


@app.get("/api/ratings/{season}")
def get_ratings(
    season: str,
    position: Optional[str] = None,
    team: Optional[str] = None,
    min_rating: Optional[float] = None,
    two_way: Optional[str] = None,
    limit: int = Query(100, le=15000),
    offset: int = 0
):
    """
    Get player ratings for a season with optional filters

    - **season**: "2024-25" or "2025-26"
    - **position**: Filter by position
    - **team**: Filter by team
    - **min_rating**: Minimum rating threshold
    - **two_way**: "Y" for two-way players only
    - **limit**: Max results (default 100, max 500)
    - **offset**: Pagination offset
    """
    with engine.connect() as conn:
        query = """
            SELECT *
            FROM player_ratings
            WHERE season = :season
        """
        params = {'season': season}

        if position:
            query += " AND position = :position"
            params['position'] = position

        if team:
            query += " AND team = :team"
            params['team'] = team

        if min_rating:
            query += " AND final_rating >= :min_rating"
            params['min_rating'] = min_rating

        if two_way == 'Y':
            query += " AND two_way = 'Y'"

        query += " ORDER BY final_rating DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset

        result = conn.execute(text(query), params)
        rows = result.fetchall()

        data = rows_to_dict(rows, result)

        return {
            "season": season,
            "count": len(data),
            "data": data
        }

@app.get("/api/player/{player_id}")
def get_player(player_id: str):
    """Get complete player information"""
    with engine.connect() as conn:
        # Get player bio
        result = conn.execute(
            text("SELECT * FROM players WHERE player_id = :player_id"),
            {'player_id': player_id}
        )
        player = result.fetchone()

        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        player_dict = dict(zip(result.keys(), player))

        # Get all ratings
        result = conn.execute(
            text("""
                SELECT * FROM player_ratings
                WHERE player_id = :player_id
                ORDER BY season DESC
            """),
            {'player_id': player_id}
        )
        ratings = rows_to_dict(result.fetchall(), result)

        return {"player": player_dict, "ratings": ratings}

@app.get("/api/stats/{player_id}/{season}")
def get_player_stats(player_id: str, season: str):
    """Get all stats for a player in a specific season"""
    with engine.connect() as conn:
        # Per game stats
        result = conn.execute(
            text("""
                SELECT * FROM player_stats_pergame
                WHERE player_id = :player_id AND season = :season
            """),
            {'player_id': player_id, 'season': season}
        )
        pergame = rows_to_dict(result.fetchall(), result)

        # Advanced stats
        result = conn.execute(
            text("""
                SELECT * FROM player_stats_advanced
                WHERE player_id = :player_id AND season = :season
            """),
            {'player_id': player_id, 'season': season}
        )
        advanced = rows_to_dict(result.fetchall(), result)

        # Misc stats
        result = conn.execute(
            text("""
                SELECT * FROM player_stats_misc
                WHERE player_id = :player_id AND season = :season
            """),
            {'player_id': player_id, 'season': season}
        )
        misc = rows_to_dict(result.fetchall(), result)

        # Rating
        result = conn.execute(
            text("""
                SELECT * FROM player_ratings
                WHERE player_id = :player_id AND season = :season
            """),
            {'player_id': player_id, 'season': season}
        )
        rating = rows_to_dict(result.fetchall(), result)

        if not pergame and not rating:
            raise HTTPException(status_code=404, detail="Stats not found for this player/season")

        return {
            "player_id": player_id,
            "season": season,
            "pergame": pergame[0] if pergame else None,
            "advanced": advanced[0] if advanced else None,
            "misc": misc[0] if misc else None,
            "rating": rating[0] if rating else None
        }


@app.get("/api/compare")
def compare_players(
    player1: str,
    player2: str,
    season: str
):
    """Compare two players for a specific season"""
    with engine.connect() as conn:
        query = text("""
            SELECT *
            FROM player_ratings
            WHERE player_id IN (:p1, :p2) AND season = :season
        """)

        result = conn.execute(query, {'p1': player1, 'p2': player2, 'season': season})
        ratings = rows_to_dict(result.fetchall(), result)

        if len(ratings) < 2:
            raise HTTPException(
                status_code=404,
                detail="Could not find both players for this season"
            )

        return {"season": season, "players": ratings}

@app.get("/api/compare-many")
def compare_many_players(
    player_ids: str,
    season: str
):
    """Compare up to 5 players. player_ids is comma-separated list of player_ids."""
    ids = [p.strip() for p in player_ids.split(',') if p.strip()][:5]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 player_ids")

    placeholders = ', '.join(f':p{i}' for i in range(len(ids)))
    params = {'season': season}
    for i, pid in enumerate(ids):
        params[f'p{i}'] = pid

    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                SELECT
                    pss.player_id, pss.full_name, pss.team, pss.position, pss.pos_group,
                    pss.class_year, pss.height, pss.weight, pss.age,
                    pss.gp, pss.min, pss.pts, pss.reb, pss.ast, pss.stl, pss.blk, pss.tov,
                    pss.fg_pct, pss.fg3m, pss.fg3_pct, pss.ft_pct,
                    pss.ts_pct, pss.efg_pct, pss.usg_pct, pss.per, pss.ortg, pss.drtg,
                    pss.ast_to_ratio, pss.win_pct, pss.ws,
                    pss.base_rating, pss.game_adj, pss.final_rating,
                    pss.min_per, pss.pts_per, pss.ast_per, pss.reb_per, pss.blk_per, pss.stl_per,
                    pss.fgpct_per, pss.p3pct_per, pss.ftpct_per,
                    t.conference
                FROM player_season_stats pss
                LEFT JOIN teams t ON pss.team = t.team_name AND pss.season = t.season
                WHERE pss.player_id IN ({placeholders}) AND pss.season = :season
            """),
            params
        )
        players = rows_to_dict(result.fetchall(), result)

    if not players:
        raise HTTPException(status_code=404, detail="No players found for given IDs and season")

    return {"season": season, "count": len(players), "players": players}


@app.get("/api/teams/{season}")
def get_teams(season: str):
    """Get all teams for a season"""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT team_name, conference, wins, losses, total_games
                FROM teams
                WHERE season = :season
                ORDER BY conference, team_name
            """),
            {'season': season}
        )
        teams = rows_to_dict(result.fetchall(), result)

        return {
            "season": season,
            "count": len(teams),
            "teams": teams
        }

ALLOWED_SORT_COLS = {
    'final_rating', 'full_name', 'team', 'position', 'age', 'height_in', 'weight', 'gp',
    'min', 'pts', 'reb', 'ast', 'stl', 'blk', 'tov',
    'fg_pct', 'fg3m', 'fg3a', 'fg3_pct', 'ft_pct', 'fgm', 'fga', 'ftm', 'fta',
    'off_reb', 'def_reb', 'ts_pct', 'efg_pct', 'orb_pct', 'drb_pct',
    'ast_pct', 'tov_pct', 'stl_pct', 'blk_pct', 'usg_pct', 'per', 'ortg', 'drtg',
    'ppr', 'pps', 'dbl_dbl', 'tpl_dbl', 'ast_to_ratio', 'stl_to_ratio', 'win_pct',
    'ws', 'ows', 'dws',
    't_min', 't_pts', 't_reb', 't_ast', 't_stl', 't_blk', 't_tov',
    't_fgm', 't_fga', 't_fg3m', 't_fg3a', 't_ftm', 't_fta',
    'class_year',
}


@app.get("/api/players/{season}")
def get_players(
    season: str,
    request: Request,
    sort_col: str = 'final_rating',
    sort_dir: str = 'desc',
    limit: int = Query(500, le=5000),
    offset: int = 0
):
    """Get wide player stats row from materialized view for a season"""
    if sort_col not in ALLOWED_SORT_COLS:
        sort_col = 'final_rating'
    order_dir = 'DESC' if sort_dir == 'desc' else 'ASC'
    HEIGHT_EXPR = (
        "(CASE WHEN height ~ '^[0-9]+-[0-9]+$' "
        "THEN SPLIT_PART(height,'-',1)::int * 12 + SPLIT_PART(height,'-',2)::int END)"
    )
    order_expr = f"{HEIGHT_EXPR} {order_dir} NULLS LAST" if sort_col == 'height_in' \
        else f"{sort_col} {order_dir} NULLS LAST"

    qp = dict(request.query_params)
    where_clauses = ["pss.season = :season"]
    params: dict = {'season': season, 'limit': limit, 'offset': offset}

    # Full-name search
    if qp.get('search'):
        where_clauses.append("full_name ILIKE :search")
        params['search'] = f"%{qp['search']}%"

    # Position group chips (comma-separated values: Guard, Wing, Big)
    if qp.get('pos_group'):
        groups = [g.strip() for g in qp['pos_group'].split(',') if g.strip()]
        if groups:
            ph = ', '.join(f':pg_{i}' for i in range(len(groups)))
            where_clauses.append(f"pos_group IN ({ph})")
            for i, g in enumerate(groups):
                params[f'pg_{i}'] = g

    # Class year chips (comma-separated)
    if qp.get('class_year'):
        years = [y.strip() for y in qp['class_year'].split(',') if y.strip()]
        if years:
            ph = ', '.join(f':cy_{i}' for i in range(len(years)))
            where_clauses.append(f"class_year IN ({ph})")
            for i, y in enumerate(years):
                params[f'cy_{i}'] = y

    # Team filter (case-insensitive exact match)
    if qp.get('team'):
        where_clauses.append("LOWER(pss.team) = LOWER(:team)")
        params['team'] = qp['team']

    # Conference filter (case-insensitive exact match)
    if qp.get('conference'):
        where_clauses.append("LOWER(t.conference) = LOWER(:conference)")
        params['conference'] = qp['conference']

    # Stat range filters — {col}_min / {col}_max sent as DB-scale values
    for key, val in qp.items():
        for suffix, op in [('_min', '>='), ('_max', '<=')]:
            if not key.endswith(suffix):
                continue
            col = key[:-len(suffix)]
            if col not in ALLOWED_SORT_COLS:
                continue
            try:
                fval = float(val)
            except ValueError:
                continue
            pname = f'f_{key}'
            if col == 'height_in':
                where_clauses.append(f"{HEIGHT_EXPR} {op} :{pname}")
            else:
                where_clauses.append(f"{col} {op} :{pname}")
            params[pname] = fval

    with engine.connect() as conn:
        query = f"""
            SELECT
                pss.player_id, pss.season, pss.full_name, pss.team, pss.position, pss.height, pss.weight,
                pss.hometown, pss.age, pss.pos_group, pss.class_year, pss.two_way,
                pss.gp, pss.min, pss.pts, pss.reb, pss.ast, pss.stl, pss.blk, pss.tov,
                pss.fg_pct, pss.fg3m, pss.fg3a, pss.fg3_pct, pss.ft_pct, pss.fgm, pss.fga, pss.ftm, pss.fta,
                pss.off_reb, pss.def_reb,
                pss.ts_pct, pss.efg_pct, pss.orb_pct, pss.drb_pct, pss.ast_pct, pss.tov_pct,
                pss.stl_pct, pss.blk_pct, pss.usg_pct, pss.per, pss.ortg, pss.drtg, pss.ppr, pss.pps,
                pss.dbl_dbl, pss.tpl_dbl, pss.ast_to_ratio, pss.stl_to_ratio, pss.win_pct,
                pss.ws, pss.ows, pss.dws,
                pss.t_min, pss.t_pts, pss.t_reb, pss.t_ast, pss.t_stl, pss.t_blk, pss.t_tov,
                pss.t_fgm, pss.t_fga, pss.t_fg3m, pss.t_fg3a, pss.t_ftm, pss.t_fta,
                pss.min_per, pss.pts_per, pss.ast_per, pss.reb_per, pss.blk_per, pss.stl_per,
                pss.fgm_per, pss.fgpct_per, pss.p3pct_per, pss.pm3_per, pss.ftpct_per,
                pss.base_rating, pss.game_adj, pss.final_rating,
                pss.min_boost, pss.three_boost, pss.fg_boost, pss.ast_boost, pss.blk_boost,
                pss.double_double_boost, pss.triple_double_boost, pss.free_throw_boost,
                pss.rating_rank,
                t.conference
            FROM player_season_stats pss
            LEFT JOIN teams t ON pss.team = t.team_name AND pss.season = t.season
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_expr}
            LIMIT :limit OFFSET :offset
        """

        count_query = f"""
            SELECT COUNT(*) FROM player_season_stats pss
            LEFT JOIN teams t ON pss.team = t.team_name AND pss.season = t.season
            WHERE {' AND '.join(where_clauses)}
        """
        count_params = {k: v for k, v in params.items() if k not in ('limit', 'offset')}
        total_count = conn.execute(text(count_query), count_params).scalar()

        result = conn.execute(text(query), params)
        data = rows_to_dict(result.fetchall(), result)

        return {"season": season, "total_count": total_count, "count": len(data), "data": data}


@app.get("/api/stats/leaderboard/{season}")
def get_leaderboard(
    season: str,
    stat: str = "pts",
    limit: int = 10
):
    """
    Get top players by stat

    - **season**: "2024-25" or "2025-26"
    - **stat**: Stat column (pts, reb, ast, etc.)
    - **limit**: Number of players
    """
    # Whitelist allowed stat columns for security
    allowed_stats = ['pts', 'trb', 'ast', 'stl', 'blk', 'fg_pct', 'fg3_pct', 'ft_pct', 'min']

    if stat not in allowed_stats:
        raise HTTPException(status_code=400, detail=f"Invalid stat. Allowed: {allowed_stats}")

    with engine.connect() as conn:
        query = f"""
            SELECT
                p.player_id,
                p.full_name,
                pg.team,
                pg.{stat},
                pg.gp,
                pr.final_rating
            FROM player_stats_pergame pg
            JOIN players p ON pg.player_id = p.player_id
            LEFT JOIN player_ratings pr ON pg.player_id = pr.player_id AND pg.season = pr.season
            WHERE pg.season = :season
              AND pg.gp >= 10
            ORDER BY pg.{stat} DESC
            LIMIT :limit
        """

        result = conn.execute(text(query), {'season': season, 'limit': limit})
        leaders = rows_to_dict(result.fetchall(), result)

        return {"season": season, "stat": stat, "leaders": leaders}

@app.get("/api/similarity/{player_id}/{season}")
def get_similarity(player_id: str, season: str):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT segment, rank, sim_player_id, sim_season, sim_name, sim_team, sim_pos,
                   sim_rating::float, score::float
            FROM player_similarity
            WHERE player_id = %s AND season = %s
            ORDER BY segment, rank
        """, (player_id, season))
        rows = cur.fetchall()
        segments = {}
        for r in rows:
            r = dict(r)
            segments.setdefault(r['segment'], []).append(r)
        return {'player_id': player_id, 'season': season, 'segments': segments}
    finally:
        conn.close()


@app.get("/api/profile/{player_id}")
def get_profile(player_id: str):
    """Full player profile: bio + all seasons of stats + similarity"""
    with engine.connect() as conn:
        # Bio
        result = conn.execute(
            text("SELECT * FROM players WHERE player_id = :pid"),
            {'pid': player_id}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Player not found")
        bio = dict(zip(result.keys(), row))

        # All seasons from each table
        def fetch_all(table):
            r = conn.execute(
                text(f"SELECT * FROM {table} WHERE player_id = :pid ORDER BY season"),
                {'pid': player_id}
            )
            return {row['season']: dict(row) for row in [dict(zip(r.keys(), row)) for row in r.fetchall()]}

        pergame  = fetch_all('player_stats_pergame')
        advanced = fetch_all('player_stats_advanced')
        misc     = fetch_all('player_stats_misc')

        r = conn.execute(
            text("SELECT * FROM player_ratings WHERE player_id = :pid ORDER BY season"),
            {'pid': player_id}
        )
        ratings = rows_to_dict(r.fetchall(), r)
        ratings = {row['season']: row for row in ratings}

        # Totals from materialized view
        r = conn.execute(
            text("""SELECT season, t_min, t_pts, t_reb, t_ast, t_stl, t_blk, t_tov,
                           t_fgm, t_fga, t_fg3m, t_fg3a, t_ftm, t_fta
                    FROM player_season_stats WHERE player_id = :pid ORDER BY season"""),
            {'pid': player_id}
        )
        totals = {row['season']: dict(row) for row in [dict(zip(r.keys(), row)) for row in r.fetchall()]}

        # Merge into season list
        all_seasons = sorted(set(list(pergame) + list(ratings)))
        seasons = []
        for s in all_seasons:
            seasons.append({
                'season':   s,
                'pergame':  pergame.get(s),
                'advanced': advanced.get(s),
                'misc':     misc.get(s),
                'totals':   totals.get(s),
                'rating':   ratings.get(s),
            })

        # Similarity (2025-26 only) — use fresh psycopg2 connection to bypass stale pool
        sim_conn = psycopg2.connect(DATABASE_URL)
        try:
            sim_cur = sim_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            sim_cur.execute("""
                SELECT segment, rank, sim_player_id, sim_season, sim_name, sim_team, sim_pos,
                       sim_rating::float, score::float
                FROM player_similarity
                WHERE player_id = %s AND season = '2025-26'
                ORDER BY segment, rank
            """, (player_id,))
            sim_rows = [dict(r) for r in sim_cur.fetchall()]
        finally:
            sim_conn.close()
        similarity = {}
        for row in sim_rows:
            similarity.setdefault(row['segment'], []).append(row)

        return {'bio': bio, 'seasons': seasons, 'similarity': similarity}


@app.get("/api/hometown-coords")
def get_hometown_coords():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT hometown, lat, lng FROM hometown_coords
            WHERE lat IS NOT NULL AND lng IS NOT NULL
        """))
        rows = rows_to_dict(result.fetchall(), result)
        return {'coords': rows}


@app.get("/api/search")
def search_players(q: str = '', limit: int = 10):
    if not q or len(q) < 2:
        return {'results': []}
    with engine.connect() as conn:
        # Return one row per player (most recent season), ordered by name match quality
        result = conn.execute(text("""
            SELECT DISTINCT ON (player_id)
                player_id, full_name, team, position, season
            FROM player_season_stats
            WHERE full_name ILIKE :q
            ORDER BY player_id, season DESC
            LIMIT :limit
        """), {'q': f'%{q}%', 'limit': limit})
        rows = rows_to_dict(result.fetchall(), result)
        rows.sort(key=lambda r: r['full_name'].lower())
        return {'results': rows}


@app.get("/api/player-count/{season}")
def get_player_count(season: str):
    """Total number of players for a season — used to fix pagination totals."""
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM player_season_stats WHERE season = :season"),
            {'season': season}
        ).scalar()
        return {'season': season, 'count': int(count)}


@app.get("/api/stat-ranges/{season}")
def get_stat_ranges(season: str):
    """Return min/max for every slider stat across the full season — one query."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                MIN(final_rating) AS final_rating_min, MAX(final_rating) AS final_rating_max,
                MIN(gp)           AS gp_min,           MAX(gp)           AS gp_max,
                MIN(age)          AS age_min,           MAX(age)          AS age_max,
                MIN(weight)       AS weight_min,        MAX(weight)       AS weight_max,
                MIN(CASE WHEN height ~ '^[0-9]+-[0-9]+$'
                    THEN SPLIT_PART(height,'-',1)::int * 12 + SPLIT_PART(height,'-',2)::int
                    END)          AS height_in_min,
                MAX(CASE WHEN height ~ '^[0-9]+-[0-9]+$'
                    THEN SPLIT_PART(height,'-',1)::int * 12 + SPLIT_PART(height,'-',2)::int
                    END)          AS height_in_max,
                MIN(pts)          AS pts_min,           MAX(pts)          AS pts_max,
                MIN("min")        AS min_min,           MAX("min")        AS min_max,
                MIN(fgm)          AS fgm_min,           MAX(fgm)          AS fgm_max,
                MIN(fga)          AS fga_min,           MAX(fga)          AS fga_max,
                MIN(fg_pct)       AS fg_pct_min,        MAX(fg_pct)       AS fg_pct_max,
                MIN(fg3m)         AS fg3m_min,          MAX(fg3m)         AS fg3m_max,
                MIN(fg3a)         AS fg3a_min,          MAX(fg3a)         AS fg3a_max,
                MIN(fg3_pct)      AS fg3_pct_min,       MAX(fg3_pct)      AS fg3_pct_max,
                MIN(ftm)          AS ftm_min,           MAX(ftm)          AS ftm_max,
                MIN(fta)          AS fta_min,           MAX(fta)          AS fta_max,
                MIN(ft_pct)       AS ft_pct_min,        MAX(ft_pct)       AS ft_pct_max,
                MIN(efg_pct)      AS efg_pct_min,       MAX(efg_pct)      AS efg_pct_max,
                MIN(ts_pct)       AS ts_pct_min,        MAX(ts_pct)       AS ts_pct_max,
                MIN(ast)          AS ast_min,           MAX(ast)          AS ast_max,
                MIN(tov)          AS tov_min,           MAX(tov)          AS tov_max,
                MIN(ast_pct)      AS ast_pct_min,       MAX(ast_pct)      AS ast_pct_max,
                MIN(tov_pct)      AS tov_pct_min,       MAX(tov_pct)      AS tov_pct_max,
                MIN(ast_to_ratio) AS ast_to_ratio_min,  MAX(ast_to_ratio) AS ast_to_ratio_max,
                MIN(ppr)          AS ppr_min,           MAX(ppr)          AS ppr_max,
                MIN(reb)          AS reb_min,           MAX(reb)          AS reb_max,
                MIN(off_reb)      AS off_reb_min,       MAX(off_reb)      AS off_reb_max,
                MIN(def_reb)      AS def_reb_min,       MAX(def_reb)      AS def_reb_max,
                MIN(orb_pct)      AS orb_pct_min,       MAX(orb_pct)      AS orb_pct_max,
                MIN(drb_pct)      AS drb_pct_min,       MAX(drb_pct)      AS drb_pct_max,
                MIN(stl)          AS stl_min,           MAX(stl)          AS stl_max,
                MIN(blk)          AS blk_min,           MAX(blk)          AS blk_max,
                MIN(stl_pct)      AS stl_pct_min,       MAX(stl_pct)      AS stl_pct_max,
                MIN(blk_pct)      AS blk_pct_min,       MAX(blk_pct)      AS blk_pct_max,
                MIN(drtg)         AS drtg_min,          MAX(drtg)         AS drtg_max,
                MIN(per)          AS per_min,           MAX(per)          AS per_max,
                MIN(usg_pct)      AS usg_pct_min,       MAX(usg_pct)      AS usg_pct_max,
                MIN(ortg)         AS ortg_min,          MAX(ortg)         AS ortg_max,
                MIN(pps)          AS pps_min,           MAX(pps)          AS pps_max,
                MIN(ws)           AS ws_min,            MAX(ws)           AS ws_max,
                MIN(ows)          AS ows_min,           MAX(ows)          AS ows_max,
                MIN(dws)          AS dws_min,           MAX(dws)          AS dws_max,
                MIN(win_pct)      AS win_pct_min,       MAX(win_pct)      AS win_pct_max,
                MIN(dbl_dbl)      AS dbl_dbl_min,       MAX(dbl_dbl)      AS dbl_dbl_max,
                MIN(tpl_dbl)      AS tpl_dbl_min,       MAX(tpl_dbl)      AS tpl_dbl_max,
                MIN(stl_to_ratio) AS stl_to_ratio_min,  MAX(stl_to_ratio) AS stl_to_ratio_max,
                MIN(t_pts)        AS t_pts_min,         MAX(t_pts)        AS t_pts_max,
                MIN(t_min)        AS t_min_min,         MAX(t_min)        AS t_min_max,
                MIN(t_fgm)        AS t_fgm_min,         MAX(t_fgm)        AS t_fgm_max,
                MIN(t_fga)        AS t_fga_min,         MAX(t_fga)        AS t_fga_max,
                MIN(t_fg3m)       AS t_fg3m_min,        MAX(t_fg3m)       AS t_fg3m_max,
                MIN(t_fg3a)       AS t_fg3a_min,        MAX(t_fg3a)       AS t_fg3a_max,
                MIN(t_ftm)        AS t_ftm_min,         MAX(t_ftm)        AS t_ftm_max,
                MIN(t_fta)        AS t_fta_min,         MAX(t_fta)        AS t_fta_max,
                MIN(t_ast)        AS t_ast_min,         MAX(t_ast)        AS t_ast_max,
                MIN(t_tov)        AS t_tov_min,         MAX(t_tov)        AS t_tov_max,
                MIN(t_reb)        AS t_reb_min,         MAX(t_reb)        AS t_reb_max,
                MIN(t_stl)        AS t_stl_min,         MAX(t_stl)        AS t_stl_max,
                MIN(t_blk)        AS t_blk_min,         MAX(t_blk)        AS t_blk_max
            FROM player_season_stats
            WHERE season = :season
        """), {'season': season})

        row = result.fetchone()
        if not row:
            return {'season': season, 'ranges': {}}

        cols = list(result.keys())
        flat = {}
        for k, v in zip(cols, row):
            flat[k] = float(v) if isinstance(v, Decimal) else v

        ranges = {}
        for col in cols:
            if col.endswith('_min'):
                key = col[:-4]
                ranges[key] = {'min': flat.get(f'{key}_min'), 'max': flat.get(f'{key}_max')}

        return {'season': season, 'ranges': ranges}


# Serve frontend — must be mounted last so /api routes take priority
import os as _os
_static_dir = _os.path.dirname(__file__)
if _os.path.exists(_os.path.join(_static_dir, "index.html")):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
