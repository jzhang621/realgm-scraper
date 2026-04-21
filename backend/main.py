"""
FastAPI Backend for NCAA Basketball Stats
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os
from decimal import Decimal
from datetime import datetime, date
import json

# Custom JSON encoder for Decimal and datetime
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

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

# Helper function to convert rows to dict
def rows_to_dict(rows, result):
    """Convert database rows to list of dicts"""
    columns = result.keys()
    return [dict(zip(columns, row)) for row in rows]


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

        # Convert Decimals to floats
        data = json.loads(json.dumps(data, cls=DecimalEncoder))

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

        return json.loads(json.dumps({
            "player": player_dict,
            "ratings": ratings
        }, cls=DecimalEncoder))

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

        return json.loads(json.dumps({
            "player_id": player_id,
            "season": season,
            "pergame": pergame[0] if pergame else None,
            "advanced": advanced[0] if advanced else None,
            "misc": misc[0] if misc else None,
            "rating": rating[0] if rating else None
        }, cls=DecimalEncoder))

@app.get("/api/search")
def search_players(
    q: str = Query(..., min_length=2),
    season: Optional[str] = None,
    limit: int = 20
):
    """
    Search players by name

    - **q**: Search query (min 2 characters)
    - **season**: Optional season filter
    - **limit**: Max results (default 20)
    """
    with engine.connect() as conn:
        if season:
            query = """
                SELECT DISTINCT
                    p.player_id,
                    p.full_name,
                    pr.team,
                    pr.position,
                    pr.final_rating
                FROM players p
                JOIN player_ratings pr ON p.player_id = pr.player_id
                WHERE LOWER(p.full_name) LIKE LOWER(:query)
                  AND pr.season = :season
                ORDER BY pr.final_rating DESC
                LIMIT :limit
            """
            params = {'query': f'%{q}%', 'season': season, 'limit': limit}
        else:
            query = """
                SELECT player_id, full_name, position
                FROM players
                WHERE LOWER(full_name) LIKE LOWER(:query)
                LIMIT :limit
            """
            params = {'query': f'%{q}%', 'limit': limit}

        result = conn.execute(text(query), params)
        rows = result.fetchall()

        data = rows_to_dict(rows, result)

        return json.loads(json.dumps({
            "query": q,
            "count": len(data),
            "results": data
        }, cls=DecimalEncoder))

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

        return json.loads(json.dumps({
            "season": season,
            "players": ratings
        }, cls=DecimalEncoder))

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

@app.get("/api/players/{season}")
def get_players(
    season: str,
    position: Optional[str] = None,
    team: Optional[str] = None,
    min_rating: Optional[float] = None,
    two_way: Optional[str] = None,
    limit: int = Query(15000, le=15000),
    offset: int = 0
):
    """Get wide player stats row from materialized view for a season"""
    with engine.connect() as conn:
        query = """
            SELECT *
            FROM player_season_stats
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
        data = json.loads(json.dumps(data, cls=DecimalEncoder))

        return {"season": season, "count": len(data), "data": data}


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

        return json.loads(json.dumps({
            "season": season,
            "stat": stat,
            "leaders": leaders
        }, cls=DecimalEncoder))

@app.get("/api/similarity/{player_id}/{season}")
def get_similarity(player_id: str, season: str):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT segment, rank, sim_player_id, sim_season, sim_name, sim_team, sim_pos, sim_rating, score
            FROM player_similarity
            WHERE player_id = :player_id AND season = :season
            ORDER BY segment, rank
        """), {'player_id': player_id, 'season': season})
        rows = rows_to_dict(result.fetchall(), result)
        rows = json.loads(json.dumps(rows, cls=DecimalEncoder))

        segments = {}
        for r in rows:
            segments.setdefault(r['segment'], []).append(r)

        return {'player_id': player_id, 'season': season, 'segments': segments}


@app.get("/api/hometown-coords")
def get_hometown_coords():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT hometown, lat, lng FROM hometown_coords
            WHERE lat IS NOT NULL AND lng IS NOT NULL
        """))
        rows = rows_to_dict(result.fetchall(), result)
        return json.loads(json.dumps({'coords': rows}, cls=DecimalEncoder))


@app.get("/api/search")
def search_players(q: str = '', limit: int = 10):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT player_id, full_name
            FROM player_similarity
            WHERE full_name ILIKE :q OR player_id = :pid
            LIMIT :limit
        """), {'q': f'%{q}%', 'pid': q, 'limit': limit})
        rows = rows_to_dict(result.fetchall(), result)

        # Also search by name in player_season_stats for 2025-26 top 100
        result2 = conn.execute(text("""
            SELECT DISTINCT player_id, full_name
            FROM player_season_stats
            WHERE full_name ILIKE :q AND season = '2025-26'
            ORDER BY full_name
            LIMIT :limit
        """), {'q': f'%{q}%', 'limit': limit})
        rows2 = rows_to_dict(result2.fetchall(), result2)

        # Merge, deduplicate
        seen = set()
        merged = []
        for r in list(rows) + list(rows2):
            if r['player_id'] not in seen:
                seen.add(r['player_id'])
                merged.append(r)

        return {'results': merged[:limit]}


# Serve frontend — must be mounted last so /api routes take priority
import os as _os
_static_dir = _os.path.dirname(__file__)
if _os.path.exists(_os.path.join(_static_dir, "index.html")):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
