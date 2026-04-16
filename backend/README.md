# NCAA Basketball Stats API

FastAPI backend for NCAA D1 Basketball statistics and player ratings.

## Features

- Player ratings with filtering (position, team, rating threshold)
- Complete player stats (per-game, advanced, misc)
- Player search and comparison
- Team information
- Statistical leaderboards

## Setup

### Local Development

1. **Install PostgreSQL** (if not already installed):
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

2. **Create database**:
```bash
createdb ncaa_basketball
```

3. **Install Python dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

4. **Set environment variable**:
```bash
export DATABASE_URL="postgresql://localhost:5432/ncaa_basketball"
```

5. **Create schema**:
```bash
psql ncaa_basketball < schema.sql
```

6. **Migrate data**:
```bash
cd backend
python migrate_data.py
```

7. **Run the API**:
```bash
uvicorn main:app --reload
```

API will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

## API Endpoints

### Get Player Ratings
```
GET /api/ratings/{season}?position=&team=&min_rating=&two_way=&limit=&offset=
```

Example:
```bash
curl "http://localhost:8000/api/ratings/2025-26?limit=10"
```

### Get Player Info
```
GET /api/player/{player_id}
```

### Get Player Stats
```
GET /api/stats/{player_id}/{season}
```

### Search Players
```
GET /api/search?q=cooper&season=2025-26
```

### Compare Players
```
GET /api/compare?player1=123&player2=456&season=2025-26
```

### Get Teams
```
GET /api/teams/{season}
```

### Leaderboard
```
GET /api/stats/leaderboard/{season}?stat=pts&limit=10
```

## Deployment

### Option 1: Railway.app (Recommended - Easy & Affordable)

1. **Sign up** at [railway.app](https://railway.app)

2. **Create new project** → PostgreSQL database

3. **Copy DATABASE_URL** from PostgreSQL service

4. **Add Web Service**:
   - Connect GitHub repo or use CLI
   - Set environment variable: `DATABASE_URL` = (from step 3)
   - Build command: `pip install -r backend/requirements.txt`
   - Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

5. **Run migrations** (one-time):
   - In Railway console, run:
     ```bash
     cd backend && psql $DATABASE_URL < schema.sql
     cd backend && python migrate_data.py
     ```

**Cost**: ~$5/month (includes PostgreSQL + web service)

### Option 2: Render.com (FREE tier available)

1. **Sign up** at [render.com](https://render.com)

2. **Create PostgreSQL database**:
   - New → PostgreSQL
   - Free tier available
   - Copy Internal Database URL

3. **Create Web Service**:
   - New → Web Service
   - Connect GitHub repo
   - Environment: Python 3
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add Environment Variable:
     - `DATABASE_URL` = (Internal Database URL from step 2)

4. **Run migrations**:
   - Use Render Shell or connect locally:
     ```bash
     psql <DATABASE_URL> < backend/schema.sql
     python backend/migrate_data.py
     ```

**Cost**: FREE tier available (database sleeps after inactivity)

### Option 3: DigitalOcean App Platform

1. **Create App**:
   - App Platform → Create App → GitHub repo

2. **Add PostgreSQL database**:
   - Components → Database → PostgreSQL
   - Auto-creates `${db.DATABASE_URL}`

3. **Configure Web Service**:
   - Build Command: `pip install -r backend/requirements.txt`
   - Run Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8080`
   - HTTP Port: 8080
   - Environment Variable:
     - `DATABASE_URL` = `${db.DATABASE_URL}`

4. **Run migrations** (SSH into container or use connection string)

**Cost**: ~$12/month (includes PostgreSQL + web service)

## Database Schema

- **players**: Player bio information
- **teams**: Team records by season
- **player_stats_pergame**: Per-game statistics
- **player_stats_advanced**: Advanced metrics (PER, TS%, etc.)
- **player_stats_misc**: Miscellaneous stats (double-doubles, win shares, etc.)
- **player_ratings**: Calculated player ratings with percentiles

See `schema.sql` for complete schema.

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required)
  - Format: `postgresql://user:password@host:port/database`

## Tech Stack

- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Relational database
- **SQLAlchemy**: Database ORM
- **Uvicorn**: ASGI server
- **Pandas**: Data migration

## Performance

- Indexed queries for fast lookups
- Connection pooling for efficiency
- Pagination support for large result sets
- Typical response times: <100ms

## Future Enhancements

- [ ] Caching layer (Redis)
- [ ] GraphQL API
- [ ] Real-time updates
- [ ] User authentication
- [ ] Favorite players/teams
- [ ] Historical trends
- [ ] Advanced analytics
