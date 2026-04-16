"""Load player ratings from CSV into PostgreSQL database"""
import pandas as pd
from sqlalchemy import create_engine

# Read CSV
df = pd.read_csv('data/processed/player_ratings_2026.csv')

# Lowercase all column names to match database schema
df.columns = df.columns.str.lower()

# Remove duplicates (keep first occurrence)
original_count = len(df)
df = df.drop_duplicates(subset=['player_id'], keep='first')
if len(df) < original_count:
    print(f"Removed {original_count - len(df)} duplicate player_ids")

# Add season column
df['season'] = '2025-26'

# Connect to database
engine = create_engine('postgresql://localhost:5432/ncaa_basketball')

# Load to database
print(f"Loading {len(df)} player ratings to database...")
df.to_sql('player_ratings', engine, if_exists='append', index=False, method='multi', chunksize=1000)

print(f"✓ Successfully loaded {len(df)} ratings")

# Verify
with engine.connect() as conn:
    result = conn.execute("SELECT COUNT(*) FROM player_ratings WHERE season = '2025-26'")
    count = result.scalar()
    print(f"✓ Verified: {count} ratings in database for 2025-26")

print("\nDone!")
