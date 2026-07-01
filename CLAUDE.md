# NIL PRO — Project Overview

NIL PRO is a college basketball player evaluation tool backed by scraped RealGM data. It lets users browse, filter, and compare NCAA D1 players by statistics to make informed NIL/recruiting decisions.

## Stack

- **Backend**: FastAPI (`backend/main.py`) served on port 8000, PostgreSQL (Neon cloud) via SQLAlchemy
- **Frontend**: Vanilla JS single-page app served as static files by FastAPI (`backend/index.html`, `backend/similarity.html`, `backend/player.html`)
- **Scraper**: Python scripts in repo root that scrape RealGM, parse HTML, and write to DB
- **MCP Server**: `mcp/nil_pro_mcp/server.py` — exposes NIL PRO data to Claude via MCP protocol

## Key DB Tables / Views

- `player_season_stats` — materialized wide-row view used by the main rankings page (`/api/players/{season}`)
- `player_ratings` — pre-computed composite ratings with percentile breakdowns and boost components
- `player_stats_pergame`, `player_stats_advanced`, `player_stats_misc` — raw stat tables
- `players` — bio data (height, weight, hometown, etc.)
- `player_similarity` — pre-computed cosine-similarity scores by segment
- `hometown_coords` — geocoded lat/lng for map view
- `teams` — conference standings (wins/losses)

## Main Page Data Flow (index.html)

1. Fetches all players for selected season via `GET /api/players/{season}?limit=15000`
2. All filtering (sliders, position chips, class year, search) is done client-side in JS
3. `player_season_stats` view returns every column needed — no additional fetches required

## Rating System

`final_rating` = `base_rating` (percentile-weighted stat score) + `game_adj` + individual boosts (minutes, 3P, FG, AST, BLK, double-double, triple-double, FT). Each component is stored as its own column so the "Rating Breakdown" section in the player modal can show the decomposition.

## Pages

- `/index.html` — Rankings table with sidebar filters (sliders per stat, position/class chips), per-game↔totals toggle, map view
- `/similarity.html` — Find players similar to a given player; uses `player_similarity` table
- `/player.html` — Full player profile page (bio, all seasons, advanced stats, similarity)

## Environment

- `backend/.env` — contains `DATABASE_URL` (Neon connection string) and auth config
- MCP server defaults to `http://localhost:8000` when `NIL_PRO_API_URL` is not set
