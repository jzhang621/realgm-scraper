"""
Migrate CSV data to PostgreSQL database
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text
import os
from datetime import datetime

# Database connection string
# Format: postgresql://username:password@host:port/database
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/ncaa_basketball')

print(f"Connecting to database...")
engine = create_engine(DATABASE_URL)

def clean_df(df):
    """Replace empty strings and 'nan' with None for proper NULL handling"""
    df = df.replace('', None)
    df = df.replace('nan', None)
    df = df.where(pd.notnull(df), None)
    return df

def migrate_players():
    """Migrate players.csv"""
    print("\n" + "="*70)
    print("Migrating players...")
    print("="*70)

    df = pd.read_csv('../data/processed/players.csv')
    df = clean_df(df)

    # Keep only required columns
    columns = ['player_id', 'full_name', 'position', 'height_ft', 'weight_lbs', 'hometown', 'birthdate']
    df = df[[col for col in columns if col in df.columns]]

    # Convert birthdate to proper format if it exists
    if 'birthdate' in df.columns:
        df['birthdate'] = pd.to_datetime(df['birthdate'], errors='coerce')

    # Remove duplicates (keep first occurrence)
    original_count = len(df)
    df = df.drop_duplicates(subset=['player_id'], keep='first')
    duplicates_removed = original_count - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate player records")

    # Load to database (append since schema already exists)
    df.to_sql('players', engine, if_exists='append', index=False, method='multi', chunksize=1000)

    print(f"✓ Loaded {len(df)} unique players")

def migrate_teams():
    """Migrate team_games_*.csv"""
    print("\n" + "="*70)
    print("Migrating teams...")
    print("="*70)

    # Load both seasons
    teams = []

    for season, file in [('2024-25', '../data/processed/team_games_2025.csv'),
                         ('2025-26', '../data/processed/team_games_2026.csv')]:
        if os.path.exists(file):
            df = pd.read_csv(file)
            df['season'] = season
            teams.append(df)
            print(f"  Loaded {len(df)} teams from {season}")

    if teams:
        df_all = pd.concat(teams, ignore_index=True)
        df_all = clean_df(df_all)

        # Rename 'team' column to 'team_name' if needed
        if 'team' in df_all.columns:
            df_all = df_all.rename(columns={'team': 'team_name'})

        df_all.to_sql('teams', engine, if_exists='append', index=False, method='multi', chunksize=1000)
        print(f"✓ Loaded {len(df_all)} team records total")

def migrate_stats_pergame():
    """Migrate player_stats_pergame.csv"""
    print("\n" + "="*70)
    print("Migrating per-game stats...")
    print("="*70)

    df = pd.read_csv('../data/processed/player_stats_pergame.csv')
    df = clean_df(df)

    # Filter for D1 only (seasons 2024-25 and 2025-26)
    df = df[df['season'].isin(['2024-25', '2025-26'])]

    print(f"  Total records: {len(df)}")
    print(f"  Seasons: {df['season'].unique()}")

    # Remove duplicates based on unique constraint
    original_count = len(df)
    df = df.drop_duplicates(subset=['player_id', 'season', 'team', 'stat_type'], keep='first')
    duplicates_removed = original_count - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate records")

    df.to_sql('player_stats_pergame', engine, if_exists='append', index=False, method='multi', chunksize=1000)

    print(f"✓ Loaded {len(df)} per-game stat records")

def migrate_stats_advanced():
    """Migrate player_stats_advanced.csv"""
    print("\n" + "="*70)
    print("Migrating advanced stats...")
    print("="*70)

    df = pd.read_csv('../data/processed/player_stats_advanced.csv')
    df = clean_df(df)

    # Filter for D1 only
    df = df[df['season'].isin(['2024-25', '2025-26'])]

    print(f"  Total records: {len(df)}")

    # Remove duplicates
    original_count = len(df)
    df = df.drop_duplicates(subset=['player_id', 'season', 'team', 'stat_type'], keep='first')
    duplicates_removed = original_count - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate records")

    df.to_sql('player_stats_advanced', engine, if_exists='append', index=False, method='multi', chunksize=1000)

    print(f"✓ Loaded {len(df)} advanced stat records")

def migrate_stats_misc():
    """Migrate player_stats_misc.csv"""
    print("\n" + "="*70)
    print("Migrating misc stats...")
    print("="*70)

    df = pd.read_csv('../data/processed/player_stats_misc.csv')
    df = clean_df(df)

    # Filter for D1 only
    df = df[df['season'].isin(['2024-25', '2025-26'])]

    print(f"  Total records: {len(df)}")

    # Remove duplicates
    original_count = len(df)
    df = df.drop_duplicates(subset=['player_id', 'season', 'team', 'stat_type'], keep='first')
    duplicates_removed = original_count - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate records")

    df.to_sql('player_stats_misc', engine, if_exists='append', index=False, method='multi', chunksize=1000)

    print(f"✓ Loaded {len(df)} misc stat records")

def migrate_ratings():
    """Migrate player_ratings_*.csv"""
    print("\n" + "="*70)
    print("Migrating player ratings...")
    print("="*70)

    ratings = []

    for season, file in [('2024-25', '../data/processed/player_ratings_2025.csv'),
                         ('2025-26', '../data/processed/player_ratings_2026.csv')]:
        if os.path.exists(file):
            df = pd.read_csv(file)

            # Add season column if not present
            if 'season' not in df.columns:
                df['season'] = season

            ratings.append(df)
            print(f"  Loaded {len(df)} ratings from {season}")

    if ratings:
        df_all = pd.concat(ratings, ignore_index=True)
        df_all = clean_df(df_all)

        # Rename columns to match database schema
        column_mapping = {
            'MIN_PER': 'min_per',
            'PTS_PER': 'pts_per',
            'PM3_PER': 'pm3_per',
            'P3PCT_PER': 'p3pct_per',
            'FGM_PER': 'fgm_per',
            'FGPCT_PER': 'fgpct_per',
            'FTPCT_PER': 'ftpct_per',
            'AST_PER': 'ast_per',
            'REB_PER': 'reb_per',
            'BLK_PER': 'blk_per',
            'STL_PER': 'stl_per'
        }
        df_all = df_all.rename(columns=column_mapping)

        df_all.to_sql('player_ratings', engine, if_exists='append', index=False, method='multi', chunksize=1000)
        print(f"✓ Loaded {len(df_all)} rating records total")

def verify_migration():
    """Verify the migration by checking record counts"""
    print("\n" + "="*70)
    print("Verifying migration...")
    print("="*70)

    with engine.connect() as conn:
        tables = ['players', 'teams', 'player_stats_pergame',
                  'player_stats_advanced', 'player_stats_misc', 'player_ratings']

        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"  {table}: {count:,} records")

        # Check seasons in ratings
        result = conn.execute(text("SELECT season, COUNT(*) FROM player_ratings GROUP BY season ORDER BY season"))
        print(f"\n  Ratings by season:")
        for row in result:
            print(f"    {row[0]}: {row[1]:,} players")

        # Top 5 rated players per season
        print(f"\n  Top 5 players by season:")
        result = conn.execute(text("""
            SELECT season, full_name, team, final_rating
            FROM player_ratings
            WHERE season IN ('2024-25', '2025-26')
            ORDER BY season, final_rating DESC
            LIMIT 10
        """))
        current_season = None
        for row in result:
            if row[0] != current_season:
                current_season = row[0]
                print(f"\n    {current_season}:")
            print(f"      {row[1]:<30} {row[2]:<20} {row[3]:.2f}")

if __name__ == '__main__':
    start_time = datetime.now()

    print("NCAA Basketball Stats Migration")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DATABASE_URL}\n")

    try:
        # Run migrations in order
        migrate_players()
        migrate_teams()
        migrate_stats_pergame()
        migrate_stats_advanced()
        migrate_stats_misc()
        migrate_ratings()

        # Verify
        verify_migration()

        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "="*70)
        print(f"✓ Migration completed successfully!")
        print(f"  Duration: {duration.total_seconds():.2f} seconds")
        print("="*70)

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
